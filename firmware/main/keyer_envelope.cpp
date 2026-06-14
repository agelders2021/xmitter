// =============================================================================
//  keyer_envelope.cpp
//
//  ESP-IDF native port of the original Arduino-framework draft at
//  Arduino_code/cw_envelope_keyer.cpp.  Behaviour is unchanged — the design
//  notes that file ships with still apply.  Key differences from the draft:
//
//    - SPI: Arduino SPIClass  ->  esp_driver_spi  spi_device_handle_t (CS
//          driven manually so the playout task owns the line timing).
//    - GPIO: Arduino digitalWrite / pinMode  ->  driver/gpio.h.
//    - Task creation: xTaskCreatePinnedToCore comes from FreeRTOS directly.
//    - Pin numbers: live in pin_map.h, not here.
//
//  Design decisions called out in cw_envelope_keyer.md MUST be preserved:
//    1) Single chasing `phase`, not RISING/FALLING state machine.
//    2) Busy-wait inside the task, NOT in an ISR.
//    3) DAC on its own SPI bus, never shares the monitoring I2C bus.
//    4) Pre-distortion hook linearizes the MC1496 control curve.
// =============================================================================
#include "keyer_envelope.h"

#include <cmath>
#include <cstdint>
#include <atomic>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_check.h"

#include "pin_map.h"

namespace keyer {

namespace {

constexpr char TAG[] = "envelope";

// ---- Playout timing --------------------------------------------------------
constexpr int64_t TICK_US  = 25;     // 40 kHz sample clock
constexpr int     LUT_SIZE = 256;    // master raised-cosine table

// ---- Edge-time vs. speed ---------------------------------------------------
//  edge_ms is the FULL phase 0->1 duration.  Perceptual 10–90 % rise is
//  ~0.6 × that for a raised cosine: 5 ms full ≈ 3 ms 10–90.
constexpr float EDGE_FRACTION = 0.15f;
constexpr float EDGE_MAX_MS   = 5.0f;
constexpr float EDGE_MIN_MS   = 2.0f;

// ---- DAC code endpoints (set from MC1496 bring-up) -------------------------
constexpr uint16_t CODE_NULL = 0x000;
constexpr uint16_t CODE_FULL = 0xFFF;

// MCP4921 command word: ch A, buffered Vref, gain = 1×, output active
constexpr uint16_t DAC_CMD   = 0x3000;

// ---- Shared state (written from WinKey side, read by playout) --------------
std::atomic<bool>  s_key_down  { false };
std::atomic<float> s_phase_inc { 0.0f };
TaskHandle_t       s_playout_handle = nullptr;

// SPI handle to the MCP4921.  Created in envelope_init().
spi_device_handle_t s_dac_dev = nullptr;

// ---- Tables ----------------------------------------------------------------
float s_rc_lut[LUT_SIZE];

void build_rc_lut() {
    for (int i = 0; i < LUT_SIZE; ++i) {
        float x = (float)i / (float)(LUT_SIZE - 1);
        s_rc_lut[i] = 0.5f * (1.0f - std::cos((float)M_PI * x));
    }
}

inline float sample_lut(float phase) {
    if (phase <= 0.0f) return s_rc_lut[0];
    if (phase >= 1.0f) return s_rc_lut[LUT_SIZE - 1];
    float fi = phase * (float)(LUT_SIZE - 1);
    int   i  = (int)fi;
    float f  = fi - (float)i;
    return s_rc_lut[i] + f * (s_rc_lut[i + 1] - s_rc_lut[i]);
}

// ---- Pre-distortion --------------------------------------------------------
//  Identity map for first bring-up.  After MC1496 is on the bench, sweep
//  DAC code → measured RF envelope, invert, and fill a table here.
constexpr bool USE_CAL_TABLE = false;

inline uint16_t predistort(float env_norm) {
    if (env_norm < 0.0f) env_norm = 0.0f;
    if (env_norm > 1.0f) env_norm = 1.0f;
    // Linear identity until calibration data exists.
    return (uint16_t)((float)CODE_NULL +
                      env_norm * (float)(CODE_FULL - CODE_NULL) + 0.5f);
}

// ---- DAC write (one 16-bit transaction) ------------------------------------
//  CS is driven manually so it stays asserted across the 16 clocks; the SPI
//  driver is configured with cs_ena_pretrans=0 and CS in spi_device_interface
//  set to -1 (no managed CS).
inline void dac_write(uint16_t code12) {
    uint16_t word = DAC_CMD | (uint16_t)(code12 & 0x0FFF);
    uint8_t tx[2] = {
        (uint8_t)((word >> 8) & 0xFF),
        (uint8_t)( word       & 0xFF),
    };

    spi_transaction_t tr = {};
    tr.length    = 16;
    tr.tx_buffer = tx;

    gpio_set_level(pins::ENV_DAC_CS, 0);
    spi_device_polling_transmit(s_dac_dev, &tr);
    gpio_set_level(pins::ENV_DAC_CS, 1);
}

// ---- Busy-wait to the next 25 µs tick boundary -----------------------------
inline void wait_until(int64_t t_us) {
    while (esp_timer_get_time() < t_us) {
        // Tight spin.  Core 1 is ours; this is the documented design.
    }
}

// ---- Playout task ----------------------------------------------------------
void playout_task(void *) {
    float phase = 0.0f;
    ESP_LOGI(TAG, "playout task running on core %d", xPortGetCoreID());

    for (;;) {
        // Idle: hold modulator nulled, sleep until a key-down edge.
        dac_write(predistort(0.0f));
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);   // clears count on take

        int64_t next_us = esp_timer_get_time();

        for (;;) {
            next_us += TICK_US;
            wait_until(next_us);

            bool  kd  = s_key_down.load(std::memory_order_relaxed);
            float inc = s_phase_inc.load(std::memory_order_relaxed);

            if (kd) {
                phase += inc;
                if (phase > 1.0f) phase = 1.0f;
            } else {
                phase -= inc;
                if (phase < 0.0f) phase = 0.0f;
            }

            dac_write(predistort(sample_lut(phase)));

            if (!kd && phase <= 0.0f) break;   // tail finished → back to idle
        }
    }
}

}  // namespace

// ---------------------------------------------------------------------------
//  Public API
// ---------------------------------------------------------------------------

esp_err_t envelope_init() {
    build_rc_lut();
    set_wpm(20.0f);   // sane default until WinKey changes it

    // CS pin: GPIO, output, drive high (idle).
    gpio_config_t cs_cfg = {};
    cs_cfg.pin_bit_mask = 1ULL << (uint64_t)pins::ENV_DAC_CS;
    cs_cfg.mode         = GPIO_MODE_OUTPUT;
    cs_cfg.pull_up_en   = GPIO_PULLUP_DISABLE;
    cs_cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
    cs_cfg.intr_type    = GPIO_INTR_DISABLE;
    ESP_RETURN_ON_ERROR(gpio_config(&cs_cfg), TAG, "CS gpio_config");
    gpio_set_level(pins::ENV_DAC_CS, 1);

    // Dedicated SPI bus — DAC must NEVER share the monitoring I2C bus.
    spi_bus_config_t bus_cfg = {};
    bus_cfg.mosi_io_num     = pins::ENV_DAC_MOSI;
    bus_cfg.miso_io_num     = -1;
    bus_cfg.sclk_io_num     = pins::ENV_DAC_SCK;
    bus_cfg.quadwp_io_num   = -1;
    bus_cfg.quadhd_io_num   = -1;
    bus_cfg.max_transfer_sz = 4;
    ESP_RETURN_ON_ERROR(
        spi_bus_initialize(pins::DAC_SPI_HOST, &bus_cfg, SPI_DMA_DISABLED),
        TAG, "spi_bus_initialize");

    spi_device_interface_config_t dev_cfg = {};
    dev_cfg.clock_speed_hz = pins::ENV_DAC_HZ;
    dev_cfg.mode           = 0;          // CPOL=0, CPHA=0
    dev_cfg.spics_io_num   = -1;         // manual CS, see dac_write()
    dev_cfg.queue_size     = 1;
    dev_cfg.flags          = SPI_DEVICE_NO_DUMMY;
    ESP_RETURN_ON_ERROR(
        spi_bus_add_device(pins::DAC_SPI_HOST, &dev_cfg, &s_dac_dev),
        TAG, "spi_bus_add_device");

    dac_write(predistort(0.0f));   // start nulled

    // Pin playout to CORE_KEYING, high prio but below idle housekeeping.
    BaseType_t ok = xTaskCreatePinnedToCore(
        playout_task, "cw_envelope",
        4096, nullptr,
        configMAX_PRIORITIES - 2,
        &s_playout_handle,
        pins::CORE_KEYING);
    if (ok != pdPASS) return ESP_ERR_NO_MEM;

    ESP_LOGI(TAG, "envelope keyer up (SPI%d, CS=GPIO%d, %d Hz)",
             pins::DAC_SPI_HOST, (int)pins::ENV_DAC_CS, pins::ENV_DAC_HZ);
    return ESP_OK;
}

void set_wpm(float wpm) {
    if (wpm < 1.0f) wpm = 1.0f;
    float dot_ms  = 1200.0f / wpm;
    float edge_ms = EDGE_FRACTION * dot_ms;
    if (edge_ms > EDGE_MAX_MS) edge_ms = EDGE_MAX_MS;
    if (edge_ms < EDGE_MIN_MS) edge_ms = EDGE_MIN_MS;
    s_phase_inc.store((float)TICK_US / (edge_ms * 1000.0f),
                      std::memory_order_relaxed);
}

void key_down() {
    s_key_down.store(true, std::memory_order_relaxed);
    if (s_playout_handle) xTaskNotifyGive(s_playout_handle);
}

void key_up() {
    s_key_down.store(false, std::memory_order_relaxed);
}

}  // namespace keyer

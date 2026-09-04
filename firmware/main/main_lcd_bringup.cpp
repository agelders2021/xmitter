// =============================================================================
//  main_lcd_bringup.cpp — front-panel + analog-board bring-up entry point.
//
//  Built INSTEAD OF the normal main.cpp when the project is configured with
//  -DLCD_BRINGUP=ON.  Skips cathode monitor, faults, and shell so a
//  partially-populated bench build doesn't spam init errors.
//
//  Boot ordering (Rev 5):
//    1. Silence chatty log tags so the serial console isn't a firehose.
//    2. I2C bus.
//    3. Front-panel PCF8575 (0x21) + MCP4725 contrast (0x62) + HD44780.
//    4. Turn backlight fully on and show " Rev N " on row 0.  Everything
//       from here on updates row 1 with a short status string so the
//       operator can see what boot step just failed even if the serial
//       log scrolls off.
//    5. Attach the QT rotary encoder at 0x37.
//    6. Check MCP4728 -- probe 0x60/0x67, disambiguate Si5351 vs factory
//       MCP4728 by a register write/read, reprogram if needed.
//    7. Init the Si5351.  Program CLK2 to 14.200 MHz, enable output.
//    8. Start backlight PWM (5-bit BAM, 17/31 duty).
//    9. Spawn the encoder poll task.
//
//  Bench wiring:
//    - STEMMA QT: Metro -> Si5351 breakout -> front-panel PCF8575 breakout.
//    - Front-panel STEMMA-out -> encoder breakout STEMMA-in.
//    - 5 V bench supply to the PCB's +5V rail.  Common the grounds.
//    - Si5351 CLK2 -> Chebyshev LPF input -> attenuator -> scope / TinySA.
// =============================================================================
#include <cstdio>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "esp_log.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "nvs_flash.h"
#include "driver/i2c_master.h"

#include "driver/gpio.h"

#include "pin_map.h"
#include "pcf8575.h"
#include "lcd_hd44780.h"
#include "vfo_si5351.h"
#include "vfo_knob.h"
#include "mcp4728.h"
#include "keyer_envelope.h"
#include "i2c_scan.h"

#if defined(LCD_BRINGUP) && !defined(REPROGRAM_ONLY)

namespace {

constexpr char TAG[] = "bringup";

// Bring-up firmware revision.  BUMP THIS on every code change so we can
// tell which build is running on the bench without reading the serial log.
constexpr int FW_REV = 30;

// I2C addresses
constexpr uint8_t  MCP4725_ADDR             = 0x62;
constexpr uint8_t  ENCODER_ADDR             = 0x37;
constexpr uint8_t  MCP4728_ADDR_FACTORY     = 0x60;   // also Si5351's address
constexpr uint8_t  MCP4728_ADDR_TARGET      = 0x67;

// LCD contrast -- bench-tuned; written once at startup.
constexpr uint16_t MCP4725_CODE_FIXED = 493;    // ~0.6 V at 5 V Vref

// PWM: 5-bit BAM, 500 us unit, frame = 15.5 ms (~65 Hz).
constexpr int PWM_BITS      = 5;
constexpr int PWM_LEVELS    = 1 << PWM_BITS;
constexpr int PWM_UNIT_US   = 500;

// Backlight duty -- fixed for this build.
constexpr uint8_t BACKLIGHT_DUTY = 17;          // 17/31 = 55 %

// Frequency limits (20 m CW band).
constexpr uint32_t FREQ_MIN_HZ    = 14000000;
constexpr uint32_t FREQ_MAX_HZ    = 14350000;
constexpr uint32_t FREQ_START_HZ  = vfo::DEFAULT_FREQ_HZ;   // 14.200 MHz
constexpr int32_t  FREQ_STEP_HZ   = 1000;

// Encoder: Adafruit QT rotary = 4 counts per mechanical detent.
constexpr int ENCODER_COUNTS_PER_DETENT = 1;  // seesaw decodes quadrature internally

// --------------------------------------------------------------------------
//  Encoder interrupt (ENC_INT = D4 = GPIO4)
//
//  All seesaw breakout INT pins are open-drain active-low and can be
//  wired-OR'd together onto J5 → D4.  The ISR gives a binary semaphore;
//  the bringup task blocks on it with a 100 ms timeout (display refresh).
//
//  If J5 is not wired (bench without INT cable), GPIO4 stays idle-high
//  via R102 (10 kΩ pull-up on board), the ISR never fires, the semaphore
//  always times out, and enc_ready stays false -- encoder reads are skipped.
//  Wire J5 to use the encoder; flash rev 22 beforehand.
// --------------------------------------------------------------------------
static SemaphoreHandle_t s_enc_sem = nullptr;

static void IRAM_ATTR enc_int_isr(void *) {
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(s_enc_sem, &woken);
    portYIELD_FROM_ISR(woken);
}

// --------------------------------------------------------------------------
//  Shared state
// --------------------------------------------------------------------------
i2c_master_bus_handle_t s_bus         = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;
SemaphoreHandle_t       s_pcf_mutex   = nullptr;
esp_timer_handle_t      s_pwm_timer   = nullptr;
bool                    s_display_ok  = false;   // set true once PCF8575+LCD both up

volatile uint32_t s_freq_hz = FREQ_START_HZ;

uint8_t s_bit_idx = 0;

// True once the PWM timer + task are running; before that, LCD writes need
// no locking because app_main is the only writer.
bool s_locking_active = false;

// --------------------------------------------------------------------------
//  I2C bus + MCP4725
// --------------------------------------------------------------------------
esp_err_t i2c_bus_init() {
    i2c_master_bus_config_t cfg = {};
    cfg.i2c_port         = pins::I2C_PORT;
    cfg.sda_io_num       = pins::I2C_SDA;
    cfg.scl_io_num       = pins::I2C_SCL;
    cfg.clk_source       = I2C_CLK_SRC_DEFAULT;
    cfg.glitch_ignore_cnt = 7;
    cfg.flags.enable_internal_pullup = true;
    return i2c_new_master_bus(&cfg, &s_bus);
}

esp_err_t mcp4725_set(uint8_t addr, uint16_t code_12bit) {
    if (code_12bit > 0x0FFF) code_12bit = 0x0FFF;
    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = addr;
    cfg.scl_speed_hz    = 400000;

    i2c_master_dev_handle_t dev = nullptr;
    esp_err_t e = i2c_master_bus_add_device(s_bus, &cfg, &dev);
    if (e != ESP_OK) return e;

    const uint8_t buf[2] = {
        (uint8_t)((code_12bit >> 8) & 0x0F),
        (uint8_t)(code_12bit & 0xFF),
    };
    e = i2c_master_transmit(dev, buf, sizeof(buf), 100);
    i2c_master_bus_rm_device(dev);
    return e;
}

// --------------------------------------------------------------------------
//  Minimal Adafruit seesaw driver -- SW reset + read encoder delta only.
// --------------------------------------------------------------------------
constexpr uint8_t SEESAW_STATUS_BASE     = 0x00;
constexpr uint8_t SEESAW_STATUS_SWRST    = 0x7F;
constexpr uint8_t SEESAW_ENCODER_BASE    = 0x11;
constexpr uint8_t SEESAW_ENCODER_INTENSET = 0x10;
constexpr uint8_t SEESAW_ENCODER_DELTA   = 0x40;

class SeesawEncoder {
 public:
    esp_err_t begin(i2c_master_bus_handle_t bus, uint8_t addr) {
        i2c_device_config_t cfg = {};
        cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
        cfg.device_address  = addr;
        cfg.scl_speed_hz    = 400000;
        esp_err_t e = i2c_master_bus_add_device(bus, &cfg, &dev_);
        if (e != ESP_OK) return e;

        const uint8_t rst[3] = { SEESAW_STATUS_BASE, SEESAW_STATUS_SWRST, 0xFF };
        e = i2c_master_transmit(dev_, rst, sizeof(rst), 100);
        if (e != ESP_OK) return e;
        vTaskDelay(pdMS_TO_TICKS(500));

        // Enable encoder interrupt so the seesaw drives INT low on new counts.
        // Without this the INT line never asserts regardless of encoder activity.
        const uint8_t intenset[3] = { SEESAW_ENCODER_BASE, SEESAW_ENCODER_INTENSET, 0x01 };
        e = i2c_master_transmit(dev_, intenset, sizeof(intenset), 100);
        if (e != ESP_OK) return e;
        ESP_LOGI("enc", "seesaw ENCODER_INTENSET armed at 0x%02X", addr);
        return ESP_OK;
    }

    esp_err_t read_delta(int32_t *delta) {
        if (!dev_ || !delta) return ESP_ERR_INVALID_ARG;
        const uint8_t reg[2] = { SEESAW_ENCODER_BASE, SEESAW_ENCODER_DELTA };
        esp_err_t e = i2c_master_transmit(dev_, reg, sizeof(reg), 100);
        if (e != ESP_OK) return e;
        esp_rom_delay_us(500);
        uint8_t buf[4] = { 0 };
        e = i2c_master_receive(dev_, buf, sizeof(buf), 100);
        if (e != ESP_OK) return e;
        *delta = ((int32_t)(int8_t)buf[0] << 24)
               | ((int32_t)buf[1] << 16)
               | ((int32_t)buf[2] <<  8)
               |  (int32_t)buf[3];
        return ESP_OK;
    }

 private:
    i2c_master_dev_handle_t dev_ = nullptr;
};

SeesawEncoder s_encoder;

// --------------------------------------------------------------------------
//  LCD text helpers
//
//  Take the PCF8575 mutex when the caller is racing PWM / other threads
//  (guarded by s_locking_active).  During app_main pre-PWM setup we skip
//  the mutex -- no other task exists yet.
// --------------------------------------------------------------------------
void lcd_write_at(uint8_t row, uint8_t col, const char *s) {
    if (!s_display_ok) return;
    if (s_locking_active) xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
    s_lcd.set_cursor(row, col);
    s_lcd.print(s);
    if (s_locking_active) xSemaphoreGive(s_pcf_mutex);
}

// Row 1 is the boot-status / running-state line.  20 char field, always
// padded so the whole row updates atomically (no leftover characters).
void render_status(const char *msg) {
    char buf[21];
    std::snprintf(buf, sizeof(buf), "%-20.20s", msg);
    lcd_write_at(1, 0, buf);
}

void render_header_and_footer() {
    if (!s_display_ok) return;
    char buf[21];
    if (s_locking_active) xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
    s_lcd.clear();
    s_lcd.set_cursor(0, 0);
    std::snprintf(buf, sizeof(buf), " Rev %-15d", FW_REV);
    s_lcd.print(buf);
    s_lcd.set_cursor(3, 0);
    s_lcd.print(" Step: 1 kHz        ");
    if (s_locking_active) xSemaphoreGive(s_pcf_mutex);
}

void render_freq(uint32_t hz) {
    char raw[32];
    std::snprintf(raw, sizeof(raw), "   %u,%03u,%03u Hz",
                  (unsigned)(hz / 1000000u),
                  (unsigned)((hz / 1000u) % 1000u),
                  (unsigned)(hz % 1000u));
    char buf[21];
    std::snprintf(buf, sizeof(buf), "%-20.20s", raw);
    lcd_write_at(2, 0, buf);
}

// --------------------------------------------------------------------------
//  MCP4728 / Si5351 startup check
//
//  Deliberately does NOT try to discriminate Si5351 vs factory MCP4728 when
//  0x60 responds -- rev 5's discrimination step left the i2c_master driver
//  in a state where the follow-up reprogram transaction NAK'd
//  (ESP_ERR_INVALID_STATE from i2c_master_transmit).  Now we just probe
//  the two addresses and pick a branch:
//
//    both ACK           -> normal (MCP4728 reprogrammed, Si5351 present)
//    only 0x67 ACK      -> MCP4728 done, Si5351 not on bus
//    only 0x60 ACK      -> ASSUME factory MCP4728, attempt reprogram
//                          (safe even if it's actually a Si5351: any
//                          registers we clobber get reset by vfo::init).
//    neither            -> nothing on bus.
//
//  User's stated bench sequence is "install MCP4728 alone first, then add
//  Si5351".  Under that plan the ambiguous case above unambiguously means
//  factory MCP4728, so the discrimination step was never worth its cost.
// --------------------------------------------------------------------------

// Try up to 3 times; delay between attempts to let the bus / chip settle.
esp_err_t reprogram_with_retries() {
    constexpr int MAX_ATTEMPTS = 3;
    esp_err_t last_err = ESP_FAIL;

    for (int attempt = 1; attempt <= MAX_ATTEMPTS; ++attempt) {
        vTaskDelay(pdMS_TO_TICKS(50));   // let bus quiesce before each try
        ESP_LOGI(TAG, "reprogram attempt %d/%d", attempt, MAX_ATTEMPTS);
        last_err = mcp4728::reprogram_address(s_bus,
                                              MCP4728_ADDR_FACTORY,
                                              MCP4728_ADDR_TARGET,
                                              pins::MCP4728_LDAC);
        if (last_err != ESP_OK) {
            ESP_LOGW(TAG, "attempt %d xfer failed: %s",
                     attempt, esp_err_to_name(last_err));
            continue;
        }
        // Give the EEPROM burn 100 ms to settle, then probe 0x67.
        vTaskDelay(pdMS_TO_TICKS(100));
        if (i2c_master_probe(s_bus, MCP4728_ADDR_TARGET, 100) == ESP_OK) {
            ESP_LOGI(TAG, "attempt %d SUCCESS -- 0x67 now responds", attempt);
            return ESP_OK;
        }
        ESP_LOGW(TAG, "attempt %d: xfer OK but 0x67 still silent", attempt);
        last_err = ESP_ERR_NOT_FOUND;
    }
    return last_err;
}

// Returns a short status string suitable for LCD row 1.
const char *mcp4728_check_and_reprogram() {
    const bool ack60 = (i2c_master_probe(s_bus, MCP4728_ADDR_FACTORY, 100) == ESP_OK);
    const bool ack67 = (i2c_master_probe(s_bus, MCP4728_ADDR_TARGET,  100) == ESP_OK);

    ESP_LOGI(TAG, "bus scan: 0x60 %s, 0x67 %s",
             ack60 ? "ACK" : "---", ack67 ? "ACK" : "---");

    if (ack67 && ack60) {
        return " Both @ 0x60/0x67   ";
    }
    if (ack67 && !ack60) {
        return " MCP4728 OK, no VFO ";
    }
    if (!ack60 && !ack67) {
        ESP_LOGE(TAG, "nothing on bus at 0x60 or 0x67");
        return " no chip @ 0x60/0x67";
    }

    // 0x60 ACKs, 0x67 empty -- assume factory MCP4728, reprogram.
    render_status(" Reprog MCP4728...  ");
    esp_err_t re = reprogram_with_retries();
    if (re == ESP_OK) {
        return " MCP4728 -> 0x67 OK ";
    }
    if (re == ESP_ERR_NOT_FOUND) {
        return " Reprog no ACK @0x67";
    }
    return " Reprog xfer FAIL   ";
}

// --------------------------------------------------------------------------
//  PWM timer callback -- one BAM sub-frame per firing.
// --------------------------------------------------------------------------
void pwm_timer_cb(void *) {
    const uint8_t bit = s_bit_idx;
    const bool    on  = (BACKLIGHT_DUTY >> bit) & 1;

    if (xSemaphoreTake(s_pcf_mutex, pdMS_TO_TICKS(2)) == pdTRUE) {
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_r, on);
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_g, on);
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_b, on);
        s_pcf.apply();
        xSemaphoreGive(s_pcf_mutex);
    }

    const int slot_us = PWM_UNIT_US * (1u << bit);
    s_bit_idx = (bit + 1) % PWM_BITS;
    esp_timer_start_once(s_pwm_timer, slot_us);
}

// --------------------------------------------------------------------------
//  Bring-up task -- encoder poll + freq refresh + VFO retune
// --------------------------------------------------------------------------
// How many consecutive all-retry-exhausted encoder poll failures before we
// declare the bus locked and issue a recovery sequence.  At 50 ms/poll and
// 3 retries each, 8 failures = ~400 ms of solid failure before reset.
constexpr int ENC_FAIL_RESET_THRESH = 8;

void bringup_task(void *) {
    int32_t  accumulator    = 0;
    uint32_t last_shown     = s_freq_hz;
    int      enc_fail_streak = 0;

    while (true) {
        // Block until INT asserts (ISR gives semaphore) or 100 ms timeout
        // (keeps display refresh alive when encoder is idle).
        //
        // Secondary gpio_get_level check: if two encoders fire simultaneously
        // the wired-OR produces one falling edge; after draining the first,
        // INT may still be low -- catch that without waiting for another ISR.
        //
        // Without J5 wired: GPIO4 stays high (R102 pull-up), semaphore
        // never fires, enc_ready is always false, encoder reads are skipped.
        const bool enc_ready =
            (xSemaphoreTake(s_enc_sem, pdMS_TO_TICKS(100)) == pdTRUE)
            || (gpio_get_level(pins::ENC_INT) == 0);

        int32_t delta = 0;
        esp_err_t e = ESP_FAIL;

        if (enc_ready) {
        // Seesaw ATTINY occasionally NAKs during internal state flush; retry
        // up to 3x before giving up on this poll cycle.  The seesaw accumulates
        // counts internally so no detents are lost when a cycle is skipped.
        for (int retry = 0; retry < 3 && e != ESP_OK; ++retry) {
            e = s_encoder.read_delta(&delta);
            if (e != ESP_OK && retry < 2) vTaskDelay(pdMS_TO_TICKS(2));
        }
        }

        if (enc_ready && e != ESP_OK) {
            // Track consecutive failures.  If the seesaw ATTINY is holding SDA
            // low (bus lockup), the PCF8575 LCD writes will start producing
            // garbage.  Issue a bus reset + re-sync the PCF8575 shadow so the
            // LCD recovers cleanly.
            if (++enc_fail_streak >= ENC_FAIL_RESET_THRESH) {
                ESP_LOGW(TAG, "encoder: %d consecutive failures -- I2C bus reset",
                         enc_fail_streak);
                enc_fail_streak = 0;

                i2c_master_bus_reset(s_bus);
                vTaskDelay(pdMS_TO_TICKS(100));   // let seesaw ATTINY re-init

                // PCF8575 output register reset to 0xFFFF on power-cycle / reset;
                // re-apply our shadow so backlight + LCD pins return to last
                // known state.
                if (xSemaphoreTake(s_pcf_mutex, pdMS_TO_TICKS(200)) == pdTRUE) {
                    s_pcf.apply();
                    xSemaphoreGive(s_pcf_mutex);
                }

                // Re-init the HD44780: the bus glitch may have clocked in a
                // partial nibble, leaving the controller in an unknown state.
                if (s_display_ok) {
                    if (xSemaphoreTake(s_pcf_mutex, pdMS_TO_TICKS(200)) == pdTRUE) {
                        s_lcd.begin(&s_pcf);   // full init sequence
                        xSemaphoreGive(s_pcf_mutex);
                    }
                    render_header_and_footer();
                    render_freq(s_freq_hz);
                    render_status(" Running            ");
                }
            }
        } else if (enc_ready) {
            enc_fail_streak = 0;
        }

        // Sync from the MBL-600 PCNT knob before applying seesaw delta so the
        // seesaw always steps from the current VFO frequency, not a stale base.
        {
            uint32_t cur = vfo::current_freq();
            if (cur != s_freq_hz) s_freq_hz = cur;
        }

        if (e == ESP_OK && delta != 0) {
            accumulator += delta;
            int32_t detents = accumulator / ENCODER_COUNTS_PER_DETENT;
            accumulator    -= detents * ENCODER_COUNTS_PER_DETENT;

            int64_t new_hz = (int64_t)s_freq_hz + (int64_t)detents * FREQ_STEP_HZ;
            if (new_hz < (int64_t)FREQ_MIN_HZ) new_hz = FREQ_MIN_HZ;
            if (new_hz > (int64_t)FREQ_MAX_HZ) new_hz = FREQ_MAX_HZ;

            uint32_t hz = (uint32_t)new_hz;
            if (hz != s_freq_hz) {
                s_freq_hz = hz;
                (void)vfo::set_freq(hz);   // silent -- if VFO absent, LCD still tracks
            }
        }

        if (s_freq_hz != last_shown) {
            render_freq(s_freq_hz);
            last_shown = s_freq_hz;
        }
        // No vTaskDelay here -- xSemaphoreTake with 100 ms timeout is the sleep.
    }
}

// --------------------------------------------------------------------------
//  keyer_dash_task — continuous dashes at 20 WPM for U3 (MC1496) bringup.
//
//  At 20 WPM: 1 unit = 60 ms, dash = 3 units = 180 ms.
//  Inter-element gap = 1 unit = 60 ms; add 5 ms for envelope tail ramp-down.
// --------------------------------------------------------------------------
void keyer_dash_task(void *) {
    for (;;) {
        keyer::key_down();
        vTaskDelay(pdMS_TO_TICKS(180));   // dash on
        keyer::key_up();
        vTaskDelay(pdMS_TO_TICKS(65));    // inter-element + envelope tail
    }
}

}  // namespace

extern "C" void app_main() {
#ifdef LDAC_SCOPE_ONLY
    // ---------- LDAC continuity diagnostic ----------
    // Bench sees D7 pulse briefly then stay HIGH, pattern repeating a few
    // times before it stops -- classic ESP32 panic-reboot loop.  Something
    // in the earlier ESP_ERROR_CHECK path was panicking on this hardware.
    // Rewrite to:
    //   * Remove all ESP_ERROR_CHECK (won't panic; log every err instead).
    //   * Hardcode GPIO_NUM_7 (rule out pins:: namespace resolution).
    //   * Simple GPIO_MODE_OUTPUT (skip INPUT_OUTPUT / readback complexity).
    //   * Heartbeat print in the loop so we can tell if the loop is even
    //     running vs. if it crashed before entering it.
    // Small settling delay first so any ROM boot messages finish before
    // our own printfs.
    vTaskDelay(pdMS_TO_TICKS(500));

    const gpio_num_t PIN   = GPIO_NUM_7;
    const esp_err_t e_rst  = gpio_reset_pin(PIN);
    const esp_err_t e_pull = gpio_set_pull_mode(PIN, GPIO_FLOATING);
    const esp_err_t e_dir  = gpio_set_direction(PIN, GPIO_MODE_OUTPUT);
    const esp_err_t e_set  = gpio_set_level(PIN, 0);

    std::printf("\n=== LDAC scope diagnostic (GPIO 7) ===\n");
    std::printf(" gpio_reset_pin       -> %s\n", esp_err_to_name(e_rst));
    std::printf(" gpio_set_pull_mode   -> %s\n", esp_err_to_name(e_pull));
    std::printf(" gpio_set_direction   -> %s\n", esp_err_to_name(e_dir));
    std::printf(" gpio_set_level(0)    -> %s\n", esp_err_to_name(e_set));
    std::printf(" now toggling at 100 Hz; expect \"tick N alive\" every ~5 s\n\n");

    uint32_t tick = 0;
    while (true) {
        gpio_set_level(PIN, 1);
        vTaskDelay(pdMS_TO_TICKS(5));
        gpio_set_level(PIN, 0);
        vTaskDelay(pdMS_TO_TICKS(5));
        if ((++tick & 0x1FF) == 0) {           // every 512 cycles ~ 5 s
            std::printf(" tick %lu alive\n", (unsigned long)tick);
        }
    }
#endif

    // Silence the chatty tags so serial output is human-readable.  Our own
    // TAG stays at the default INFO level.
    esp_log_level_set("i2c.master", ESP_LOG_WARN);
    esp_log_level_set("vfo",        ESP_LOG_WARN);
    esp_log_level_set("pcf8575",    ESP_LOG_WARN);
    esp_log_level_set("lcd",        ESP_LOG_WARN);
    esp_log_level_set("knob",       ESP_LOG_WARN);
    // mcp4728 stays at INFO so we can see the reprogram byte log and any
    // per-attempt failure messages during bring-up.

    std::printf("\n=== xmitter bring-up rev %d (build %s %s) ===\n",
                FW_REV, __DATE__, __TIME__);
    fflush(stdout);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(i2c_bus_init());

    // ------- Full I2C bus scan -- shows every address that ACKs so the
    //  bench operator can eyeball the whole bus at boot.  Read-only.
    (void)i2c_scan::scan(s_bus);

    // ------- Stage A: display up (best-effort so the reprogram diagnostic
    //  can run with only the MCP4728 breakout powered from the STEMMA QT
    //  chain -- 5 V bench supply for the front-panel PCB can be off.  If
    //  PCF8575 or LCD isn't reachable, s_display_ok stays false and every
    //  render_*/lcd_write_at call becomes a no-op; rely on serial for
    //  status.
    if (esp_err_t e = s_pcf.begin(s_bus, pins::I2C_ADDR_PCF8575_PANEL); e != ESP_OK) {
        ESP_LOGW(TAG, "PCF8575 at 0x%02X missing (%s) -- no LCD status this boot",
                 pins::I2C_ADDR_PCF8575_PANEL, esp_err_to_name(e));
    } else if (esp_err_t e = s_lcd.begin(&s_pcf); e != ESP_OK) {
        ESP_LOGW(TAG, "HD44780 init failed: %s -- no LCD status this boot",
                 esp_err_to_name(e));
    } else {
        s_display_ok = true;
    }

    if (esp_err_t e = mcp4725_set(MCP4725_ADDR, MCP4725_CODE_FIXED); e != ESP_OK) {
        ESP_LOGW(TAG, "MCP4725 (contrast) missing at 0x%02X (%s)",
                 MCP4725_ADDR, esp_err_to_name(e));
    }

    if (s_display_ok) {
        s_lcd.backlight_rgb(true, true, true);
        render_header_and_footer();
        render_status(" Booting Rev 15     ");
        render_freq(FREQ_START_HZ);
    }
    ESP_LOGI(TAG, "display %s", s_display_ok ? "up" : "SKIPPED (front-panel off)");

    // ------- Stage B: encoder + ENC_INT GPIO ---------------------------------
    render_status(" Encoder init...    ");
    bool encoder_ok = false;
    if (esp_err_t e = s_encoder.begin(s_bus, ENCODER_ADDR); e == ESP_OK) {
        encoder_ok = true;
        ESP_LOGI(TAG, "encoder attached at 0x%02X", ENCODER_ADDR);
    } else {
        ESP_LOGE(TAG, "encoder MISSING at 0x%02X (%s)",
                 ENCODER_ADDR, esp_err_to_name(e));
    }

    // Set up interrupt-driven encoder reads.  ENC_INT (D4/GPIO4) is pulled
    // high by R102 (10 kΩ) on the board.  Without J5 wired the pin stays
    // idle-high, the ISR never fires, and the task runs on the 100 ms timeout
    // only -- encoder reads are skipped until the cable is installed.
    s_enc_sem = xSemaphoreCreateBinary();
    gpio_set_direction(pins::ENC_INT, GPIO_MODE_INPUT);
    gpio_set_pull_mode(pins::ENC_INT, GPIO_FLOATING);   // R102 is the pull-up
    gpio_set_intr_type(pins::ENC_INT, GPIO_INTR_NEGEDGE);
    gpio_install_isr_service(0);
    gpio_isr_handler_add(pins::ENC_INT, enc_int_isr, nullptr);
    ESP_LOGI(TAG, "ENC_INT ISR armed on GPIO%d (INT %s)",
             (int)pins::ENC_INT,
             gpio_get_level(pins::ENC_INT) ? "idle-high (ok)"
                                           : "asserted at boot");

    render_status(encoder_ok ? " Encoder OK         "
                             : " Encoder MISSING    ");
    vTaskDelay(pdMS_TO_TICKS(400));   // let operator read the line

    // ------- Stage B2: MBL-600 optical encoder (PCNT, GPIO2/3) -------------
    render_status(" MBL-600 init...    ");
    if (esp_err_t e = knob::g_vfo_knob.begin(pins::ENC_FREQ_B, pins::ENC_FREQ_A);
        e != ESP_OK) {
        ESP_LOGE(TAG, "MBL-600 PCNT init failed: %s", esp_err_to_name(e));
        render_status(" MBL-600 FAIL       ");
    } else if (esp_err_t e = knob::g_vfo_knob.start(pins::CORE_KEYING); e != ESP_OK) {
        ESP_LOGE(TAG, "MBL-600 task start failed: %s", esp_err_to_name(e));
        render_status(" MBL-600 task FAIL  ");
    } else {
        ESP_LOGI(TAG, "MBL-600 PCNT up on GPIO%d/%d",
                 (int)pins::ENC_FREQ_A, (int)pins::ENC_FREQ_B);
        render_status(" MBL-600 OK         ");
    }
    vTaskDelay(pdMS_TO_TICKS(400));

    // ------- Stage C: MCP4728 address --------------------------------------
    render_status(" MCP4728 check...   ");
    const char *mcp_status = mcp4728_check_and_reprogram();
    render_status(mcp_status);
    vTaskDelay(pdMS_TO_TICKS(600));

    // ------- Stage D: Si5351 VFO ------------------------------------------
    render_status(" Si5351 init...     ");
    bool vfo_ok = false;
    if (esp_err_t e = vfo::init(s_bus); e != ESP_OK) {
        ESP_LOGE(TAG, "Si5351: bus 0x60 not answering (%s)", esp_err_to_name(e));
        render_status(" Si5351 NOT ON BUS  ");
    } else if (esp_err_t e = vfo::set_freq(FREQ_START_HZ); e != ESP_OK) {
        ESP_LOGE(TAG, "Si5351 set_freq: %s", esp_err_to_name(e));
        render_status(" Si5351 tune FAIL   ");
    } else if (esp_err_t e = vfo::on(); e != ESP_OK) {
        ESP_LOGE(TAG, "Si5351 on: %s", esp_err_to_name(e));
        render_status(" Si5351 output FAIL ");
    } else {
        vfo_ok = true;
        ESP_LOGI(TAG, "Si5351 CLK2 = %u Hz, output enabled",
                 (unsigned)FREQ_START_HZ);
        render_status(" Si5351 CLK2 @ 14.2M");
    }
    vTaskDelay(pdMS_TO_TICKS(vfo_ok ? 800 : 3000));

    // ------- Stage E: MCP4728 null DAC — ch A+B to mid-scale (2048) --------
    //  Sets VA_INJ and VB_INJ to ~2.5 V (mid-scale with VDD ref), putting
    //  T1 and T2 at approximately midline before any null trim is applied.
    render_status(" Null DAC...        ");
    {
        esp_err_t ea = mcp4728::write_channel_dac(
                           s_bus, pins::I2C_ADDR_MCP4728, 0, 2048);
        esp_err_t eb = mcp4728::write_channel_dac(
                           s_bus, pins::I2C_ADDR_MCP4728, 1, 2048);
        if (ea == ESP_OK && eb == ESP_OK) {
            render_status(" NullDAC A+B=2048   ");
        } else {
            ESP_LOGW(TAG, "NullDAC chA:%s chB:%s",
                     esp_err_to_name(ea), esp_err_to_name(eb));
            render_status(" NullDAC WARN       ");
        }
    }
    vTaskDelay(pdMS_TO_TICKS(600));

    // ------- Stage F: keyer envelope + 20 WPM continuous dash test ----------
    render_status(" Keyer init...      ");
    bool keyer_ok = false;
    if (esp_err_t e = keyer::envelope_init(); e != ESP_OK) {
        ESP_LOGE(TAG, "keyer envelope init: %s", esp_err_to_name(e));
        render_status(" Keyer FAIL         ");
    } else {
        keyer::set_wpm(20.0f);
        ESP_LOGI(TAG, "keyer up -- continuous dashes @ 20 WPM through U3");
        render_status(" Keyer 20 WPM       ");
        keyer_ok = true;
    }
    vTaskDelay(pdMS_TO_TICKS(400));

    // ------- Stage G (was E): backlight PWM + encoder task ------------------
    s_pcf_mutex = xSemaphoreCreateMutex();
    if (!s_pcf_mutex) {
        ESP_LOGE(TAG, "mutex alloc failed");
        return;
    }
    s_locking_active = true;

    esp_timer_create_args_t timer_args = {};
    timer_args.callback        = &pwm_timer_cb;
    timer_args.dispatch_method = ESP_TIMER_TASK;
    timer_args.name            = "backlight_bam";
    ESP_ERROR_CHECK(esp_timer_create(&timer_args, &s_pwm_timer));
    ESP_ERROR_CHECK(esp_timer_start_once(s_pwm_timer, PWM_UNIT_US));

    render_status(keyer_ok      ? " Keyer 20WPM dashes "
                  : encoder_ok ? " Running            "
                               : " Running, no knob   ");

    if (keyer_ok)
        xTaskCreate(keyer_dash_task, "cw_dash", 2048, nullptr, 4, nullptr);

    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "boot complete (rev %d)", FW_REV);
}

#endif  // LCD_BRINGUP && !REPROGRAM_ONLY

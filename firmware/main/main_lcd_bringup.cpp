// =============================================================================
//  main_lcd_bringup.cpp — front-panel + analog-board bring-up entry point.
//
//  Built INSTEAD OF the normal main.cpp when the project is configured with
//  -DLCD_BRINGUP=ON.  Skips MCP4728, cathode monitor, faults, and shell so
//  a partially-populated bench build doesn't spam init errors.
//
//  Rev 2: analog-board VFO bring-up
//    1. Bring up shared I2C bus.
//    2. Front-panel PCF8575 (0x21) + HD44780 4-bit driver.
//    3. MCP4725 (0x62) fixed at DAC=493 (~0.6 V) contrast.
//    4. Backlight held steady at 17/31 duty via 5-bit BAM PWM.
//    5. Si5351A (0x60) on the analog board -- CLK0 at 14.200000 MHz,
//       output enabled so a scope sees RF into the Chebyshev LPF.
//    6. I2C QT rotary encoder (0x37) now steps VFO frequency +/- 1 kHz
//       per mechanical detent.  Clamped to 14.000-14.350 MHz.
//
//  Bench wiring:
//    - STEMMA QT: Metro -> Si5351 breakout -> front-panel PCF8575 breakout
//      (any order that reaches all four addresses is fine).
//    - Front-panel STEMMA-out -> encoder breakout STEMMA-in.
//    - 5 V bench supply to the front-panel +5V rail.  Common the grounds.
//    - Si5351 CLK0 -> Chebyshev LPF input -> scope.
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

#include "pin_map.h"
#include "pcf8575.h"
#include "lcd_hd44780.h"
#include "vfo_si5351.h"
#include "mcp4728.h"

#ifdef LCD_BRINGUP

namespace {

constexpr char TAG[] = "lcd_bringup";

// Bring-up firmware revision.  BUMP THIS on every code change so we can
// tell which build is running on the bench without reading the serial log.
constexpr int FW_REV = 4;

// I2C addresses
constexpr uint8_t  MCP4725_ADDR             = 0x62;
constexpr uint8_t  ENCODER_ADDR             = 0x37;
constexpr uint8_t  MCP4728_ADDR_FACTORY     = 0x60;  // also Si5351's address
constexpr uint8_t  MCP4728_ADDR_TARGET      = 0x67;

// LCD contrast -- bench-tuned; written once at startup.
constexpr uint16_t MCP4725_CODE_FIXED = 493;    // ~0.6 V at 5 V Vref

// PWM: 5-bit BAM, 500 us unit, frame = 15.5 ms (~65 Hz).
constexpr int PWM_BITS      = 5;
constexpr int PWM_LEVELS    = 1 << PWM_BITS;    // 32 levels
constexpr int PWM_UNIT_US   = 500;

// Backlight duty -- fixed for this build.
constexpr uint8_t BACKLIGHT_DUTY = 17;          // 17/31 = 55 %

// Frequency limits (20 m CW band, per encoders.h).
constexpr uint32_t FREQ_MIN_HZ    = 14000000;
constexpr uint32_t FREQ_MAX_HZ    = 14350000;
constexpr uint32_t FREQ_START_HZ  = vfo::DEFAULT_FREQ_HZ;   // 14.200 MHz
constexpr int32_t  FREQ_STEP_HZ   = 1000;

// Encoder: Adafruit QT rotary = 4 counts per mechanical detent.
constexpr int ENCODER_COUNTS_PER_DETENT = 4;

// --------------------------------------------------------------------------
//  Shared state
// --------------------------------------------------------------------------
i2c_master_bus_handle_t s_bus       = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;
SemaphoreHandle_t       s_pcf_mutex = nullptr;
esp_timer_handle_t      s_pwm_timer = nullptr;

// Current VFO frequency, Hz.  Reads/writes are atomic on 32-bit ESP32.
volatile uint32_t s_freq_hz = FREQ_START_HZ;

uint8_t s_bit_idx = 0;

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
//  MCP4728 / Si5351 sanity check + optional reprogram
//
//  Runs before vfo::init().  Reads the bus at 0x60 (factory MCP4728 =
//  Si5351) and 0x67 (target MCP4728 address).  Four possible states:
//
//    0x67 ACK + 0x60 ACK   -> normal running config (MCP4728 reprogrammed
//                             and Si5351 both present).  Nothing to do.
//    0x67 ACK + 0x60 NAK   -> MCP4728 already reprogrammed, Si5351 not
//                             on the bus yet.  Warn but continue.
//    0x60 ACK + 0x67 NAK   -> ambiguous.  Identify by trying a Si5351
//                             register write/readback.  If Si5351, no
//                             MCP4728 to reprogram.  If not, assume
//                             factory MCP4728 and reprogram to 0x67.
//    both NAK              -> nothing on the bus at either address.
//                             Warn; Si5351 init will fail loudly.
// --------------------------------------------------------------------------

// Distinguish Si5351 from factory MCP4728 at the same address.  Writes
// 0xFF to Si5351 REG_OUTPUT_ENABLE (reg 3) then reads it back; Si5351
// returns 0xFF, MCP4728 does not (0x03 is interpreted as fast-write
// upper nibble = 3 and readback returns its status stream instead).
// The Si5351 write is idempotent -- 0xFF disables all outputs, which
// is chip default at boot, so no state disturbance.  The MCP4728 write
// briefly nudges DAC A output; harmless with nothing wired to it in
// bring-up.
bool device_at_addr_is_si5351(uint8_t addr) {
    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = addr;
    cfg.scl_speed_hz    = 400000;

    i2c_master_dev_handle_t dev = nullptr;
    if (i2c_master_bus_add_device(s_bus, &cfg, &dev) != ESP_OK) return false;

    bool is_si = false;
    const uint8_t write_buf[2] = { 0x03, 0xFF };
    if (i2c_master_transmit(dev, write_buf, sizeof(write_buf), 100) == ESP_OK) {
        const uint8_t reg = 0x03;
        uint8_t readback = 0;
        if (i2c_master_transmit_receive(dev, &reg, 1, &readback, 1, 100) == ESP_OK) {
            if (readback == 0xFF) is_si = true;
        }
    }
    i2c_master_bus_rm_device(dev);
    return is_si;
}

void mcp4728_check_and_reprogram() {
    const bool ack60 = (i2c_master_probe(s_bus, MCP4728_ADDR_FACTORY, 100) == ESP_OK);
    const bool ack67 = (i2c_master_probe(s_bus, MCP4728_ADDR_TARGET,  100) == ESP_OK);

    if (ack67) {
        if (ack60) {
            ESP_LOGI(TAG, "MCP4728 @ 0x%02X and Si5351 @ 0x%02X -- normal",
                     MCP4728_ADDR_TARGET, MCP4728_ADDR_FACTORY);
        } else {
            ESP_LOGW(TAG, "MCP4728 @ 0x%02X but Si5351 NOT on bus at 0x%02X",
                     MCP4728_ADDR_TARGET, MCP4728_ADDR_FACTORY);
        }
        return;
    }

    // 0x67 empty
    if (!ack60) {
        ESP_LOGW(TAG, "no ACK at 0x%02X or 0x%02X -- MCP4728 + Si5351 both absent?",
                 MCP4728_ADDR_FACTORY, MCP4728_ADDR_TARGET);
        return;
    }

    // 0x60 ACKs, 0x67 empty -- Si5351 or factory MCP4728?
    ESP_LOGI(TAG, "0x%02X responds, 0x%02X empty -- identifying...",
             MCP4728_ADDR_FACTORY, MCP4728_ADDR_TARGET);
    if (device_at_addr_is_si5351(MCP4728_ADDR_FACTORY)) {
        ESP_LOGI(TAG, "0x%02X is Si5351; no factory MCP4728 to reprogram",
                 MCP4728_ADDR_FACTORY);
        return;
    }

    // Looks like factory MCP4728.  Reprogram.
    ESP_LOGI(TAG, "0x%02X appears to be factory MCP4728; reprogramming to 0x%02X",
             MCP4728_ADDR_FACTORY, MCP4728_ADDR_TARGET);
    esp_err_t re = mcp4728::reprogram_address(s_bus,
                                              MCP4728_ADDR_FACTORY,
                                              MCP4728_ADDR_TARGET,
                                              pins::MCP4728_LDAC);
    if (re != ESP_OK) {
        ESP_LOGE(TAG, "MCP4728 reprogram transaction failed: %s",
                 esp_err_to_name(re));
        return;
    }

    // Give the EEPROM burn a moment to settle before verifying.
    vTaskDelay(pdMS_TO_TICKS(100));
    if (i2c_master_probe(s_bus, MCP4728_ADDR_TARGET, 100) == ESP_OK) {
        ESP_LOGI(TAG, "MCP4728 reprogrammed OK -- now at 0x%02X",
                 MCP4728_ADDR_TARGET);
    } else {
        ESP_LOGE(TAG, "reprogram sent but 0x%02X still not responding",
                 MCP4728_ADDR_TARGET);
    }
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
//  LCD text -- all callers MUST hold s_pcf_mutex.
// --------------------------------------------------------------------------
void render_header_locked() {
    char buf[21];
    s_lcd.clear();
    s_lcd.set_cursor(0, 0);
    std::snprintf(buf, sizeof(buf), " Rev %-15d", FW_REV);
    s_lcd.print(buf);
    s_lcd.set_cursor(1, 0);
    s_lcd.print(" VFO (Si5351)       ");
    s_lcd.set_cursor(3, 0);
    s_lcd.print(" Step: 1 kHz        ");
}

void render_freq_locked(uint32_t hz) {
    // "14,200,000 Hz" = 13 chars; center in 20 with 3 + 4 padding
    char raw[32];
    std::snprintf(raw, sizeof(raw), "   %u,%03u,%03u Hz",
                  (unsigned)(hz / 1000000u),
                  (unsigned)((hz / 1000u) % 1000u),
                  (unsigned)(hz % 1000u));
    char buf[21];
    std::snprintf(buf, sizeof(buf), "%-20.20s", raw);
    s_lcd.set_cursor(2, 0);
    s_lcd.print(buf);
}

// --------------------------------------------------------------------------
//  Bring-up task -- encoder poll + LCD text refresh + VFO retune
// --------------------------------------------------------------------------
void bringup_task(void *) {
    xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
    render_header_locked();
    render_freq_locked(s_freq_hz);
    xSemaphoreGive(s_pcf_mutex);

    int32_t  accumulator = 0;
    uint32_t last_shown  = 0;

    while (true) {
        int32_t delta = 0;
        esp_err_t e = s_encoder.read_delta(&delta);
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
                if (esp_err_t ve = vfo::set_freq(hz); ve != ESP_OK) {
                    ESP_LOGW(TAG, "vfo::set_freq(%u) failed: %s",
                             (unsigned)hz, esp_err_to_name(ve));
                }
            }
        } else if (e != ESP_OK) {
            static int64_t last_log = 0;
            const int64_t now = esp_timer_get_time();
            if (now - last_log > 5'000'000) {
                ESP_LOGW(TAG, "encoder read failed: %s", esp_err_to_name(e));
                last_log = now;
            }
        }

        if (s_freq_hz != last_shown) {
            xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
            render_freq_locked(s_freq_hz);
            xSemaphoreGive(s_pcf_mutex);
            last_shown = s_freq_hz;
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

}  // namespace

extern "C" void app_main() {
    std::printf("\n=== xmitter bring-up rev %d ===\n", FW_REV);
    std::printf(" build: %s %s\n", __DATE__, __TIME__);
    std::printf(" I2C: PCF8575 0x%02X | MCP4725 0x%02X (=%u fixed) |"
                " encoder 0x%02X | Si5351 0x60\n",
                pins::I2C_ADDR_PCF8575_PANEL, MCP4725_ADDR,
                (unsigned)MCP4725_CODE_FIXED, ENCODER_ADDR);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(i2c_bus_init());
    ESP_LOGI(TAG, "I2C up: SDA=GPIO%d SCL=GPIO%d",
             (int)pins::I2C_SDA, (int)pins::I2C_SCL);

    ESP_ERROR_CHECK(s_pcf.begin(s_bus, pins::I2C_ADDR_PCF8575_PANEL));

    if (esp_err_t e = mcp4725_set(MCP4725_ADDR, MCP4725_CODE_FIXED); e != ESP_OK) {
        ESP_LOGE(TAG, "MCP4725 set failed: %s", esp_err_to_name(e));
    }

    ESP_ERROR_CHECK(s_lcd.begin(&s_pcf));

    s_pcf_mutex = xSemaphoreCreateMutex();
    if (!s_pcf_mutex) { ESP_LOGE(TAG, "mutex alloc failed"); return; }

    esp_timer_create_args_t timer_args = {};
    timer_args.callback        = &pwm_timer_cb;
    timer_args.dispatch_method = ESP_TIMER_TASK;
    timer_args.name            = "backlight_bam";
    ESP_ERROR_CHECK(esp_timer_create(&timer_args, &s_pwm_timer));
    ESP_ERROR_CHECK(esp_timer_start_once(s_pwm_timer, PWM_UNIT_US));

    // Encoder -- if missing, LCD still shows freq, just can't retune.
    if (esp_err_t e = s_encoder.begin(s_bus, ENCODER_ADDR); e != ESP_OK) {
        ESP_LOGE(TAG, "encoder begin failed at 0x%02X: %s",
                 ENCODER_ADDR, esp_err_to_name(e));
    } else {
        ESP_LOGI(TAG, "encoder attached at 0x%02X", ENCODER_ADDR);
    }

    // MCP4728 address check + optional one-time reprogram from factory
    // 0x60 to 0x67.  Must run before vfo::init() because the Si5351 also
    // lives at 0x60 -- we need to disambiguate before touching either.
    mcp4728_check_and_reprogram();

    // VFO -- init, tune, enable.
    if (esp_err_t e = vfo::init(s_bus); e != ESP_OK) {
        ESP_LOGE(TAG, "vfo::init failed: %s (Si5351 wiring?)", esp_err_to_name(e));
    } else {
        if (esp_err_t se = vfo::set_freq(s_freq_hz); se != ESP_OK) {
            ESP_LOGE(TAG, "vfo::set_freq failed: %s", esp_err_to_name(se));
        }
        if (esp_err_t oe = vfo::on(); oe != ESP_OK) {
            ESP_LOGE(TAG, "vfo::on failed: %s", esp_err_to_name(oe));
        } else {
            ESP_LOGI(TAG, "VFO CLK2 = %u Hz, output enabled",
                     (unsigned)s_freq_hz);
        }
    }

    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "bring-up rev %d running -- turn encoder to retune VFO",
             FW_REV);
}

#endif  // LCD_BRINGUP

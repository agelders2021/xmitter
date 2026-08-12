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

#include "pin_map.h"
#include "pcf8575.h"
#include "lcd_hd44780.h"
#include "vfo_si5351.h"
#include "mcp4728.h"

#ifdef LCD_BRINGUP

namespace {

constexpr char TAG[] = "bringup";

// Bring-up firmware revision.  BUMP THIS on every code change so we can
// tell which build is running on the bench without reading the serial log.
constexpr int FW_REV = 6;

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
constexpr int ENCODER_COUNTS_PER_DETENT = 4;

// --------------------------------------------------------------------------
//  Shared state
// --------------------------------------------------------------------------
i2c_master_bus_handle_t s_bus       = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;
SemaphoreHandle_t       s_pcf_mutex = nullptr;
esp_timer_handle_t      s_pwm_timer = nullptr;

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
//  LCD text helpers
//
//  Take the PCF8575 mutex when the caller is racing PWM / other threads
//  (guarded by s_locking_active).  During app_main pre-PWM setup we skip
//  the mutex -- no other task exists yet.
// --------------------------------------------------------------------------
void lcd_write_at(uint8_t row, uint8_t col, const char *s) {
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
//  MCP4728 / Si5351 sanity check + optional reprogram
// --------------------------------------------------------------------------

// Write 0xFF to Si5351 REG_OUTPUT_ENABLE (reg 3) then read it back.  A
// Si5351 will echo 0xFF; a factory MCP4728 does not.  Idempotent for
// Si5351 (0xFF is the reset default) and only temporarily nudges the
// MCP4728's DAC A output if that's what's on the bus -- no EEPROM burn.
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

// Returns a short status string suitable for LCD row 1.
const char *mcp4728_check_and_reprogram() {
    const bool ack60 = (i2c_master_probe(s_bus, MCP4728_ADDR_FACTORY, 100) == ESP_OK);
    const bool ack67 = (i2c_master_probe(s_bus, MCP4728_ADDR_TARGET,  100) == ESP_OK);

    if (ack67 && ack60) {
        ESP_LOGI(TAG, "MCP4728 at 0x67, Si5351 at 0x60 -- normal");
        return " Both @ 0x60/0x67   ";
    }
    if (ack67 && !ack60) {
        ESP_LOGW(TAG, "MCP4728 at 0x67, Si5351 NOT on bus");
        return " MCP4728 OK, no VFO ";
    }
    if (!ack60 && !ack67) {
        ESP_LOGE(TAG, "No ACK at 0x60 or 0x67");
        return " no chip @ 0x60/0x67";
    }

    // 0x60 ACKs, 0x67 empty -- identify.
    if (device_at_addr_is_si5351(MCP4728_ADDR_FACTORY)) {
        ESP_LOGI(TAG, "0x60 is Si5351; no factory MCP4728");
        return " Si5351 only        ";
    }

    // Factory MCP4728 -- reprogram.
    ESP_LOGI(TAG, "reprogramming factory MCP4728 -> 0x67");
    render_status(" Reprog MCP4728...  ");
    esp_err_t re = mcp4728::reprogram_address(s_bus,
                                              MCP4728_ADDR_FACTORY,
                                              MCP4728_ADDR_TARGET,
                                              pins::MCP4728_LDAC);
    if (re != ESP_OK) {
        ESP_LOGE(TAG, "MCP4728 reprogram xfer failed: %s", esp_err_to_name(re));
        return " Reprog xfer FAIL   ";
    }
    vTaskDelay(pdMS_TO_TICKS(100));
    if (i2c_master_probe(s_bus, MCP4728_ADDR_TARGET, 100) != ESP_OK) {
        ESP_LOGE(TAG, "reprogram sent but 0x67 not responding");
        return " Reprog no ACK @0x67";
    }
    ESP_LOGI(TAG, "MCP4728 now at 0x67");
    return " MCP4728 -> 0x67 OK ";
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
void bringup_task(void *) {
    int32_t  accumulator = 0;
    uint32_t last_shown  = s_freq_hz;

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
                (void)vfo::set_freq(hz);   // silent -- if VFO absent, LCD still tracks
            }
        }

        if (s_freq_hz != last_shown) {
            render_freq(s_freq_hz);
            last_shown = s_freq_hz;
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

}  // namespace

extern "C" void app_main() {
    // Silence the chatty tags so serial output is human-readable.  Our own
    // TAG stays at the default INFO level.
    esp_log_level_set("i2c.master", ESP_LOG_WARN);
    esp_log_level_set("vfo",        ESP_LOG_WARN);
    esp_log_level_set("mcp4728",    ESP_LOG_WARN);
    esp_log_level_set("pcf8575",    ESP_LOG_WARN);
    esp_log_level_set("lcd",        ESP_LOG_WARN);

    std::printf("\n=== xmitter bring-up rev %d (build %s %s) ===\n",
                FW_REV, __DATE__, __TIME__);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(i2c_bus_init());

    // ------- Stage A: display up ------------------------------------------
    if (esp_err_t e = s_pcf.begin(s_bus, pins::I2C_ADDR_PCF8575_PANEL); e != ESP_OK) {
        ESP_LOGE(TAG, "PCF8575 at 0x%02X missing (%s) -- front panel unwired?",
                 pins::I2C_ADDR_PCF8575_PANEL, esp_err_to_name(e));
        return;
    }
    if (esp_err_t e = mcp4725_set(MCP4725_ADDR, MCP4725_CODE_FIXED); e != ESP_OK) {
        ESP_LOGW(TAG, "MCP4725 (contrast) missing at 0x%02X (%s)",
                 MCP4725_ADDR, esp_err_to_name(e));
    }
    if (esp_err_t e = s_lcd.begin(&s_pcf); e != ESP_OK) {
        ESP_LOGE(TAG, "HD44780 init failed: %s", esp_err_to_name(e));
        return;
    }

    // Backlight fully on so the boot status is readable; PWM takes over later.
    s_lcd.backlight_rgb(true, true, true);

    render_header_and_footer();
    render_status(" Booting Rev 5      ");
    render_freq(FREQ_START_HZ);
    ESP_LOGI(TAG, "display up");

    // ------- Stage B: encoder ---------------------------------------------
    render_status(" Encoder init...    ");
    bool encoder_ok = false;
    if (esp_err_t e = s_encoder.begin(s_bus, ENCODER_ADDR); e == ESP_OK) {
        encoder_ok = true;
        ESP_LOGI(TAG, "encoder attached at 0x%02X", ENCODER_ADDR);
    } else {
        ESP_LOGE(TAG, "encoder MISSING at 0x%02X (%s)",
                 ENCODER_ADDR, esp_err_to_name(e));
    }
    render_status(encoder_ok ? " Encoder OK         "
                             : " Encoder MISSING    ");
    vTaskDelay(pdMS_TO_TICKS(400));   // let operator read the line

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

    // ------- Stage E: backlight PWM + encoder task ------------------------
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

    render_status(encoder_ok ? " Running            "
                             : " Running, no knob   ");

    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "boot complete (rev %d)", FW_REV);
}

#endif  // LCD_BRINGUP

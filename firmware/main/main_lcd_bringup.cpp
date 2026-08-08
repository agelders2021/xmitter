// =============================================================================
//  main_lcd_bringup.cpp — front-panel LCD bring-up test entry point.
//
//  Built INSTEAD OF the normal main.cpp when the project is configured with
//  -DLCD_BRINGUP=ON.  Skips VFO, MCP4728, cathode monitor, faults, and shell
//  so an unattached-hardware bench test doesn't spam init errors.
//
//  This build:
//    1. Bring up shared I2C bus.
//    2. Front-panel PCF8575 at 0x21.
//    3. MCP4725 (LCD contrast) at 0x62, fixed at DAC=493 (~0.6 V) --
//       the sweet spot found on the bench.  Written once at startup.
//    4. HD44780 4-bit driver.
//    5. Backlight = uniform white via 5-bit BAM PWM (esp_timer + mutex).
//    6. I2C QT rotary encoder at 0x37 controls the backlight duty
//       (0..31); each detent = one duty level.
//
//  Bench wiring:
//    - STEMMA QT: Metro -> front-panel PCF8575 breakout (SDA/SCL).
//    - Front-panel STEMMA-out -> encoder breakout STEMMA-in.
//    - Bench 5 V supply to the PCB's +5V rail.  Common the grounds.
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

#ifdef LCD_BRINGUP

namespace {

constexpr char TAG[] = "lcd_bringup";

// Bring-up firmware revision.  BUMP THIS on every code change so we can
// tell which build is running on the bench without reading the serial log.
constexpr int FW_REV = 1;

// I2C addresses
constexpr uint8_t  MCP4725_ADDR       = 0x62;
constexpr uint8_t  ENCODER_ADDR       = 0x37;

// LCD contrast -- bench-tuned sweet spot, applied once at startup.
constexpr uint16_t MCP4725_CODE_FIXED = 493;    // ~0.6 V at 5 V Vref

// PWM: 5-bit BAM, 500 us unit, frame = 15.5 ms (~65 Hz).
constexpr int PWM_BITS      = 5;
constexpr int PWM_LEVELS    = 1 << PWM_BITS;    // 32 levels (0..31)
constexpr int PWM_UNIT_US   = 500;
constexpr int PWM_FRAME_US  = (PWM_LEVELS - 1) * PWM_UNIT_US;

// Backlight starting duty (middle of range).
constexpr uint8_t BACKLIGHT_START_DUTY = PWM_LEVELS / 2;   // 16/31

// Encoder: Adafruit QT rotary = 4 counts per mechanical detent.
constexpr int ENCODER_COUNTS_PER_DETENT = 4;
constexpr int DUTY_PER_DETENT           = 1;

// --------------------------------------------------------------------------
//  Shared state
// --------------------------------------------------------------------------
i2c_master_bus_handle_t s_bus       = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;
SemaphoreHandle_t       s_pcf_mutex = nullptr;
esp_timer_handle_t      s_pwm_timer = nullptr;

// Single common backlight duty for all three channels (white).  Byte-sized
// so writes are atomic.  0..PWM_LEVELS-1.
volatile uint8_t s_duty = BACKLIGHT_START_DUTY;

// BAM sub-frame index; only touched from the timer callback.
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
//  PWM timer callback -- one BAM sub-frame per firing.
// --------------------------------------------------------------------------
void pwm_timer_cb(void *) {
    const uint8_t bit  = s_bit_idx;
    const uint8_t duty = s_duty;
    const bool    on   = (duty >> bit) & 1;

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
    s_lcd.print(" Backlight (encoder)");
}

void render_duty_locked(uint8_t duty) {
    const unsigned pct = (unsigned)((duty * 100u + (PWM_LEVELS - 1) / 2)
                                    / (PWM_LEVELS - 1));

    char raw[32];
    std::snprintf(raw, sizeof(raw), "  Level %u/%u  %u%%",
                  (unsigned)duty, (unsigned)(PWM_LEVELS - 1), pct);
    char buf[21];
    std::snprintf(buf, sizeof(buf), "%-20.20s", raw);
    s_lcd.set_cursor(2, 0);
    s_lcd.print(buf);

    // 20-cell bar graph on row 3
    char bar[21];
    const int bars = (int)((duty * 20 + (PWM_LEVELS - 1) / 2)
                            / (PWM_LEVELS - 1));
    for (int i = 0; i < 20; ++i) bar[i] = (i < bars) ? '*' : ' ';
    bar[20] = 0;
    s_lcd.set_cursor(3, 0);
    s_lcd.print(bar);
}

// --------------------------------------------------------------------------
//  Bring-up task -- encoder poll + LCD text refresh
// --------------------------------------------------------------------------
void bringup_task(void *) {
    xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
    render_header_locked();
    render_duty_locked(s_duty);
    xSemaphoreGive(s_pcf_mutex);

    int32_t accumulator = 0;
    uint8_t last_shown  = 0xFF;   // force initial draw

    while (true) {
        int32_t delta = 0;
        esp_err_t e = s_encoder.read_delta(&delta);
        if (e == ESP_OK && delta != 0) {
            accumulator += delta;
            int32_t detents = accumulator / ENCODER_COUNTS_PER_DETENT;
            accumulator    -= detents * ENCODER_COUNTS_PER_DETENT;

            int32_t new_duty = (int32_t)s_duty + detents * DUTY_PER_DETENT;
            if (new_duty < 0)                new_duty = 0;
            if (new_duty > PWM_LEVELS - 1)   new_duty = PWM_LEVELS - 1;
            s_duty = (uint8_t)new_duty;
        } else if (e != ESP_OK) {
            static int64_t last_log = 0;
            const int64_t now = esp_timer_get_time();
            if (now - last_log > 5'000'000) {
                ESP_LOGW(TAG, "encoder read failed: %s", esp_err_to_name(e));
                last_log = now;
            }
        }

        if (s_duty != last_shown) {
            xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
            render_duty_locked(s_duty);
            xSemaphoreGive(s_pcf_mutex);
            last_shown = s_duty;
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

}  // namespace

extern "C" void app_main() {
    std::printf("\n=== LCD bring-up rev %d ===\n", FW_REV);
    std::printf(" build: %s %s\n", __DATE__, __TIME__);
    std::printf(" PCF8575 @ 0x%02X, MCP4725 @ 0x%02X (fixed %u),"
                " encoder @ 0x%02X\n",
                pins::I2C_ADDR_PCF8575_PANEL, MCP4725_ADDR,
                (unsigned)MCP4725_CODE_FIXED, ENCODER_ADDR);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(i2c_bus_init());
    ESP_LOGI(TAG, "I2C up: SDA=GPIO%d SCL=GPIO%d @ %lu Hz",
             (int)pins::I2C_SDA, (int)pins::I2C_SCL,
             (unsigned long)pins::I2C_HZ);

    ESP_ERROR_CHECK(s_pcf.begin(s_bus, pins::I2C_ADDR_PCF8575_PANEL));

    // Contrast: set once, never touch again.
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

    if (esp_err_t e = s_encoder.begin(s_bus, ENCODER_ADDR); e != ESP_OK) {
        ESP_LOGE(TAG, "encoder begin failed at 0x%02X: %s",
                 ENCODER_ADDR, esp_err_to_name(e));
    } else {
        ESP_LOGI(TAG, "encoder attached at 0x%02X", ENCODER_ADDR);
    }

    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "bring-up rev %d running -- turn encoder to adjust backlight",
             FW_REV);
}

#endif  // LCD_BRINGUP

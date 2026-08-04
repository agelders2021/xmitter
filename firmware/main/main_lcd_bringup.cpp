// =============================================================================
//  main_lcd_bringup.cpp — front-panel LCD bring-up test entry point.
//
//  Built INSTEAD OF the normal main.cpp when the project is configured with
//  -DLCD_BRINGUP=ON.  Skips VFO, MCP4728, cathode monitor, faults, and shell
//  so an unattached-hardware bench test doesn't spam init errors.
//
//  What it does:
//    1. Bring up the shared I2C bus.
//    2. Attach the front-panel PCF8575 at 0x21.
//    3. Attach the MCP4725 (LCD contrast DAC) at 0x62 and set V0 = 0.7 V
//       (12-bit code 573 at 5 V Vref).
//    4. Init the HD44780 4-bit driver.
//    5. Spawn a task that cycles "Red" -> "Green" -> "Blue" every 5 s, with
//       the active color's backlight modulated 40 -> 60 -> 40 % across the
//       5 s window while the two non-cycled channels hold at 50 %.
//
//  Backlight PWM is 6-bit bit-angle modulation at 60 Hz, driven from the
//  same task.  ~3 % I2C bus utilization -- leaves plenty of room for the
//  encoders in a later stage.
//
//  Bench wiring:
//    - STEMMA QT: Metro -> front-panel PCF8575 breakout (SDA/SCL).
//    - Separate 5 V bench supply to the PCB's +5V rail (STEMMA QT V+ is
//      3.3 V; the WH2004A LCD needs >= 4.5 V).  Common the grounds.
// =============================================================================
#include <cstdio>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "esp_chip_info.h"
#include "esp_rom_sys.h"      // esp_rom_delay_us
#include "nvs_flash.h"
#include "driver/i2c_master.h"

#include "pin_map.h"
#include "pcf8575.h"
#include "lcd_hd44780.h"

#ifdef LCD_BRINGUP

namespace {

constexpr char TAG[] = "lcd_bringup";

// MCP4725 contrast DAC
constexpr uint8_t  MCP4725_ADDR       = 0x62;
constexpr uint16_t MCP4725_CODE_0V7   = 573;   // 0.7 V at 5 V Vref (0.7/5*4095)

// PWM parameters
constexpr int  PWM_BITS         = 6;        // 6-bit BAM -> 64 levels
constexpr int  PWM_LEVELS       = 1 << PWM_BITS;   // 64
constexpr int  PWM_FRAME_US     = 16667;    // 60 Hz frame period
constexpr int  PWM_UNIT_US      = PWM_FRAME_US / (PWM_LEVELS - 1);  // ~264 us

// Color cycle timing
constexpr int64_t WORD_DURATION_US = 5'000'000;   // 5 s per word
constexpr int     N_COLORS         = 3;

const char *kWords[N_COLORS] = { "Red  ", "Green", "Blue " };  // padded to 5 chars

i2c_master_bus_handle_t s_bus = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;

// --------------------------------------------------------------------------
//  I2C bus + MCP4725 helpers
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

// MCP4725 fast-mode write (no EEPROM burn).  Two bytes:
//   byte 0: C2 C1 PD1 PD0 D11 D10 D9 D8   (C2:C1 = 00 -> fast mode, normal power)
//   byte 1: D7 D6 D5 D4 D3 D2 D1 D0
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
        (uint8_t)((code_12bit >> 8) & 0x0F),   // C2..PD0 = 0, D11..D8
        (uint8_t)(code_12bit & 0xFF),          // D7..D0
    };
    e = i2c_master_transmit(dev, buf, sizeof(buf), 100);
    i2c_master_bus_rm_device(dev);
    return e;
}

// --------------------------------------------------------------------------
//  6-bit bit-angle modulation on the three backlight FET gates.
//
//  One call = one 16.7 ms frame; the task loops calling this back-to-back.
//  Sub-frames are emitted in ascending bit order (weights 1, 2, 4, 8, 16, 32);
//  each sub-frame does one PCF8575 write and then delays for weight * unit_us.
//
//  Argument duty_* is 0..63 (0 = off, 63 = full).
// --------------------------------------------------------------------------
void backlight_pwm_frame(uint8_t duty_r, uint8_t duty_g, uint8_t duty_b) {
    for (int bit = 0; bit < PWM_BITS; ++bit) {
        const bool r_on = (duty_r >> bit) & 1;
        const bool g_on = (duty_g >> bit) & 1;
        const bool b_on = (duty_b >> bit) & 1;
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_r, r_on);
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_g, g_on);
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_b, b_on);
        s_pcf.apply();

        // Busy-wait -- we're in a dedicated task and the slot times (>= 264 us
        // at bit 0, up to ~8.4 ms at bit 5) are shorter than a FreeRTOS tick
        // at CONFIG_FREERTOS_HZ = 1000.  Sleeping the CPU would sacrifice
        // timing precision for no bus benefit.
        esp_rom_delay_us(PWM_UNIT_US * (1u << bit));
    }
}

// --------------------------------------------------------------------------
//  Duty helpers
// --------------------------------------------------------------------------
// Convert percent (0..100) to a 6-bit BAM duty (0..63).
uint8_t pct_to_duty(int pct) {
    if (pct <   0) pct = 0;
    if (pct > 100) pct = 100;
    return (uint8_t)((pct * (PWM_LEVELS - 1) + 50) / 100);
}

// Triangular wave over a 5 s phase, output 40..60..40 (percent).
int triangle_40_60(int64_t phase_us) {
    // phase_us in [0, WORD_DURATION_US).  Map to 0..1..0.
    const float x = (float)phase_us / (float)WORD_DURATION_US;   // 0..1
    const float tri = (x < 0.5f) ? (2.0f * x) : (2.0f * (1.0f - x));
    return 40 + (int)(tri * 20.0f + 0.5f);
}

// --------------------------------------------------------------------------
//  LCD text
// --------------------------------------------------------------------------
void render_header() {
    s_lcd.clear();
    s_lcd.set_cursor(0, 0);
    s_lcd.print(" LCD bring-up test  ");   // 20 chars
}

void render_word(int active_idx) {
    // Row 2, roughly centered ("Green" is 5 chars -> column 7 in a 20-wide row)
    s_lcd.set_cursor(2, 0);
    s_lcd.print("                    ");   // wipe line
    s_lcd.set_cursor(2, 7);
    s_lcd.print(kWords[active_idx]);
}

void render_percentages(int r, int g, int b) {
    char buf[21];
    std::snprintf(buf, sizeof(buf), "R:%3d G:%3d B:%3d   ", r, g, b);
    s_lcd.set_cursor(3, 0);
    s_lcd.print(buf);
}

// --------------------------------------------------------------------------
//  Bring-up task
// --------------------------------------------------------------------------
void bringup_task(void *) {
    render_header();

    const int64_t t0 = esp_timer_get_time();
    int  last_active = -1;
    int  last_pcts[3] = { -1, -1, -1 };
    int64_t last_text_us = 0;

    while (true) {
        const int64_t now      = esp_timer_get_time();
        const int64_t elapsed  = now - t0;
        const int     active   = (int)((elapsed / WORD_DURATION_US) % N_COLORS);
        const int64_t phase_us = elapsed % WORD_DURATION_US;

        if (active != last_active) {
            render_word(active);
            last_active = active;
        }

        // Percentages: active channel triangles 40..60; others held at 50.
        int pct[3] = { 50, 50, 50 };
        pct[active] = triangle_40_60(phase_us);

        // Update the bottom-row percentages roughly 5x per second (avoid
        // spamming the LCD every PWM frame).
        if (now - last_text_us > 200'000 &&
            (pct[0] != last_pcts[0] || pct[1] != last_pcts[1] ||
             pct[2] != last_pcts[2])) {
            render_percentages(pct[0], pct[1], pct[2]);
            last_pcts[0] = pct[0]; last_pcts[1] = pct[1]; last_pcts[2] = pct[2];
            last_text_us = now;
        }

        backlight_pwm_frame(pct_to_duty(pct[0]),
                            pct_to_duty(pct[1]),
                            pct_to_duty(pct[2]));
    }
}

}  // namespace

extern "C" void app_main() {
    std::printf("\n=== LCD bring-up test ===\n");
    std::printf(" build: %s %s\n", __DATE__, __TIME__);
    std::printf(" PCF8575 @ 0x%02X, MCP4725 @ 0x%02X, WH2004A over 4-bit\n",
                pins::I2C_ADDR_PCF8575_PANEL, MCP4725_ADDR);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(i2c_bus_init());
    ESP_LOGI(TAG, "I2C up: SDA=GPIO%d SCL=GPIO%d @ %lu Hz",
             (int)pins::I2C_SDA, (int)pins::I2C_SCL,
             (unsigned long)pins::I2C_HZ);

    ESP_ERROR_CHECK(s_pcf.begin(s_bus, pins::I2C_ADDR_PCF8575_PANEL));

    // Set LCD contrast BEFORE HD44780 init so characters are visible on the
    // first frame.
    esp_err_t e = mcp4725_set(MCP4725_ADDR, MCP4725_CODE_0V7);
    if (e != ESP_OK) {
        ESP_LOGE(TAG, "MCP4725 set failed: %s (LCD contrast may be off)",
                 esp_err_to_name(e));
    } else {
        ESP_LOGI(TAG, "MCP4725 -> code %u (~0.7 V @ 5 V Vref)",
                 (unsigned)MCP4725_CODE_0V7);
    }

    ESP_ERROR_CHECK(s_lcd.begin(&s_pcf));

    // Kick off the cycle task.  Pinned to CORE_MONITOR (core 0) with priority
    // just above idle -- we don't need real-time, and CORE_KEYING isn't in
    // play in this bring-up.
    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "bring-up running");
}

#endif  // LCD_BRINGUP

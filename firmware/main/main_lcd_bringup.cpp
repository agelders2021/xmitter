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
//    5. Spawn a bit-angle-modulation PWM sub-frame timer that runs the R/G/B
//       backlight FETs at independent duties, plus a task that cycles
//       "Red" / "Green" / "Blue" every 5 s and moves the active channel's
//       duty in a 40 -> 60 -> 40 % triangle over each 5 s window.
//
//  PWM architecture:
//    esp_timer one-shot fires at each BAM sub-frame boundary.  Callback
//    runs on the esp_timer service task, takes a mutex, writes the three
//    backlight bits via the PCF8575 shadow, releases the mutex, then
//    re-arms itself for the next slot.  LCD text writes take the same
//    mutex so an LCD row update never interrupts a sub-frame mid-write.
//    Task never busy-waits, so nothing pins a CPU core.
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
#include "freertos/semphr.h"

#include "esp_log.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "esp_chip_info.h"
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

// PWM parameters -- 5-bit BAM (32 levels).  Slots run 500 us -> 8 ms.
// Frame = (2^5 - 1) * 500 us = 15.5 ms  ->  ~65 Hz.  Well above flicker
// threshold, and the longest slot (8 ms) is short enough that a delayed
// LCD text update never darkens a whole frame.
constexpr int PWM_BITS      = 5;
constexpr int PWM_LEVELS    = 1 << PWM_BITS;      // 32
constexpr int PWM_UNIT_US   = 500;
constexpr int PWM_FRAME_US  = (PWM_LEVELS - 1) * PWM_UNIT_US;   // 15500

// Color cycle timing
constexpr int64_t WORD_DURATION_US = 5'000'000;   // 5 s per word
constexpr int     N_COLORS         = 3;

const char *kWords[N_COLORS] = { "Red  ", "Green", "Blue " };  // padded

// --------------------------------------------------------------------------
//  Shared state
// --------------------------------------------------------------------------
i2c_master_bus_handle_t s_bus       = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;
SemaphoreHandle_t       s_pcf_mutex = nullptr;   // serializes PCF8575 shadow ops
esp_timer_handle_t      s_pwm_timer = nullptr;

// Backlight duty targets, 0..PWM_LEVELS-1.  Byte-sized so single-byte writes
// are atomic; readers may briefly observe an old-then-new mix across channels,
// which is invisible.
volatile uint8_t s_duty_r = PWM_LEVELS / 2;
volatile uint8_t s_duty_g = PWM_LEVELS / 2;
volatile uint8_t s_duty_b = PWM_LEVELS / 2;

// Current BAM sub-frame index (0..PWM_BITS-1).  Only touched from the timer
// callback, so no synchronization needed.
uint8_t s_bit_idx = 0;

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
        (uint8_t)((code_12bit >> 8) & 0x0F),
        (uint8_t)(code_12bit & 0xFF),
    };
    e = i2c_master_transmit(dev, buf, sizeof(buf), 100);
    i2c_master_bus_rm_device(dev);
    return e;
}

// --------------------------------------------------------------------------
//  esp_timer PWM callback -- one BAM sub-frame per firing.
//
//  Runs on the esp_timer service task (default dispatch = ESP_TIMER_TASK).
//  Takes the shared PCF8575 mutex with a short timeout; if the mutex is
//  held by an LCD write, we skip this sub-frame and re-arm normally.  The
//  visible cost of a skipped sub-frame is at most one BAM bit's worth of
//  brightness on one channel, invisible in practice.
// --------------------------------------------------------------------------
void pwm_timer_cb(void *) {
    const uint8_t bit = s_bit_idx;
    const uint8_t r   = s_duty_r;
    const uint8_t g   = s_duty_g;
    const uint8_t b   = s_duty_b;

    if (xSemaphoreTake(s_pcf_mutex, pdMS_TO_TICKS(2)) == pdTRUE) {
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_r, (r >> bit) & 1);
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_g, (g >> bit) & 1);
        s_pcf.shadow_bit(lcd::kDefaultPinMap.bl_b, (b >> bit) & 1);
        s_pcf.apply();
        xSemaphoreGive(s_pcf_mutex);
    }
    // If we couldn't get the mutex we just skip this slot; timing model
    // still marches forward.

    const int slot_us = PWM_UNIT_US * (1u << bit);
    s_bit_idx = (bit + 1) % PWM_BITS;
    esp_timer_start_once(s_pwm_timer, slot_us);
}

// --------------------------------------------------------------------------
//  Duty helpers
// --------------------------------------------------------------------------
uint8_t pct_to_duty(int pct) {
    if (pct <   0) pct = 0;
    if (pct > 100) pct = 100;
    return (uint8_t)((pct * (PWM_LEVELS - 1) + 50) / 100);
}

// Triangular 40..60..40 percent over one WORD_DURATION_US window.
int triangle_40_60(int64_t phase_us) {
    const float x = (float)phase_us / (float)WORD_DURATION_US;
    const float tri = (x < 0.5f) ? (2.0f * x) : (2.0f * (1.0f - x));
    return 40 + (int)(tri * 20.0f + 0.5f);
}

// --------------------------------------------------------------------------
//  LCD text -- all callers MUST hold s_pcf_mutex.
// --------------------------------------------------------------------------
void render_header_locked() {
    s_lcd.clear();
    s_lcd.set_cursor(0, 0);
    s_lcd.print(" LCD bring-up test  ");
}

void render_word_locked(int active_idx) {
    s_lcd.set_cursor(2, 0);
    s_lcd.print("                    ");
    s_lcd.set_cursor(2, 7);
    s_lcd.print(kWords[active_idx]);
}

void render_percentages_locked(int r, int g, int b) {
    char buf[21];
    std::snprintf(buf, sizeof(buf), "R:%3d G:%3d B:%3d   ", r, g, b);
    s_lcd.set_cursor(3, 0);
    s_lcd.print(buf);
}

// --------------------------------------------------------------------------
//  Bring-up task -- updates duty targets and LCD text.
// --------------------------------------------------------------------------
void bringup_task(void *) {
    xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
    render_header_locked();
    xSemaphoreGive(s_pcf_mutex);

    const int64_t t0 = esp_timer_get_time();
    int  last_active   = -1;
    int  last_pct[3]   = { -1, -1, -1 };
    int64_t last_txt_us = 0;

    while (true) {
        const int64_t now      = esp_timer_get_time();
        const int64_t elapsed  = now - t0;
        const int     active   = (int)((elapsed / WORD_DURATION_US) % N_COLORS);
        const int64_t phase_us = elapsed % WORD_DURATION_US;

        // Compute target percentages.
        // SOLO TEST: active channel at 100%, others at 0%.  Isolates each
        // color so we can see whether the channels themselves are vivid or
        // whether the "always-50%-baseline" scheme was washing everything out.
        (void)phase_us;
        int pct[3] = { 0, 0, 0 };
        pct[active] = 100;

        // Push new duty to the PWM state.  Single-byte writes are atomic.
        s_duty_r = pct_to_duty(pct[0]);
        s_duty_g = pct_to_duty(pct[1]);
        s_duty_b = pct_to_duty(pct[2]);

        // LCD writes: word row when it changes, percentages row at 1 Hz.
        bool need_word = (active != last_active);
        bool need_pcts = (now - last_txt_us > 1'000'000) &&
                        (pct[0] != last_pct[0] ||
                         pct[1] != last_pct[1] ||
                         pct[2] != last_pct[2]);
        if (need_word || need_pcts) {
            xSemaphoreTake(s_pcf_mutex, portMAX_DELAY);
            if (need_word) {
                render_word_locked(active);
                last_active = active;
            }
            if (need_pcts) {
                render_percentages_locked(pct[0], pct[1], pct[2]);
                last_pct[0] = pct[0]; last_pct[1] = pct[1]; last_pct[2] = pct[2];
                last_txt_us = now;
            }
            xSemaphoreGive(s_pcf_mutex);
        }

        vTaskDelay(pdMS_TO_TICKS(50));
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

    // Contrast DAC first so characters are legible on the first frame.
    if (esp_err_t e = mcp4725_set(MCP4725_ADDR, MCP4725_CODE_0V7); e != ESP_OK) {
        ESP_LOGE(TAG, "MCP4725 set failed: %s (LCD contrast may be off)",
                 esp_err_to_name(e));
    } else {
        ESP_LOGI(TAG, "MCP4725 -> code %u (~0.7 V @ 5 V Vref)",
                 (unsigned)MCP4725_CODE_0V7);
    }

    ESP_ERROR_CHECK(s_lcd.begin(&s_pcf));

    // Serializes any code that touches the PCF8575 shadow (PWM timer +
    // LCD text updates).  Created BEFORE the timer starts.
    s_pcf_mutex = xSemaphoreCreateMutex();
    if (!s_pcf_mutex) {
        ESP_LOGE(TAG, "mutex alloc failed");
        return;
    }

    // Kick off the PWM timer.  ESP_TIMER_TASK dispatch = callback runs on
    // the esp_timer service task (safe to do I2C from there).
    esp_timer_create_args_t timer_args = {};
    timer_args.callback        = &pwm_timer_cb;
    timer_args.arg             = nullptr;
    timer_args.dispatch_method = ESP_TIMER_TASK;
    timer_args.name            = "backlight_bam";
    ESP_ERROR_CHECK(esp_timer_create(&timer_args, &s_pwm_timer));
    ESP_ERROR_CHECK(esp_timer_start_once(s_pwm_timer, PWM_UNIT_US));

    // Text/duty update task, low priority, pinned to CORE_MONITOR.
    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "bring-up running (%d-bit BAM, %d us unit, ~%d Hz frame)",
             PWM_BITS, PWM_UNIT_US, 1'000'000 / PWM_FRAME_US);
}

#endif  // LCD_BRINGUP

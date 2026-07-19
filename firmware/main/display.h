// =============================================================================
//  display.h -- high-level driver for the front-panel WH2004A LCD.
//
//  Owns the front-panel PCF8575 (0x21) + the HD44780 character driver, and
//  runs a periodic refresh task on CORE_MONITOR.  Line 1 currently shows
//  the VFO frequency with thousands separators.
//
//  Other modules can call g_display.mark_dirty() to signal that a line
//  needs re-rendering; otherwise the task re-checks state each period and
//  only rewrites lines whose content has changed (so we don't pound the
//  I2C bus with identical data).
// =============================================================================
#pragma once

#include <cstdint>

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c_master.h"

#include "pcf8575.h"
#include "lcd_hd44780.h"

namespace display {

class Display {
 public:
    // Attach the PCF8575 to the shared I2C bus, then run the HD44780 init.
    // Idempotent.  Address defaults to pins::I2C_ADDR_PCF8575_PANEL (0x21).
    esp_err_t begin(i2c_master_bus_handle_t bus);

    // Spawn the periodic refresh task pinned to `core` at priority `prio`.
    esp_err_t start(BaseType_t   core,
                    UBaseType_t  prio        = 3,
                    uint32_t     stack_words = 4096,
                    TickType_t   period      = pdMS_TO_TICKS(200));

    // Force a refresh next tick (currently just re-reads VFO frequency).
    void mark_dirty();

    // Access to the LCD for one-off writes (test commands from the shell).
    lcd::HD44780 &lcd() { return lcd_; }

 private:
    static void task_entry(void *self);
    void run();
    void refresh_line1_();     // frequency line

    pcf8575::Device pcf_;
    lcd::HD44780    lcd_;
    TaskHandle_t    handle_        = nullptr;
    TickType_t      period_        = pdMS_TO_TICKS(200);
    volatile bool   dirty_         = true;
    uint32_t        last_freq_hz_  = 0;
    bool            begun_         = false;
};

extern Display g_display;

// Format a uint32_t in decimal with commas as thousands separators.
// Example: 14200000 -> "14,200,000".  Returns number of chars written
// (not counting the trailing NUL).  If buflen is too small, writes nothing
// and returns 0.
size_t format_with_commas(char *buf, size_t buflen, uint32_t value);

}  // namespace display

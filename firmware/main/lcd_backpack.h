// =============================================================================
//  lcd_backpack.h -- HD44780 driver for the standard "I2C LCD" PCF8574
//  backpack (Mantech LCD2004 / Handson DSP-1165 / generic "QAPASS" modules).
//
//  Bit layout on the PCF8574 (fixed by the backpack PCB, not configurable):
//    P0 = RS, P1 = R/W, P2 = E, P3 = Backlight (1 = ON),
//    P4..P7 = D4..D7.  R/W is driven low always (write-only).
//
//  Factory address is 0x27 for PCF8574T, 0x3F for PCF8574AT; begin() with
//  addr=0 auto-detects by probing both.
// =============================================================================
#pragma once

#include <cstdint>

#include "esp_err.h"
#include "driver/i2c_master.h"

namespace lcd_backpack {

class Device {
 public:
    esp_err_t begin(i2c_master_bus_handle_t bus,
                    uint8_t                 addr = 0,
                    uint8_t                 rows = 2);

    esp_err_t clear();
    esp_err_t home();
    esp_err_t set_cursor(uint8_t row, uint8_t col);
    esp_err_t print(const char *s);
    esp_err_t print(char c);
    esp_err_t display_on(bool on);
    esp_err_t backlight(bool on);

    uint8_t addr() const { return addr_; }

 private:
    esp_err_t write_nibble_(uint8_t nibble, bool rs);
    esp_err_t write_byte_(uint8_t byte,     bool rs);
    esp_err_t cmd_(uint8_t byte)  { return write_byte_(byte, false); }
    esp_err_t data_(uint8_t byte) { return write_byte_(byte, true);  }
    esp_err_t i2c_write_(uint8_t v);

    i2c_master_dev_handle_t dev_       = nullptr;
    uint8_t                 addr_      = 0;
    uint8_t                 rows_      = 2;
    uint8_t                 bl_mask_   = 0x08;   // P3 high by default (BL on)
};

}  // namespace lcd_backpack

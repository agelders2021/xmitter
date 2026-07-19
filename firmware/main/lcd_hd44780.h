// =============================================================================
//  lcd_hd44780.h -- HD44780-compatible character LCD driver over PCF8575.
//
//  Wire model: front-panel Winstar WH2004A-CFH-JT# 20x4 LCD driven in 4-bit
//  parallel mode.  Six PCF8575 pins carry the interface: RS, E, DB4-DB7.
//  R/W is tied to GND on the schematic (write-only).  Three more PCF8575
//  pins can drive the RGB backlight FET gates through the on-board
//  current-limit resistors (2N7000 low-side switches, 1 = LED on).
//
//  Which PCF8575 bit maps to which LCD signal is set by the PinMap struct
//  handed to begin().  See lcd_hd44780.cpp for the currently-assumed
//  default assignment; verify against KiCAD/frontpanel/frontpanel.kicad_sch
//  before you flash the first hardware.
//
//  Threading: the LCD driver is not internally locked.  The `display`
//  module owns a single instance and only writes to it from its own task,
//  so no external synchronization is needed.  If you ever want to write
//  from more than one task, wrap the calls in a mutex.
// =============================================================================
#pragma once

#include <cstdint>
#include <cstddef>

#include "esp_err.h"

#include "pcf8575.h"

namespace lcd {

// PCF8575 bit positions (0..15) for each LCD signal.  Bit 0 = P00, bit 7 = P07,
// bit 8 = P10, bit 15 = P17.
struct PinMap {
    uint8_t rs;      // register-select
    uint8_t e;       // enable strobe (falling edge latches data)
    uint8_t db4;     // data lines D4..D7 (4-bit mode)
    uint8_t db5;
    uint8_t db6;
    uint8_t db7;
    uint8_t bl_r;    // backlight red   FET gate   (1 = ON)
    uint8_t bl_g;    // backlight green FET gate
    uint8_t bl_b;    // backlight blue  FET gate
};

// Default assignment matching the current best-guess frontpanel schematic.
// If you rewired at layout time, change these numbers in lcd_hd44780.cpp
// (or override via a new PinMap at begin()) -- nothing else references them.
extern const PinMap kDefaultPinMap;

class HD44780 {
 public:
    // Attach to an already-begin()-ed PCF8575.  Runs the HD44780 4-bit
    // init sequence per Winstar datasheet page 18 (4-bit interface).
    // Idempotent -- calling begin() again re-runs the init sequence, which
    // is harmless.
    esp_err_t begin(pcf8575::Device *pcf, const PinMap &pins = kDefaultPinMap);

    // -- Display control ----------------------------------------------------
    esp_err_t clear();                        // clear DDRAM, cursor -> 0,0
    esp_err_t home();                         // cursor -> 0,0 (no clear)
    esp_err_t set_cursor(uint8_t row, uint8_t col);
    esp_err_t print(const char *s);
    esp_err_t print(char c);
    esp_err_t display_on(bool on);            // hide/show the display

    // -- Backlight ----------------------------------------------------------
    // Bool per channel.  For now this is on/off only; software PWM through
    // the PCF8575 is possible later but I2C bandwidth caps effective PWM
    // frequency at ~100 Hz.
    esp_err_t backlight_rgb(bool r, bool g, bool b);

 private:
    esp_err_t write_nibble_(uint8_t nibble, bool rs);
    esp_err_t write_byte_(uint8_t byte, bool rs);
    esp_err_t cmd_(uint8_t byte)       { return write_byte_(byte, false); }
    esp_err_t data_(uint8_t byte)      { return write_byte_(byte, true);  }
    esp_err_t pulse_e_();

    pcf8575::Device *pcf_  = nullptr;
    PinMap           pins_ = {};
};

}  // namespace lcd

// =============================================================================
//  pcf8575.h -- thin driver for the NXP/TI PCF8575 I2C 16-bit GPIO expander.
//
//  The chip has no register map: write two bytes to set all 16 outputs, read
//  two bytes to read all 16 inputs.  Outputs are quasi-bidirectional -- "1"
//  is weakly pulled high through an internal ~100 uA source, "0" is actively
//  driven to GND.  Write "1" to a bit before using it as an input.
//
//  Byte order per datasheet: byte 1 = P00-P07 (bits 0-7 of the 16-bit shadow),
//  byte 2 = P10-P17 (bits 8-15).
//
//  Class is a plain wrapper -- multiple instances are fine (there are two
//  PCF8575s on this rig: 0x20 for relay drives on the analog board, 0x21 for
//  the LCD + LEDs on the front panel).
// =============================================================================
#pragma once

#include <cstdint>

#include "esp_err.h"
#include "driver/i2c_master.h"

namespace pcf8575 {

class Device {
 public:
    // Add the device to the shared I2C bus.  `addr` is the 7-bit I2C address.
    // Idempotent (safe to call more than once).
    esp_err_t begin(i2c_master_bus_handle_t bus, uint8_t addr);

    // Write the full 16-bit output word to the chip.
    esp_err_t write(uint16_t value);

    // Read the full 16-bit input word.  For pins you want to read as inputs,
    // the corresponding output bit must have been left at "1" so the pin
    // floats via the internal pull-up.
    esp_err_t read(uint16_t *value);

    // -- Shadow-based helpers ------------------------------------------------
    // For LCD driving we build up a full 16-bit word from many independent
    // "set this bit" calls, then flush once with apply().  The shadow avoids
    // needing to read back to modify one bit.
    void      set_shadow(uint16_t v)              { shadow_ = v; }
    uint16_t  shadow() const                      { return shadow_; }
    void      shadow_bit(uint8_t bit, bool value);
    esp_err_t apply()                             { return write(shadow_); }

 private:
    i2c_master_dev_handle_t dev_ = nullptr;
    uint16_t                shadow_ = 0xFFFFu;   // all high (all inputs) at power-on
};

}  // namespace pcf8575

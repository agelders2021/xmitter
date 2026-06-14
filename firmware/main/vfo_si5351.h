// =============================================================================
//  vfo_si5351.h
//
//  Minimal Si5351A driver for the xmitter VFO.  Generates the 14.000-14.350 MHz
//  carrier that feeds the keyer's pad/LPF/buffer chain.  CLK0 only — CLK1 and
//  CLK2 are left disabled.
//
//  Design references:
//    - Documentation/20m-leveled-keyed-buffer.md  (signal chain context)
//    - Si5351A/B/C-B datasheet (Rev. 1.0, SiLabs)
//    - AN619 — Si5351 register programming notes
//
//  Bus: shared I2C with the rest of monitoring (see pin_map.h I2C_PORT).
//  Caller is responsible for initializing the I2C master bus once at boot
//  and passing the bus handle to vfo_init().
// =============================================================================
#pragma once

#include <cstdint>
#include "esp_err.h"
#include "driver/i2c_master.h"

namespace vfo {

// Default operating frequency for first power-on (also the band centre).
constexpr uint32_t DEFAULT_FREQ_HZ = 14200000;

// Crystal on the Adafruit Si5351A breakout (factory part: 25.000 MHz, ±10 ppm).
constexpr uint32_t XTAL_HZ_DEFAULT = 25000000;

// Initialize the chip.  Adds the Si5351 onto the shared I2C bus, resets it
// into a known state, and disables all outputs.  CLK0 stays off until
// vfo_on() is called.  Idempotent — safe to call again to recover.
esp_err_t init(i2c_master_bus_handle_t bus);

// Set CLK0 to f_hz.  Range: 8 kHz – 160 MHz (Si5351 spec); xmitter only ever
// needs 14.0–14.4 MHz so we don't bother with the multi-band fractional cases.
// Programmes PLLA + Multisynth0 from the requested frequency.  Output state
// (on/off) is unchanged — call vfo_on() once you want RF.
esp_err_t set_freq(uint32_t f_hz);

// Enable / disable CLK0 output (drive strength stays at 8 mA — see datasheet
// table for Si5351A drive levels).  vfo_off() also goes to power-down state.
esp_err_t on();
esp_err_t off();

// Last commanded frequency in Hz (for status reports).
uint32_t current_freq();

// True if the driver believes CLK0 is currently on.
bool is_on();

}  // namespace vfo

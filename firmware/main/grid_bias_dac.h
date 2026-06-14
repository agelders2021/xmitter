// =============================================================================
//  grid_bias_dac.h — per-tube grid bias control (stub).
//
//  Hardware (per Documentation/2026-06-08-pa-validation.md §"Two-state bias"):
//    MCP4728 quad I2C DAC → 2× OPA454 HV op-amps → 6146B grid pins.
//    Maps DAC code 0 → −90 V (IDLE / deep cutoff),
//                code 4095 → −50 V (OPERATE / shallow class C).
//
//  Two operating states:
//    IDLE     — key-up, both tubes biased off, 0 mA plate current.
//    OPERATE  — key-down, shallow class C; envelope DAC then modulates drive.
//
//  Sequencing rules (cw_envelope_keyer.md §"Firmware sequencing"):
//    Key down: IDLE→OPERATE bias, wait 200 µs, then start envelope ramp.
//    Key up:   envelope tail to null, wait 1 ms guard, then OPERATE→IDLE.
//
//  TODO: real implementation once MCP4728 is on the board and per-tube
//  calibration constants are in NVS.
// =============================================================================
#pragma once

#include "esp_err.h"
#include "driver/i2c_master.h"

namespace bias {

enum class State { Idle, Operate };

esp_err_t init(i2c_master_bus_handle_t bus);

// Slam both tubes to the given state.  Returns immediately; settling time
// (~200 µs grid-side RC) is the caller's responsibility to wait out before
// changing the envelope DAC code.
esp_err_t set_state(State s);

// Per-tube fine trim around the commanded state, signed counts, +/-N around
// the centre code.  Used to balance tube spread (typically ±2–3 V).
esp_err_t trim(int tube_id, int delta_counts);

State current_state();

}  // namespace bias

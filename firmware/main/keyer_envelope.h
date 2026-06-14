// =============================================================================
//  keyer_envelope.h
//
//  Raised-cosine CW envelope generator.  Public API is intentionally tiny —
//  the WinKey state machine only ever needs four entry points.  See
//  Documentation/cw_envelope_keyer.md for the full design rationale; do not
//  refactor away the "single chasing phase" loop or move SPI into an ISR.
// =============================================================================
#pragma once

#include "esp_err.h"

namespace keyer {

// Bring up the MCP4921 SPI peripheral, build the raised-cosine LUT, and
// spawn the pinned playout task on CORE_KEYING.  Call once from app_main()
// AFTER the monitoring core's I2C bus is up, so power-supply sequencing has
// settled before the modulator can be driven.
esp_err_t envelope_init();

// Update the per-tick phase step.  Call whenever the WPM setpoint changes.
// Safe from any core.
void set_wpm(float wpm);

// Element edge callbacks from the WinKey scheduler.
void key_down();
void key_up();

}  // namespace keyer

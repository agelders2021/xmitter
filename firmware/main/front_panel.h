// =============================================================================
//  front_panel.h — rotary encoder + push-button front panel (stub).
//
//  Two encoders so far (more "to be defined"):
//    FREQ  — Δ counts move VFO frequency (units: Hz, scale set by step mode).
//    POWER — Δ counts move power setpoint.  POWER fans out internally to
//            both the envelope DAC CODE_FULL constant and the OPERATE-state
//            grid bias offset (see leveled-buffer.md / pa-validation.md).
//
//  Pushbuttons (encoder shafts) cycle step size / engage menus — TBD.
//
//  Eventual implementation: PCNT units for clean quadrature decode on the
//  S3, ISR-fed event queue → debounced delta forwarded to vfo::set_freq()
//  and bias::trim() respectively.
// =============================================================================
#pragma once

#include "esp_err.h"

namespace front_panel {

esp_err_t init();    // spawn polling/PCNT task pinned to CORE_MONITOR

// Direct setters — used by the USB-CDC shell and (eventually) by stored
// presets, in addition to encoder twist.
esp_err_t set_freq_hz(uint32_t hz);
esp_err_t set_power_pct(uint8_t pct);

uint32_t freq_hz();
uint8_t  power_pct();

}  // namespace front_panel

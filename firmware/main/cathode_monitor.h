// =============================================================================
//  cathode_monitor.h — per-tube cathode-current monitoring (stub).
//
//  Hardware: ADS1115 16-bit I2C ADC, two channels (one per tube), sampling
//  the buffered cathode-current sense voltage at the top of R_C (10 Ω).
//  See Documentation/pa_cathode_monitor.md for the full 7-layer fail-safe.
//
//  Firmware path (Level 6) — eventual:
//    - Sample @ 1 kHz/ch with a 10-sample running average.
//    - Thresholds:
//        warn  > 1.2 V (120 mA) for >50 ms → soft fault, throttle envelope.
//        hard  > 1.5 V (150 mA) for >5 ms  → call fault::assert_overcurrent().
//    - Log every 1 s during normal operation.
// =============================================================================
#pragma once

#include "esp_err.h"
#include "driver/i2c_master.h"

namespace cathode {

esp_err_t init(i2c_master_bus_handle_t bus);

// Most-recent per-tube average current in milliamps.
float current_mA(int tube_id);

}  // namespace cathode

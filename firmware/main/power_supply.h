// =============================================================================
//  power_supply.h — main HV supply sequencing (stub).
//
//  Hardware is not yet designed.  The eventual flow looks like:
//    psu_on()  : filament warm-up → bias supply → screen → plate, gated by
//                ready feedback at each step.
//    psu_off() : reverse sequence with discharge delays.
//
//  For now: presents the API so main.cpp + the shell can call it harmlessly.
// =============================================================================
#pragma once

#include "esp_err.h"

namespace psu {

enum class State { Off, WarmingUp, Ready, ShuttingDown, Fault };

esp_err_t init();
esp_err_t on();
esp_err_t off();
State     state();

}  // namespace psu

// =============================================================================
//  fault_handler.h — hardware fail-safe gate + soft-fault logging (stub).
//
//  Owns the GPIO that drives the high-side MOSFET in the screen-voltage
//  supply.  Open = screen at 0 V = tubes guaranteed off within ~100 µs
//  (cap discharge).  See Documentation/pa_cathode_monitor.md §"Watchdog gate".
//
//  Trigger sources:
//    - hardware comparator latch (LM393, wired-OR to GPIO).
//    - cathode-monitor soft trip (1.5 V hard threshold).
//    - esp_task_wdt timeout on the keying or monitoring task.
//    - explicit fault::assert_*() calls from any module.
//
//  Recovery requires an explicit fault::clear() after the underlying
//  condition is gone — never auto-clears.
// =============================================================================
#pragma once

#include "esp_err.h"

namespace fault {

enum class Cause {
    None,
    Overcurrent,    // cathode threshold exceeded
    HardwareLatch,  // LM393 comparator tripped
    Watchdog,       // esp_task_wdt fired
    PSU,            // power-supply ready signal lost
    Firmware,       // any module's assert
};

esp_err_t init();

// Assert a fault.  Drops the screen-voltage gate immediately; logs cause and
// timestamp to NVS for post-mortem.  Idempotent if already asserted.
esp_err_t assert_fault(Cause c);

// Clear after the condition is verified gone.  Re-arms the hardware gate.
esp_err_t clear();

Cause current_cause();
bool  is_asserted();

}  // namespace fault

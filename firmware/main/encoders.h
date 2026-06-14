// =============================================================================
//  encoders.h — rotary encoder driver (PCNT-based, quadrature decode).
//
//  Three encoders so far (extend by adding a new pcnt_unit_handle_t + entry):
//    FREQ — high-PPR optical (MBL-600-100P-5L): tunes the VFO.
//    STEP — Bourns PEC11 mechanical: cycles the frequency step table.
//    FUNC — Bourns PEC11 mechanical: future menu/function selection.
//
//  Each PEC11 click = 4 quadrature transitions = 1 detent.  We divide PCNT
//  counts by 4 so a single click of the step or func wheel reads as one
//  delta.  The optical encoder produces 4 × PPR transitions per turn
//  (400 at 100 PPR); we use those raw — a fast spin should change the band
//  edge quickly without feeling sluggish.
//
//  Step table — single source of truth, easy to edit.  Order matters: the
//  STEP encoder cycles through it left/right in this order.
// =============================================================================
#pragma once

#include <cstdint>
#include <cstddef>
#include "esp_err.h"

namespace encoders {

// ---- Frequency step table ---------------------------------------------------
//  Edit this list to add / remove / reorder step sizes.  The STEP encoder
//  cycles through it; `default_step_index()` returns the boot-time selection.
//  Values are in Hz applied per quadrature count from the FREQ encoder.
constexpr uint32_t FREQ_STEP_HZ_TABLE[] = {
    1,    // 1 Hz   (fine tuning)
    5,    // 5 Hz
    10,   // 10 Hz
    20,   // 20 Hz
    50,   // 50 Hz
    100,  // 100 Hz
    500,  // 500 Hz
    1000, // 1 kHz  (fast scan)
};
constexpr size_t FREQ_STEP_TABLE_LEN =
    sizeof(FREQ_STEP_HZ_TABLE) / sizeof(FREQ_STEP_HZ_TABLE[0]);
constexpr size_t FREQ_STEP_DEFAULT_INDEX = 4;   // 50 Hz at boot

// ---- Operating frequency limits (20 m CW band) ------------------------------
constexpr uint32_t FREQ_MIN_HZ = 14000000;
constexpr uint32_t FREQ_MAX_HZ = 14350000;

// ---- API --------------------------------------------------------------------
//  Spawns the polling task on CORE_MONITOR (priority 4, 10 ms tick).  All
//  encoders are armed at the same time; the FREQ encoder is wired through
//  to vfo::set_freq(), the STEP encoder cycles the step table, the FUNC
//  encoder counts are exposed via func_delta() for future use.
esp_err_t init();

// Currently-selected step (Hz/click), and its index into the table.
uint32_t step_hz();
size_t   step_index();

// Force the step table index (clamped to [0, FREQ_STEP_TABLE_LEN-1]).
void set_step_index(size_t i);

// Read & clear the accumulated FUNC encoder delta (signed clicks since last
// call).  Returns 0 when nothing has moved.
int  func_delta();

// True if the FUNC / STEP pushbutton was pressed since the last poll
// (auto-clears on read).
bool step_button_pressed();
bool func_button_pressed();

}  // namespace encoders

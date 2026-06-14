// =============================================================================
//  keyer_winkey.h — WinKey-compatible Morse element scheduler (stub).
//
//  Will eventually:
//    - Decode paddle closures (DIT/DAH on PADDLE_DIT / PADDLE_DAH GPIOs).
//    - Maintain dit/dah/space timing from current WPM.
//    - Toggle keyer::key_down() / key_up() on each element boundary.
//    - Implement the WinKey serial protocol (K1EL) over USB CDC so any
//      mainstream logging program can drive the rig.
//
//  For now: presents the public API so main.cpp can wire it in.
// =============================================================================
#pragma once

#include "esp_err.h"

namespace winkey {

esp_err_t init();              // spawn scheduler task pinned to CORE_KEYING
void      set_wpm(float wpm);  // forwarded to keyer::set_wpm

}  // namespace winkey

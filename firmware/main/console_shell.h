// =============================================================================
//  console_shell.h — USB-CDC command shell.
//
//  Brings up an esp_console REPL on the native USB-Serial-JTAG port and
//  registers the xmitter-specific commands:
//      vfo freq <hz>
//      vfo on
//      vfo off
//      vfo status
//      status            (overall rig state)
//      psu on / psu off  (no-op until supply hardware exists)
// =============================================================================
#pragma once

#include "esp_err.h"

namespace shell {

esp_err_t init();

}

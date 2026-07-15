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
#include "driver/i2c_master.h"

namespace shell {

// Pass in the shared I2C bus handle so commands like `i2c scan` and
// `mcp4728 reprogram` can talk to devices on the bus.
esp_err_t init(i2c_master_bus_handle_t bus);

}

// =============================================================================
//  i2c_scan.h — probe every address on the shared I2C bus and report which
//  ones respond.  Handy for verifying the MCP4728 EEPROM address reprogram
//  before/after, and for smoke-testing the bus during bring-up in general.
// =============================================================================
#pragma once

#include "esp_err.h"
#include "driver/i2c_master.h"

namespace i2c_scan {

// Probe addresses 0x08..0x77 (the valid 7-bit range excluding the reserved
// low and high blocks) and print a summary to stdout.  Uses
// i2c_master_probe() with a 50 ms per-address timeout.  Read-only — never
// writes to the bus.
esp_err_t scan(i2c_master_bus_handle_t bus);

}  // namespace i2c_scan

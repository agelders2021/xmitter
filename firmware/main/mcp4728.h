// =============================================================================
//  mcp4728.h — Microchip MCP4728 4-channel 12-bit I2C DAC.
//
//  Present on Rev A as the "null DAC" for the MC1496 buffer/keyer stage.
//  Ships from Microchip at I2C address 0x60, which collides with the
//  Adafruit Si5351A breakout.  The plan is to move it to 0x67 (upper end
//  of its 0x60..0x67 EEPROM-programmable range) so 0x62/0x63 remain
//  reserved for the future MCP4725 grid-bias DACs.
//
//  Only the address-reprogram operation is implemented right now; the DAC
//  channel-write API will land when the bias/keyer bring-up starts.
// =============================================================================
#pragma once

#include "esp_err.h"
#include "driver/i2c_master.h"
#include "driver/gpio.h"

namespace mcp4728 {

// One-shot EEPROM address reprogram (Microchip DS22187 §5.4.3).  Sends the
// three-byte "Write I2C Address Bits" sequence to the device currently at
// cur_addr, telling it to burn new_addr into its address EEPROM.  The
// change is persistent — the chip retains the new address across power
// cycles.
//
// LDAC handling: the datasheet requires LDAC to transition from HIGH to
// LOW during the LOW half of the ACK bit on byte 1.  This implementation
// takes the simpler path of holding LDAC LOW for the entire transaction,
// which is documented to work on the parts most builders encounter but is
// not the strictly-literal reading of the datasheet.  If the chip refuses
// the reprogram (post-scan still shows cur_addr), rebuild with the
// bit-bang variant compiled in.
//
// This function returns ESP_OK if the I2C transaction completed cleanly.
// It does NOT verify that the new address took effect — the caller should
// probe the bus (i2c_scan::scan or i2c_master_probe) after calling this.
esp_err_t reprogram_address(i2c_master_bus_handle_t bus,
                            uint8_t                 cur_addr,
                            uint8_t                 new_addr,
                            gpio_num_t              ldac_pin);

// Compute the three bytes that reprogram_address() will send.  Exposed so
// the console command can print them for eyeball verification against the
// datasheet before the burn goes ahead.  Returns ESP_ERR_INVALID_ARG if
// either address is outside 0x60..0x67.
esp_err_t plan_reprogram_bytes(uint8_t cur_addr,
                               uint8_t new_addr,
                               uint8_t out_bytes[3]);

}  // namespace mcp4728

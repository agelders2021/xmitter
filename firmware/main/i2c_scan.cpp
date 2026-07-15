// =============================================================================
//  i2c_scan.cpp — see header.
// =============================================================================
#include "i2c_scan.h"

#include <cstdio>

#include "esp_log.h"

#include "pin_map.h"

namespace i2c_scan {

namespace {

constexpr char TAG[] = "i2c_scan";

// Map a responding address to a friendly name, or nullptr if unknown.
// Kept close to pin_map.h so a new device gets one entry here and shows
// up correctly next scan.
const char *name_for(uint8_t addr) {
    switch (addr) {
        case pins::I2C_ADDR_PCF8575_PANEL:   return "PCF8575 (front panel)";
        case pins::I2C_ADDR_PCF8575_MAIN:    return "PCF8575 (main board)";
        case pins::I2C_ADDR_MAX17048:        return "MAX17048 (Metro fuel gauge) "
                                                    "-or- QT rotary (default)";
        case pins::I2C_ADDR_ENC_STEP:        return "QT rotary encoder (STEP)";
        case pins::I2C_ADDR_ENC_FUNC:        return "QT rotary encoder (FUNC)";
        case pins::I2C_ADDR_SI5351:          return "Si5351A -or- MCP4728 (unprogrammed)";
        case pins::I2C_ADDR_MCP4728:         return "MCP4728 (post-reprogram)";
        default:                             return nullptr;
    }
}

}  // namespace

esp_err_t scan(i2c_master_bus_handle_t bus) {
    if (bus == nullptr) {
        ESP_LOGE(TAG, "bus handle is null");
        return ESP_ERR_INVALID_ARG;
    }

    std::printf("i2c scan: probing 0x08..0x77 on the shared bus...\n");
    std::printf("     ");
    for (int col = 0; col < 16; ++col) std::printf(" %X ", col);
    std::printf("\n");

    unsigned found = 0;
    uint8_t hits[112] = {};
    unsigned hit_count = 0;

    for (int row = 0; row < 8; ++row) {
        std::printf("  %X0:", row);
        for (int col = 0; col < 16; ++col) {
            uint8_t addr = (uint8_t)((row << 4) | col);
            if (addr < 0x08 || addr > 0x77) {
                std::printf(" .. ");
                continue;
            }
            esp_err_t e = i2c_master_probe(bus, addr, /*timeout_ms=*/50);
            if (e == ESP_OK) {
                std::printf(" %02X ", addr);
                hits[hit_count++] = addr;
                ++found;
            } else if (e == ESP_ERR_NOT_FOUND) {
                std::printf(" -- ");
            } else {
                // Timeout / bus error — treat as absent but count separately
                // so we notice a sick bus.
                std::printf(" ?? ");
            }
        }
        std::printf("\n");
    }

    std::printf("\ni2c scan: %u device%s responded\n",
                found, found == 1 ? "" : "s");
    for (unsigned i = 0; i < hit_count; ++i) {
        const char *n = name_for(hits[i]);
        std::printf("  0x%02X  %s\n", hits[i], n ? n : "(unknown)");
    }
    return ESP_OK;
}

}  // namespace i2c_scan

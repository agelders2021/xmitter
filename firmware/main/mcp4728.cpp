// =============================================================================
//  mcp4728.cpp — MCP4728 driver.  See header.
// =============================================================================
#include "mcp4728.h"

#include <cstring>

#include "esp_log.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"

namespace mcp4728 {

namespace {

constexpr char TAG[] = "mcp4728";

// MCP4728 valid I2C address range: 0x60..0x67 (fixed high nibble 1100,
// three low bits programmable via EEPROM).
constexpr uint8_t ADDR_MIN = 0x60;
constexpr uint8_t ADDR_MAX = 0x67;

bool valid(uint8_t addr) { return addr >= ADDR_MIN && addr <= ADDR_MAX; }

}  // namespace

esp_err_t plan_reprogram_bytes(uint8_t cur_addr,
                               uint8_t new_addr,
                               uint8_t out_bytes[3]) {
    if (!valid(cur_addr) || !valid(new_addr) || out_bytes == nullptr) {
        return ESP_ERR_INVALID_ARG;
    }

    const uint8_t cur_bits = cur_addr & 0x07;   // A2 A1 A0 of current
    const uint8_t new_bits = new_addr & 0x07;   // A2 A1 A0 of new

    // MCP4728 "Write I2C Address Bits" command -- Microchip DS22187 §5.6.6.
    // Three command bytes follow the START + device-address-byte.  All three
    // are of the form 0110_0AAA_R where AAA is a 3-bit address field and R
    // is a role bit (1 = "Write Addr cmd" / confirm, 0 = "new address").
    //
    //   Byte 1 (write-addr command with CURRENT addr, prove we know it):
    //       0 1 1 0 0 A2c A1c A0c  1    ->  0x61 | (cur_bits << 1)
    //   Byte 2 (new address, R=0):
    //       0 1 1 0 0 A2n A1n A0n  0    ->  0x60 | (new_bits << 1)
    //   Byte 3 (confirm new address, R=1):
    //       0 1 1 0 0 A2n A1n A0n  1    ->  0x61 | (new_bits << 1)
    //
    // (An earlier revision of this file used 0x68 as the base and only sent
    // two bytes; that pattern gets decoded by the chip as a Multi-Write DAC
    // command instead of an address change -- ACKs but no effect.)
    out_bytes[0] = (uint8_t)(0x61 | (cur_bits << 1));
    out_bytes[1] = (uint8_t)(0x60 | (new_bits << 1));
    out_bytes[2] = (uint8_t)(0x61 | (new_bits << 1));

    return ESP_OK;
}

esp_err_t reprogram_address(i2c_master_bus_handle_t bus,
                            uint8_t                 cur_addr,
                            uint8_t                 new_addr,
                            gpio_num_t              ldac_pin) {
    if (bus == nullptr)               return ESP_ERR_INVALID_ARG;
    if (!valid(cur_addr))             return ESP_ERR_INVALID_ARG;
    if (!valid(new_addr))             return ESP_ERR_INVALID_ARG;
    if (cur_addr == new_addr) {
        ESP_LOGW(TAG, "cur_addr == new_addr, nothing to do");
        return ESP_OK;
    }

    uint8_t bytes[3];
    ESP_RETURN_ON_ERROR(plan_reprogram_bytes(cur_addr, new_addr, bytes),
                        TAG, "plan_reprogram_bytes");

    // Configure LDAC as GPIO output, idle HIGH before we begin.
    gpio_config_t io = {};
    io.pin_bit_mask = 1ULL << ldac_pin;
    io.mode         = GPIO_MODE_OUTPUT;
    io.pull_up_en   = GPIO_PULLUP_DISABLE;
    io.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io.intr_type    = GPIO_INTR_DISABLE;
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio_config LDAC");
    ESP_RETURN_ON_ERROR(gpio_set_level(ldac_pin, 1), TAG, "LDAC high");
    vTaskDelay(pdMS_TO_TICKS(2));

    // Add the current MCP4728 to the bus so we can write to it.  Remove
    // when done so re-init at the new address works cleanly.
    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = cur_addr;
    cfg.scl_speed_hz    = 100000;   // 100 kHz — well below the 400 kHz max;
                                    // gives the EEPROM cell plenty of time.

    i2c_master_dev_handle_t dev = nullptr;
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus, &cfg, &dev),
                        TAG, "add MCP4728 device");

    ESP_LOGI(TAG, "Reprogram: 0x%02X -> 0x%02X  (cmd bytes: %02X %02X %02X)",
             cur_addr, new_addr, bytes[0], bytes[1], bytes[2]);

    // Pull LDAC LOW before START and hold through the whole transaction.
    ESP_ERROR_CHECK(gpio_set_level(ldac_pin, 0));

    // All three command bytes go in the payload; the driver adds the START
    // and device-address-byte automatically.
    esp_err_t xfer = i2c_master_transmit(dev, bytes, 3, /*timeout_ms=*/200);

    // EEPROM burn time is ~50 ms per the datasheet.  Keep LDAC LOW through
    // the burn to be safe.
    vTaskDelay(pdMS_TO_TICKS(60));

    // Restore LDAC HIGH (normal operating state — no channel updates
    // triggered) and detach from the bus at the OLD address.
    ESP_ERROR_CHECK(gpio_set_level(ldac_pin, 1));
    i2c_master_bus_rm_device(dev);

    if (xfer != ESP_OK) {
        ESP_LOGE(TAG, "I2C transmit failed: %s", esp_err_to_name(xfer));
        return xfer;
    }

    ESP_LOGI(TAG, "Reprogram sequence sent OK. Rescan the bus to verify.");
    return ESP_OK;
}

}  // namespace mcp4728

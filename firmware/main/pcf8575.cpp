// =============================================================================
//  pcf8575.cpp -- see header.
// =============================================================================
#include "pcf8575.h"

#include "esp_log.h"

namespace pcf8575 {

namespace {
constexpr char TAG[] = "pcf8575";
}

esp_err_t Device::begin(i2c_master_bus_handle_t bus, uint8_t addr)
{
    if (dev_) return ESP_OK;   // idempotent

    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = addr;
    cfg.scl_speed_hz    = 400000;   // fast-mode -- PCF8575 supports up to 400 kHz

    esp_err_t e = i2c_master_bus_add_device(bus, &cfg, &dev_);
    if (e != ESP_OK) {
        ESP_LOGE(TAG, "add_device 0x%02X failed: %s", addr, esp_err_to_name(e));
        return e;
    }
    ESP_LOGI(TAG, "PCF8575 @ 0x%02X attached", addr);
    return ESP_OK;
}

esp_err_t Device::write(uint16_t value)
{
    if (!dev_) return ESP_ERR_INVALID_STATE;
    // Byte order per datasheet: low byte (P00-P07) first, then high byte
    // (P10-P17).
    const uint8_t buf[2] = { (uint8_t)(value & 0xFF), (uint8_t)(value >> 8) };
    return i2c_master_transmit(dev_, buf, sizeof(buf), 100 /*ms*/);
}

esp_err_t Device::read(uint16_t *value)
{
    if (!dev_ || !value) return ESP_ERR_INVALID_ARG;
    uint8_t buf[2] = { 0, 0 };
    esp_err_t e = i2c_master_receive(dev_, buf, sizeof(buf), 100);
    if (e == ESP_OK) *value = (uint16_t)buf[0] | ((uint16_t)buf[1] << 8);
    return e;
}

void Device::shadow_bit(uint8_t bit, bool value)
{
    if (bit >= 16) return;
    if (value) shadow_ |=  (uint16_t)(1u << bit);
    else       shadow_ &= (uint16_t)~(1u << bit);
}

}  // namespace pcf8575

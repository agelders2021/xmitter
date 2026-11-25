// =============================================================================
//  lcd_backpack.cpp -- see header.
// =============================================================================
#include "lcd_backpack.h"

#include "esp_log.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "rom/ets_sys.h"

namespace lcd_backpack {

namespace {
constexpr char TAG[] = "lcd_bp";

constexpr uint8_t BIT_RS = 0x01;
constexpr uint8_t BIT_RW = 0x02;
constexpr uint8_t BIT_E  = 0x04;
constexpr uint8_t BIT_BL = 0x08;

constexpr uint8_t CMD_CLEAR     = 0x01;
constexpr uint8_t CMD_HOME      = 0x02;
constexpr uint8_t CMD_ENTRY     = 0x04;
constexpr uint8_t CMD_DISPLAY   = 0x08;
constexpr uint8_t CMD_FUNCTION  = 0x20;
constexpr uint8_t CMD_SET_DDRAM = 0x80;

constexpr uint8_t ROW_ADDR[4] = { 0x00, 0x40, 0x14, 0x54 };

esp_err_t probe_addr(i2c_master_bus_handle_t bus, uint8_t addr) {
    return i2c_master_probe(bus, addr, 100);
}
}  // namespace

esp_err_t Device::begin(i2c_master_bus_handle_t bus, uint8_t addr, uint8_t rows)
{
    if (!bus) return ESP_ERR_INVALID_ARG;

    if (addr == 0) {
        if (probe_addr(bus, 0x27) == ESP_OK)      addr = 0x27;
        else if (probe_addr(bus, 0x3F) == ESP_OK) addr = 0x3F;
        else {
            ESP_LOGE(TAG, "no backpack ACK at 0x27 or 0x3F");
            return ESP_ERR_NOT_FOUND;
        }
        ESP_LOGI(TAG, "auto-detected backpack at 0x%02X", addr);
    }

    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = addr;
    cfg.scl_speed_hz    = 400000;
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus, &cfg, &dev_),
                        TAG, "add_device 0x%02X", addr);
    addr_    = addr;
    rows_    = rows;
    bl_mask_ = BIT_BL;

    vTaskDelay(pdMS_TO_TICKS(50));

    ESP_RETURN_ON_ERROR(i2c_write_(bl_mask_), TAG, "idle");

    ESP_RETURN_ON_ERROR(write_nibble_(0x03, false), TAG, "wake 1");
    vTaskDelay(pdMS_TO_TICKS(5));
    ESP_RETURN_ON_ERROR(write_nibble_(0x03, false), TAG, "wake 2");
    ets_delay_us(150);
    ESP_RETURN_ON_ERROR(write_nibble_(0x03, false), TAG, "wake 3");
    ets_delay_us(150);

    ESP_RETURN_ON_ERROR(write_nibble_(0x02, false), TAG, "4-bit switch");
    ets_delay_us(150);

    const uint8_t n_bit = (rows_ > 1) ? 0x08 : 0x00;
    ESP_RETURN_ON_ERROR(cmd_(CMD_FUNCTION | n_bit), TAG, "function set");
    ets_delay_us(50);

    ESP_RETURN_ON_ERROR(cmd_(CMD_DISPLAY), TAG, "display off");
    ets_delay_us(50);
    ESP_RETURN_ON_ERROR(cmd_(CMD_CLEAR), TAG, "clear");
    vTaskDelay(pdMS_TO_TICKS(3));

    ESP_RETURN_ON_ERROR(cmd_(CMD_ENTRY | 0x02), TAG, "entry mode");
    ets_delay_us(50);

    ESP_RETURN_ON_ERROR(cmd_(CMD_DISPLAY | 0x04), TAG, "display on");
    ets_delay_us(50);

    ESP_LOGI(TAG, "init done (addr 0x%02X, %u rows)", addr_, (unsigned)rows_);
    return ESP_OK;
}

esp_err_t Device::clear() {
    esp_err_t e = cmd_(CMD_CLEAR);
    vTaskDelay(pdMS_TO_TICKS(3));
    return e;
}

esp_err_t Device::home() {
    esp_err_t e = cmd_(CMD_HOME);
    vTaskDelay(pdMS_TO_TICKS(3));
    return e;
}

esp_err_t Device::set_cursor(uint8_t row, uint8_t col) {
    if (row >= 4) row = 3;
    return cmd_(CMD_SET_DDRAM | (uint8_t)(ROW_ADDR[row] + col));
}

esp_err_t Device::print(const char *s) {
    if (!s) return ESP_ERR_INVALID_ARG;
    while (*s) {
        esp_err_t e = data_((uint8_t)*s++);
        if (e != ESP_OK) return e;
    }
    return ESP_OK;
}

esp_err_t Device::print(char c) {
    return data_((uint8_t)c);
}

esp_err_t Device::display_on(bool on) {
    return cmd_(CMD_DISPLAY | (on ? 0x04 : 0x00));
}

esp_err_t Device::backlight(bool on) {
    bl_mask_ = on ? BIT_BL : 0x00;
    return i2c_write_(bl_mask_);
}

esp_err_t Device::write_nibble_(uint8_t nibble, bool rs)
{
    const uint8_t base = (uint8_t)((nibble & 0x0F) << 4)
                       | bl_mask_
                       | (rs ? BIT_RS : 0);
    ESP_RETURN_ON_ERROR(i2c_write_(base | BIT_E), TAG, "E hi");
    ets_delay_us(1);
    ESP_RETURN_ON_ERROR(i2c_write_(base),         TAG, "E lo");
    ets_delay_us(50);
    return ESP_OK;
}

esp_err_t Device::write_byte_(uint8_t byte, bool rs)
{
    ESP_RETURN_ON_ERROR(write_nibble_(byte >> 4,   rs), TAG, "high nibble");
    ESP_RETURN_ON_ERROR(write_nibble_(byte & 0x0F, rs), TAG, "low nibble");
    return ESP_OK;
}

esp_err_t Device::i2c_write_(uint8_t v)
{
    if (!dev_) return ESP_ERR_INVALID_STATE;
    return i2c_master_transmit(dev_, &v, 1, 100);
}

}  // namespace lcd_backpack

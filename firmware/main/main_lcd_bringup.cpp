// =============================================================================
//  main_lcd_bringup.cpp — front-panel LCD bring-up test entry point.
//
//  Built INSTEAD OF the normal main.cpp when the project is configured with
//  -DLCD_BRINGUP=ON.  Skips VFO, MCP4728, cathode monitor, faults, and shell
//  so an unattached-hardware bench test doesn't spam init errors.
//
//  Stage 1b (encoder-controlled contrast):
//    1. Bring up the shared I2C bus.
//    2. Attach the front-panel PCF8575 at 0x21.
//    3. Attach the MCP4725 (LCD contrast DAC) at 0x62 and set V0 = 0.7 V.
//    4. Init the HD44780 4-bit driver.
//    5. Backlight = steady WHITE (all three FETs on, no PWM).  Color cycling
//       was proven working in stage 1a; not needed here.
//    6. Attach an I2C QT rotary encoder at 0x37 (A0 jumper closed on the
//       breakout to move off factory 0x36, which collides with the Metro's
//       on-board MAX17048 fuel gauge).
//    7. Encoder task: read delta, adjust MCP4725 code, redraw LCD with
//       current DAC code + voltage.  Each detent = ~50 mV.
//
//  Bench wiring:
//    - STEMMA QT: Metro -> front-panel PCF8575 breakout (SDA/SCL).
//    - Front panel's STEMMA-out -> encoder breakout STEMMA-in.
//    - Separate 5 V bench supply to the PCB's +5V rail.  Common the grounds.
// =============================================================================
#include <cstdio>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "esp_chip_info.h"
#include "esp_rom_sys.h"
#include "nvs_flash.h"
#include "driver/i2c_master.h"

#include "pin_map.h"
#include "pcf8575.h"
#include "lcd_hd44780.h"

#ifdef LCD_BRINGUP

namespace {

constexpr char TAG[] = "lcd_bringup";

// I2C addresses
constexpr uint8_t  MCP4725_ADDR       = 0x62;
constexpr uint8_t  ENCODER_ADDR       = 0x37;   // A0 jumper closed on breakout

// MCP4725
constexpr uint16_t DAC_START_CODE     = 573;    // ~0.7 V at 5 V Vref
constexpr int      DAC_CODES_PER_DETENT = 40;   // ~50 mV / detent

// Adafruit QT encoder = 4 quadrature counts per mechanical detent
constexpr int      ENCODER_COUNTS_PER_DETENT = 4;

// --------------------------------------------------------------------------
//  Shared handles
// --------------------------------------------------------------------------
i2c_master_bus_handle_t s_bus = nullptr;
pcf8575::Device         s_pcf;
lcd::HD44780            s_lcd;

// --------------------------------------------------------------------------
//  I2C bus + MCP4725 helpers
// --------------------------------------------------------------------------
esp_err_t i2c_bus_init() {
    i2c_master_bus_config_t cfg = {};
    cfg.i2c_port         = pins::I2C_PORT;
    cfg.sda_io_num       = pins::I2C_SDA;
    cfg.scl_io_num       = pins::I2C_SCL;
    cfg.clk_source       = I2C_CLK_SRC_DEFAULT;
    cfg.glitch_ignore_cnt = 7;
    cfg.flags.enable_internal_pullup = true;
    return i2c_new_master_bus(&cfg, &s_bus);
}

esp_err_t mcp4725_set(uint8_t addr, uint16_t code_12bit) {
    if (code_12bit > 0x0FFF) code_12bit = 0x0FFF;

    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = addr;
    cfg.scl_speed_hz    = 400000;

    i2c_master_dev_handle_t dev = nullptr;
    esp_err_t e = i2c_master_bus_add_device(s_bus, &cfg, &dev);
    if (e != ESP_OK) return e;

    const uint8_t buf[2] = {
        (uint8_t)((code_12bit >> 8) & 0x0F),
        (uint8_t)(code_12bit & 0xFF),
    };
    e = i2c_master_transmit(dev, buf, sizeof(buf), 100);
    i2c_master_bus_rm_device(dev);
    return e;
}

// --------------------------------------------------------------------------
//  Minimal Adafruit seesaw driver -- just what's needed to read the encoder
//  delta register on a QT rotary encoder breakout.  Full driver will be
//  extracted to seesaw_encoder.{h,cpp} once this works.
// --------------------------------------------------------------------------
// Seesaw register base + offset addresses (from Adafruit_seesaw firmware)
constexpr uint8_t SEESAW_STATUS_BASE     = 0x00;
constexpr uint8_t SEESAW_STATUS_SWRST    = 0x7F;

constexpr uint8_t SEESAW_ENCODER_BASE    = 0x11;
constexpr uint8_t SEESAW_ENCODER_DELTA   = 0x40;

class SeesawEncoder {
 public:
    esp_err_t begin(i2c_master_bus_handle_t bus, uint8_t addr) {
        i2c_device_config_t cfg = {};
        cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
        cfg.device_address  = addr;
        cfg.scl_speed_hz    = 400000;
        esp_err_t e = i2c_master_bus_add_device(bus, &cfg, &dev_);
        if (e != ESP_OK) return e;

        // Software reset
        const uint8_t rst[3] = { SEESAW_STATUS_BASE, SEESAW_STATUS_SWRST, 0xFF };
        e = i2c_master_transmit(dev_, rst, sizeof(rst), 100);
        if (e != ESP_OK) return e;
        // Adafruit lib waits 500 ms; seesaw needs << that but be generous
        vTaskDelay(pdMS_TO_TICKS(500));

        return ESP_OK;
    }

    // Read the accumulated encoder delta since the last read.  Big-endian
    // int32 per seesaw protocol.
    esp_err_t read_delta(int32_t *delta) {
        if (!dev_ || !delta) return ESP_ERR_INVALID_ARG;
        const uint8_t reg[2] = { SEESAW_ENCODER_BASE, SEESAW_ENCODER_DELTA };
        esp_err_t e = i2c_master_transmit(dev_, reg, sizeof(reg), 100);
        if (e != ESP_OK) return e;
        // Seesaw needs a moment to prep the response
        esp_rom_delay_us(500);
        uint8_t buf[4] = { 0 };
        e = i2c_master_receive(dev_, buf, sizeof(buf), 100);
        if (e != ESP_OK) return e;
        *delta = ((int32_t)(int8_t)buf[0] << 24)
               | ((int32_t)buf[1] << 16)
               | ((int32_t)buf[2] <<  8)
               |  (int32_t)buf[3];
        return ESP_OK;
    }

 private:
    i2c_master_dev_handle_t dev_ = nullptr;
};

SeesawEncoder s_encoder;

// --------------------------------------------------------------------------
//  LCD text
// --------------------------------------------------------------------------
void render_header() {
    s_lcd.clear();
    s_lcd.set_cursor(0, 0);
    s_lcd.print(" LCD bring-up test  ");
    s_lcd.set_cursor(1, 0);
    s_lcd.print(" Contrast (encoder) ");
}

void render_contrast(uint16_t code) {
    // code / 4095 * 5.00 V
    const float volts = ((float)code) * (5.0f / 4095.0f);
    char buf[21];

    std::snprintf(buf, sizeof(buf), "  DAC:%4u = %1.2f V ",
                  (unsigned)code, (double)volts);
    s_lcd.set_cursor(2, 0);
    s_lcd.print(buf);

    // Simple bar on row 3: one asterisk per 5 % of code range.
    char bar[21];
    const int bars = (int)((code * 20 + 2047) / 4095);
    for (int i = 0; i < 20; ++i) bar[i] = (i < bars) ? '*' : ' ';
    bar[20] = 0;
    s_lcd.set_cursor(3, 0);
    s_lcd.print(bar);
}

// --------------------------------------------------------------------------
//  Bring-up task -- encoder poll + contrast adjust
// --------------------------------------------------------------------------
void bringup_task(void *) {
    render_header();

    uint16_t dac_code   = DAC_START_CODE;
    int32_t  accumulator = 0;
    uint16_t last_shown  = 0xFFFF;

    mcp4725_set(MCP4725_ADDR, dac_code);
    render_contrast(dac_code);
    last_shown = dac_code;

    while (true) {
        int32_t delta = 0;
        esp_err_t e = s_encoder.read_delta(&delta);
        if (e == ESP_OK && delta != 0) {
            accumulator += delta;
            int32_t detents = accumulator / ENCODER_COUNTS_PER_DETENT;
            accumulator    -= detents * ENCODER_COUNTS_PER_DETENT;

            int32_t new_code = (int32_t)dac_code + detents * DAC_CODES_PER_DETENT;
            if (new_code <    0) new_code =    0;
            if (new_code > 4095) new_code = 4095;
            dac_code = (uint16_t)new_code;

            mcp4725_set(MCP4725_ADDR, dac_code);
        } else if (e != ESP_OK) {
            static int64_t last_log = 0;
            const int64_t now = esp_timer_get_time();
            if (now - last_log > 5'000'000) {
                ESP_LOGW(TAG, "encoder read failed: %s", esp_err_to_name(e));
                last_log = now;
            }
        }

        if (dac_code != last_shown) {
            render_contrast(dac_code);
            last_shown = dac_code;
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

}  // namespace

extern "C" void app_main() {
    std::printf("\n=== LCD bring-up: encoder contrast ===\n");
    std::printf(" build: %s %s\n", __DATE__, __TIME__);
    std::printf(" PCF8575 @ 0x%02X, MCP4725 @ 0x%02X, encoder @ 0x%02X\n",
                pins::I2C_ADDR_PCF8575_PANEL, MCP4725_ADDR, ENCODER_ADDR);

    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(i2c_bus_init());
    ESP_LOGI(TAG, "I2C up: SDA=GPIO%d SCL=GPIO%d @ %lu Hz",
             (int)pins::I2C_SDA, (int)pins::I2C_SCL,
             (unsigned long)pins::I2C_HZ);

    ESP_ERROR_CHECK(s_pcf.begin(s_bus, pins::I2C_ADDR_PCF8575_PANEL));
    ESP_ERROR_CHECK(s_lcd.begin(&s_pcf));

    // Backlight = full white, steady.  No PWM this stage.
    s_lcd.backlight_rgb(true, true, true);

    // Encoder.  If missing, log and continue -- LCD still shows starting
    // contrast, just can't be adjusted.
    if (esp_err_t e = s_encoder.begin(s_bus, ENCODER_ADDR); e != ESP_OK) {
        ESP_LOGE(TAG, "encoder begin failed at 0x%02X: %s",
                 ENCODER_ADDR, esp_err_to_name(e));
    } else {
        ESP_LOGI(TAG, "encoder attached at 0x%02X", ENCODER_ADDR);
    }

    xTaskCreatePinnedToCore(bringup_task, "lcd_bringup", 4096, nullptr,
                            3, nullptr, pins::CORE_MONITOR);

    ESP_LOGI(TAG, "bring-up running -- turn encoder to adjust contrast");
}

#endif  // LCD_BRINGUP

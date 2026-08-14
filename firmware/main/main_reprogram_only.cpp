// =============================================================================
//  main_reprogram_only.cpp
//
//  Isolated MCP4728 address-reprogram build.  Uses ONLY the legacy
//  driver/i2c.h stack.  driver/i2c_master.h is NOT included.  Everything
//  else (PCF8575, MCP4725, LCD, encoder, Si5351, bringup task) is
//  excluded so there's no chance of the two I2C driver stacks colliding.
//
//  Build:  firmware\reprogram_only.bat
//  Flag :  -DREPROGRAM_ONLY=ON (also implies exclusion of main.cpp and
//          main_lcd_bringup.cpp app_mains via their guards)
//
//  Behavior:
//    1. Install legacy driver on I2C_NUM_0 at 100 kHz.
//    2. Probe 0x67 -- if it ACKs, log "already reprogrammed" and idle.
//    3. Probe 0x60 -- must ACK, else log FAIL and idle.
//    4. Drive LDAC LOW (Adafruit-style: transition happens while bus is
//       idle, before START).
//    5. Send the 3-byte "Write I2C Address" command sequence via
//       i2c_cmd_link.
//    6. Wait 60 ms EEPROM burn.  LDAC HIGH.
//    7. Probe 0x67 to verify.  Print SUCCESS or FAIL to serial.  Idle.
//
//  Serial output at 115200; log tag "reprog".
// =============================================================================
#include <cstdio>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include "driver/i2c.h"          // LEGACY only -- do NOT include i2c_master.h
#include "driver/gpio.h"

#include "pin_map.h"

#ifdef REPROGRAM_ONLY

namespace {

constexpr char TAG[] = "reprog";
constexpr uint8_t CUR_ADDR = 0x60;
constexpr uint8_t NEW_ADDR = 0x67;

bool probe_addr(uint8_t addr, TickType_t timeout_ticks) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (uint8_t)((addr << 1) | 0), true);
    i2c_master_stop(cmd);
    esp_err_t e = i2c_master_cmd_begin(I2C_NUM_0, cmd, timeout_ticks);
    i2c_cmd_link_delete(cmd);
    return e == ESP_OK;
}

}  // namespace

extern "C" void app_main() {
    std::printf("\n\n=== MCP4728 legacy-driver reprogram (isolated build) ===\n");
    std::printf(" build : %s %s\n", __DATE__, __TIME__);
    std::printf(" SDA   : GPIO %d\n", (int)pins::I2C_SDA);
    std::printf(" SCL   : GPIO %d\n", (int)pins::I2C_SCL);
    std::printf(" LDAC  : GPIO %d  (must be wired to MCP4728 breakout LDAC)\n",
                (int)pins::MCP4728_LDAC);
    std::printf(" 0x%02X -> 0x%02X reprogram target\n\n", CUR_ADDR, NEW_ADDR);
    fflush(stdout);

    ESP_ERROR_CHECK(nvs_flash_init());

    // ---- Install legacy I2C driver ----
    i2c_config_t conf = {};
    conf.mode             = I2C_MODE_MASTER;
    conf.sda_io_num       = pins::I2C_SDA;
    conf.scl_io_num       = pins::I2C_SCL;
    conf.sda_pullup_en    = GPIO_PULLUP_ENABLE;
    conf.scl_pullup_en    = GPIO_PULLUP_ENABLE;
    conf.master.clk_speed = 100000;

    if (i2c_param_config(I2C_NUM_0, &conf) != ESP_OK) {
        ESP_LOGE(TAG, "i2c_param_config FAILED");
        while (true) vTaskDelay(pdMS_TO_TICKS(1000));
    }
    if (i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0) != ESP_OK) {
        ESP_LOGE(TAG, "i2c_driver_install FAILED");
        while (true) vTaskDelay(pdMS_TO_TICKS(1000));
    }
    ESP_LOGI(TAG, "legacy I2C driver installed on I2C_NUM_0");

    // ---- Setup LDAC pin ----
    gpio_reset_pin(pins::MCP4728_LDAC);
    gpio_set_pull_mode(pins::MCP4728_LDAC, GPIO_FLOATING);
    gpio_set_direction(pins::MCP4728_LDAC, GPIO_MODE_OUTPUT);
    gpio_set_level(pins::MCP4728_LDAC, 1);
    vTaskDelay(pdMS_TO_TICKS(10));

    // ---- Check if already reprogrammed ----
    if (probe_addr(NEW_ADDR, pdMS_TO_TICKS(50))) {
        std::printf("=========================================\n");
        std::printf(" 0x%02X already ACKs -- chip already at target.\n", NEW_ADDR);
        std::printf(" No reprogram needed.\n");
        std::printf(" Reflash bringup.bat to return to normal.\n");
        std::printf("=========================================\n");
        while (true) vTaskDelay(pdMS_TO_TICKS(1000));
    }

    // ---- Confirm chip is at 0x60 ----
    if (!probe_addr(CUR_ADDR, pdMS_TO_TICKS(50))) {
        std::printf("=========================================\n");
        std::printf(" FAIL: no ACK at 0x%02X -- check STEMMA cable + power\n",
                    CUR_ADDR);
        std::printf("=========================================\n");
        while (true) vTaskDelay(pdMS_TO_TICKS(1000));
    }
    ESP_LOGI(TAG, "chip found at 0x%02X, proceeding with reprogram", CUR_ADDR);

    // ---- Compute the 3-byte command payload inline ----
    // Per DS22187 §5.6.8 "Write I2C Address Bits":
    //   byte 1: 0110_0AAA_1 with AAA = CURRENT addr bits (prove we know it)
    //   byte 2: 0110_0AAA_0 with AAA = NEW     addr bits (data)
    //   byte 3: 0110_0AAA_1 with AAA = NEW     addr bits (confirm)
    const uint8_t cur_bits = CUR_ADDR & 0x07;
    const uint8_t new_bits = NEW_ADDR & 0x07;
    const uint8_t bytes[3] = {
        (uint8_t)(0x61 | (cur_bits << 1)),
        (uint8_t)(0x60 | (new_bits << 1)),
        (uint8_t)(0x61 | (new_bits << 1)),
    };
    ESP_LOGI(TAG, "cmd bytes: %02X %02X %02X", bytes[0], bytes[1], bytes[2]);

    // ---- Adafruit-style: LDAC HIGH -> LOW while bus is idle, before START.
    gpio_set_level(pins::MCP4728_LDAC, 0);
    vTaskDelay(pdMS_TO_TICKS(1));

    // ---- Send reprogram transaction ----
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (uint8_t)((CUR_ADDR << 1) | 0), true);
    i2c_master_write_byte(cmd, bytes[0], true);
    i2c_master_write_byte(cmd, bytes[1], true);
    i2c_master_write_byte(cmd, bytes[2], true);
    i2c_master_stop(cmd);
    esp_err_t xfer_err = i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(200));
    i2c_cmd_link_delete(cmd);

    vTaskDelay(pdMS_TO_TICKS(60));      // EEPROM burn
    gpio_set_level(pins::MCP4728_LDAC, 1);

    ESP_LOGI(TAG, "reprogram xfer result: %s", esp_err_to_name(xfer_err));

    // ---- Verify ----
    vTaskDelay(pdMS_TO_TICKS(50));
    const bool ok_new = probe_addr(NEW_ADDR, pdMS_TO_TICKS(100));
    const bool ok_old = probe_addr(CUR_ADDR, pdMS_TO_TICKS(100));

    std::printf("\n=========================================\n");
    if (ok_new && !ok_old) {
        std::printf(" SUCCESS: 0x%02X ACKs, 0x%02X no longer ACKs.\n",
                    NEW_ADDR, CUR_ADDR);
        std::printf(" MCP4728 successfully reprogrammed.\n");
        std::printf(" Reflash bringup.bat to return to normal.\n");
    } else if (ok_old && !ok_new) {
        std::printf(" FAIL: chip still at 0x%02X.  Reprogram xfer: %s\n",
                    CUR_ADDR, esp_err_to_name(xfer_err));
        std::printf(" LDAC wire OK?  D%d -> breakout LDAC pin?\n",
                    (int)pins::MCP4728_LDAC);
    } else if (ok_new && ok_old) {
        std::printf(" WEIRD: BOTH addresses ACK.  Bus glitch?\n");
    } else {
        std::printf(" WEIRD: NEITHER address ACKs after reprogram.\n");
    }
    std::printf("=========================================\n\n");
    fflush(stdout);

    while (true) vTaskDelay(pdMS_TO_TICKS(1000));
}

#endif  // REPROGRAM_ONLY

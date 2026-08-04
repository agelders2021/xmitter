// =============================================================================
//  main.cpp — xmitter firmware entry point.
//
//  Boot flow:
//    1. NVS for persistent fault log + calibration constants.
//    2. Bring up the shared I2C bus (Si5351 + bias DAC + cathode ADC).
//    3. Initialize each module in dependency order.  Stubs log a warning
//       but return OK so the rig can still boot and exercise the VFO.
//    4. Spawn the envelope playout task (pinned to CORE_KEYING).
//    5. Bring up the USB-CDC shell so the operator can `vfo freq 14200000`,
//       `vfo on`, etc. before any of the power-supply hardware exists.
//
//  The watchdog is NOT yet armed; faults / WDT come online once the screen
//  voltage gate hardware is wired.  See fault_handler.h.
// =============================================================================
#include <cstdio>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "esp_err.h"
#include "esp_chip_info.h"
#include "nvs_flash.h"
#include "driver/i2c_master.h"

#include "pin_map.h"
#include "vfo_si5351.h"
#include "vfo_knob.h"
#include "keyer_envelope.h"
#include "keyer_winkey.h"
#include "grid_bias_dac.h"
#include "cathode_monitor.h"
#include "fault_handler.h"
#include "front_panel.h"
#include "power_supply.h"
#include "console_shell.h"
#include "display.h"

namespace {

constexpr char TAG[] = "xmitter";

i2c_master_bus_handle_t s_i2c_bus = nullptr;

esp_err_t i2c_bus_init() {
    i2c_master_bus_config_t cfg = {};
    cfg.i2c_port         = pins::I2C_PORT;
    cfg.sda_io_num       = pins::I2C_SDA;
    cfg.scl_io_num       = pins::I2C_SCL;
    cfg.clk_source       = I2C_CLK_SRC_DEFAULT;
    cfg.glitch_ignore_cnt = 7;
    cfg.flags.enable_internal_pullup = true;  // breakouts have their own 10k
    return i2c_new_master_bus(&cfg, &s_i2c_bus);
}

void print_banner() {
    esp_chip_info_t chip;
    esp_chip_info(&chip);
    std::printf("\n");
    std::printf("=========================================\n");
    std::printf("  xmitter — 20m CW vacuum-tube tx\n");
    std::printf("  build: %s %s\n", __DATE__, __TIME__);
    std::printf("  chip : ESP32-S3, %d core(s), rev v%d.%d\n",
                chip.cores, chip.revision / 100, chip.revision % 100);
    std::printf("=========================================\n");
}

}  // namespace

#ifndef LCD_BRINGUP
extern "C" void app_main() {
    print_banner();

    // 1) NVS.  Erase + retry if the partition was reformatted from an older
    //    layout (common after sdkconfig changes).
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    // 2) Shared I2C bus.
    ESP_ERROR_CHECK(i2c_bus_init());
    ESP_LOGI(TAG, "I2C bus up: SDA=GPIO%d SCL=GPIO%d @ %lu Hz",
             (int)pins::I2C_SDA, (int)pins::I2C_SCL,
             (unsigned long)pins::I2C_HZ);

    // 3) Modules.  Stubs that log a warning are expected at this stage.
    ESP_ERROR_CHECK(fault::init());
    ESP_ERROR_CHECK(psu::init());

    if (esp_err_t e = vfo::init(s_i2c_bus); e != ESP_OK) {
        ESP_LOGE(TAG, "VFO init failed: %s  (continuing — check Si5351 wiring)",
                 esp_err_to_name(e));
    } else {
        // Park CLK0 at the band centre, but leave the output disabled until
        // the operator types `vfo on` (or the WinKey scheduler keys down).
        if (vfo::set_freq(vfo::DEFAULT_FREQ_HZ) != ESP_OK) {
            ESP_LOGE(TAG, "VFO set_freq failed at default frequency");
        }
    }

    // 3a) MBL-600 frequency knob.  PCNT hardware set up here; polling task
    //     pinned to CORE_KEYING so the knob -> VFO path runs alongside the
    //     envelope keyer.  If the pins are NC (Rev A analog board still on
    //     the bench without a receiver chip installed), begin() logs a
    //     warning and both begin/start become no-ops.
    if (esp_err_t e = knob::g_vfo_knob.begin(pins::ENC_FREQ_A,
                                             pins::ENC_FREQ_B);
        e != ESP_OK) {
        ESP_LOGE(TAG, "vfo_knob begin failed: %s", esp_err_to_name(e));
    } else {
        ESP_ERROR_CHECK(knob::g_vfo_knob.start(pins::CORE_KEYING));
    }

    ESP_ERROR_CHECK(bias::init(s_i2c_bus));
    ESP_ERROR_CHECK(cathode::init(s_i2c_bus));

    ESP_ERROR_CHECK(keyer::envelope_init());
    ESP_ERROR_CHECK(winkey::init());

    ESP_ERROR_CHECK(front_panel::init());

    // 3b) Front-panel LCD.  Own PCF8575 (0x21) + HD44780 4-bit driver.
    //     Task pinned to CORE_MONITOR -- I2C-heavy, non-real-time.
    if (esp_err_t e = display::g_display.begin(s_i2c_bus); e != ESP_OK) {
        ESP_LOGE(TAG, "display begin failed: %s (LCD not on bus?)",
                 esp_err_to_name(e));
    } else {
        ESP_ERROR_CHECK(display::g_display.start(pins::CORE_MONITOR));
    }

    // 4) USB-CDC shell.  Last so all the commands' targets are alive.
    ESP_ERROR_CHECK(shell::init(s_i2c_bus));

    ESP_LOGI(TAG, "boot complete");

    // app_main returns; the shell REPL task + pinned modules keep running.
}
#endif  // !LCD_BRINGUP

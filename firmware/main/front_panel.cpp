// =============================================================================
//  front_panel.cpp — wires up the encoders module to the rest of the rig.
//
//  Most of the heavy lifting (PCNT, polling, step table) lives in encoders.cpp.
//  This file only:
//    - Brings up the encoder driver.
//    - Surfaces the simple status getters used by the console shell.
//    - Forwards `set_freq_hz()` / `set_power_pct()` from the shell.
// =============================================================================
#include "front_panel.h"

#include "esp_log.h"

#include "encoders.h"
#include "vfo_si5351.h"

namespace front_panel {

namespace {
constexpr char TAG[] = "front_panel";
uint8_t s_power = 0;
}

esp_err_t init() {
    esp_err_t err = encoders::init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "encoder init failed: %s", esp_err_to_name(err));
        return err;
    }
    ESP_LOGI(TAG, "front panel ready (freq step %lu Hz)",
             (unsigned long)encoders::step_hz());
    return ESP_OK;
}

esp_err_t set_freq_hz(uint32_t hz) {
    if (hz < encoders::FREQ_MIN_HZ) hz = encoders::FREQ_MIN_HZ;
    if (hz > encoders::FREQ_MAX_HZ) hz = encoders::FREQ_MAX_HZ;
    return vfo::set_freq(hz);
}

esp_err_t set_power_pct(uint8_t pct) {
    if (pct > 100) pct = 100;
    s_power = pct;
    ESP_LOGI(TAG, "power = %u %% (envelope CODE_FULL + bias trim TBD)", pct);
    return ESP_OK;
}

uint32_t freq_hz()   { return vfo::current_freq(); }
uint8_t  power_pct() { return s_power; }

}  // namespace front_panel

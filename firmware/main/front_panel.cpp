// =============================================================================
//  front_panel.cpp — stub.  See header.
// =============================================================================
#include "front_panel.h"

#include "esp_log.h"
#include "vfo_si5351.h"

namespace front_panel {

namespace {
constexpr char TAG[] = "front_panel";
uint32_t s_freq_hz  = vfo::DEFAULT_FREQ_HZ;
uint8_t  s_power    = 0;
}

esp_err_t init() {
    ESP_LOGW(TAG, "rotary encoders not implemented yet (stub)");
    return ESP_OK;
}

esp_err_t set_freq_hz(uint32_t hz) {
    s_freq_hz = hz;
    return vfo::set_freq(hz);
}

esp_err_t set_power_pct(uint8_t pct) {
    if (pct > 100) pct = 100;
    s_power = pct;
    ESP_LOGI(TAG, "power = %u %% (envelope CODE_FULL + bias trim TBD)", pct);
    return ESP_OK;
}

uint32_t freq_hz()  { return s_freq_hz; }
uint8_t  power_pct(){ return s_power; }

}  // namespace front_panel

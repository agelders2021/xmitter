// =============================================================================
//  power_supply.cpp — stub.  See header.
// =============================================================================
#include "power_supply.h"

#include "esp_log.h"

namespace psu {

namespace {
constexpr char TAG[] = "psu";
State s_state = State::Off;
}

esp_err_t init() {
    ESP_LOGW(TAG, "power-supply sequencer not implemented yet (stub)");
    s_state = State::Off;
    return ESP_OK;
}

esp_err_t on() {
    ESP_LOGI(TAG, "psu on (stub — no hardware)");
    s_state = State::Ready;
    return ESP_OK;
}

esp_err_t off() {
    ESP_LOGI(TAG, "psu off (stub)");
    s_state = State::Off;
    return ESP_OK;
}

State state() { return s_state; }

}  // namespace psu

// =============================================================================
//  grid_bias_dac.cpp — stub.  See header.
// =============================================================================
#include "grid_bias_dac.h"

#include "esp_log.h"

namespace bias {

namespace {
constexpr char TAG[] = "bias";
State s_state = State::Idle;
}

esp_err_t init(i2c_master_bus_handle_t /*bus*/) {
    ESP_LOGW(TAG, "MCP4728 grid bias DAC not implemented yet (stub)");
    s_state = State::Idle;
    return ESP_OK;
}

esp_err_t set_state(State s) {
    s_state = s;
    ESP_LOGI(TAG, "state = %s (no-op stub)",
             s == State::Idle ? "IDLE" : "OPERATE");
    return ESP_OK;
}

esp_err_t trim(int tube_id, int delta_counts) {
    ESP_LOGD(TAG, "trim tube %d %+d (no-op stub)", tube_id, delta_counts);
    return ESP_OK;
}

State current_state() { return s_state; }

}  // namespace bias

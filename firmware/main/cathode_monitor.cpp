// =============================================================================
//  cathode_monitor.cpp — stub.  See header.
// =============================================================================
#include "cathode_monitor.h"

#include "esp_log.h"

namespace cathode {

namespace { constexpr char TAG[] = "cathode"; }

esp_err_t init(i2c_master_bus_handle_t /*bus*/) {
    ESP_LOGW(TAG, "ADS1115 cathode monitor not implemented yet (stub)");
    return ESP_OK;
}

float current_mA(int /*tube_id*/) {
    return 0.0f;
}

}  // namespace cathode

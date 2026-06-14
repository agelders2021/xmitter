// =============================================================================
//  fault_handler.cpp — stub.  See header.
// =============================================================================
#include "fault_handler.h"

#include "esp_log.h"

namespace fault {

namespace {
constexpr char TAG[] = "fault";
Cause s_cause = Cause::None;
}

esp_err_t init() {
    ESP_LOGW(TAG, "fault handler not implemented yet (stub)");
    s_cause = Cause::None;
    return ESP_OK;
}

esp_err_t assert_fault(Cause c) {
    s_cause = c;
    ESP_LOGE(TAG, "ASSERT cause=%d (stub — no hardware gate driven)", (int)c);
    return ESP_OK;
}

esp_err_t clear() {
    ESP_LOGI(TAG, "CLEAR (stub)");
    s_cause = Cause::None;
    return ESP_OK;
}

Cause current_cause() { return s_cause; }
bool  is_asserted()   { return s_cause != Cause::None; }

}  // namespace fault

// =============================================================================
//  keyer_winkey.cpp — stub.  See header.
// =============================================================================
#include "keyer_winkey.h"

#include "esp_log.h"
#include "keyer_envelope.h"

namespace winkey {

namespace { constexpr char TAG[] = "winkey"; }

esp_err_t init() {
    ESP_LOGW(TAG, "winkey scheduler not implemented yet (stub)");
    return ESP_OK;
}

void set_wpm(float wpm) {
    keyer::set_wpm(wpm);
}

}  // namespace winkey

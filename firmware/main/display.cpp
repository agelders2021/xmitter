// =============================================================================
//  display.cpp -- see header.
// =============================================================================
#include "display.h"

#include <cstdio>
#include <cstring>

#include "esp_log.h"
#include "esp_check.h"

#include "pin_map.h"
#include "vfo_si5351.h"

namespace display {

namespace {
constexpr char TAG[] = "display";
constexpr uint8_t LCD_COLS = 20;
}  // namespace

Display g_display;

// -----------------------------------------------------------------------------
// Public API
// -----------------------------------------------------------------------------
esp_err_t Display::begin(i2c_master_bus_handle_t bus)
{
    if (begun_) return ESP_OK;
    if (!bus)   return ESP_ERR_INVALID_ARG;

    ESP_RETURN_ON_ERROR(pcf_.begin(bus, pins::I2C_ADDR_PCF8575_PANEL),
                        TAG, "pcf8575 begin");
    ESP_RETURN_ON_ERROR(lcd_.begin(&pcf_), TAG, "lcd begin");

    // White backlight (all three channels on) so the display is legible
    // right after boot.  Firmware can dim / recolor later.
    lcd_.backlight_rgb(true, true, true);

    // Splash: fixed content so the user can tell the LCD is alive even if
    // the VFO isn't reporting.
    lcd_.set_cursor(0, 0);
    lcd_.print("     xmitter  20m   ");     // 20 chars
    lcd_.set_cursor(1, 0);
    lcd_.print("        --  Hz      ");     // placeholder for freq
    lcd_.set_cursor(2, 0);
    lcd_.print("                    ");
    lcd_.set_cursor(3, 0);
    lcd_.print("                    ");

    begun_ = true;
    return ESP_OK;
}

esp_err_t Display::start(BaseType_t   core,
                        UBaseType_t   prio,
                        uint32_t      stack_words,
                        TickType_t    period)
{
    if (handle_) return ESP_OK;
    if (!begun_) return ESP_ERR_INVALID_STATE;

    period_ = period;

    BaseType_t r = xTaskCreatePinnedToCore(
        &Display::task_entry, "display",
        stack_words, this, prio, &handle_, core);
    if (r != pdPASS) {
        ESP_LOGE(TAG, "task create failed");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "task pinned to core %d, prio %u, period %u ms",
             (int)core, (unsigned)prio,
             (unsigned)(period_ * portTICK_PERIOD_MS));
    return ESP_OK;
}

void Display::mark_dirty() { dirty_ = true; }

// -----------------------------------------------------------------------------
// Task
// -----------------------------------------------------------------------------
void Display::task_entry(void *arg) {
    static_cast<Display *>(arg)->run();
}

void Display::run() {
    ESP_LOGI(TAG, "display task running on core %d", xPortGetCoreID());
    TickType_t last_wake = xTaskGetTickCount();
    for (;;) {
        vTaskDelayUntil(&last_wake, period_);

        // Cheap dirty check: refresh line 1 if the frequency has changed
        // OR if someone explicitly requested a refresh.
        uint32_t cur = vfo::current_freq();
        if (dirty_ || cur != last_freq_hz_) {
            refresh_line1_();
            last_freq_hz_ = cur;
            dirty_ = false;
        }
    }
}

void Display::refresh_line1_()
{
    // Line 1 layout for a 20-char row:
    //     "   14,200,000 Hz    "
    //  positions 0..2 pad, freq starts at col 3, unit at col 16, pad to 20.
    // The comma-formatted frequency is at most 13 chars ("4,294,967,295")
    // so it fits in cols 3..15 with 3 chars of unit tail.
    char buf[24];
    char freq[16];
    size_t nf = format_with_commas(freq, sizeof(freq), vfo::current_freq());
    if (nf == 0) { std::strcpy(freq, "?"); nf = 1; }

    // Center the freq in the 14-char freq field for readability.
    // Field: cols 3..16 (14 chars).  Actually we'll left-pad freq into the
    // full 20-char line, then append " Hz" and pad the rest with spaces.
    std::snprintf(buf, sizeof(buf), "%*s Hz", (int)(17 - 3), freq);
    // buf is now "<pad-to-14>freq Hz" -- length 17.  Pad to 20 with spaces.
    size_t len = std::strlen(buf);
    while (len < LCD_COLS) buf[len++] = ' ';
    buf[LCD_COLS] = '\0';

    lcd_.set_cursor(1, 0);
    lcd_.print(buf);
}

// -----------------------------------------------------------------------------
// Free function: comma formatter
// -----------------------------------------------------------------------------
size_t format_with_commas(char *buf, size_t buflen, uint32_t value)
{
    // Format value as decimal into a scratch string, then re-emit into buf
    // with a comma every three digits from the right.
    char tmp[16];
    int n = std::snprintf(tmp, sizeof(tmp), "%lu", (unsigned long)value);
    if (n <= 0) return 0;

    int commas   = (n - 1) / 3;
    size_t total = (size_t)n + (size_t)commas;
    if (total + 1 > buflen) return 0;

    // Walk from right to left copying digits, inserting a comma every 3.
    int src = n - 1;
    size_t dst = total - 1;
    buf[total] = '\0';
    int digit_i = 0;
    while (src >= 0) {
        if (digit_i == 3) {
            buf[dst--] = ',';
            digit_i = 0;
        }
        buf[dst--] = tmp[src--];
        digit_i++;
    }
    return total;
}

}  // namespace display

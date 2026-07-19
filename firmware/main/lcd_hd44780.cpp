// =============================================================================
//  lcd_hd44780.cpp -- see header.
// =============================================================================
#include "lcd_hd44780.h"

#include <cstring>

#include "esp_log.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "rom/ets_sys.h"     // ets_delay_us for sub-tick waits

namespace lcd {

// -----------------------------------------------------------------------------
// PCF8575 pin assignment for the WH2004A on the front-panel PCB.  Verified
// against KiCAD/frontpanel/frontpanel.kicad_sch on 2026-07-17.  Adafruit
// breakout pin labels (P0..P15) map linearly to the 16-bit shadow bits.
//
// NOTE (2026-07-19): the front-panel PCB now also has P0..P3 routed to the
// LCD's DB0..DB3 header pins (previously left unrouted).  In 4-bit mode
// the LCD ignores DB0..DB3 completely, so this driver still writes only
// via DB4..DB7.  If the LCD ever needs 8-bit mode, add db0..db3 fields
// to PinMap, rewrite write_byte_() to send a full byte per E-pulse, and
// switch the wake-up sequence from 0x3 (8-bit function set) to 0x2
// (4-bit function set) accordingly.  Until then, firmware should treat
// P0..P3 as reserved-for-LCD -- i.e., leave them at whatever value the
// PCF8575 shadow already has and don't drive them for other purposes
// while E is toggling (mechanically the jumper wires at the LCD header
// can be popped if P0..P3 need reallocation for LEDs / paddle / etc.).
// -----------------------------------------------------------------------------
const PinMap kDefaultPinMap = {
    .rs   = 12,   // P12
    .e    = 11,   // P11
    .db4  = 4,    // P4  (P0..P3 also wired to DB0..DB3 but unused in 4-bit)
    .db5  = 5,    // P5
    .db6  = 6,    // P6
    .db7  = 7,    // P7
    .bl_r = 8,    // P8  -- red   backlight FET gate  (1 = ON via 2N7000)
    .bl_g = 9,    // P9  -- green backlight FET gate
    .bl_b = 10,   // P10 -- blue  backlight FET gate
};

namespace {
constexpr char TAG[] = "lcd";

// HD44780 commands
constexpr uint8_t CMD_CLEAR       = 0x01;
constexpr uint8_t CMD_HOME        = 0x02;
constexpr uint8_t CMD_ENTRY       = 0x04;   // + I/D (increment), S (shift)
constexpr uint8_t CMD_DISPLAY     = 0x08;   // + D (on), C (cursor), B (blink)
constexpr uint8_t CMD_FUNCTION    = 0x20;   // + DL (data length), N (lines), F (font)
constexpr uint8_t CMD_SET_DDRAM   = 0x80;

// DDRAM row addresses for a 20x4 display (WH2004A page 12)
constexpr uint8_t ROW_ADDR[4] = { 0x00, 0x40, 0x14, 0x54 };

}  // namespace

// -----------------------------------------------------------------------------
// Bring-up
// -----------------------------------------------------------------------------
esp_err_t HD44780::begin(pcf8575::Device *pcf, const PinMap &pins)
{
    if (!pcf) return ESP_ERR_INVALID_ARG;
    pcf_  = pcf;
    pins_ = pins;

    // Winstar page 18 says to wait > 40 ms after VDD stable.  We're called
    // long after boot, so this is defensive but cheap.
    vTaskDelay(pdMS_TO_TICKS(50));

    // Force RS=0, E=0, all data bits=0, backlight off to start.
    pcf_->set_shadow(0);
    ESP_RETURN_ON_ERROR(pcf_->apply(), TAG, "pcf init write");

    // Wake-up sequence (8-bit mode function-set, three times, per HD44780
    // spec).  Only the high nibble matters here.
    ESP_RETURN_ON_ERROR(write_nibble_(0x03, false), TAG, "wake 1");
    vTaskDelay(pdMS_TO_TICKS(5));
    ESP_RETURN_ON_ERROR(write_nibble_(0x03, false), TAG, "wake 2");
    ets_delay_us(150);
    ESP_RETURN_ON_ERROR(write_nibble_(0x03, false), TAG, "wake 3");
    ets_delay_us(150);

    // Now switch to 4-bit interface.
    ESP_RETURN_ON_ERROR(write_nibble_(0x02, false), TAG, "4-bit switch");
    ets_delay_us(150);

    // Full function set: 4-bit, 2-line (works for 20x4 -- controller sees it
    // as two logical lines that wrap), 5x8 font.
    ESP_RETURN_ON_ERROR(cmd_(CMD_FUNCTION | 0x08), TAG, "function set");
    ets_delay_us(50);

    // Display OFF while we configure entry mode + clear.
    ESP_RETURN_ON_ERROR(cmd_(CMD_DISPLAY), TAG, "display off");
    ets_delay_us(50);
    ESP_RETURN_ON_ERROR(cmd_(CMD_CLEAR), TAG, "clear");
    vTaskDelay(pdMS_TO_TICKS(3));       // clear takes ~1.53 ms

    // Entry mode: increment cursor, no display shift.
    ESP_RETURN_ON_ERROR(cmd_(CMD_ENTRY | 0x02), TAG, "entry mode");
    ets_delay_us(50);

    // Display ON, cursor off, blink off.
    ESP_RETURN_ON_ERROR(cmd_(CMD_DISPLAY | 0x04), TAG, "display on");
    ets_delay_us(50);

    ESP_LOGI(TAG, "HD44780 init done (RS=P%02u E=P%02u DB4..7=P%02u..P%02u)",
             pins_.rs, pins_.e, pins_.db4, pins_.db7);
    return ESP_OK;
}

// -----------------------------------------------------------------------------
// Control commands
// -----------------------------------------------------------------------------
esp_err_t HD44780::clear() {
    esp_err_t e = cmd_(CMD_CLEAR);
    vTaskDelay(pdMS_TO_TICKS(3));
    return e;
}

esp_err_t HD44780::home() {
    esp_err_t e = cmd_(CMD_HOME);
    vTaskDelay(pdMS_TO_TICKS(3));
    return e;
}

esp_err_t HD44780::set_cursor(uint8_t row, uint8_t col) {
    if (row >= 4) row = 3;
    return cmd_(CMD_SET_DDRAM | (uint8_t)(ROW_ADDR[row] + col));
}

esp_err_t HD44780::print(const char *s) {
    if (!s) return ESP_ERR_INVALID_ARG;
    while (*s) {
        esp_err_t e = data_((uint8_t)*s++);
        if (e != ESP_OK) return e;
    }
    return ESP_OK;
}

esp_err_t HD44780::print(char c) {
    return data_((uint8_t)c);
}

esp_err_t HD44780::display_on(bool on) {
    return cmd_(CMD_DISPLAY | (on ? 0x04 : 0x00));
}

esp_err_t HD44780::backlight_rgb(bool r, bool g, bool b) {
    if (!pcf_) return ESP_ERR_INVALID_STATE;
    pcf_->shadow_bit(pins_.bl_r, r);
    pcf_->shadow_bit(pins_.bl_g, g);
    pcf_->shadow_bit(pins_.bl_b, b);
    return pcf_->apply();
}

// -----------------------------------------------------------------------------
// Low-level nibble / byte writes
// -----------------------------------------------------------------------------
// Build one PCF8575 shadow with RS + data nibble + backlight state (from
// current shadow), assert E, pulse.  RS is passed in; data comes from the
// low nibble of `nibble` argument.  Backlight bits in the shadow are left
// untouched (they may be set by a preceding backlight_rgb() call).
esp_err_t HD44780::write_nibble_(uint8_t nibble, bool rs)
{
    if (!pcf_) return ESP_ERR_INVALID_STATE;

    pcf_->shadow_bit(pins_.rs,  rs);
    pcf_->shadow_bit(pins_.e,   false);
    pcf_->shadow_bit(pins_.db4, (nibble & 0x01) != 0);
    pcf_->shadow_bit(pins_.db5, (nibble & 0x02) != 0);
    pcf_->shadow_bit(pins_.db6, (nibble & 0x04) != 0);
    pcf_->shadow_bit(pins_.db7, (nibble & 0x08) != 0);
    ESP_RETURN_ON_ERROR(pcf_->apply(), TAG, "nibble setup");

    return pulse_e_();
}

esp_err_t HD44780::write_byte_(uint8_t byte, bool rs)
{
    ESP_RETURN_ON_ERROR(write_nibble_(byte >> 4,   rs), TAG, "high nibble");
    ESP_RETURN_ON_ERROR(write_nibble_(byte & 0x0F, rs), TAG, "low nibble");
    return ESP_OK;
}

esp_err_t HD44780::pulse_e_()
{
    // Assert E, wait > Tpw (140 ns per WH2004A), de-assert, wait > Tc - Tpw
    // (~1000 ns).  I2C write time (~30 us at 400 kHz) already dwarfs these
    // limits, so the delays are mostly documentation.
    pcf_->shadow_bit(pins_.e, true);
    ESP_RETURN_ON_ERROR(pcf_->apply(), TAG, "E hi");
    ets_delay_us(1);
    pcf_->shadow_bit(pins_.e, false);
    ESP_RETURN_ON_ERROR(pcf_->apply(), TAG, "E lo");
    ets_delay_us(50);       // instruction execution time (39 us for most cmds)
    return ESP_OK;
}

}  // namespace lcd

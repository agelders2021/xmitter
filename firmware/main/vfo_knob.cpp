// =============================================================================
//  vfo_knob.cpp -- see header.
// =============================================================================
#include "vfo_knob.h"

#include <algorithm>
#include <cstdlib>

#include "esp_log.h"
#include "esp_check.h"

#include "pin_map.h"
#include "vfo_si5351.h"
#include "encoders.h"     // FREQ_MIN_HZ / FREQ_MAX_HZ / FREQ_STEP_HZ_TABLE

namespace knob {

namespace {

constexpr char TAG[] = "knob";

// PCNT clock on ESP32-S3 is APB (80 MHz).  A 1000 ns glitch filter kills
// sub-microsecond spikes -- well below any real MBL-600 transition
// (peak ~2.5 kHz per channel = 400 us minimum period) but above the
// RF-coupling / ESD-transient timescales.
constexpr uint32_t GLITCH_NS  = 1000;

// PCNT counter ceiling.  Worst-case knob spin is roughly 6 rev/s of a
// 100 PPR encoder in 4x quadrature = 2400 counts/s.  At 20 ms poll
// that's 48 counts per poll cycle, so 10 000 is a comfortable ceiling.
constexpr int      PCNT_LIMIT = 10000;

// Tier thresholds: |delta counts per poll| -> multiplier.  See
// Documentation/front_panel_interface.md for the derivation.
constexpr int16_t TIER1_MAX = 1;    // <= 1  -> 1x    (precision tuning)
constexpr int16_t TIER2_MAX = 5;    // <= 5  -> 10x   (comfortable spin)
constexpr int16_t TIER3_MAX = 15;   // <= 15 -> 100x  (band-hopping)
                                    //  >15  -> 1000x (frantic)

}  // namespace

VfoKnob g_vfo_knob;

// ------------------------------------------------------------------------- //
// Hardware bring-up                                                         //
// ------------------------------------------------------------------------- //
esp_err_t VfoKnob::begin(gpio_num_t a, gpio_num_t b)
{
    if (a == GPIO_NUM_NC || b == GPIO_NUM_NC) {
        ESP_LOGW(TAG, "MBL-600 A/B pins NC -- knob disabled");
        return ESP_OK;
    }
    if (unit_) return ESP_OK;   // already begun

    // ---- PCNT unit ---------------------------------------------------------
    pcnt_unit_config_t unit_cfg = {};
    unit_cfg.low_limit           = -PCNT_LIMIT;
    unit_cfg.high_limit          =  PCNT_LIMIT;
    unit_cfg.flags.accum_count   = true;
    ESP_RETURN_ON_ERROR(pcnt_new_unit(&unit_cfg, &unit_), TAG, "pcnt_new_unit");

    pcnt_glitch_filter_config_t filter = { .max_glitch_ns = GLITCH_NS };
    ESP_RETURN_ON_ERROR(pcnt_unit_set_glitch_filter(unit_, &filter),
                        TAG, "glitch filter");

    // ---- Channel A: edges on pin A, direction gated by level of pin B -----
    pcnt_chan_config_t chan_a_cfg = {};
    chan_a_cfg.edge_gpio_num  = a;
    chan_a_cfg.level_gpio_num = b;
    ESP_RETURN_ON_ERROR(pcnt_new_channel(unit_, &chan_a_cfg, &chan_a_),
                        TAG, "chan A");
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_edge_action(chan_a_,
            PCNT_CHANNEL_EDGE_ACTION_DECREASE,   // A rising
            PCNT_CHANNEL_EDGE_ACTION_INCREASE),  // A falling
        TAG, "chan A edge");
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_level_action(chan_a_,
            PCNT_CHANNEL_LEVEL_ACTION_KEEP,      // B high: keep as-is
            PCNT_CHANNEL_LEVEL_ACTION_INVERSE),  // B low : invert
        TAG, "chan A level");

    // ---- Channel B: edges on pin B, direction gated by level of pin A -----
    pcnt_chan_config_t chan_b_cfg = {};
    chan_b_cfg.edge_gpio_num  = b;
    chan_b_cfg.level_gpio_num = a;
    ESP_RETURN_ON_ERROR(pcnt_new_channel(unit_, &chan_b_cfg, &chan_b_),
                        TAG, "chan B");
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_edge_action(chan_b_,
            PCNT_CHANNEL_EDGE_ACTION_INCREASE,   // B rising
            PCNT_CHANNEL_EDGE_ACTION_DECREASE),  // B falling
        TAG, "chan B edge");
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_level_action(chan_b_,
            PCNT_CHANNEL_LEVEL_ACTION_KEEP,
            PCNT_CHANNEL_LEVEL_ACTION_INVERSE),
        TAG, "chan B level");

    ESP_RETURN_ON_ERROR(pcnt_unit_enable(unit_),      TAG, "unit enable");
    ESP_RETURN_ON_ERROR(pcnt_unit_clear_count(unit_), TAG, "clear count");
    ESP_RETURN_ON_ERROR(pcnt_unit_start(unit_),       TAG, "unit start");

    ESP_LOGI(TAG, "MBL-600 PCNT up on GPIO %d/%d, glitch %uns",
             (int)a, (int)b, (unsigned)GLITCH_NS);
    return ESP_OK;
}

// ------------------------------------------------------------------------- //
// Task management                                                           //
// ------------------------------------------------------------------------- //
esp_err_t VfoKnob::start(BaseType_t   core,
                        UBaseType_t  prio,
                        uint32_t     stack_words,
                        TickType_t   poll_period)
{
    if (handle_) return ESP_OK;   // already started
    period_ = poll_period;

    BaseType_t r = xTaskCreatePinnedToCore(
        &VfoKnob::task_entry,
        "vfo_knob",
        stack_words,
        this,
        prio,
        &handle_,
        core);
    if (r != pdPASS) {
        ESP_LOGE(TAG, "task create failed");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "task pinned to core %d, prio %u, period %u ms",
             (int)core, (unsigned)prio,
             (unsigned)(period_ * portTICK_PERIOD_MS));
    return ESP_OK;
}

void VfoKnob::task_entry(void *arg)
{
    static_cast<VfoKnob *>(arg)->run();
}

void VfoKnob::run()
{
    ESP_LOGI(TAG, "knob task running on core %d", xPortGetCoreID());
    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        vTaskDelayUntil(&last_wake, period_);
        stats_.poll_count++;

        if (!unit_) continue;   // hardware not brought up

        int cur = 0;
        pcnt_unit_get_count(unit_, &cur);
        if (cur == 0) continue;
        pcnt_unit_clear_count(unit_);

        int16_t delta = (int16_t)cur;
        stats_.last_delta       = std::abs((int)delta);
        stats_.total_ticks_abs += std::abs((int)delta);

        uint32_t mult = multiplier_for(delta);
        stats_.last_multiplier = mult;

        // Apply tiered step to the current VFO frequency, clamped to band.
        int64_t step_hz = (int64_t)delta * (int64_t)base_step_hz_ * (int64_t)mult;
        int64_t curf    = (int64_t)vfo::current_freq();
        int64_t next    = std::clamp(curf + step_hz,
                                     (int64_t)encoders::FREQ_MIN_HZ,
                                     (int64_t)encoders::FREQ_MAX_HZ);
        if ((uint32_t)next != vfo::current_freq()) {
            vfo::set_freq((uint32_t)next);
        }
    }
}

// ------------------------------------------------------------------------- //
// Accessors + shim                                                          //
// ------------------------------------------------------------------------- //
void     VfoKnob::set_base_step_hz(uint32_t hz) { base_step_hz_ = hz; }
uint32_t VfoKnob::base_step_hz() const          { return base_step_hz_; }
VfoKnob::Stats VfoKnob::stats() const           { return stats_; }

uint32_t VfoKnob::multiplier_for(int16_t delta)
{
    int16_t abs_d = (int16_t)std::abs((int)delta);
    if (abs_d <= TIER1_MAX) return 1;
    if (abs_d <= TIER2_MAX) return 10;
    if (abs_d <= TIER3_MAX) return 100;
    return 1000;
}

void VfoKnob::inject(int16_t ticks)
{
    if (ticks == 0) return;
    uint32_t mult = multiplier_for(ticks);
    int64_t  step = (int64_t)ticks * (int64_t)base_step_hz_ * (int64_t)mult;
    int64_t  curf = (int64_t)vfo::current_freq();
    int64_t  next = std::clamp(curf + step,
                               (int64_t)encoders::FREQ_MIN_HZ,
                               (int64_t)encoders::FREQ_MAX_HZ);
    if ((uint32_t)next != vfo::current_freq()) {
        vfo::set_freq((uint32_t)next);
    }
}

}  // namespace knob

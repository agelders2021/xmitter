// =============================================================================
//  vfo_knob.cpp -- see header.
// =============================================================================
#include "vfo_knob.h"

#include <algorithm>
#include <cstdlib>

#include "esp_log.h"
#include "esp_check.h"
#include "esp_timer.h"

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

// PCNT counter ceiling.  At 100 PPR × 4x quadrature × 6 rev/s = 2400
// counts/s; 10 000 is a comfortable ceiling that the counter will never
// reach between ISR wake-ups.
constexpr int PCNT_LIMIT = 10000;

// Watchpoints that arm the ISR.  Any movement from 0 crosses ±1 and
// gives the semaphore.  After the task reads and clears the counter, the
// hardware counter is back at 0 and the watchpoints re-arm automatically.
constexpr int WP_POS =  1;
constexpr int WP_NEG = -1;

// Tier thresholds: |delta counts per poll| -> multiplier.  See
// Documentation/front_panel_interface.md for the derivation.
constexpr int16_t TIER1_MAX = 1;    // <= 1  -> 1x    (precision tuning)
constexpr int16_t TIER2_MAX = 5;    // <= 5  -> 10x   (comfortable spin)
constexpr int16_t TIER3_MAX = 15;   // <= 15 -> 100x  (band-hopping)
                                    //  >15  -> 1000x (frantic)

}  // namespace

VfoKnob g_vfo_knob;

// ISR: runs in interrupt context.  Gives the semaphore so run() unblocks.
bool IRAM_ATTR VfoKnob::on_reach_isr(pcnt_unit_handle_t /*unit*/,
                                      const pcnt_watch_event_data_t * /*edata*/,
                                      void *user_data)
{
    SemaphoreHandle_t sem = static_cast<SemaphoreHandle_t>(user_data);
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(sem, &woken);
    return woken == pdTRUE;
}

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

    // 2x quadrature decode: count edges on the CW-lag signal (b), gate
    // direction by the CW-lead signal (a).
    //
    // Counting `b` edges means the first event of each half-cycle is `b`
    // rising/falling -- at that moment `a` is solidly mid-cycle (it
    // transitioned one step earlier) and is the most stable possible level
    // sample.  Counting `a` edges (the previous approach) fires the PCNT
    // at the *last* event of each half-cycle for CW but the *first* event
    // for CCW; at that first CCW transition `a` is just starting to
    // settle, and signal skew through the RS-422 chain put the level gate
    // in the wrong state (giving +1 instead of -1 for CCW).
    pcnt_chan_config_t chan_a_cfg = {};
    chan_a_cfg.edge_gpio_num  = b;   // CW-lag signal  (GPIO2, encoder A) -- count its edges
    chan_a_cfg.level_gpio_num = a;   // CW-lead signal (GPIO3, encoder B) -- gate direction
    ESP_RETURN_ON_ERROR(pcnt_new_channel(unit_, &chan_a_cfg, &chan_a_),
                        TAG, "chan A");
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_edge_action(chan_a_,
            PCNT_CHANNEL_EDGE_ACTION_INCREASE,   // `b` rising  → base INCREASE
            PCNT_CHANNEL_EDGE_ACTION_DECREASE),  // `b` falling → base DECREASE
        TAG, "chan A edge");
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_level_action(chan_a_,
            PCNT_CHANNEL_LEVEL_ACTION_KEEP,      // `a` high → keep base action
            PCNT_CHANNEL_LEVEL_ACTION_INVERSE),  // `a` low  → invert base action
        TAG, "chan A level");
    // chan_b_ intentionally left unconfigured (2x decode).

    // Watchpoints at ±1: any movement from 0 fires on_reach_isr, which gives
    // sem_.  After the task reads and clears the counter, it returns to 0 and
    // the watchpoints re-arm automatically for the next movement.
    sem_ = xSemaphoreCreateBinary();
    if (!sem_) return ESP_ERR_NO_MEM;

    ESP_RETURN_ON_ERROR(pcnt_unit_add_watch_point(unit_, WP_POS), TAG, "wp +1");
    ESP_RETURN_ON_ERROR(pcnt_unit_add_watch_point(unit_, WP_NEG), TAG, "wp -1");

    pcnt_event_callbacks_t cbs = {};
    cbs.on_reach = on_reach_isr;
    ESP_RETURN_ON_ERROR(pcnt_unit_register_event_callbacks(unit_, &cbs, sem_),
                        TAG, "register cb");

    ESP_RETURN_ON_ERROR(pcnt_unit_enable(unit_),      TAG, "unit enable");
    ESP_RETURN_ON_ERROR(pcnt_unit_clear_count(unit_), TAG, "clear count");
    ESP_RETURN_ON_ERROR(pcnt_unit_start(unit_),       TAG, "unit start");

    ESP_LOGI(TAG, "MBL-600 PCNT up, 2x decode: edge GPIO %d, gate GPIO %d, glitch %uns",
             (int)a, (int)b, (unsigned)GLITCH_NS);
    return ESP_OK;
}

// ------------------------------------------------------------------------- //
// Task management                                                           //
// ------------------------------------------------------------------------- //
esp_err_t VfoKnob::start(BaseType_t  core,
                         UBaseType_t prio,
                         uint32_t    stack_words)
{
    if (handle_) return ESP_OK;   // already started

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
    ESP_LOGI(TAG, "task pinned to core %d, prio %u (interrupt-driven)",
             (int)core, (unsigned)prio);
    return ESP_OK;
}

void VfoKnob::task_entry(void *arg)
{
    static_cast<VfoKnob *>(arg)->run();
}

void VfoKnob::run()
{
    ESP_LOGI(TAG, "knob task running on core %d (interrupt-driven)", xPortGetCoreID());

    // Debounce state: suppress reversals within 20 ms of the last applied step.
    // An optical encoder shouldn't bounce, but a single-tick overshoot on knob
    // release would otherwise undo the previous step entirely.
    constexpr int64_t DEBOUNCE_US = 20000;
    int8_t  last_dir     = 0;
    int64_t last_step_us = 0;

    for (;;) {
        // Block until the PCNT watchpoint ISR fires (any encoder movement).
        xSemaphoreTake(sem_, portMAX_DELAY);
        stats_.poll_count++;

        if (!unit_) continue;

        int cur = 0;
        pcnt_unit_get_count(unit_, &cur);
        // Clear before applying so the watchpoints re-arm from 0.
        // Any counts arriving in the tiny window between get and clear are
        // absorbed into the next interrupt; acceptable for a VFO knob.
        pcnt_unit_clear_count(unit_);

        int16_t delta = (int16_t)cur;
        stats_.last_delta       = std::abs((int)delta);
        stats_.total_ticks_abs += std::abs((int)delta);

        if (delta == 0) continue;   // count cleared between WP and get_count

        ESP_LOGW(TAG, "raw delta=%+d", (int)delta);  // TODO remove after CCW decode confirmed

        // Suppress a direction reversal that arrives within the debounce window.
        int8_t  dir = (delta > 0) ? 1 : -1;
        int64_t now = esp_timer_get_time();
        if (dir == -last_dir && (now - last_step_us) < DEBOUNCE_US) {
            ESP_LOGW(TAG, "  suppressed (debounce)");
            continue;
        }
        last_dir     = dir;
        last_step_us = now;

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

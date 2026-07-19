// =============================================================================
//  vfo_knob.h -- MBL-600 -> Si5351 frequency-tuning knob.
//
//  Owns a PCNT unit configured for 4x quadrature decoding of the two
//  differential A/B pairs coming out of the AM26LS32 receiver on the
//  analog board's interface sheet (post-CAT6, post-single-ended level
//  shift).  Runs a periodic polling task that reads the accumulated
//  counter delta, applies a tiered velocity multiplier, and dispatches
//  to vfo::set_freq().
//
//  Design decisions:
//    - PCNT does quadrature in silicon (no missed ticks even at fast
//      knob spin).  Polling reads the accumulated delta once per period
//      -- simpler than a per-tick ISR, and adequate because 20 ms max
//      display latency is imperceptible for VFO tuning.
//    - Tiered multiplier (1x / 10x / 100x / 1000x based on |delta|)
//      keyed off delta-per-poll.  Threshold tuning is at the top of
//      vfo_knob.cpp; see the front-panel doc for rationale.
//    - Singleton (there is one VFO knob), but wrapped in a class so
//      start(core, prio, ...) chooses the RTOS home at boot -- the same
//      module can run on CORE_MONITOR or CORE_KEYING by changing one
//      argument.  See Documentation/front_panel_interface.md.
// =============================================================================
#pragma once

#include <cstdint>

#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/pulse_cnt.h"

namespace knob {

class VfoKnob {
 public:
    // Bring up the PCNT unit + both channels.  Idempotent.  If either
    // pin is GPIO_NUM_NC the knob logs a warning and stays disabled --
    // subsequent begin/start/inject calls become no-ops.
    esp_err_t begin(gpio_num_t a, gpio_num_t b);

    // Spawn the polling task pinned to `core` at priority `prio`.  Choose
    // `poll_period` in ticks (default 20 ms = 50 Hz).  Idempotent.
    esp_err_t start(BaseType_t   core,
                    UBaseType_t  prio        = 4,
                    uint32_t     stack_words = 4096,
                    TickType_t   poll_period = pdMS_TO_TICKS(20));

    // STEP-button integration will call this once we implement it.  For
    // now the default is 10 Hz.  Values should come from
    // encoders::FREQ_STEP_HZ_TABLE.
    void     set_base_step_hz(uint32_t hz);
    uint32_t base_step_hz() const;

    // Console shim: pretend the encoder moved `ticks` counts between two
    // consecutive polls.  Reuses the same tier math as a real turn, so
    // `freq +N` from the shell exercises the full path before the
    // MBL-600 is wired.
    void inject(int16_t ticks);

    // Debug snapshot -- accessed by the console `knob stats` command.
    struct Stats {
        uint32_t poll_count;         // number of poll ticks since boot
        uint32_t last_delta;         // |delta| of the most recent nonzero poll
        uint32_t last_multiplier;    // multiplier applied to that delta
        uint32_t total_ticks_abs;    // running sum of |delta| across all polls
    };
    Stats stats() const;

 private:
    static void task_entry(void *self);
    void run();

    // Delta -> multiplier lookup.  Also used by inject().
    static uint32_t multiplier_for(int16_t delta);

    // Hardware
    pcnt_unit_handle_t    unit_   = nullptr;
    pcnt_channel_handle_t chan_a_ = nullptr;
    pcnt_channel_handle_t chan_b_ = nullptr;

    // Task
    TaskHandle_t handle_ = nullptr;
    TickType_t   period_ = pdMS_TO_TICKS(20);

    // State (task-only after start())
    uint32_t base_step_hz_ = 10;
    Stats    stats_        = {};
};

// Global instance.  Declared here, defined in the .cpp.
extern VfoKnob g_vfo_knob;

}  // namespace knob

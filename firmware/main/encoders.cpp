// =============================================================================
//  encoders.cpp — PCNT-based quadrature decode for the three front-panel
//  encoders.  Pinned polling task on core 0 reads counters every 10 ms,
//  computes deltas, and dispatches to the VFO / step table / func channel.
//
//  Why poll rather than use PCNT watchpoint callbacks:
//    - Bookkeeping is simpler (one place that owns delta → action).
//    - 10 ms tick is fast enough for the operator (100 updates/sec) while
//      coalescing multi-step spins into single VFO writes.
//    - Mechanical PEC11 bounce (5 ms max) gets debounced by the period
//      itself + the PCNT glitch filter (~12.8 µs).
// =============================================================================
#include "encoders.h"

#include <atomic>
#include <cstdint>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/pulse_cnt.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_check.h"
#include "esp_timer.h"

#include "pin_map.h"
#include "vfo_si5351.h"

namespace encoders {

namespace {

constexpr char TAG[] = "enc";

// PCNT counter wraps at this magnitude — well within the int16 range of the
// counter.  Big enough that a fast spin between 10 ms polls won't saturate
// (100 PPR × 6 rev/s × 4 quad transitions × 10 ms = 24 counts/tick).
constexpr int PCNT_LIMIT = 10000;

// Glitch-filter span.  PCNT source clock on the S3 is APB = 80 MHz; 1000 ns
// kills sub-1µs spikes — well below mechanical bounce timescales but enough
// for RF coupling immunity.
constexpr uint32_t GLITCH_NS = 1000;

// ---- State ---------------------------------------------------------------
pcnt_unit_handle_t s_unit_freq = nullptr;
pcnt_unit_handle_t s_unit_step = nullptr;
pcnt_unit_handle_t s_unit_func = nullptr;

int s_last_freq = 0;
int s_last_step = 0;
int s_last_func = 0;

std::atomic<size_t> s_step_index { FREQ_STEP_DEFAULT_INDEX };
std::atomic<int>    s_func_accum { 0 };
std::atomic<bool>   s_step_pressed { false };
std::atomic<bool>   s_func_pressed { false };

// ---- Helpers ---------------------------------------------------------------
esp_err_t make_unit(gpio_num_t a, gpio_num_t b, pcnt_unit_handle_t *out,
                    const char *tag)
{
    if (a == GPIO_NUM_NC || b == GPIO_NUM_NC) {
        ESP_LOGI(TAG, "%s: A/B pins not wired, skipping", tag);
        *out = nullptr;
        return ESP_OK;
    }

    pcnt_unit_config_t unit_cfg = {};
    unit_cfg.high_limit = PCNT_LIMIT;
    unit_cfg.low_limit  = -PCNT_LIMIT;
    unit_cfg.flags.accum_count = true;   // counter doesn't reset on watch hit
    ESP_RETURN_ON_ERROR(pcnt_new_unit(&unit_cfg, out), TAG, "pcnt_new_unit %s", tag);

    pcnt_glitch_filter_config_t filter = { .max_glitch_ns = GLITCH_NS };
    ESP_RETURN_ON_ERROR(pcnt_unit_set_glitch_filter(*out, &filter),
                        TAG, "glitch filter %s", tag);

    // Two channels for full quadrature decode.  Edge action = decrement /
    // increment depending on the level of the OTHER signal.
    pcnt_chan_config_t ch_cfg_a = {};
    ch_cfg_a.edge_gpio_num  = a;
    ch_cfg_a.level_gpio_num = b;
    pcnt_channel_handle_t ch_a;
    ESP_RETURN_ON_ERROR(pcnt_new_channel(*out, &ch_cfg_a, &ch_a),
                        TAG, "channel A %s", tag);
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_edge_action(ch_a, PCNT_CHANNEL_EDGE_ACTION_DECREASE,
                                            PCNT_CHANNEL_EDGE_ACTION_INCREASE),
        TAG, "edge A %s", tag);
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_level_action(ch_a, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
                                             PCNT_CHANNEL_LEVEL_ACTION_INVERSE),
        TAG, "level A %s", tag);

    pcnt_chan_config_t ch_cfg_b = {};
    ch_cfg_b.edge_gpio_num  = b;
    ch_cfg_b.level_gpio_num = a;
    pcnt_channel_handle_t ch_b;
    ESP_RETURN_ON_ERROR(pcnt_new_channel(*out, &ch_cfg_b, &ch_b),
                        TAG, "channel B %s", tag);
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_edge_action(ch_b, PCNT_CHANNEL_EDGE_ACTION_INCREASE,
                                            PCNT_CHANNEL_EDGE_ACTION_DECREASE),
        TAG, "edge B %s", tag);
    ESP_RETURN_ON_ERROR(
        pcnt_channel_set_level_action(ch_b, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
                                             PCNT_CHANNEL_LEVEL_ACTION_INVERSE),
        TAG, "level B %s", tag);

    // Internal pull-ups on the encoder inputs — PEC11s output open-collector
    // to GND, optical encoder is push-pull but pullups are harmless.
    gpio_set_pull_mode(a, GPIO_PULLUP_ONLY);
    gpio_set_pull_mode(b, GPIO_PULLUP_ONLY);

    ESP_RETURN_ON_ERROR(pcnt_unit_enable(*out), TAG, "enable %s", tag);
    ESP_RETURN_ON_ERROR(pcnt_unit_clear_count(*out), TAG, "clear %s", tag);
    ESP_RETURN_ON_ERROR(pcnt_unit_start(*out), TAG, "start %s", tag);
    return ESP_OK;
}

// Pushbutton setup — input with pullup, IRQ-on-fall to set a flag.
void IRAM_ATTR button_isr(void *arg) {
    auto *flag = static_cast<std::atomic<bool>*>(arg);
    flag->store(true, std::memory_order_relaxed);
}

esp_err_t setup_button(gpio_num_t pin, std::atomic<bool> *flag, const char *tag) {
    if (pin == GPIO_NUM_NC) return ESP_OK;
    gpio_config_t cfg = {};
    cfg.pin_bit_mask = 1ULL << (uint64_t)pin;
    cfg.mode         = GPIO_MODE_INPUT;
    cfg.pull_up_en   = GPIO_PULLUP_ENABLE;
    cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
    cfg.intr_type    = GPIO_INTR_NEGEDGE;
    ESP_RETURN_ON_ERROR(gpio_config(&cfg), TAG, "gpio_config %s", tag);
    return gpio_isr_handler_add(pin, button_isr, flag);
}

// ---- Polling task ----------------------------------------------------------
//  10 ms tick.  Drain PCNT counters, convert to deltas, apply to outputs.
void poll_task(void *) {
    ESP_LOGI(TAG, "encoder poll task running on core %d", xPortGetCoreID());
    const TickType_t period = pdMS_TO_TICKS(10);
    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        vTaskDelayUntil(&last_wake, period);

        // ---- Frequency encoder (optical, no /4 division) ----
        if (s_unit_freq) {
            int now = 0;
            pcnt_unit_get_count(s_unit_freq, &now);
            int d = now - s_last_freq;
            if (d != 0) {
                s_last_freq = now;
                uint32_t step = step_hz();
                int64_t  f    = (int64_t)vfo::current_freq() + (int64_t)d * step;
                if (f < (int64_t)FREQ_MIN_HZ) f = FREQ_MIN_HZ;
                if (f > (int64_t)FREQ_MAX_HZ) f = FREQ_MAX_HZ;
                vfo::set_freq((uint32_t)f);
            }
        }

        // ---- Step-size encoder (PEC11, /4 for detents) ----
        if (s_unit_step) {
            int now = 0;
            pcnt_unit_get_count(s_unit_step, &now);
            int raw_d = now - s_last_step;
            int clicks = raw_d / 4;                 // detent = one click
            if (clicks != 0) {
                s_last_step += clicks * 4;          // keep the fractional part
                int idx = (int)s_step_index.load() + clicks;
                if (idx < 0) idx = 0;
                if (idx >= (int)FREQ_STEP_TABLE_LEN) idx = FREQ_STEP_TABLE_LEN - 1;
                s_step_index.store((size_t)idx);
                ESP_LOGI(TAG, "step -> %lu Hz (idx %d)",
                         (unsigned long)FREQ_STEP_HZ_TABLE[idx], idx);
            }
        }

        // ---- Function encoder (PEC11, /4) — just accumulate ----
        if (s_unit_func) {
            int now = 0;
            pcnt_unit_get_count(s_unit_func, &now);
            int raw_d = now - s_last_func;
            int clicks = raw_d / 4;
            if (clicks != 0) {
                s_last_func += clicks * 4;
                s_func_accum.fetch_add(clicks, std::memory_order_relaxed);
            }
        }
    }
}

}  // namespace

// ===========================================================================
//  Public API
// ===========================================================================

esp_err_t init() {
    // ISR service for the pushbuttons.  ESP_INTR_FLAG_IRAM keeps the handler
    // resident even during flash operations (safe but not strictly required).
    esp_err_t err = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "gpio_install_isr_service: %s", esp_err_to_name(err));
        return err;
    }

    ESP_RETURN_ON_ERROR(make_unit(pins::ENC_FREQ_A, pins::ENC_FREQ_B,
                                  &s_unit_freq, "freq"),
                        TAG, "freq encoder");
    ESP_RETURN_ON_ERROR(make_unit(pins::ENC_STEP_A, pins::ENC_STEP_B,
                                  &s_unit_step, "step"),
                        TAG, "step encoder");
    ESP_RETURN_ON_ERROR(make_unit(pins::ENC_FUNC_A, pins::ENC_FUNC_B,
                                  &s_unit_func, "func"),
                        TAG, "func encoder");

    ESP_RETURN_ON_ERROR(setup_button(pins::ENC_FREQ_SW, &s_step_pressed,
                                     "freq_sw"),
                        TAG, "freq button");  // freq encoder usually has none
    ESP_RETURN_ON_ERROR(setup_button(pins::ENC_STEP_SW, &s_step_pressed,
                                     "step_sw"),
                        TAG, "step button");
    ESP_RETURN_ON_ERROR(setup_button(pins::ENC_FUNC_SW, &s_func_pressed,
                                     "func_sw"),
                        TAG, "func button");

    BaseType_t ok = xTaskCreatePinnedToCore(
        poll_task, "enc_poll",
        4096, nullptr,
        4,                          // mid priority on the monitor core
        nullptr,
        pins::CORE_MONITOR);
    if (ok != pdPASS) return ESP_ERR_NO_MEM;

    ESP_LOGI(TAG, "encoders up (freq A=GPIO%d B=GPIO%d, step idx=%u → %lu Hz)",
             (int)pins::ENC_FREQ_A, (int)pins::ENC_FREQ_B,
             (unsigned)s_step_index.load(),
             (unsigned long)step_hz());
    return ESP_OK;
}

uint32_t step_hz() {
    return FREQ_STEP_HZ_TABLE[s_step_index.load(std::memory_order_relaxed)];
}

size_t step_index() {
    return s_step_index.load(std::memory_order_relaxed);
}

void set_step_index(size_t i) {
    if (i >= FREQ_STEP_TABLE_LEN) i = FREQ_STEP_TABLE_LEN - 1;
    s_step_index.store(i, std::memory_order_relaxed);
}

int func_delta() {
    return s_func_accum.exchange(0, std::memory_order_relaxed);
}

bool step_button_pressed() {
    return s_step_pressed.exchange(false, std::memory_order_relaxed);
}

bool func_button_pressed() {
    return s_func_pressed.exchange(false, std::memory_order_relaxed);
}

}  // namespace encoders

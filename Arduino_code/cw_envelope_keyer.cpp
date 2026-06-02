// =============================================================================
//  cw_envelope_keyer.cpp
//
//  Raised-cosine CW keying-envelope generator for a vacuum-tube 20 m CW rig.
//  Target: Adafruit Metro ESP32-S3.  Runs as the keying process on core 1
//  (APP_CPU); the monitoring / PA-protection process runs on core 0 (PRO_CPU).
//
//  Signal path:
//      WinKey state machine  --(key up/down edges)-->  this playout layer
//      this layer  --(SPI, dedicated bus)-->  MCP4921 DAC
//      DAC  -->  1-2 pole reconstruction LPF (~4-8 kHz)  -->  level shift
//      -->  MC1496 modulating port  -->  RF envelope
//
//  Design notes are at the bottom of the file.
// =============================================================================

#include <Arduino.h>
#include <SPI.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"

// ----------------------------------------------------------------------------
//  Configuration
// ----------------------------------------------------------------------------

// --- DAC (MCP4921, 12-bit SPI) on its OWN bus, NOT the monitoring I2C bus ----
static constexpr int   DAC_CS_PIN   = 10;     // chip select
static constexpr int   DAC_SCK_PIN  = 12;     // dedicated SPI bus for the DAC
static constexpr int   DAC_MOSI_PIN = 11;     // (MISO unused for MCP4921)
static constexpr uint32_t DAC_SPI_HZ = 20000000UL;  // MCP4921 tolerates 20 MHz

// MCP4921 command word: ch A, buffered Vref, gain = 1x, output active
static constexpr uint16_t DAC_CMD = 0x3000;

// --- Playout timing ----------------------------------------------------------
static constexpr int64_t TICK_US   = 25;      // 40 kHz sample clock
static constexpr int     LUT_SIZE  = 256;     // master raised-cosine table

// --- Edge-time vs. speed -----------------------------------------------------
// edge_ms below is the FULL phase 0->1 duration. Perceptual 10-90% rise is
// roughly 0.6 x that for a raised cosine, so a 5 ms full edge ~= 3 ms 10-90.
static constexpr float EDGE_FRACTION = 0.15f; // edge as fraction of a dot
static constexpr float EDGE_MAX_MS   = 5.0f;  // floor speeds peg here
static constexpr float EDGE_MIN_MS   = 2.0f;  // never crisper than this

// --- DAC code endpoints (set from your MC1496 bring-up) ----------------------
// CODE_NULL  = control value that nulls the modulator output (RF off)
// CODE_FULL  = control value for full drive (RF at key-down amplitude)
static constexpr uint16_t CODE_NULL = 0x000;
static constexpr uint16_t CODE_FULL = 0xFFF;

// ----------------------------------------------------------------------------
//  Shared state (written by WinKey task, read by playout task)
// ----------------------------------------------------------------------------
static volatile bool  s_key_down  = false;    // 32-bit aligned bool -> atomic enough
static volatile float s_phase_inc = 0.0f;     // per-tick phase step, set by WPM
static TaskHandle_t   s_playout_handle = nullptr;

static SPIClass s_dac_spi(FSPI);               // dedicated SPI peripheral

// ----------------------------------------------------------------------------
//  Tables
// ----------------------------------------------------------------------------
static float s_rc_lut[LUT_SIZE];               // master raised cosine, 0..1

static void build_rc_lut() {
    for (int i = 0; i < LUT_SIZE; ++i) {
        float x = (float)i / (float)(LUT_SIZE - 1);     // 0..1
        s_rc_lut[i] = 0.5f * (1.0f - cosf((float)M_PI * x));
    }
}

// Sample the master LUT at a normalized phase in [0,1] with linear interp.
static inline float sample_lut(float phase) {
    if (phase <= 0.0f) return s_rc_lut[0];
    if (phase >= 1.0f) return s_rc_lut[LUT_SIZE - 1];
    float fi = phase * (float)(LUT_SIZE - 1);
    int   i  = (int)fi;
    float f  = fi - (float)i;
    return s_rc_lut[i] + f * (s_rc_lut[i + 1] - s_rc_lut[i]);
}

// ----------------------------------------------------------------------------
//  Pre-distortion hook  -- linearize the MC1496 control -> RF-envelope curve.
//
//  Input : desired normalized RF envelope  (0 = off, 1 = full)
//  Output: 12-bit DAC code to send so the *RF envelope* is that value.
//
//  Default below is a straight linear map (identity, for first bring-up).
//  To linearize: measure RF amplitude vs. DAC code across the range, invert
//  it, and fill s_cal[] so that envelope level maps to the code that actually
//  produces it. Then enable USE_CAL_TABLE.
// ----------------------------------------------------------------------------
#define USE_CAL_TABLE 0

#if USE_CAL_TABLE
static constexpr int CAL_SIZE = 64;
static uint16_t s_cal[CAL_SIZE];   // index = round(env * (CAL_SIZE-1)) -> DAC code

// TODO: load this from measured data (NVS, header, or a calibration routine).
static void load_cal_table() {
    for (int k = 0; k < CAL_SIZE; ++k) {                 // placeholder = linear
        float env = (float)k / (float)(CAL_SIZE - 1);
        s_cal[k] = CODE_NULL + (uint16_t)(env * (CODE_FULL - CODE_NULL) + 0.5f);
    }
}
#endif

static inline uint16_t predistort(float env_norm) {
    if (env_norm < 0.0f) env_norm = 0.0f;
    if (env_norm > 1.0f) env_norm = 1.0f;
#if USE_CAL_TABLE
    float fk = env_norm * (float)(CAL_SIZE - 1);
    int   k  = (int)fk;
    float f  = fk - (float)k;
    if (k >= CAL_SIZE - 1) return s_cal[CAL_SIZE - 1];
    return (uint16_t)(s_cal[k] + f * ((int)s_cal[k + 1] - (int)s_cal[k]) + 0.5f);
#else
    return CODE_NULL + (uint16_t)(env_norm * (CODE_FULL - CODE_NULL) + 0.5f);
#endif
}

// ----------------------------------------------------------------------------
//  DAC write
// ----------------------------------------------------------------------------
static inline void dac_write(uint16_t code12) {
    uint16_t word = DAC_CMD | (code12 & 0x0FFF);
    digitalWrite(DAC_CS_PIN, LOW);
    s_dac_spi.transfer16(word);
    digitalWrite(DAC_CS_PIN, HIGH);
}

// ----------------------------------------------------------------------------
//  Deterministic busy-wait to the next tick boundary.
//  Core 1 only spins while an element is actually in flight; it blocks
//  (zero CPU) between characters. This is the "cycles to burn" tradeoff.
// ----------------------------------------------------------------------------
static inline void wait_until(int64_t t_us) {
    while (esp_timer_get_time() < t_us) { /* spin */ }
}

// ----------------------------------------------------------------------------
//  Playout task -- the envelope is a single position `phase` (0..1) that
//  chases the key state. Up while key down, down while key up. Mid-edge
//  reversals (fast QSK, next element starting before the tail decays) are
//  handled for free because the key state is re-read every tick.
// ----------------------------------------------------------------------------
static void playout_task(void *) {
    float phase = 0.0f;

    for (;;) {
        // Idle: hold the modulator nulled and sleep until a key-down edge.
        dac_write(predistort(0.0f));
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);   // clears count on take

        int64_t next_us = esp_timer_get_time();

        // Active: run the timed chase loop until fully decayed AND key is up.
        for (;;) {
            next_us += TICK_US;
            wait_until(next_us);

            bool  kd  = s_key_down;     // atomic single-word read
            float inc = s_phase_inc;    // may briefly lag a WPM change; harmless

            if (kd) {
                phase += inc;
                if (phase > 1.0f) phase = 1.0f;
            } else {
                phase -= inc;
                if (phase < 0.0f) phase = 0.0f;
            }

            dac_write(predistort(sample_lut(phase)));

            if (!kd && phase <= 0.0f) break;   // tail finished -> back to idle
        }
    }
}

// ----------------------------------------------------------------------------
//  API consumed by the WinKey emulation / control layer
// ----------------------------------------------------------------------------

// Set keying speed; recomputes the per-tick phase step. Call whenever the
// WinKey speed (or speed pot) changes. Safe to call from the other core.
void keyer_set_wpm(float wpm) {
    if (wpm < 1.0f) wpm = 1.0f;
    float dot_ms  = 1200.0f / wpm;
    float edge_ms = EDGE_FRACTION * dot_ms;
    if (edge_ms > EDGE_MAX_MS) edge_ms = EDGE_MAX_MS;
    if (edge_ms < EDGE_MIN_MS) edge_ms = EDGE_MIN_MS;
    s_phase_inc = (float)TICK_US / (edge_ms * 1000.0f);
}

// Called by the WinKey state machine on each element boundary.
void keyer_key_down() {
    s_key_down = true;
    if (s_playout_handle) xTaskNotifyGive(s_playout_handle);  // wake if idle
}

void keyer_key_up() {
    s_key_down = false;   // running loop sees this and ramps the tail down
}

// ----------------------------------------------------------------------------
//  Init -- call once from setup(), after the monitoring core is up.
// ----------------------------------------------------------------------------
void keyer_envelope_init() {
    build_rc_lut();
#if USE_CAL_TABLE
    load_cal_table();
#endif
    keyer_set_wpm(20.0f);                 // sane default

    pinMode(DAC_CS_PIN, OUTPUT);
    digitalWrite(DAC_CS_PIN, HIGH);
    s_dac_spi.begin(DAC_SCK_PIN, -1, DAC_MOSI_PIN, DAC_CS_PIN);
    s_dac_spi.beginTransaction(SPISettings(DAC_SPI_HZ, MSBFIRST, SPI_MODE0));
    dac_write(predistort(0.0f));          // start nulled

    // Pin the playout task to core 1, high priority, away from monitoring.
    xTaskCreatePinnedToCore(
        playout_task, "cw_envelope",
        4096, nullptr,
        configMAX_PRIORITIES - 2,         // high, but below any wdt/idle housekeeping
        &s_playout_handle,
        1 /* APP_CPU */);
}

// =============================================================================
//  DESIGN NOTES
//
//  Why a phase-chase instead of explicit RISING/KEY_DOWN/FALLING states:
//    A single position that integrates toward the key state collapses all four
//    states into one rule and makes mid-edge reversals continuous (no clicks
//    from snapping). Rise and fall are automatically symmetric -- same LUT.
//
//  Why busy-wait timing in a task, not a GPTimer ISR:
//    Doing the SPI DAC write inside a 25 us ISR is fragile. With core 1
//    dedicated to keying you can afford to spin; the task blocks (0% CPU)
//    between characters and only spins while an element is in flight. Jitter
//    is bounded by the lookup + SPI write (< ~1-2 us) << 25 us tick.
//    If you ever want it ISR-driven instead: GPTimer @ 40 kHz -> ISR sets a
//    "tick" flag / notifies; keep the SPI write in the task, not the ISR.
//
//  Bus discipline (the important one):
//    The DAC is on its OWN SPI bus. Do NOT put it on the I2C bus the
//    monitoring core uses for the ADS1115 / bias MCP4728 -- an ADS1115 read
//    can hold I2C for milliseconds and the resulting contention becomes
//    edge jitter, i.e. clicks.
//
//  FAIL-SAFE (do not skip on a tube PA):
//    This DAC defaulting to CODE_NULL only mutes the *drive* via the MC1496.
//    Add an INDEPENDENT hardware key-line gate (e.g. a GPIO that hard-mutes
//    driver bias / removes screen) refreshed by a watchdog, so a firmware
//    hang cannot strand the 6146Bs keyed-on. Register the keying task with
//    esp_task_wdt and have the watchdog drop that hardware gate on timeout.
//
//  Calibrating the predistortion:
//    1. Sweep DAC code, measure RF envelope amplitude (scope/detector).
//    2. Invert: for each desired envelope level, record the code that makes it.
//    3. Fill s_cal[], set USE_CAL_TABLE = 1. Now the transmitted envelope is a
//       true raised cosine even if the MC1496 gain curve is not linear.
// =============================================================================

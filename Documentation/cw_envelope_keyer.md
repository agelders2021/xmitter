# CW Envelope Keyer — Context for Claude Code

Companion document for `cw_envelope_keyer.cpp`. Read this before modifying the
module. Several design choices look unusual and are **deliberate** — the notes
below say which ones must not be "refactored away."

---

## What this module does

It generates the **amplitude envelope** for a CW (Morse) signal so that the
keyed RF has soft, click-free rise/fall edges instead of hard on/off keying.
Hard keying produces wide sidebands (key clicks); a raised-cosine envelope
suppresses them.

It does **not** decode paddle/keyboard input or implement Morse timing — that
is the WinKey-emulation layer, which lives elsewhere and calls into this module.

### Where it sits in the rig

This is one subsystem of a homebrew 20 m CW vacuum-tube transmitter:

- **PA:** push-pull 6146B beam tetrodes
- **Driver:** push-pull 6CL6 pentodes
- **VFO buffer / level control:** **MC1496** balanced modulator — the RF carrier
  passes through it, and its **modulating port sets the output amplitude**. That
  port is this module's target.
- **Controller:** Adafruit Metro ESP32-S3, FreeRTOS, dual-core.

Signal path this module drives:

```
WinKey layer --(key up/down edges)--> THIS MODULE
THIS MODULE  --(SPI)--> MCP4921 DAC --> reconstruction LPF (~4-8 kHz)
             --> level shift --> MC1496 modulating port --> RF envelope
```

---

## RTOS / core model

| Core | Process | Responsibility |
|------|---------|----------------|
| Core 0 (PRO_CPU) | Monitoring | ADS1115 cathode-current sensing, PA protection, MCP4728 bias adjustment — all over **I2C** |
| Core 1 (APP_CPU) | Keying | This envelope module + the WinKey emulation |

The playout task is created with `xTaskCreatePinnedToCore(..., 1)` so it stays on
core 1, isolated from the monitoring I2C traffic.

---

## Public API (what the WinKey layer calls)

```cpp
void keyer_envelope_init();        // call once from setup(), after monitoring is up
void keyer_set_wpm(float wpm);     // call when keying speed changes
void keyer_key_down();             // call on each element start (mark)
void keyer_key_up();               // call on each element end (space)
```

That is the **entire** interface. The WinKey state machine owns Morse timing and
just toggles `keyer_key_down()` / `keyer_key_up()` on element boundaries.
`keyer_set_wpm()` should be called whenever the operator's speed setting changes,
so the edge time can track speed.

### Minimal integration example

```cpp
void setup() {
    // ... bring up monitoring core, Si5351, bias, etc. first ...
    keyer_envelope_init();
    keyer_set_wpm(25.0f);
}

// inside the WinKey element scheduler:
//   start of a dot/dash:
keyer_key_down();
//   end of a dot/dash:
keyer_key_up();
//   speed pot / WinKey speed command changed:
keyer_set_wpm(new_wpm);
```

---

## Design decisions that must NOT be undone

These are intentional. Do not "simplify" them without understanding the
consequence noted.

1. **Envelope is a single chasing `phase`, not explicit RISING/FALLING states.**
   Each tick, `phase` (0..1) integrates toward the current key state. This makes
   mid-edge reversals (fast QSK, next element starting before the tail decays)
   continuous — no discontinuity, no click. Rise and fall are symmetric because
   they walk the same LUT. Do not split this back into separate edge routines.

2. **Timing is a busy-wait inside the task, not a hardware-timer ISR.**
   The task blocks at 0% CPU between characters and only spins while an element
   is in flight, waiting on `esp_timer_get_time()` to each 25 us boundary. This
   uses core 1's spare cycles by design. Jitter is bounded by the lookup + SPI
   write (~1-2 us) << the 25 us tick. **Do not** move the SPI DAC write into an
   ISR — that is the fragile path. (A GPTimer-notify variant is acceptable, but
   the SPI write stays in the task.)

3. **The DAC is on its own SPI bus.**
   It must **never** share the I2C bus the monitoring core uses for the ADS1115
   and MCP4728. An ADS1115 read can hold that bus for milliseconds; the resulting
   contention becomes envelope-edge jitter, i.e. clicks. Keep buses separate.

4. **The LUT is pre-distorted via `predistort()` to linearize the MC1496.**
   A cosine *control voltage* only yields a cosine *RF envelope* if the modulator
   is linear, which it is not. The predistortion table corrects this so the
   transmitted envelope is a true raised cosine. This is the main reason for
   doing the envelope digitally rather than with an analog shaper.

---

## Tuning parameters (top of the .cpp)

| Constant | Meaning | Default |
|----------|---------|---------|
| `TICK_US` | Sample period of the playout loop | 25 us (40 kHz) |
| `LUT_SIZE` | Master raised-cosine table length | 256 |
| `EDGE_FRACTION` | Edge time as a fraction of one dot | 0.15 |
| `EDGE_MAX_MS` | Max full edge (slow speeds peg here) | 5.0 ms |
| `EDGE_MIN_MS` | Min full edge (fastest, crispest) | 2.0 ms |
| `CODE_NULL` | DAC code that nulls modulator output (RF off) | set at bring-up |
| `CODE_FULL` | DAC code for full key-down amplitude | set at bring-up |

WPM → edge mapping: `edge = clamp(EDGE_FRACTION * (1200 / wpm), EDGE_MIN_MS, EDGE_MAX_MS)`.
This pegs at 5 ms for speeds <= ~30 WPM and shortens above that.

**Edge time convention:** `edge_ms` is the **full** phase 0→1 duration. The
10–90% rise figure operators usually quote is ~0.6x that (5 ms full ≈ 3 ms 10–90).

---

## Calibration (predistortion) — TODO

Currently `USE_CAL_TABLE` is `0` (linear identity map) for first bring-up.
To linearize the MC1496:

1. Sweep the DAC code across its range; at each code measure the RF envelope
   amplitude (scope or RF detector at the modulator output).
2. Invert the curve: for each desired normalized envelope level, record the DAC
   code that actually produces it.
3. Fill `s_cal[]` with that mapping and set `USE_CAL_TABLE = 1`.

Source of `s_cal[]` data is open — could be a compiled-in header, NVS, or an
interactive calibration routine. (A calibration routine is on the open-work list.)

---

## Fail-safe requirement (do not skip — this is a tube PA)

Nulling this DAC only mutes the **drive** via the MC1496. It does **not** by
itself protect the PA. There must be an **independent hardware key-line gate**
(e.g. a GPIO that hard-mutes driver bias / removes screen voltage), refreshed by
a watchdog, so that a firmware hang cannot strand the 6146Bs keyed-on. Register
the keying task with `esp_task_wdt` and have the watchdog drop that hardware gate
on timeout. This is separate from, and must not depend on, the DAC value.

---

## Hardware notes

- DAC: MCP4921, 12-bit, SPI, command word `0x3000` (ch A, buffered, 1x gain,
  active). Tolerates 20 MHz SCK.
- Give the DAC a dedicated SPI bus (see decision #3). Pins in the .cpp are
  placeholders — set `DAC_CS_PIN` / `DAC_SCK_PIN` / `DAC_MOSI_PIN` to match the
  board. MISO is unused for the MCP4921.
- After the DAC: a mild 1–2 pole reconstruction low-pass (~4–8 kHz) to smooth DAC
  steps, then level-shift/scale into the MC1496 modulating port's linear range.

---

## Open work / next steps

- [ ] DAC-sweep-and-invert calibration routine to populate `s_cal[]`.
- [ ] Qucs-S sim of the reconstruction filter + MC1496 modulating port to verify
      the edge shape and check the transmitted spectrum before committing values.
- [ ] Wire `keyer_set_wpm()` to the WinKey speed source (command + speed pot).
- [ ] Watchdog + hardware fail-safe gate (see fail-safe section).
- [ ] Confirm `CODE_NULL` / `CODE_FULL` against the actual MC1496 bring-up.

---

## Environment

- Build: Arduino-ESP32 framework on the Metro ESP32-S3.
- Simulation (for the analog side): Qucs-S v26.1.1 + ngspice (LTspice compat).
- Implementation lives in `cw_envelope_keyer.cpp` (not reproduced here).

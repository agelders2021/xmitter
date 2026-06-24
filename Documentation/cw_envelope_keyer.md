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
- **Driver:** push-pull 12HG7 pentodes
- **VFO buffer / level control:** **MC1496** balanced modulator — the RF carrier
  passes through it, and its **modulating port sets the output amplitude**. That
  port is this module's target.
- **Controller:** Adafruit Metro ESP32-S3, FreeRTOS, dual-core.

Signal path this module drives:

```
WinKey layer --(key up/down edges)--> THIS MODULE
THIS MODULE  --(SPI)--> MCP4921 DAC --> R_F (1.5 kΩ) ──┬── MC1496 pin 1
                                                       │   (R4 = 51 Ω to GND)
                                                    C_F (680 nF)
                                                       │
                                                      GND
             --> MC1496 modulating port --> MC1496 diff output (~2.5 V p-p)
             --> LM7171 post-keyer amp (G = 4) --> ~10 V p-p diff
             --> 12HG7 driver --> driver-output transformer --> 6146B grids
```

---

## RTOS / core model

┌──────────────────┬────────────┬─────────────────────────────────────────────────────────────────────────────────────┐
│ Core             │ Process    │ Responsibility                                                                      │
├──────────────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────┤
│ Core 0 (PRO_CPU) │ Monitoring │ ADC1 cathode-current sensing (built-in 12-bit), PA protection, MCP4728 bias adj (I²C)│
│ Core 1 (APP_CPU) │ Keying     │ This envelope module + the WinKey emulation                                         │
└──────────────────┴────────────┴─────────────────────────────────────────────────────────────────────────────────────┘

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

3. **The envelope DAC is on its own SPI bus.**
   It must **never** share the I2C bus the monitoring core uses for the
   MCP4728 bias DACs and the Si5351. Keep envelope timing (SPI, deterministic)
   independent of bias control + VFO programming (I2C, occasional bursts that
   could blocking-stall the envelope path otherwise). Cathode current is read
   via the ESP32-S3's built-in ADC1 (no I2C needed for that path either).

4. **The LUT is pre-distorted via `predistort()` to linearize the MC1496.**
   A cosine *control voltage* only yields a cosine *RF envelope* if the modulator
   is linear, which it is not. The predistortion table corrects this so the
   transmitted envelope is a true raised cosine. This is the main reason for
   doing the envelope digitally rather than with an analog shaper.

---

## Tuning parameters (top of the .cpp)

┌─────────────────┬───────────────────────────────────────────────┬──────────────────┐
│ Constant        │ Meaning                                       │ Default          │
├─────────────────┼───────────────────────────────────────────────┼──────────────────┤
│ `TICK_US`       │ Sample period of the playout loop             │ 25 µs (40 kHz)   │
│ `LUT_SIZE`      │ Master raised-cosine table length             │ 256              │
│ `EDGE_FRACTION` │ Edge time as a fraction of one dot            │ 0.15             │
│ `EDGE_MAX_MS`   │ Max full edge (slow speeds peg here)          │ 5.0 ms           │
│ `EDGE_MIN_MS`   │ Min full edge (fastest, crispest)             │ 2.0 ms           │
│ `CODE_NULL`     │ DAC code that nulls modulator output (RF off) │ set at bring-up  │
│ `CODE_FULL`     │ DAC code for full key-down amplitude          │ set at bring-up  │
└─────────────────┴───────────────────────────────────────────────┴──────────────────┘

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
- **Reconstruction LPF + level scaler (single passive stage):**

  ```
                  R_F = 1.5 kΩ
  MCP4921 OUT ───/\/\/\───┬─── MC1496 pin 1 (SIG_P)
                          │
                       C_F = 680 nF (film, MKT/MKP)
                          │
                         GND         (R4 = 51 Ω to GND already on pin 1)
  ```

  R_F + R4 form the divider; C_F to GND provides the single-pole rolloff.
  Combined behavior:

  ┌──────────────────────────────┬─────────────────────────────┬──────────────────────────────────────────────┐
  │ Parameter                    │ Value                       │ How                                          │
  ├──────────────────────────────┼─────────────────────────────┼──────────────────────────────────────────────┤
  │ DC scale                     │ 3.3 V DAC → 108 mV at pin 1 │ R4 / (R_F + R4) = 51 / 1551 = 0.0329         │
  │ LPF −3 dB                    │ 4.75 kHz                    │ Thevenin R = R_F ‖ R4 = 49 Ω; τ = 34 µs      │
  │ 40 kHz image (1st DAC alias) │ −18.5 dB                    │ Single-pole rolloff                          │
  │ Settling (3τ)                │ ~100 µs                     │ ≪ 2–5 ms envelope edge → no shape distortion │
  │ Pin 1 at 14 MHz              │ |Z_C| = 0.017 Ω             │ C_F also AC-grounds pin 1 → carrier isolation│
  └──────────────────────────────┴─────────────────────────────┴──────────────────────────────────────────────┘

  108 mV peak drives the modulator ~4× past AN531's linear boundary, into
  saturation. That's intentional: `CODE_FULL` is calibrated to the actual
  saturation point and the predistortion LUT linearizes the envelope.
  For mostly-linear operation, use R_F = 3.3 kΩ → ~50 mV peak (keeps the
  same ~4.6 kHz cutoff with the same C_F).

  For steeper image rejection (−36 dB at 40 kHz): cascade an R = 1 kΩ /
  C = 33 nF stage before R_F, or use Sallen-Key Butterworth on the spare
  TL072. Single-pole is sufficient for CW.

- **Reduced carrier injection (for cleaner modulator output spectrum):**

  The original keyer.sch had V_carrier ≈ 100 mV peak at the carrier port —
  deep into switching mode (square-wave-like output, harmonics at 3f, 5f,
  7f …). To push the modulator into true 4-quadrant multiplier behavior
  (sinusoidal output, much lower harmonic content), the attenuation is
  done **upstream in the VFO subcircuit** rather than at C1: the Pi pad
  is uprated from 6 dB to **20 dB**, and the LPF is upgraded from 5-pole
  to **7-pole Chebyshev** (same fc = 17.5 MHz) to push harmonic rejection
  deeper (now critical, since carrier harmonics translate directly to
  spurs in linear-multiplier mode).

  See `vfo_input_stage.md` for the current pad and LPF values
  (original derivation is in `legacy/20m-leveled-keyed-buffer.md`).
  Effect on the keyer:

  ┌───────────────────────────────────┬────────────────┬───────────────────────────────────┐
  │ Parameter                         │ Before         │ After                             │
  ├───────────────────────────────────┼────────────────┼───────────────────────────────────┤
  │ V_RF_IN to keyer (post-pad)       │ ~380 mV peak   │ ~38 mV peak                       │
  │ V_pin10 (with C1 = 330 pF)        │ ~100 mV peak   │ ~32 mV peak                       │
  │ Modulator mode                    │ Hard switching │ Linear / soft-switching boundary  │
  │ 3rd-harmonic spur at carrier port │ ~−42 dBc       │ ~−69 dBc                          │
  └───────────────────────────────────┴────────────────┴───────────────────────────────────┘

  C1 stays at the original 330 pF — the cap divider with R1 = 51 Ω is no
  longer being used as an attenuator; the upstream pad does that work.
  After hardware bring-up, an additional discrete pad can be inserted
  between the VFO and the keyer's RF_IN if the measured carrier amplitude
  needs further trimming.

- **Post-keyer voltage amplifier (between MC1496 outputs and 12HG7 driver):**

  With V_pin10 ≈ 32 mV peak (after the 20 dB pad upstream), the MC1496's
  output is ~1.4 V p-p differential — well short of the 8 V p-p the
  12HG7 driver was sized for. An LM7171 op-amp per side bridges the gap
  with gain ≈ 6:

  ```
                                    +12 V    ─8.3 V    (existing rails)
                                       │       │
                                     ──┴───────┴──   bypass: 10 µF + 100 nF per rail

  MC1496 OUT_P ── 100 nF ──┬── (+) LM7171_A ── 100 nF ── 12HG7 driver in 1
                           │        │
                          100k     (−) ── 10k ── GND
                           │        └── 47k ── op-amp output (feedback)
                          GND
  ```

  (Mirror circuit on OUT_N → driver in 2.)

  ┌──────────────────┬─────────────────────────────────────────────┬─────────────────────────────────────────┐
  │ Parameter        │ Value                                       │ Notes                                   │
  ├──────────────────┼─────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Gain             │ 1 + R_F/R_G = 5.8                           │ R_F = 47 kΩ, R_G = 10 kΩ                │
  │ BW at G = 5.8    │ ~34 MHz                                     │ LM7171 GBW = 200 MHz                    │
  │ Output swing     │ Rail-to-rail−2 V                            │ Ample for ±5 V swing on ±10 V rails     │
  │ Input bias point │ 0 V (via 100 kΩ to GND)                     │ Well within CM range of split supply    │
  │ Drives           │ ~100 Ω cathode-input of grounded-grid 12HG7 │ Output impedance ≪ 100 Ω                │
  └──────────────────┴─────────────────────────────────────────────┴─────────────────────────────────────────┘

  Drive headroom: keyer ~1.4 V p-p × 5.8 ≈ 8 V p-p at driver input —
  matches the 8 V p-p design point of the driver/PA chain.

  **Re-tuning notes:** To push modulator linearity even harder, increase
  the Pi pad attenuation in the VFO subcircuit (e.g., from 20 dB to 26 dB)
  rather than touching C1. Then raise R_F to compensate for the further
  drop in modulator gain. Practical limit with LM7171 is R_F ≈ 60 kΩ
  (gain 7); BW drops to ~28 MHz, still safely above the 14 MHz carrier.
  Beyond that, swap to a faster op-amp (AD8055, LMH6610, AD8009 — all
  300+ MHz GBW).

  Why LM7171 (not TL072): TL072's 3 MHz GBW is well below the 14 MHz
  carrier; LM7171's 200 MHz GBW leaves flat gain through the carrier band
  at the chosen gain of ~6.

---

## Next-phase enhancement: DAC-driven digital carrier null

The current design (per `xmitter_prj/keyer.sch`, mirrored in
`KiCAD/buffer_keyer.kicad_sch`) uses a **PNP-injection nulling scheme**
to cancel the MC1496's residual carrier leakage. T1 / T2 (2N3906 PNPs)
biased through the R5–R10 8.2 kΩ symmetry network and R6 / R8 2.7 kΩ
base resistors drive complementary collector currents that get summed
at the MC1496 SIG_P (pin 1) and SIG_N (pin 4) inputs via 8.2 kΩ
isolation resistors (R9, R10). This shifts the lower-diff-pair bias
balance and nulls the carrier feedthrough — functionally identical to
the 50 kΩ manual null pot shown in the MC1496 application note Figure 7,
just split into a current-injection topology.

The 51 Ω resistors R3 / R4 at pins 1 and 4 satisfy the app note's
critical constraint: "low DC resistance between the bases of the lower
differential amplifier (pins 1 and 4) and ground… not significantly
higher than the 51 Ω utilized in the circuit shown in Figure 3" (AN531
page 5). The 8.2 kΩ injection resistors and the 1.5 kΩ envelope-feed
resistor are high enough to not disturb this requirement (51 Ω
dominates the parallel combination).

**The DAC enhancement modulates the PNP BASE voltages** (not direct
injection at MC1496 pins 1/4). Hardware on hand (Adafruit MCP4728
acquired 2026-06); implementation deferred until after first-light.

### Hardware additions

- `R_INJ1` = 330 kΩ from **DAC_NULL_P → T1 base** (the BASE of the
  +side null PNP, joining the existing R6 / R5 / R7 bias network at
  that node)
- `R_INJ2` = 330 kΩ from **DAC_NULL_N → T2 base** (the BASE of the
  −side null PNP, joining the existing R8 / R9 / R10 bias network)
- `DAC_NULL_P` / `DAC_NULL_N` = two of the four channels of the
  on-hand Adafruit MCP4728 breakout (Adafruit PID 4470, 12-bit
  4-channel I²C DAC). The other two channels remain available for
  the planned PA bias-adjustment role (`cathode_monitor` integration).
- The 330 kΩ series resistors isolate the DAC from the live PNP base
  bias network (which sits around the PNP's Vbe-below-rail point) and
  limit any fault current; they're not the dominant impedance at the
  base node — the 2.7 kΩ R6 / R8 bias resistors are. The DAC just
  trims the base voltage by a few mV worth of offset.
- **Why NOT direct injection at MC1496 pins 1 / 4:** an earlier draft
  of this doc described 330 kΩ direct injection at the SIG pins.
  That approach would parallel the 51 Ω R3 / R4 resistors with 330 kΩ
  to the DAC, raising the DC resistance at pins 1 / 4 above the app
  note's recommended ceiling and degrading the carrier null vs
  temperature. The QUCS simulation (`keyer.sch`) uses PNP-base
  modulation specifically to preserve the 51 Ω constraint while still
  giving the DAC enough leverage on the carrier null to track drift.
  The PNP's current-mode gain amplifies the small DAC-trim voltage at
  the base into a useful collector-current shift at the SIG pin.

### I²C address — MCP4728 vs Si5351 collision

The Adafruit MCP4728 ships with factory I²C address **0x60**, which
**collides with the Adafruit Si5351A breakout** (also 0x60 default).
Resolution path for this project:

- **Reprogram the MCP4728's EEPROM address** via the chip's built-in
  address-write command (LDAC pin pulled low + special I²C sequence).
  One-time firmware setup routine; address persists across power
  cycles.
- **Target address: 0x62** (avoids 0x60 Si5351, 0x61 Si5351-with-ADDR,
  0x20 MCP23017, and leaves room around 0x48 for any future I²C ADC if
  the built-in ADC1 path proves insufficient).
- Why not the Si5351 ADDR solder-jumper: requires bridging an 0805-pad
  pair on the breakout PCB — too small for this builder's hand
  tremor. Firmware re-program is the cleaner path.
- **Wiring requirement**: the MCP4728's LDAC pin must connect to an
  ESP32-S3 GPIO (not tied to GND), so firmware can drive it during
  the address-write sequence. After the one-time programming, LDAC
  can be parked high (envelope updates don't need latching at the
  speeds involved here).

### Coverage analysis

Approximate — exact numbers depend on the PNP bias point and the
MCP4728 reference configuration (assumed internal 2.048 V Vref,
gain 1×; matches the MCP4921 envelope DAC config).

┌──────────────────────────┬──────────────────────────────────────────────────────┐
│ Quantity                 │ Value                                                │
├──────────────────────────┼──────────────────────────────────────────────────────┤
│ Mid-scale on both DACs   │ No differential injection (null starting point)      │
│ Full-scale swing per pin │ ±15 mV at MC1496 pins 1/4 (via PNP transconductance) │
│ Total differential range │ ±30 mV                                               │
│ MC1496 worst-case offset │ ≤ 5 mV (datasheet)                                   │
│ Headroom                 │ ~6× over worst-case offset                           │
│ Resolution per LSB       │ ~8 µV at the SIG pins (12-bit DAC ÷ attenuation)     │
└──────────────────────────┴──────────────────────────────────────────────────────┘

The PNP's transconductance (≈ gm × ΔV_base × R4_eq) turns a small
base-voltage trim into a useful collector-current shift; the 8.2 kΩ
R9/R10 isolation + 51 Ω R3/R4 at pins 1/4 set the effective impedance
the injected current sees. Resolution is far finer than needed; the
binary search converges in about 12 cycles to a level well below the
modulator's own noise floor. Final calibration confirms numbers during
bring-up.

### Firmware

- Run a binary search at each key-down (or once on bring-up plus
  periodic re-checks) by walking DAC_A while keeping
  `DAC_A + DAC_B = full_scale`, sampling the carrier-leakage level
  at the MC1496 output via an envelope detector or the cathode
  monitor signal
- Convergence: ~12 iterations (12-bit resolution); each iteration
  needs settling time of ~100 µs for the RC network
- Store the converged DAC code pair in NVS; refresh every N
  transmissions or whenever a temperature/operating-condition
  delta crosses a threshold

### Tradeoff vs running PNPs at fixed bias only

- **Cost**: two DAC channels (DAC_NULL_P / DAC_NULL_N) + ~30 lines
  of firmware + two 330 kΩ series resistors. MCP4728 itself is
  shared on the I²C bus, no extra silicon beyond what's already
  ordered.
- **Benefit**: eliminates static null error from PNP β mismatch,
  PNP bias-network drift, and ambient temperature variation;
  eliminates the alignment-time null trim step entirely.
- **Risk**: if the firmware loop fails (sensor fault, etc.) the
  rig falls back to whatever DAC code was last in NVS — same
  failure mode as the envelope DAC fail-safe. Worst case: the rig
  operates with whatever static null happened to be in NVS at last
  successful run, no worse than not having the enhancement at all.

Original design notes preserved in
`xmitter_prj/legacy/mc1496_level_control.md`.

---

## Open work / next steps

- [ ] DAC-sweep-and-invert calibration routine to populate `s_cal[]`.
- [ ] Qucs-S sim of the reconstruction filter (R_F = 1.5 kΩ, C_F = 680 nF) +
      MC1496 modulating port to verify the edge shape and check the transmitted
      spectrum before locking values in hardware.
- [ ] Wire `keyer_set_wpm()` to the WinKey speed source (command + speed pot).
- [ ] Watchdog + hardware fail-safe gate (see fail-safe section).
- [ ] Confirm `CODE_NULL` / `CODE_FULL` against the actual MC1496 bring-up.

---

## Environment

- Build: Arduino-ESP32 framework on the Metro ESP32-S3.
- Simulation (for the analog side): Qucs-S v26.1.1 + ngspice (LTspice compat).
- Implementation lives in `cw_envelope_keyer.cpp` (not reproduced here).

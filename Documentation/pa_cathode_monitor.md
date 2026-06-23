# PA Cathode Current Monitor and Failsafe Chain

Per-tube cathode-current monitoring on the push-pull 6146B PA, with all the
defensive layers between a hot cathode and the MCU's ADC pin.

## Why this matters

The cathode is the only point in the PA where you can measure the **total** tube
current (plate + screen + grid) cleanly. It's the right place to detect:

- **Tube faults** — internal flashover, gas, runaway, end-of-life
- **Operating-point drift** — bias supply shift, screen supply ripple, thermal
- **PA overdrive** — drive level inappropriate for current bias / load
- **Loss of grid bias** — bias supply failure → tubes try to run at zero bias

But "the cathode" is at +1 V nominal during normal operation, sitting one
component (a 10 Ω resistor) away from a 600 V plate supply. If R_C ever opens,
the cathode floats up to plate voltage. Any sense path connected to the cathode
top needs serious protection between it and the ADC.

## System block diagram

```
                                            +600V plate
                                              │
                                             6146B
                                              │
        Cathode pin ──┬── R_C(10Ω) ── GND        ← Level 0 (cathode resistor)
                      │
                      ├── C_BYP(0.01µF) ── GND   ← RF bypass
                      │
                      └─→ DC sense tap
                          │
                          F1 (PTC, 100mA hold)   ← Level 1 (thermal slow-blow)
                          │
                          R_S(10kΩ)              ← Level 2 (current limit)
                          │
                  ┌───────┼─────────────┐
                  │       │             │
                 D1     C_FILT(1nF)    D2        ← Level 3 (clamp + anti-alias)
                  │       │             │
                 GND     GND          +3.3V
                          │
                  ┌───────┴─────────┐
                  │                 │
              U1: Op-amp           U2: Comparator   ← Level 4: buffer +
              buffer (+5V)         (LM393)              Level 5: fast hardware trip
                  │                 │
            (gain = 1)           open-drain ─┬─→ to SR latch / watchdog gate
                  │                          │
                  ▼                          │
            ADC input ───→ MCU ADC ──→ firmware  ← Level 6 (soft trip)
                                       │
                                       └──→ NVS fault log  ← Level 7 (post-mortem)
```

## Layer-by-layer design

### Level 0 — Cathode resistor + RF bypass

┌───────────┬───────────────────────┬──────────────────────────────────────────────────────────────────────────┐
│ Component │ Value                 │ Notes                                                                    │
├───────────┼───────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ R_C       │ 10 Ω, 1 W metal film  │ Sense resistor; carries full cathode current. 1 W = 4× margin at 150 mA  │
│ C_BYP     │ 0.01 µF NP0 ceramic   │ RF bypass to GND. Mount **at the tube socket cathode pin**, short leads  │
│           │                       │ (≤5 mm). Low-ESL package (1206 or smaller).                              │
└───────────┴───────────────────────┴──────────────────────────────────────────────────────────────────────────┘

**Critical layout rule:** the **DC sense tap leaves the R_C top *before* C_BYP**.
RF currents go through C_BYP to ground; DC sense goes elsewhere. This prevents
14 MHz RF from coupling into the sense chain.

Operating point (per tube, full drive):
- I_cathode_avg ≈ 100 mA (= I_plate_avg + I_screen + I_grid_drive ≈ 80 + 15 + 5)
- V_sense_DC ≈ 1.0 V
- ADC operating point: ~30 % of full-scale on a 3.3 V ADC → comfortable headroom

### Level 1 — PTC fuse (resettable thermal)

┌───────────┬─────────────────┬────────────────────────────────────────────────────┐
│ Component │ Value           │ Notes                                              │
├───────────┼─────────────────┼────────────────────────────────────────────────────┤
│ F1        │ Bourns MF-R010  │ Hold 100 mA, trip 200 mA, V_max 60 V, R ~5 Ω init  │
└───────────┴─────────────────┴────────────────────────────────────────────────────┘

Slow-blow thermal protection. Opens within ~1 s at 500 mA sustained, faster at
higher currents. Self-resets when the fault clears. Catches the case where R_C
opens AND clamp diodes are conducting hard — without F1, D1/D2 would burn
through trying to clamp 60 mA of fault current continuously. With F1, the fault
current trips F1 in <1 s and protects everything downstream.

V_max = 60 V means **F1 can't survive a 600 V cathode-open fault on its own** —
the fault voltage exceeds F1's V_max. R_S (Level 2) handles that case by
limiting fault current to a value F1 can handle while the comparator (Level 5)
trips the watchdog gate within microseconds.

### Level 2 — Series current limiter

┌───────────┬──────────────────────────┬─────────────────────┐
│ Component │ Value                    │ Notes               │
├───────────┼──────────────────────────┼─────────────────────┤
│ R_S       │ 10 kΩ, 1/4 W metal film  │ Fault current limit │
└───────────┴──────────────────────────┴─────────────────────┘

If everything above failed and the sense tap saw the full 600 V plate supply,
R_S limits fault current to 600 V / 10 kΩ = **60 mA**. That's:

- Survivable for clamp diodes (BAT54 has 200 mA peak, 30 mA continuous — would be
  damaged eventually but not instantly)
- Below F1's trip current (so F1 trips and opens the path before D1/D2 die)
- Well below R_S's own thermal limit (60 mA × 600 V × duty cycle of 100 % =
  36 W instantaneous, but R_S only sees this during the brief fault window
  before F1 opens; integrated energy is small)

Normal-case impedance of R_S vs. the op-amp's high input impedance: ADC bias
current is microamps, so the 10 kΩ drop is microvolts. No measurement error.

### Level 3 — Schottky clamps + anti-alias filter

┌───────────┬────────────────────┬────────────────────────────────────────────────┐
│ Component │ Value              │ Notes                                          │
├───────────┼────────────────────┼────────────────────────────────────────────────┤
│ D1        │ BAT54 (or 1N5817)  │ Schottky to GND, catches negative excursions   │
│ D2        │ BAT54 (or 1N5817)  │ Schottky to +3.3 V, catches positive excursions│
│ C_FILT    │ 1 nF X7R           │ Anti-alias / RF rejection                      │
└───────────┴────────────────────┴────────────────────────────────────────────────┘

D1 and D2 turn on ~300 mV beyond their rail and shunt overvoltage into the
supply. C_FILT in parallel makes the node a single-pole LPF with R_S:
fc = 1 / (2π × 10 kΩ × 1 nF) ≈ **16 kHz**. Rejects 14 MHz RF and the keying
envelope's harmonics (well above the ~200 Hz envelope content); fast enough
not to slow the comparator trip beyond ~60 µs.

The +3.3 V rail must be **stiff enough to absorb the fault current** transient
without sagging. With F1 + R_S limiting the worst case to 60 mA, the +3.3 V
rail needs an electrolytic bulk cap (~10 µF) near the clamp node to absorb the
energy. The Schottky clamps then conduct for the brief window until F1 trips
(< 1 s).

### Level 4 — Op-amp buffer (ADC isolation)

┌─────────────┬──────────────────────┬───────────────────────────────────────────────────────────────┐
│ Component   │ Value                │ Notes                                                         │
├─────────────┼──────────────────────┼───────────────────────────────────────────────────────────────┤
│ U1          │ OPA1641              │ ±20 V differential input protection, single-supply, FET input │
│ Alternates  │ LMC6041 / LM358      │ All work; OPA1641 has lowest leakage                          │
│ Supply      │ +5 V regulated, GND  │ Same +5 V the ADC uses                                        │
└─────────────┴──────────────────────┴───────────────────────────────────────────────────────────────┘

Configured as **unity-gain buffer** (output tied to inverting input). Provides:

- **Hard limit on ADC voltage:** op-amp output can only swing within its
  supplies. Even if input goes to 600 V briefly, output stays within 0–5 V.
  ADC is physically protected regardless of upstream failures.
- **High input impedance:** doesn't load R_S or affect measurement.
- **Low output impedance:** drives the ADC sample-and-hold cleanly.

OPA1641's built-in **±20 V differential input protection** means it survives
input excursions to ±20 V even if D1/D2 fail. That's an additional defensive
layer at no extra cost.

**Sanity check:** with V_sense_DC at 1.0 V nominal, the op-amp is well within
its CM range (0 V to +3 V with +5 V supply). At fault (input clamped to ~3.3 V
by D2), op-amp is at the edge of CM but still within absolute max.

### Level 5 — Hardware comparator (FAST hardware trip)

┌───────────┬────────────────────────────┬─────────────────────────────────────────────────────────────┐
│ Component │ Value                      │ Notes                                                       │
├───────────┼────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ U2        │ LM393                      │ Dual comparator (one section per tube)                      │
│ V_REF     │ +1.5 V from divider on the │ Trip threshold = 150 mA cathode current. One divider + trim │
│           │ shared +5 V LM4040 rail    │ feeds both tubes' comparators (same threshold).             │
│ R_HYST    │ 470 kΩ                     │ Positive feedback output → (+) input — 50 mV hysteresis     │
│ R_PULLUP  │ 4.7 kΩ to +3.3 V           │ LM393 has open-collector output                             │
│ C_DEC     │ 100 nF X7R                 │ Local supply bypass at LM393 supply pin                     │
└───────────┴────────────────────────────┴─────────────────────────────────────────────────────────────┘

The op-amp output (Layer 4) feeds the comparator (+) input. Comparator (−) input
sits at the precision +1.5 V reference. When V_sense exceeds 1.5 V:

- Comparator output snaps low (open-collector pulled to GND)
- Hysteresis prevents chatter near the threshold
- Output latched in an SR flip-flop (or NAND-latch from two LM393 sections)
- Latched fault drives the **watchdog gate** (a high-side MOSFET or SSR in the
  screen-voltage supply) → screen drops to 0 V → tubes go dark in <100 µs
- Latch is cleared by firmware **after** acknowledging the fault

Total fault response time:
- Op-amp slew + comparator decision: < 5 µs
- Latch + gate drive: < 10 µs
- Screen voltage discharge: < 50 µs (depends on screen supply cap value)
- **Total cathode-to-tubes-off latency: well under 100 µs**

That's fast enough to protect the tubes from internal flashover faults that
would otherwise damage them in milliseconds.

### Level 6 — Firmware soft trip

ADC samples cathode voltage at **1 kHz** per channel (ADS1115 if external
high-resolution ADC, or built-in MCU ADC if 12-bit is enough).

┌───────────┬─────────┬────────────────────┬──────────────────────────────────────────────────────────────────┐
│ Threshold │ Voltage │ Cathode current    │ Action                                                           │
├───────────┼─────────┼────────────────────┼──────────────────────────────────────────────────────────────────┤
│ Nominal   │ 1.0 V   │ 100 mA             │ Normal operation, log every 1 s                                  │
│ Warning   │ 1.2 V   │ 120 mA for >50 ms  │ Soft fault: log, alert UI, reduce envelope DAC code by 10 %      │
│ Hard      │ 1.5 V   │ 150 mA for >5 ms   │ Hard fault: drop screen via watchdog GPIO, log timestamp, UI     │
└───────────┴─────────┴────────────────────┴──────────────────────────────────────────────────────────────────┘

The hardware comparator (Level 5) trips at 1.5 V too — both fire on hard
faults; the hardware path is faster, the firmware path provides logging.

Use a **running average** (10-sample / 10 ms window) before applying
thresholds, to avoid false trips from RF transients getting into the sense
chain (despite C_BYP).

### Level 7 — Persistent fault log

NVS storage (ESP32 wear-leveling NVS partition) records each fault event:

```c
struct FaultLog {
    uint32_t timestamp;       // unix seconds
    uint8_t  tube_id;         // 0 or 1
    uint8_t  fault_type;      // 0=warning, 1=hard
    uint16_t i_cathode_mA;    // current at trip
    uint16_t duration_ms;     // how long it persisted
    uint16_t recovered;       // 0=manual reset required, 1=auto-cleared
};
```

Ring buffer of last 32 events. Accessible via serial/web UI for post-mortem
analysis. Cleared by operator command.

## Per-tube wiring + grounding

```
Tube socket cathode pin
   │
   ├── R_C (mounted DIRECTLY at the socket pin) ── GND_RF
   │       │
   │      C_BYP ── GND_RF   (twisted with R_C lead, short)
   │
   └── DC sense wire ──────────→ analog board
                                  (twisted pair with GND_SENSE return)
                                  
   GND_RF and GND_SENSE meet at the analog board's single ground point.
```

Three separate "grounds":
- **GND_RF**: chassis ground at the tube socket area; bypass caps return here
- **GND_SENSE**: analog signal ground at the analog board
- **GND_DIG**: digital ground at the MCU board

All three meet at **one point**: the analog board's star ground. Prevents
ground-loop currents from corrupting the cathode sense measurement.

**Sense wire is a TWISTED PAIR**: DC sense + GND_SENSE return. Twisting kills
common-mode pickup. Optional: shielded cable, with shield grounded ONLY at the
analog board (avoids ground loops).

## Calibration procedure (bring-up)

1. **Zero**: tubes in deep cutoff (key-up). ADC reading is the offset.
   Store as `cathode_offset[tube_id]`.

2. **Gain**: insert a known shunt resistor in series with the cathode return
   to a DMM. Apply moderate drive. Read both DMM (I_cathode in mA) and ADC
   counts. Compute `gain[tube_id] = (ADC_count − offset) / I_cathode_mA`.
   Repeat at 3-4 current levels to verify linearity.

3. **Threshold trim**: drive the tube to known I_cathode = 150 mA. Adjust the
   LM4040 divider trim until the comparator just trips. Verify it un-trips
   when I_cathode drops to 100 mA (50 mV hysteresis).

Store calibration constants in NVS. Re-run periodically (every 100 operating
hours or after any servicing).

## Per-tube → both-tubes summing

Two parallel sense chains, one per tube. Both feed into:

- **Per-tube ADC channels** (for individual tube monitoring + balance trim)
- **Comparator chain**: each tube's comparator output goes to an OR gate
  (or wired-OR with shared pull-up). Either tube tripping fires the watchdog.
- **Optional sum probe**: sum the two cathode voltages via two 10 kΩ resistors
  to a third comparator with threshold at 1.4 V (≡ 280 mA total cathode).
  Catches the case where both tubes drift hot together.

## BOM (per-tube, ×2 for the pair)

┌─────────────────┬──────────────────────────────┬──────────┬─────────────────────────────────────────────────┐
│ Ref             │ Part                         │ Qty/tube │ Notes                                           │
├─────────────────┼──────────────────────────────┼──────────┼─────────────────────────────────────────────────┤
│ R_C             │ 10 Ω 1 % 1 W metal film      │ 1        │ Vishay PR01000101000JR500 or similar            │
│ C_BYP           │ 0.01 µF NP0 ceramic, 100 V   │ 1        │ Mount AT the tube socket                        │
│ F1              │ Bourns MF-R010               │ 1        │ PTC, 100 mA hold                                │
│ R_S             │ 10 kΩ 1 % 1/4 W              │ 1        │                                                 │
│ D1, D2          │ BAT54 (or 1N5817)            │ 2        │ Schottky clamps                                 │
│ C_FILT          │ 1 nF X7R 50 V                │ 1        │                                                 │
│ U1 (op-amp)     │ OPA1641                      │ 1        │ One section per tube (or OPA1642 dual for both) │
│ U2 (comparator) │ LM393                        │ 0.5      │ One IC handles both tubes                       │
│ U_REF           │ LM4040DIZ-5.0                │ 0        │ Already in grid_bias BOM; same +5 V rail powers │
│                 │                              │          │ both subsystems (CLAUDE.md: same analog board)  │
│ R_DIV1          │ 4.7 kΩ 1 % 1/8 W             │ 0.5      │ Divider top: +5 V → trim pot                    │
│ R_TRIM          │ Bourns 3296W 1 kΩ trim pot   │ 0.5      │ Sets V_REF tap; one divider feeds both tubes    │
│ R_DIV2          │ 1.5 kΩ 1 % 1/8 W             │ 0.5      │ Divider bottom: trim pot → GND. Nominal tap =   │
│                 │                              │          │ 1.50 V (range 1.21–1.74 V across full pot)      │
│ R_HYST          │ 470 kΩ                       │ 1        │                                                 │
│ R_PULLUP        │ 4.7 kΩ                       │ 1        │ LM393 output pull-up                            │
│ C_DEC           │ 100 nF X7R                   │ several  │ Decoupling at each IC                           │
└─────────────────┴──────────────────────────────┴──────────┴─────────────────────────────────────────────────┘

## Watchdog gate (the screen-voltage interrupter)

The fault output from Level 5 / Level 6 needs to **actually do something** to
protect the tubes. The screen-voltage gate is the cleanest interrupter:

┌───────────┬───────────────────────────────────────────────────┬─────────────────────────────────┐
│ Component │ Value                                             │ Notes                           │
├───────────┼───────────────────────────────────────────────────┼─────────────────────────────────┤
│ Q1        │ High-side P-channel MOSFET (e.g., IRF9540)        │ Switches screen voltage         │
│ R_GATE    │ 10 kΩ to source                                   │ Pulls gate to source (default ON)│
│ Q2        │ NPN switch (2N3904)                               │ Pulls gate low to turn OFF Q1   │
│ Trigger   │ OR of: comparator latches, MCU GPIO, esp_task_wdt │ Any source can fire             │
└───────────┴───────────────────────────────────────────────────┴─────────────────────────────────┘

When tripped, Q1 opens, screen drops to 0 V, tubes go dark. Tube cathode current
returns to leakage levels (< 100 µA). The plate supply is still hot but the
tubes can't conduct without screen voltage.

**Why screen instead of plate, grid, or filament?**

- **Plate**: hard to switch reliably at 600 V / 250 mA without a relay (slow,
  arcing). Drops would also have to dissipate the energy of the plate supply
  cap discharge.
- **Grid bias**: already the firmware's normal off mechanism. Hardware should
  have an independent path.
- **Filament**: takes seconds for cathode to cool. Doesn't protect against
  the immediate fault.
- **Screen**: low current (~30 mA), small voltage (200 V), fast off (cap
  discharge in µs). Tubes are guaranteed off without screen voltage.

## Open items

- [ ] Choose ADC: built-in ESP32 ADC (12-bit, fast) vs. ADS1115 (16-bit, slow
      but precise). For 100 µA resolution at 100 mA range, 12-bit on 3.3 V
      gives 80 µA LSB — adequate.
- [ ] Decide hardware vs. firmware-only latch. Pure firmware (using
      `esp_task_wdt` GPIO) is simpler but takes ~1 ms to fire. Hardware
      latch is < 100 µs but adds a 74HC chip.
- [ ] Confirm BAT54 voltage rating handles the 60 mA fault current transient.
      Datasheet: peak 200 mA for 1 µs. For F1's < 1 s trip window, ~60 mA
      sustained is right at the BAT54 limit. Consider BAS70-04W or upsizing
      to PMEG3050 for headroom.
- [ ] PCB layout: cathode socket area to analog board distance, twisted-pair
      wire gauge, shielding decision.

## Related docs

- `Documentation/2026-06-08-pa-validation.md` — PA operating point that
  determines I_cathode nominal and limits
- `Documentation/Grid_Bias_Schematic.pdf` — companion subsystem on the same
  analog board. Both subsystems share a **single LM4040DIZ-5.0** producing
  the +5 V reference rail: grid_bias uses it raw (R_G input to OPA454);
  cathode_monitor divides it down to +1.5 V (R_DIV1 / R_TRIM / R_DIV2 above)
  for the LM393 threshold. One chip, two consumers.
- `xmitter_prj/grid_bias.sch` — QUCS-S sim of the bias circuit; supplies are
  V+ = +5 V (V3) and V− = −90 V (V2), LM4040 = 5 V
- `Documentation/cw_envelope_keyer.md` — firmware fail-safe rationale (the
  watchdog gate concept originated here)

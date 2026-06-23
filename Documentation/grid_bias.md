# Grid Bias Subsystem

Per-tube negative grid-bias generation for the push-pull 6146B PA, with a
DAC-controlled OPERATE/IDLE bias point and a hardware crash-bar that
slams both grids to deep cutoff on a cathode-current fault.

Schematic: `KiCAD/bias.kicad_sch` (sheet name "Bias"). Simulation:
`xmitter_prj/grid_bias.sch`.

## Why this matters

The 6146B is a small TV horizontal-output tube being run hard. The grid
bias voltage sets the operating point — too shallow and the tube draws
runaway plate current; too deep and the drive can't switch it on. The
correct operating point also differs slightly between the two tubes
because of normal tube-to-tube parameter spread. And on any cathode-
current fault, the bias has to slam to full cutoff in microseconds —
faster than firmware can respond.

Specifically the subsystem does four things:

- **Generate −85 V IDLE on cold boot** before the MCU is even running.
  DAC EEPROM startup = 0 V → V_out = −85 V → tubes cut off in standby.
- **Switch to OPERATE bias (~−50 V) per tube on key-down**, with per-tube
  trim of a few DAC counts to balance plate current between the two
  6146Bs.
- **Bias-slam to cutoff on CT_FAULT trip** via a 2N7000 that pulls the
  DAC control input to GND, forcing V_out back to −85 V in < 1 µs.
  Independent of the MCU.
- **Reference-grade precision**: bias point set by an LM4040 5 V shunt
  reference, not by the noisy +5 V supply rail.

## System block diagram

```
                              GRID_BLOCK_CRASH (from cathode monitor OR)
                                          │
                                          │     R_GATE 10k
                                          ├────[====]──── Q2/Q3 (2N7000) gate
                                          │
        +12V ── R_Z(2.2k) ─┬─ LM4040DIZ-5.0 ─── GND
                           │      (U11)
                           └──── 100nF (C23) ── GND       ← Reference
                                                           bypass
                       ┌─── +5V_REF (precision; ~2 mA)
                       │
                       │
                       ├──── R_GA(10k) ───→ U5A IN-    (Tube A summing junction)
                       │
                       └──── R_GB(10k) ───→ U10A IN-   (Tube B summing junction)

                                                R_FA / R_FB  (170k)
                                          ┌────[========]──────┐
                                          │                    │
   GRID_CTL_A_IN ─── R_PADA(1k) ──┬─→ U5A IN+        U5A OUT ──┴─── R_GLA(22k) ── GRID_BIAS_A_OUT
   (from DAC #1)                  │                                                 (to Tube A grid,
                                  │                                                  −85 V IDLE to
                                  Q3 drain                                          ~−25 V at full)
                                  (2N7000)
                                  Source → GND
                                  Gate ← R_GATE ← GRID_BLOCK_CRASH

   GRID_CTL_B_IN ─── R_PADB(1k) ──┬─→ U10A IN+      U10A OUT ──── R_GLB(22k) ── GRID_BIAS_B_OUT
   (from DAC #2)                  │                                              (to Tube B grid)
                                  │
                                  Q2 drain
                                  (2N7000)
                                  Source → GND
                                  Gate ← R_GATE ← GRID_BLOCK_CRASH (same R_GATE serves both)

        Supplies:
          +12V ──→ R_Z(2.2k) → LM4040 (precision +5 V_REF)
                ──→ LM7805 (U9) → +5V supply rail
                ──→ external negative DC-DC (Murata NMA0509 + LM431) → −90 V rail
```

## Architecture decisions

### Precision reference vs supply rail are SEPARATE nets

There are two distinct +5 V nets on this sheet:

- **+5V** — power supply rail. Sourced by **U9 LM7805** from +12 V.
  Drives OPA454 V+ pins, plus all the +5 V loads on the buffer_keyer
  and cathode_monitor sheets (~30 mA total). Modest accuracy (~4 %),
  decent regulation.
- **+5V_REF** — precision shunt reference. Sourced by **U11 LM4040DIZ-5.0**
  biased from +12 V through R_Z (2.2 kΩ). Drives only R_GA and R_GB
  (the two OPA454 summing-junction reference inputs), plus the
  cathode-monitor's 1.5 V threshold divider on its own sheet.
  Tight accuracy (1 % initial, 100 ppm/°C).
  Total draw on +5V_REF: ~2 mA.

These two nets share GND but never touch each other. **Why:** the LM4040
sets the absolute bias point (V_out_IDLE = −V_REF × R_F/R_G = −85 V).
Letting that depend on the LM7805's output would tie the IDLE bias to
the LM7805's regulation accuracy and load-dependent voltage. Separating
them costs one chip + one resistor + one cap; gains a precision floor.

### Why the LM4040 bias resistor is 2.2 kΩ

R_Z (2.2 kΩ) carries 3.2 mA at no-load (12 V − 5 V) / 2.2 kΩ. With the
~2 mA load on +5V_REF, the LM4040 sinks 1.2 mA — comfortably above its
1 mA minimum. Headroom remains across temperature and tolerance. Could
go as low as 1.5 kΩ for more bias margin, but 2.2 kΩ is the lowest
standard E12 value that keeps LM4040 power dissipation under 5 mW
(well below the 100 mW SOT-23 limit).

### Why R_pad sits between the DAC input and the IN+ pin

R_PADA (1 kΩ) and R_PADB (1 kΩ) sit in series between each DAC input
hierarchical label (GRID_CTL_A_IN / GRID_CTL_B_IN) and the
corresponding OPA454's IN+ pin. The 2N7000 bias-slam drain ties onto
the **OPA454 side** of R_pad — *not* the DAC side. Two reasons:

- **DAC protection on bias-slam.** When CT_FAULT trips and Q2/Q3 turn on,
  the 2N7000 drain pulls its node to GND. With R_pad in series, the
  DAC sees 1 kΩ → GND (well within its drive capability). Without
  R_pad, the DAC output would be short-circuited to GND every time
  the bias slammed — a fast way to kill a DAC over many crashes.
- **Current limit on DAC fault.** If the DAC ever exceeds 0–5 V or
  shorts to a rail, R_pad limits the current into the OPA454 input
  protection diodes to (V_fault − V_clamp)/1 kΩ — survivable.

### Why both 2N7000s share one R_GATE

Q2 and Q3 (one bias-slam per tube) are both gate-driven from the same
GRID_BLOCK_CRASH signal through a single shared R_GATE (10 kΩ). Both
gates always fire together — there's no scenario where one tube needs
to be cut off and the other doesn't. Total gate capacitance is ~60 pF
(2 × 30 pF), turn-on time τ = R_GATE × Cg = 600 ns. Plenty fast for
the < 100 µs fault-response budget.

### Why bypass caps are shared between U5 and U10

U5 and U10 sit physically close on the PCB (planned for adjacent DIP-8
sockets). One pair of caps on each supply rail (C17 + C19 on V+, C18
+ C20 on V−) serves both chips. Per-chip dedicated bypass would be the
textbook approach, but **grid bias is essentially DC**:

- Bias signal bandwidth < 1 MHz even on the fastest event (bias-slam,
  ~600 ns)
- OPA454 PSRR at this bandwidth is > 90 dB
- Noise budget at grid is ±50 mV (grid drive itself is ±25 to ±50 V
  peak — a 1000:1 ratio)
- OPA454 V+ quiescent draw is ~3.5 mA with no dynamic content

Even ±100 mV of supply ripple would translate to < 30 µV at the bias
output — vastly below anything that would affect tube operation.

### Why 1 µF instead of 10 µF on the bulk caps

The OPA454 datasheet recommends 100 nF + 10 µF on each rail for
general use. That assumes µV-class instrumentation accuracy. At
DC-bias accuracy targets (mV-class), 1 µF is enough to keep the
supply quiet across the OPA454's low quiescent current. Switching
to ceramic 1 µF (X7R) is cleaner than electrolytic 10 µF (lower ESR,
no polarity concern, smaller footprint).

## Transfer function

The OPA454 acts as a non-inverting summing amp:

    V_out = V_DAC × (1 + R_F/R_G) − V_REF × R_F/R_G
          = V_DAC × 18 − 85

With R_F = 170 kΩ, R_G = 10 kΩ, V_REF = +5 V, and V− supply = −90 V:

- V_DAC = 0 V    → V_out = −85 V (IDLE: tubes deeply cut off)
- V_DAC = 1.94 V → V_out = −50 V (OPERATE: shallow class C)
- V_DAC = 3.30 V → V_out = −25.6 V (firmware MUST cap below this —
                                    further forward-biases the grid)

Per-tube OPERATE DAC code (~2410 of 4095 nominal) may differ by a few
counts between tubes to balance plate current. Calibrated at bring-up
via the cathode-current monitor.

## Power-up sequencing and fail-safes

Three layers of bias-side safety:

- **DAC EEPROM safe-park.** MCP4725 startup value = 0 → bias = −85 V
  immediately on cold boot, before MCU initializes I²C or runs any
  application code.
- **Hardware bias-slam (Q2/Q3 + R_GATE).** GRID_BLOCK_CRASH from the
  cathode-monitor OR-latch yanks both bias inputs to GND in ~600 ns,
  forcing V_out to −85 V regardless of DAC state. Independent of MCU.
- **Firmware-controlled IDLE↔OPERATE.** Per-tube DAC writes manage the
  normal key-up/key-down bias change. WinKey signals trigger the DAC
  transitions in the firmware (see cw_envelope_keyer.md).

## Layer-by-layer design

### Level 0 — Power supply tree

┌───────────┬──────────────────────────────────┬──────────────────────────────────────────────────────┐
│ Component │ Value                            │ Notes                                                │
├───────────┼──────────────────────────────────┼──────────────────────────────────────────────────────┤
│ U9        │ LM7805CT (TO-220)                │ +12 V → +5 V supply rail. ~30 mA load (OPA454 V+×2,  │
│           │                                  │ all buffer_keyer/cathode_monitor +5 V loads).        │
│           │                                  │ Dissipation ~270 mW, no heatsink needed at this load │
│ C21       │ 0.22 µF X7R                      │ LM7805 input bypass (between +12 V and GND)          │
│ C22       │ 0.1 µF X7R                       │ LM7805 output bypass (stability requirement)         │
│ U11       │ LM4040DIZ-5.0 (TO-92 3-pin)      │ Precision +5 V shunt reference (1 % initial)         │
│ R_Z       │ 2.2 kΩ 5 % 1/4 W                 │ LM4040 bias resistor from +12 V → cathode (3.2 mA    │
│           │                                  │ no-load, 1.2 mA at full load — both within spec)     │
│ C23       │ 100 nF X7R                       │ LM4040 cathode → GND bypass; HF rejection on REF rail│
└───────────┴──────────────────────────────────┴──────────────────────────────────────────────────────┘

### Level 1 — Bias gain stage (one per tube)

┌───────────┬──────────────────────────────────┬──────────────────────────────────────────────────────┐
│ Component │ Value                            │ Notes                                                │
├───────────┼──────────────────────────────────┼──────────────────────────────────────────────────────┤
│ U5 / U10  │ OPA454AIDA (SOIC-8 on DIP-8 adp) │ High-voltage op-amp; V+ = +5 V, V− = −90 V (95 V     │
│           │                                  │ total, 5 V under 100 V op-max). U5 = Tube A, U10 = B │
│ R_FA/R_FB │ 170 kΩ 1 %                       │ Feedback from OUT → IN−. Sets gain × 18 and the      │
│           │                                  │ −85 V IDLE offset (with V_REF on R_G)                │
│ R_GA/R_GB │ 10 kΩ 1 %                        │ +5 V_REF → IN−. Lower-leg of the inverting summing  │
│           │                                  │ junction                                              │
│ R_PADA    │ 1 kΩ 5 %                         │ DAC #1 (Tube A) → IN+ series resistor (1 k impedance │
│ R_PADB    │ 1 kΩ 5 %                         │ DAC #2 (Tube B) → IN+ series resistor                │
│ R_GLA     │ 22 kΩ 5 %                        │ U5A OUT → Tube A grid (load isolation)               │
│ R_GLB     │ 22 kΩ 5 %                        │ U10A OUT → Tube B grid (load isolation)              │
└───────────┴──────────────────────────────────┴──────────────────────────────────────────────────────┘

### Level 2 — Bias-slam (one MOSFET per tube, shared gate driver)

┌───────────┬──────────────────────────────────┬──────────────────────────────────────────────────────┐
│ Component │ Value                            │ Notes                                                │
├───────────┼──────────────────────────────────┼──────────────────────────────────────────────────────┤
│ Q2        │ 2N7000 (TO-92)                   │ Tube B bias-slam. Drain → IN+ side of R_PADB;        │
│           │                                  │ source → GND; gate → R_GATE → GRID_BLOCK_CRASH       │
│ Q3        │ 2N7000 (TO-92)                   │ Tube A bias-slam. Same topology as Q2 on R_PADA      │
│ R_GATE    │ 10 kΩ 5 %                        │ SHARED gate resistor between Q2 and Q3. R_GATE ×    │
│           │                                  │ (2 × Cg) ≈ 600 ns turn-on; well under fault budget   │
└───────────┴──────────────────────────────────┴──────────────────────────────────────────────────────┘

### Level 3 — Supply bypass (shared between U5 and U10)

┌───────────┬──────────────────────────────────┬──────────────────────────────────────────────────────┐
│ Component │ Value                            │ Notes                                                │
├───────────┼──────────────────────────────────┼──────────────────────────────────────────────────────┤
│ C17       │ 1 µF X7R ceramic                 │ V+ bulk; pooled across U5 and U10 V+ pins            │
│ C19       │ 100 nF X7R                       │ V+ HF bypass; pooled                                 │
│ C18       │ 1 µF X7R ceramic                 │ V− bulk; pooled across U5 and U10 V− pins            │
│ C20       │ 100 nF X7R                       │ V− HF bypass; pooled                                 │
└───────────┴──────────────────────────────────┴──────────────────────────────────────────────────────┘

Note: C17 and C18 currently use the `Device:C_Polarized` symbol. At 1 µF
the part will be a non-polarized X7R ceramic in production; the symbol
choice doesn't affect electrical correctness but should be switched to
`Device:C` to avoid an assembly-orientation hazard.

## Inter-sheet I/O

Hierarchical labels exported by / imported into this sheet:

- **GRID_CTL_A_IN** (input) — Tube A bias DAC output, from off-sheet
  MCP4725 #1 (I²C). 0–3.3 V range. Drives U5A IN+ via R_PADA.
- **GRID_CTL_B_IN** (input) — Tube B bias DAC output, from off-sheet
  MCP4725 #2 (I²C). Drives U10A IN+ via R_PADB.
- **GRID_BLOCK_CRASH** (input) — Active-high fault signal from
  cathode-monitor OR-latch. Fires both Q2 and Q3 bias-slams
  simultaneously.
- **GRID_BIAS_A_OUT** (output) — Tube A grid bias, −85 V to ~−25 V
  swing through R_GLA.
- **GRID_BIAS_B_OUT** (output) — Tube B grid bias, same swing through R_GLB.

Power port nets used:

- **+12 V** — sourced off-sheet (Metro VIN or external 12 V supply)
- **+5 V** — generated locally by U9, also exported via the +5 V power
  port to buffer_keyer and cathode_monitor sheets
- **−90 V** — sourced off-sheet (per design PDF: isolated DC-DC + LM431
  shunt regulator)
- **GND** — star-grounded to analog board

## BOM summary (this sheet)

Active components:

- **2× OPA454AIDA** (U5, U10) — high-voltage op-amp, SOIC-8 on DIP-8 adapter
- **1× LM4040DIZ-5.0** (U11) — precision +5 V shunt reference, TO-92
- **1× LM7805CT** (U9) — 5 V linear regulator, TO-220
- **2× 2N7000** (Q2, Q3) — N-channel MOSFET, TO-92

Resistors (1/4 W; 1 % metal film for precision parts, 5 % carbon for others):

- 2× 170 kΩ 1 % (R_FA, R_FB)
- 2× 10 kΩ 1 % (R_GA, R_GB)
- 1× 10 kΩ 5 % (R_GATE)
- 2× 22 kΩ 5 % (R_GLA, R_GLB)
- 2× 1 kΩ 5 % (R_PADA, R_PADB)
- 1× 2.2 kΩ 5 % (R_Z)

Capacitors (all X7R ceramic):

- 3× 100 nF (C19, C20, C23)
- 2× 1 µF (C17, C18)
- 1× 0.22 µF (C21)
- 1× 0.1 µF (C22)

Total: 6 active devices, 10 resistors, 7 capacitors.

## Calibration procedure (bring-up)

1. **Verify rails before powering up bias.** With +12 V applied and
   +5 V and −90 V rails confirmed, check +5 V_REF reads 5.000 ±50 mV
   at the LM4040 cathode (TP_REF if added, or directly at U11).
2. **Verify IDLE bias.** With both bias DACs at code 0, V_out at
   each grid should read −85 V ±2 V (the ±2 V slop is from R_F/R_G
   tolerance; tighten if needed for plate-current balance).
3. **Sweep OPERATE DAC code.** With one tube at a time (other tube
   blocked at −85 V), step the DAC from 0 toward 2500, watching
   cathode current via the cathode-monitor ADC. Find the DAC code
   that produces target I_cathode = 100 mA. Record per tube as
   `bias_code_operate[tube_id]`. Expect codes around 2400–2500.
4. **Verify bias-slam.** Manually pulse GRID_BLOCK_CRASH high while
   in OPERATE. Both grid outputs should snap to −85 V within
   < 5 µs (oscilloscope on each grid output).
5. **Store calibration in NVS.** `bias_code_operate[tube_id]`,
   `bias_code_idle = 0`, calibration timestamp. Re-run every 100
   operating hours or after tube swap.

## Open items

- [x] ~~Rename `KiCAD/untitled.kicad_sch` → `bias.kicad_sch`.~~ Done 2026-06-23.
- [ ] Assign footprints to all R and C (currently `(none set)`).
      Suggested: 1206 or 1812 for hand-solder ceramic caps; through-hole
      1/4 W axial for resistors. Power resistors (R_Z dissipates < 25 mW
      — no special concern).
- [ ] Change C17 and C18 from `Device:C_Polarized` to `Device:C` (assembly
      hazard mitigation; no electrical change).
- [ ] Confirm +12 V rail source on root sheet (Metro VIN passthrough vs
      dedicated 12 V supply input on this board).
- [ ] Confirm −90 V rail topology decision: isolated DC-DC (Murata
      NMA0509 + LM431 shunt) per the original PDF, or alternative.

## Related docs

- `Documentation/cw_envelope_keyer.md` — envelope DAC, WinKey hook,
  firmware bias control via MCP4725 (the DACs driving GRID_CTL_*_IN).
- `Documentation/pa_cathode_monitor.md` — cathode-current monitor that
  generates GRID_BLOCK_CRASH. Shares the LM4040 +5 V_REF rail from
  this sheet (1.5 V comparator threshold from a 4.7 k / 1 k trim / 1.5 k
  divider).
- `Documentation/Grid_Bias_Schematic.pdf` — earlier design PDF (Design A:
  OPA454 single-supply HV; Design B: LM358 + MPSA92 PNP fallback if
  OPA454 unobtainable). KiCad sheet implements Design A.
- `Documentation/2026-06-08-pa-validation.md` — PA operating point
  (V6 = 180 V, bias = −60 V, R17 = 300 Ω) that determines bias-code
  calibration targets.
- `xmitter_prj/grid_bias.sch` — QUCS simulation. Topology, R/C values,
  and supply rail polarities match this sheet's implementation.

# PA Validation Session — 2026-06-08

End-to-end simulation work on the keyer → driver → PA chain, ending with confirmation that
the push-pull 6146B PA can hit ~50 W output safely within tube ratings. Captures every
change made this session, the sweep results that validated the design, and the lessons
learned about ngspice quirks that bit us along the way.

## Summary

┌──────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Question                                                 │ Answer arrived at                                                                                                                                                                                                                                                                                │
├──────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Is C_TANK = 33 pF the right value?                       │ **Yes.** Tank already accounts for ~8.5 pF 6146B output capacitance per tube → effective 41.5 pF per side → resonance lands at 14.2 MHz. Sweep showed peak power within ±1 pF.                                                                                                                   │
│ Best R17 load for the PA in standalone test?             │ **~320 Ω** (broad peak from 290–360 Ω, all within 2 % of max). Equivalent to the ~300 Ω the balun + 50 Ω antenna naturally present in the full chain.                                                                                                                                            │
│ Max V6 drive without exceeding tube ratings?             │ **Dissipation alone: V6 = 240 V is safe** (14 W/tube, 55 W out). **But the grid-voltage spec (−150 V max) is the binding constraint** — bias = −70 V, V6 = 160 V puts peak negative grid voltage at exactly −150 V; above that overdrives the grid. See "Corrected operating point" below.        │
│ Can we hit 50 W safely (with the grid voltage limit)?    │ **Yes** — bias = **−60 V**, V6 = **180 V** on R17 = 300 Ω gives 50 W out, 24 W/tube dissipation (5 % margin on 25 W rating), peak grid at exactly −150 V. (The earlier "−70 V / V6 = 200 V" hit peak grid of −170 V, 20 V over spec, no longer the design point.)                                  │
│ Does the modulator-port linear-mode redesign work?       │ **Yes.** 20 dB pad + 7-pole LPF + LM7171 post-amp (gain ~5.8) restored full driver input level while moving the MC1496 into true 4-quadrant multiplier behaviour (carrier port ~30 mV peak, well below switching threshold).                                                                     │
└──────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

## Changes committed this session

### VFO subcircuit (`vfo_subcircuit.sch`)

**Pi pad** upgraded from 6 dB to **20 dB** to reduce carrier amplitude into the keyer:

┌──────────┬───────┬────────────┐
│ Ref      │ Old   │ New        │
├──────────┼───────┼────────────┤
│ RP1, RP3 │ 150 Ω │ **62 Ω**   │
│ RP2      │ 39 Ω  │ **240 Ω**  │
└──────────┴───────┴────────────┘

Result: V_RF_IN to keyer drops from ~380 mV peak to ~38 mV peak, putting the MC1496
carrier port in linear-multiplier mode.

**LPF** upgraded from 5-pole to **7-pole Chebyshev** (same fc = 17.5 MHz, 0.1 dB ripple)
for deeper harmonic rejection — necessary now that the modulator passes carrier harmonics
directly to the output instead of generating its own from switching mode:

┌──────────────┬──────────────────────┬─────────────────────────────────────────┐
│ Element      │ Old (5-pole)         │ New (7-pole)                            │
├──────────────┼──────────────────────┼─────────────────────────────────────────┤
│ CF1 / CF7    │ 200 pF               │ **220 pF**                              │
│ LF2 / LF6    │ 13 t T50-6 (~624 nH) │ 13 t T50-6 (~647 nH) ← same as before   │
│ CF3 / CF5    │ 360 pF               │ **390 pF**                              │
│ LF4 (center) │ 13 t T50-6           │ **14 t T50-6** (~715 nH)                │
└──────────────┴──────────────────────┴─────────────────────────────────────────┘

Stopband rejection improvement at the LPF output:

┌────────────────┬────────┬──────────┬────────┐
│ Harmonic       │ 5-pole │ 7-pole   │ Δ      │
├────────────────┼────────┼──────────┼────────┤
│ 2f (28.4 MHz)  │ 13 dB  │ **28 dB**│ +15 dB │
│ 3f (42.6 MHz)  │ 33 dB  │ **60 dB**│ +27 dB │
│ 5f (71 MHz)    │ 58 dB  │ **95 dB**│ +37 dB │
└────────────────┴────────┴──────────┴────────┘

### Keyer subcircuit (`keyer.sch`)

- **R10 = 8.2 kΩ** (was 1 kΩ in earlier version) — completes the symmetry fix with R5, R7, R9 so the PNP null injection is balanced
- **Re = 200 Ω** (was 1 kΩ) — increases modulator gain (12HG7 driver wants ~8 V p-p input)
- **C1 = 330 pF** (unchanged) — cap divider not used for attenuation; the upstream pad does that work
- **R11, R12 = 22 kΩ** (was 1 kΩ) — carrier-port bias divider standing current dropped from 6 mA to ~0.3 mA (no functional change)
- **LM7171 post-amp** (one per differential side, gain = 5.8) — restores the ~8 V p-p drive the driver needs after the modulator runs in low-gain linear mode

### LM7171 post-keyer amplifier (new subcircuit `Op_Amp_Out.sch`)

Non-inverting gain-of-5.8 amp, AC-coupled in/out, powered from existing +12 V / −8.3 V:

┌─────────────┬─────────────┬─────────────────────────────────────────────────┐
│ Part        │ Value       │ Role                                            │
├─────────────┼─────────────┼─────────────────────────────────────────────────┤
│ LM7171AIN   │ —           │ 200 MHz GBW op-amp (DIP-8/SOIC-8)               │
│ C_IN, C_OUT │ 100 nF X7R  │ Couples around the +10 V DC at MC1496 outputs   │
│ R_B         │ 100 kΩ 1%   │ + input bias to GND                             │
│ R_F         │ 30 kΩ 1%    │ Feedback (gain = 1 + R_F/R_G = 4)               │
│ R_G         │ 10 kΩ 1%    │ Inverting-input leg to GND                      │
└─────────────┴─────────────┴─────────────────────────────────────────────────┘

(Schematic ships with R_F = 30 kΩ for gain 4. After this session's analysis the
recommended value for production is R_F = 47 kΩ giving gain 5.8 — see
`cw_envelope_keyer.md` for the trade-off table.)

### PA subcircuit (`PA_subcircuit.sch`)

- Plate-current sense probe path restructured during diode experiments (then reverted)
- Tran window extended to 3.5 µs (was 200 ns) so RMS/mean stats can integrate over ~50 cycles instead of ~3
- R17 (standalone test load) = 300 Ω — represents the ~300 Ω the balun delivers in full chain
- V6 (standalone drive) = 160 V — useful single-point baseline; **180 V at bias = −60 V is the 50 W operating point** that honors the grid voltage spec (the earlier "200 V at bias = −70 V" recommendation violated the −150 V grid limit by 20 V — see "Grid voltage constraint" below)

### Balun subcircuit (`Balun_6to1_subcircuit.sch`)

- Added 0.5 Ω Rser to break a singular-matrix between LP and the PA's L6 (both inductors between the same two nodes at DC — needed *any* non-zero R to disambiguate)

## PA sweep results

All numbers below: standalone PA sim, GRID = 70 V, SCREEN = 200 V, V_supply = 600 V,
C_TANK = 33 pF, sim window = 3.5 µs (50 cycles at 14.2 MHz), R17 = 300 Ω unless noted.

### R17 sweep at V6 = 160 V

┌──────────┬───────────┬─────────────────────┐
│ R17 (Ω)  │ V_rms (V) │ P_out (W)           │
├──────────┼───────────┼─────────────────────┤
│ 220      │ 92.3      │ 38.7                │
│ 240      │ 98.6      │ 40.5                │
│ 260      │ 104.4     │ 41.9                │
│ 275      │ 108.3     │ 42.7                │
│ 290      │ 111.8     │ 43.1                │
│ 300      │ 114.0     │ 43.3                │
│ 310      │ 115.9     │ 43.3                │
│ **325**  │ **118.7** │ **43.4** ← peak     │
│ 340      │ 121.1     │ 43.1                │
│ 360      │ 124.0     │ 42.7                │
│ 380      │ 126.5     │ 42.1                │
│ 420      │ 130.6     │ 40.6                │
└──────────┴───────────┴─────────────────────┘

Conclusion: broad plateau 290–360 Ω, peak ~325 Ω. Tube spread (±10 %) swamps any
finer optimization; **300 Ω is the production target**.

### V6 sweep at R17 = 300 Ω

Each V6 row gives peak current, average current, output power, plate dissipation per tube:

┌─────────┬──────────────────┬─────────────────┬───────────────┬─────────────────┬─────────────────┬────────────┐
│ V6 (V)  │ I_peak (mA/tube) │ I_avg (mA/tube) │ P_in/tube (W) │ P_out total (W) │ P_diss/tube (W) │ Efficiency │
├─────────┼──────────────────┼─────────────────┼───────────────┼─────────────────┼─────────────────┼────────────┤
│ 80      │ 59               │ 8.5             │ 5.1           │ 0.9             │ 4.7             │ 9 %        │
│ 100     │ 133              │ 20.2            │ 12.1          │ 5.0             │ 9.6             │ 21 %       │
│ 120     │ 224              │ 35.0            │ 21.0          │ 14.3            │ 13.8            │ 34 %       │
│ 140     │ 318              │ 50.8            │ 30.5          │ 29.3            │ 15.8            │ 48 %       │
│ 160     │ 377              │ 60.9            │ 36.5          │ 41.6            │ 15.7            │ 57 %       │
│ 180     │ 400              │ 64.6            │ 38.8          │ 47.0            │ 15.3            │ 61 %       │
│ **200** │ **416**          │ **66.8**        │ **40.1**      │ **50.3**        │ **14.9**        │ **63 %**   │
│ 220     │ 426              │ 68.2            │ 40.9          │ 52.8            │ 14.5            │ 65 %       │
│ 240     │ 433              │ 69.1            │ 41.5          │ 54.6            │ 14.2            │ 66 %       │
└─────────┴──────────────────┴─────────────────┴───────────────┴─────────────────┴─────────────────┴────────────┘

Tube envelope check (6146B: 25 W plate, 270 mA peak emission steady-state):

- **Dissipation peaks at V6 = 140–160 V (~15.8 W/tube)** — *60 % of rating* — well within envelope
- Above V6 ≈ 160 V, dissipation *decreases* even as output rises (efficiency improves faster than input power grows in class C)
- Peak plate current of 416 mA at V6 = 200 V looks scary by itself but is acceptable — the 270 mA rating is steady-state, not instantaneous peak; what kills tubes is average dissipation, not peak current
- **HOWEVER:** the grid-voltage spec is what binds the operating point, NOT
  plate dissipation. See next section.

### Grid voltage constraint (the binding limit)

The 6146B's max peak negative grid voltage is **−150 V**. With bias = −70 V
and V6 differential drive between the two grids, each grid swings ±V6/2
around its bias. So:

- bias −70 V, V6 = 160 V → peak grid = −70 − 80 = **−150 V** (at the limit)
- bias −70 V, V6 = 200 V → peak grid = −70 − 100 = **−170 V** (20 V over spec)

The V6 = 200 V operating point that maximised the dissipation/output trade
**violates the grid voltage spec by 20 V**. Exceeding peak grid voltage is
one of the fastest failure modes for vacuum tubes — far quicker than slow
plate-dissipation overload. So the design must back off from V6 = 200 V to
honour the grid limit.

A paired (bias, V6) sweep ran each operating point at the limit point where
peak grid = exactly −150 V (V6 = 2 × (150 − |bias|)):

┌───────────┬───────────┬──────────┬─────────────┬─────────────┬──────────────────────────┐
│ Bias      │ V6        │ P_out    │ I_peak/tube │ P_diss/tube │ Eff                      │
├───────────┼───────────┼──────────┼─────────────┼─────────────┼──────────────────────────┤
│ −75 V     │ 150 V     │ 22 W     │ 276 mA      │ 21 W        │ 35 %                     │
│ −70 V     │ 160 V     │ 35 W     │ 341 mA      │ 23 W        │ 43 %                     │
│ −65 V     │ 170 V     │ 44 W     │ 380 mA      │ 24 W        │ 48 %                     │
│ **−60 V** │ **180 V** │ **50 W** │ **412 mA**  │ **24 W**    │ **51 %** ← 50 W target   │
│ −55 V     │ 190 V     │ 56 W     │ 431 mA      │ 23 W        │ 54 %                     │
│ −50 V     │ 200 V     │ 60 W     │ 442 mA      │ 23 W        │ 56 %                     │
│ −45 V     │ 210 V     │ 63 W     │ 459 mA      │ 23 W        │ 57 %                     │
└───────────┴───────────┴──────────┴─────────────┴─────────────┴──────────────────────────┘

Key observation: **plate dissipation is nearly flat at 21–24 W/tube** across
the whole bias range. The trade-off isn't "deep C = efficient vs. shallow C
= lossy" — it's "deep C = less output for the same heat vs. shallow C =
more output for the same heat." Shallow bias wins on power-per-watt-of-
dissipation; the only real cost is higher peak current (still inside the
6146B emission envelope at all sweep points).

### Corrected operating point

┌──────────────────────────┬─────────────────────────────────────────────────────────────────────┐
│ Metric                   │ Value                                                               │
├──────────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ V6 drive amplitude       │ **180 V peak** (≈8 V p-p × driver gain at the LM7171 output)        │
│ R17 / load impedance     │ **300 Ω** (matches the balun's 6:1 step-down from 50 Ω antenna)     │
│ Plate supply (V_supply)  │ 600 V DC                                                            │
│ Screen voltage           │ +200 V                                                              │
│ Grid bias                │ **−60 V** (operating; see below for hardware-vs-firmware strategy)  │
│ Output power             │ **50 W**                                                            │
│ Plate dissipation        │ 24 W/tube (5 % margin on 25 W CW rating)                            │
│ Peak grid voltage        │ **−150 V** (exactly at spec)                                        │
│ Efficiency               │ 51 %                                                                │
└──────────────────────────┴─────────────────────────────────────────────────────────────────────┘

### Bias rail strategy: hardware−rail vs firmware−adjusted

Set the **hardware bias supply rail to −65 to −70 V** (deeper than operating
point), and have firmware bring the operating bias to −60 V via the per-tube
DAC + HV op-amp (OPA454) circuit captured in `legacy/20m-leveled-keyed-buffer.md`.
Rationale:

- **Power-up safe**: hardware default is deep cutoff before firmware runs
- **Fail-safe**: if firmware hangs, bias falls back to hardware rail (cutoff) —
  same watchdog pattern as the keyer DAC
- **Per-tube balance**: same DACs that bias the tubes can trim tube-to-tube
  spread (typically ±2–3 V)
- **Drift headroom**: dissipation is nearly flat across the −70 → −60 V
  modulation range, so any firmware control loop has room to wander without
  exiting the safe envelope

**Practical firmware target**: operate at **bias = −63 V** instead of −60 V
to give 3 V of cushion before grid voltage hits −150 V under any
combination of tube spread, supply ripple, and DAC quantisation. Costs
~1–2 W of output (49 W instead of 50 W); eliminates the "ride the spec
continuously" anxiety.

### Two-state bias operation (refinement of the strategy above)

Because the per-tube grid bias is firmware-controlled via the DAC + OPA454,
nothing forces a single fixed operating-bias value. **Use two distinct bias
setpoints** — one for key-up (idle), one for key-down (transmit) — and the
PA gets meaningfully safer plus cleaner.

┌────────────────────────┬───────────┬─────────────────────────┬───────────────┬─────────────────────┐
│ State                  │ Bias      │ Tube state              │ Plate current │ Standby dissipation │
├────────────────────────┼───────────┼─────────────────────────┼───────────────┼─────────────────────┤
│ **IDLE** (key-up)      │ **−90 V** │ Deep cutoff, fully off  │ 0 mA          │ 0 W per tube        │
│ **OPERATE** (key-down) │ **−50 V** │ Shallow class C         │ per envelope  │ per envelope        │
└────────────────────────┴───────────┴─────────────────────────┴───────────────┴─────────────────────┘

The IDLE state gives belt-and-braces safety: even if the MC1496's carrier
null isn't perfect, biased-off tubes can't emit RF. Plate current is exactly
zero in IDLE (not just "low"), so standby dissipation is exactly zero.

The OPERATE state is the same −50 V shallow class C that earlier analysis
identified as optimum for envelope linearity: conduction threshold around
V6 = 80 V, leaving ~75 V of clean modulation range from threshold to 50 W
output, with full envelope range available to the keyer's predistortion LUT
without hitting the conduction-onset cliff that fixed −70 V or −60 V bias
would create.

#### Firmware sequencing

The bias DAC settles in ~200 µs (R_GL = 22 kΩ × tube grid input capacitance
~10 pF gives a 0.22 µs grid-side time constant; the OPA454 output impedance
is negligible). The envelope DAC's raised-cosine edge is 3–5 ms. So the
bias transition can complete well before the envelope opens up the
modulator.

**Key-down sequence:**
1. WinKey layer signals `keyer_key_down()`
2. Per-tube bias DACs commanded from IDLE → OPERATE
3. Wait 200 µs for OPA454 + grid input cap to settle
4. Kick off envelope DAC raised-cosine ramp toward `CODE_FULL`

**Key-up sequence:**
1. Envelope DAC ramps from `CODE_FULL` → 0 (raised-cosine, 3–5 ms)
2. Wait 1 ms guard after envelope reaches null
3. Per-tube bias DACs commanded from OPERATE → IDLE
4. Wait 200 µs to confirm tubes are back in deep cutoff

Total turn-on time: ~3.2 ms (200 µs bias + 3 ms envelope), indistinguishable
from a fixed-bias transmitter in operator feel but spectrally cleaner because
the envelope doesn't have to traverse a conduction-onset nonlinearity.

#### Hardware change

The bias circuit drawn in `Grid_Bias_Schematic.pdf` was originally sized for
the −70 V to −50 V range. For two-state operation we need the IDLE state to
reach −90 V. Change one resistor:

┌──────────┬────────────────────────┬──────────────────────────┐
│ Resistor │ Original (−70 V range) │ Two-state (−90 V range)  │
├──────────┼────────────────────────┼──────────────────────────┤
│ R_2      │ 3.57 kΩ                │ **2.78 kΩ**              │
│ R_3      │ 1.00 kΩ                │ unchanged                │
│ R_F      │ 50 kΩ                  │ unchanged                │
│ R_in     │ 10 kΩ                  │ unchanged                │
└──────────┴────────────────────────┴──────────────────────────┘

Same OPA454, same DAC, same supplies — just one resistor value. New range
maps DAC code 0 → −90 V (IDLE) and code 4095 → −50 V (OPERATE). Per-tube
trim around the operating point is still ~±2 V via the bottom 2-3 bits of
the DAC near the high end.

#### Future direction: dynamic bias modulation

The bias DAC's update rate (~360 kHz on MCP4725 fast-mode I²C) is far faster
than the 3-5 ms envelope. A v2 firmware could **slide bias from −80 V at
envelope-low to −50 V at envelope-peak in sync with the envelope DAC** — the
RF equivalent of Envelope Tracking used in modern PAs. Benefits:

- Eliminate the conduction-threshold nonlinearity entirely
- Lower peak heat (less dissipation when envelope is low)
- Tighter spectrum (less PA-generated distortion)

Costs: more firmware complexity (two DAC tracks to coordinate), calibration
of bias-vs-envelope mapping. Hardware is already capable; this is a firmware
extension worth keeping the door open for after first-light bring-up.

### Grid-bias subcircuit implementation files

┌─────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ File                                    │ Purpose                                                                                                                                                                                                                                              │
├─────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ `xmitter_prj/grid_bias.sch`             │ The 2-port subcircuit. External pins: `Control_In` (from DAC), `Grid_Bias_Out` (to 6146B grid). Internal: +12 V / +5 V LM4040 ref / −85 V supplies, OPA454, R_pad, R_G, R_F = 170 kΩ, R_GL = 22 kΩ.                              │
│ `xmitter_prj/grid_bias_check.sch`       │ Test wrapper instantiating `grid_bias` as a Sub component. Drives Control_In with V1, loads Grid_Bias_Out with 1 MΩ, sweeps V1 = 0–3.3 V via `.SW` + `.DC` blocks. **Canonical reference for parameter-sweep setup in QUCS-S.** │
│ `xmitter_prj/opa454.lib`                │ TI's PSpice OPA454 model, converted to ngspice (PSpice expression VCVS → Berkeley B-source). Includes 5-pin wrapper `OPA454_5PIN` that ties enable HIGH and exposes only +IN, −IN, V+, V−, OUT.                                  │
│ `xmitter_prj/grid_bias_standalone.cir`  │ Hand-written ngspice netlist that replicates `grid_bias_check.sch`'s circuit without QUCS-S. Useful for rapid iteration. Confirms V_out = V_DAC × 18 − 85 to 3 decimal places.                                                    │
│ `xmitter_prj/ngspice.py`                │ CLI wrapper: `python ngspice.py <stem>` runs ngspice_con on `<stem>.cir`, parses the rawfile, writes `<stem>.dat.ngspice` for `gui_plot.py`. Saves typing the full path to `ngspice_con.exe`.                                    │
│ `Documentation/Grid_Bias_Schematic.pdf` │ 5-page reference doc with both design variants (Design A: OPA454 HV op-amp; Design B: discrete PNP level-shifter), component tables, transfer functions, and the two-state firmware sequencing notes.                            │
└─────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

#### Important QUCS-S gotchas learned setting this up

┌─────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Symptom                                                                 │ Cause                                                                                          │ Fix                                                                                                                                 │
├─────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Custom `.sym` file fails to load ("No symbol loaded")                   │ Non-ASCII characters in Description (em dash, ohm symbol, etc.)                                │ Keep `.sym` files strictly ASCII. QUCS-S symbol parser is not Unicode-clean.                                                        │
│ SpLib component generates `XX1  OPA454_5PIN` with no nodes              │ "Port name" column in the SpLib dialog can't be edited in QUCS-S 26.1.1 Windows build (UI bug) │ Use template `"auto"` instead of `"opamp5t"` — QUCS-S generates a generic box symbol from the .SUBCKT pin order.                    │
│ `.SW` parameter sweep produces a single `op` only                       │ The "Simulation" field (first SW property) was empty                                           │ Set the `.SW`'s first property to the name of a `.DC` (or `.AC` / `.TR`) simulation block on the same schematic.                    │
│ `dc dac_v ...` fails with "Voltage source ... named 'dac_v' is not …"   │ `dc` ngspice command sweeps a SOURCE, not a `.PARAM`                                           │ Sweep the Vdc source directly (e.g., `V1`). The `.SW` "Parameter" field accepts a source name as well as a parameter name.          │
└─────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

## New tooling

### `tools/sweep_param.py` — generic ngspice parameter sweep

Substitutes a regex-captured value in a netlist, runs ngspice in parallel across N
workers, parses the spice4qucs rawfiles, computes a chosen metric on a chosen probe.
Replaces the earlier C_TANK-specific `sweep_ctank.py` (kept for reference).

Common invocations:

```bash
# C_TANK sweep
python sweep_param.py PA_netlist.cir \
  --pattern '\.PARAM\s+C_TANK\s*=\s*([\d.]+\s*p?F?)' \
  --values 27pF,30pF,33pF,36pF,42pF \
  --probe v(pr1) --load 300 --metric p_into_r

# R17 (load) sweep — note --metric rms since R changes per row
python sweep_param.py PA_netlist.cir \
  --pattern 'R17\s+\S+\s+\S+\s+(\d+)' \
  --values '220,260,290,300,325,360,420' \
  --probe v(pr1) --metric rms

# V6 (drive) sweep, peak plate current
python sweep_param.py PA_netlist.cir \
  --pattern 'V6\s+\S+\s+\S+\s+DC\s+0\s+SIN\(0\s+([\d.]+)' \
  --values '100,140,160,180,200,220' \
  --probe 'i(vpr3)' --metric peak_abs

# Same V6 sweep, average plate current (for dissipation analysis)
python sweep_param.py PA_netlist.cir \
  --pattern 'V6\s+\S+\s+\S+\s+DC\s+0\s+SIN\(0\s+([\d.]+)' \
  --values '100,140,160,180,200,220' \
  --probe 'i(vpr3)' --metric mean
```

Metrics supported: `mean`, `peak`, `peak_neg`, `peak_abs`, `peak_to_peak`, `rms`,
`p_into_r`. Mean and RMS use **trapezoidal time-weighting** (essential — see lessons
below). The `--dry-run` flag confirms the pattern matched the intended line before
launching a long-running sweep.

### `tools/sweep_bias_drive.py` — paired (bias, V6) sweep for grid-voltage-constrained analysis

Built after the grid-voltage spec issue surfaced. Sweeps tuple pairs of (GRID
bias, V6 drive) where each pair sits exactly at the −150 V grid spec limit
(V6 = 2 × (150 − |bias|)). Runs ngspice in parallel for each pair; reports
combined power and dissipation table. Hardcoded R_LOAD = 300 Ω; edit the
`PAIRS` list at the top of the script to add intermediate points.

```bash
python sweep_bias_drive.py
# (no args — operating points are baked in)
```

This is the tool that produced the corrected operating-point table above.

### `tools/gui_plot.py` change

Removed the 750 ms auto-close of the progress window after a successful ngspice run.
Window now stays open so the user can read through the log for warnings.

### `tools/plot.py` change

Second-and-beyond plot curves default to `(none)` instead of auto-populating with the
next variable in the dep list. The default is now: only curve A is auto-selected; B+
overlays are opt-in. Cleaner plots, no obscuring of curve A.

## Lessons learned (worth remembering)

### 1. ngspice transient sampling vs. RMS/mean accuracy

Adaptive timestep means samples cluster around fast-changing parts of the waveform. A
simple arithmetic mean of sample values is BIASED — it overweights wherever the solver
took small steps.

**Fix:** trapezoidal time-weighted integration:

```python
integral = sum(0.5 * (y[i] + y[i+1]) * (t[i+1] - t[i]) for i in range(n-1))
mean = integral / (t[-1] - t[0])
```

For RMS: same trapezoidal integration of `(y - mean)^2`.

This is now built into `sweep_param.py`.

### 2. ngspice transient window length vs. RMS/mean validity

You also need **enough complete cycles** in the sampled window for the statistic to be
representative. A class C pulse train sampled across 2.8 cycles gives wildly noisy
mean values; 50 cycles is plenty.

For 14.2 MHz: tstop - tstart ≥ ~3.5 µs (50 cycles).

`PA_netlist.cir` had `tran tstep=2.02ns tstop=1.0002ms tstart=1ms`, a **200 ns window
== 2.8 cycles**. Mean/RMS bogus. Bumped tstop to 1.0035 ms (3.5 µs window = 50 cycles).
Now stats are stable to <1 % run-to-run.

### 3. Koren tube model unphysical negative plate current

The 6146B Koren-style SPICE model can produce small negative plate current during the
off-half cycle (a physical tube can't emit electrons from its plate, so this is a model
artifact). It's small enough that it averages to nearly zero across a cycle and barely
affects output power calculations.

**Tried to fix with series diodes** — gave up after the diodes caused multiple cascading
convergence failures (initial-condition stiffness; diode-in-series-with-0V-voltage-source
underdetermined branch). The cure was worse than the disease.

**Conclusion: live with the artifact.** Peak positive plate current (which matters for
tube ratings) is correct regardless; the negative tail just looks ugly on the plot.

### 4. Diode in series with a 0 V voltage source = SPICE pain

Don't put an ideal voltage source (`Vname A B DC 0`, used as a current sense) in series
with a diode. When the diode blocks, the branch current must be 0, but the 0 V source
doesn't constrain current — only voltage. The solver finds the branch underdetermined
and either oscillates or hits "timestep too small."

**If you really need this**, reorder so the diode is BEFORE the 0 V source in the
direction of current flow. Then the diode constrains the current to its forward I-V
curve (or to 0 when blocking), and the 0 V source just measures it.

### 5. The `uic` flag and `.IC` components in QUCS-S

The QUCS-S netlist generator auto-emits `uic` on the `tran` line whenever there are
`.IC` (Initial Voltage) components in the schematic. There's no UI toggle that
overrides this.

`uic` means "skip operating-point analysis; use my `.IC` values to start the transient"
— which is fine for purely linear circuits but **catastrophic for nonlinear devices
that need to find their own bias point** (diodes, tubes near cutoff). The fix is to
remove `.IC` components from the schematic; `.NODESET` components are kept (they're
just OP hints, not fixed values, and don't trigger `uic`).

### 6. Parallel ngspice == real speedup

The sweep tool spawns one ngspice process per swept value, capped at `cpu_count - 1`
workers. On the 32-core dev machine, 27-value sweeps take seconds instead of minutes.

The trade-off vs. running them sequentially: each ngspice loads its own copy of the
6146B/12HG7/MC1496 model libraries. Memory use scales linearly with workers, but for
ngspice's ~20 MB footprint per process, that's nothing.

## Updated/replaced docs

- `cw_envelope_keyer.md` — added Reduced carrier injection + LM7171 post-amp sections
- `20m-leveled-keyed-buffer.md` — VFO pad/LPF sections rewritten; BOM updated; added "PA monitoring and control — design options" section (deferred work)

## Deferred (next session)

- Per-tube grid bias control (DAC + HV op-amp); per-tube grid current sense; ADC protection for cathode-current sense — design options captured in `20m-leveled-keyed-buffer.md`
- Calibration sweep at hardware bring-up to populate the keyer's `s_cal[]` predistortion LUT (deferred to actual hardware bench work — see `cw_envelope_keyer.md`)
- Bring `cw_envelope_keyer.md` LM7171 R_F default in line with R_F = 47 kΩ recommendation (currently the schematic ships with 30 kΩ; analysis says 47 kΩ is the right gain)

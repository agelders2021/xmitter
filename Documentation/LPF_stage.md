# Output LPF Stage — Current State

Five-pole Chebyshev low-pass filter at the 50 Ω output of the rig.
Removes harmonics of the 14.2 MHz carrier (2nd at 28.4 MHz, 3rd at
42.6 MHz, etc.) so emissions land inside the FCC Part 97 mask and
spurious radiation from the antenna is suppressed.

Single-band design for 20 m only; no provision for other bands.
Single-impedance design for 50 Ω only (PA → balun → this LPF → coax
→ external ATU → antenna).

Source of truth: `xmitter_prj/LPF_50ohm_subcircuit.sch`.

## Block diagram

```
[from balun output] ── L1 ──┬── L2 ─── [50 Ω coax → external ATU]
                            │
   C1 ──── GND     C2 ──── GND     C3 ──── GND
   300 pF          450 pF          300 pF
```

CLC-LCLCL topology, 5 reactive elements: C1 shunt → L1 series →
C2 shunt → L2 series → C3 shunt. 50 Ω source (balun output) and
50 Ω load (coax to external ATU). Cutoff frequency ~15 MHz, 5.6 %
above the 14.2 MHz operating frequency.

## Component values

┌──────┬─────────┬──────────────────────────────────────────────┐
│ Ref  │ Value   │ Role                                         │
├──────┼─────────┼──────────────────────────────────────────────┤
│ C1   │ 300 pF  │ Input shunt                                  │
│ L1   │ 540 nH  │ Series inductor (first)                      │
│ C2   │ 450 pF  │ Center shunt                                 │
│ L2   │ 540 nH  │ Series inductor (second)                     │
│ C3   │ 300 pF  │ Output shunt                                 │
└──────┴─────────┴──────────────────────────────────────────────┘

## Design choices

Choices made in the original filter analysis (now inlined here so
this doc is self-contained):

**Filter family**: **Chebyshev with 0.1 dB passband ripple**.
Chosen over Butterworth for steeper rolloff above cutoff. The
0.1 dB ripple is invisible in the passband but buys ~5 dB extra
suppression at the 2nd harmonic compared to a same-order
Butterworth.

**Order**: **5 reactive elements**. Gives ~38 dB at 2× f_c
(28.4 MHz), ~58 dB at 2.84× f_c (42.6 MHz). Higher orders
(7 or 9) increase rolloff but require more parts, tighter
tolerances, and add insertion loss. 5-pole hits the FCC mask
with margin.

**Topology**: **CLC (capacitor input/output)**. Shunt capacitors
at both ends, series inductors between, central shunt capacitor.
Inductor-input (LCL) would give the same response shape but
needs more wound parts and more board area; CLC minimizes
inductors.

**Cutoff**: **15 MHz** (5.6 % above 14.2 MHz). Gives good
passband performance at the operating frequency while still
aggressive on harmonics. Lower cutoff would increase passband
loss; higher cutoff would degrade 2nd-harmonic suppression.

## Inductor build

L1 and L2 both 540 nH single-wound on a toroidal core.

┌─────────────┬─────────────┬─────────────────────────────────┐
│ Core        │ Turns for   │ Notes                           │
│             │ 540 nH      │                                 │
├─────────────┼─────────────┼─────────────────────────────────┤
│ T68-6       │ 11 turns    │ AL ≈ 4.7 nH/t²; 11² × 4.7 =     │
│             │             │ 569 nH (+5.4 %, within tol.)    │
│ T50-6       │ 12 turns    │ AL ≈ 4.0 nH/t²; 12² × 4.0 =     │
│             │             │ 576 nH (+7 %, edge of tolerance)│
└─────────────┴─────────────┴─────────────────────────────────┘

**Use T68-6 + 11 turns + #22 AWG enameled** per the project
single-gauge wire plan. The +5.4 % L tolerance just shifts the
filter cutoff from ~15 MHz to ~14.6 MHz — still above 14.2 MHz,
harmonic suppression unchanged.

Mount L1 and L2 either on perpendicular axes or with ≥ 1"
separation to prevent stray mutual coupling between them.

## Capacitor selection

All three caps see RF voltage and current at 50 W into 50 Ω
(V_rms = 50 V, V_peak = ~71 V). The shunt elements are the
most stressed.

┌──────┬─────────┬───────────────────────────────────────────────┐
│ Ref  │ Value   │ Recommended part                              │
├──────┼─────────┼───────────────────────────────────────────────┤
│ C1   │ 300 pF  │ Silver mica 500 V (CD15/CD19) or NPO/C0G 500V │
│ C2   │ 450 pF  │ Silver mica 500 V (use 470 pF nearest std)    │
│ C3   │ 300 pF  │ Same as C1                                    │
└──────┴─────────┴───────────────────────────────────────────────┘

**Critical**: do NOT use X7R or other Class II ceramic for
these caps. Capacitance changes with applied voltage in Class II
dielectrics, which detunes the filter and adds distortion.
Silver mica or NPO/C0G are the only acceptable choices.

The 500 V rating gives generous margin against the ~71 V peak
operating voltage AND against the standing waves that show up
during external ATU tune-up (see "ATU interaction" below).

## Expected response

From a Monte Carlo tolerance analysis (200 runs, all 5
components varied independently at ±5 %):

┌─────────────────────────┬───────────────────────────────┐
│ Frequency               │ Insertion loss / rejection    │
├─────────────────────────┼───────────────────────────────┤
│ 14.2 MHz (carrier)      │ < 0.3 dB (±0.3 dB spread)     │
│ 28.4 MHz (2nd harmonic) │ 28-38 dB rejection            │
│ 42.6 MHz (3rd harmonic) │ 45-55 dB rejection            │
│ 71 MHz (5th harmonic)   │ 80+ dB rejection              │
└─────────────────────────┴───────────────────────────────┘

The cutoff shift due to ±5 % component tolerance is at most
±500 kHz — well clear of the 14.2 MHz operating frequency.
Stopband variations are a few dB but never threaten the FCC
Part 97 emissions mask (−43 dBc minimum for HF amateur).

For Monte Carlo simulation in ngspice via QUCS-S, use a
`.control` block that wraps `alter` statements around each
component value with `{nominal × (1 + 0.05*(2*rnd-1))}`. The
analysis runs in seconds for 100-200 sweeps.

## Power dissipation

At 50 W input with insertion loss < 0.3 dB:

- Power out of filter: ~46.7 W
- Total filter dissipation: ~3.3 W
- Per inductor (Q-limited): ~1 W
- Per capacitor (ESR-limited, NPO/mica): negligible

T68-6 cores at 1 W dissipation run warm but not hot. No
auxiliary cooling needed.

## ATU interaction

The filter feeds 50 Ω coax to an external ATU. During tune-up,
the ATU presents arbitrary reactances to the filter output
until the ATU's bridge reaches null. The 500 V capacitor
rating provides margin for the standing waves this creates.

Once tuned, the ATU presents 50 Ω to the filter output and the
analysis above applies as designed.

## What is NOT in this stage

- The 6:1 balun is upstream — see `balun_stage.md`
- The external ATU is downstream of this filter and is not part
  of the project build
- The PA's plate tank (which provides additional filtering via
  the tank Q) is upstream — see `PA_stage.md`
- The separate 7-pole Chebyshev LPF on the control board
  (cutoff 17.5 MHz, suppresses Si5351 harmonics) is a different
  filter at a different point in the chain — see
  `vfo_input_stage.md`

## References

- `xmitter_prj/LPF_50ohm_subcircuit.sch` — current simulation
- `Documentation/balun_stage.md` — upstream balun
- `Documentation/PA_stage.md` — upstream PA stage and tank
- `Documentation/vfo_input_stage.md` — upstream control-board
  LPF (different filter, different purpose)

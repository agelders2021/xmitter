# PA Stage — Current State

Push-pull pair of 6146B beam power tetrodes driving a balanced
plate tank at 14.2 MHz. Output 50 W into 300 Ω differential
(then through the 6:1 balun to 50 Ω unbalanced, through the LPF,
through coax to the external ATU).

Source of truth: `xmitter_prj/PA_subcircuit.sch`. Per-tube grid
bias circuit is in `xmitter_prj/grid_bias.sch`; cathode monitor
is in `Documentation/pa_cathode_monitor.md`.

## Block diagram

```
                                        ┌──── +600 V B+ (V_supply)
                                        │
                                       L4 / L5  1.71 µH plate tank
                                       (air-core, self-supporting)
                                        │
                                       L10/L11  1 µH parasitic supp
                                       R14/R15  47 Ω damping
                                        │
                              ┌─────────┴──────┐
[grid from xfmr] → R3 → R4 ── grid          plate ── C12/C13 (tank cap)
                              │  6146B  │
                              │ screen  ── R2 → +200 V (V_SCREEN)
                              │         │       (with C8/C9 bypass)
                              │ cathode ── R1 (10 Ω) → GND
                              │         │       (cathode-current sense)
                              └─────────┘
                              C6 (0.24 pF) → opposite grid (neutralization)

[symmetric: second tube, R7/R8/R5/R6/L5/L11/R15/C7/C13/C10/C11]

Plate tank L4/L5 + variable C12/C13 + link L6 → balun input
```

End to end:

- Each tube grid is driven from the driver output transformer
  secondary half via a 1 kΩ grid stopper (R3 / R7)
- 22 kΩ grid leak (R4 / R8) returns to the firmware-controlled
  bias rail (the OPA454 per-tube bias output)
- Cathode through 10 Ω sense resistor to GND
- Screen fed from +200 V through 220 Ω feed resistor, bypassed
  to GND by 0.01 µF X7R + 100 pF NPO at the screen pin
- Plate through 1 µH air-core parasitic suppressor in parallel
  with a 47 Ω damping resistor
- Plate tank: L4 + L5 (each 1.71 µH air-core, coupled k = 0.75)
  in series across the plate-to-plate path; C12 + C13 (variable,
  10-75 pF/section) tune the tank to 14.2 MHz resonance
- Link winding L6 (2.5 µH air-core, k ≈ 0.80 to plate coils)
  delivers the differential RF to the balun input
- Neutralization caps C6 / C7 (0.24 pF, plate-to-opposite-grid)
  cancel the 6146B's intrinsic Cga

## Component values (per side; lower index = lower tube)

### Grid network

┌──────────┬────────┬─────────────────────────────────────────┐
│ Ref      │ Value  │ Role                                    │
├──────────┼────────┼─────────────────────────────────────────┤
│ R3, R7   │ 1 kΩ   │ Grid stopper                            │
│ R4, R8   │ 22 kΩ  │ Grid leak / bias return                 │
│ C6, C7   │ 0.24pF │ Neutralization, plate → opposite grid   │
└──────────┴────────┴─────────────────────────────────────────┘

### Cathode

┌──────────┬────────┬─────────────────────────────────────────┐
│ Ref      │ Value  │ Role                                    │
├──────────┼────────┼─────────────────────────────────────────┤
│ R1, R5   │ 10 Ω   │ Cathode current sense (1 mV per mA)     │
└──────────┴────────┴─────────────────────────────────────────┘

### Screen path (per tube — two bypass caps each)

┌──────────────┬──────────────────────┬───────────────────────────┐
│ Ref          │ Value                │ Role                      │
├──────────────┼──────────────────────┼───────────────────────────┤
│ R2, R6       │ 220 Ω                │ Screen feed resistor      │
│ C8, C10      │ 0.01 µF X7R ≥ 400 V  │ Screen bypass, low-freq   │
│ C9, C11      │ 100 pF NPO ≥ 500 V   │ Screen bypass, HF         │
│ V_SCREEN     │ +200 V               │ Screen supply             │
└──────────────┴──────────────────────┴───────────────────────────┘

### Plate path (per tube)

┌──────────────┬─────────┬───────────────────────────────────────┐
│ Ref          │ Value   │ Role                                  │
├──────────────┼─────────┼───────────────────────────────────────┤
│ L10, L11     │ 1 µH    │ Parasitic suppressor (air-core)       │
│ R14, R15     │ 47 Ω    │ Parasitic suppressor damping          │
│ L4, L5       │ 1.71 µH │ Plate tank coil (air-core)            │
│ C12, C13     │ ~39 pF  │ Tank cap (variable 10-75 pF/section)  │
│ L6           │ 2.5 µH  │ Link/output winding to balun (k ≈ 0.8)│
│ V_supply     │ +600 V  │ B+ via plate tank center tap          │
└──────────────┴─────────┴───────────────────────────────────────┘

### Output coupling / load

┌──────────┬────────┬─────────────────────────────────────────┐
│ Ref      │ Value  │ Role                                    │
├──────────┼────────┼─────────────────────────────────────────┤
│ R10, R11 │ 1 MΩ   │ Output DC blocking / discharge          │
│ R17      │ 300 Ω  │ Standalone test load (representing balun│
│          │        │ + 50 Ω antenna via 6:1 step-down)       │
└──────────┴────────┴─────────────────────────────────────────┘

## Operating point (validated 2026-06-08)

Two-state bias under firmware control:

┌──────────┬────────┬───────────────────────────────────────────┐
│ State    │ Bias   │ Behavior                                  │
├──────────┼────────┼───────────────────────────────────────────┤
│ IDLE     │ −90 V  │ Deep cutoff, 0 mA plate current, 0 W diss │
│ OPERATE  │ −60 V  │ Shallow class C, ~50 W RF out @ 14.2 MHz  │
└──────────┴────────┴───────────────────────────────────────────┘

Per-tube envelope at OPERATE (V_supply = 600 V, V_SCREEN = 200 V,
R_load = 300 Ω):

┌───────────────────────────────────┬───────────────────────────┐
│ Parameter                         │ Value                     │
├───────────────────────────────────┼───────────────────────────┤
│ V6 drive amplitude (peak)         │ 180 V                     │
│ Output power                      │ 50 W total                │
│ Plate dissipation (per tube)      │ 24 W (5 % under 25 W max) │
│ Peak grid voltage                 │ −150 V (at spec limit)    │
│ Peak plate current per tube       │ 412 mA                    │
│ Average plate current per tube    │ ~66 mA                    │
│ Efficiency                        │ 51 %                      │
└───────────────────────────────────┴───────────────────────────┘

The −150 V peak grid voltage is the binding spec — not plate
dissipation. The two-state bias scheme keeps the rig dramatically
safer than a single-bias design, and IDLE state guarantees zero
standby dissipation.

For derivation, sweep tables, and design history see
`Documentation/2026-06-08-pa-validation.md`.

## Plate tank design

The tank impedance must match the desired load to deliver the
target power. For push-pull, both plate coils couple to the link
winding L6, so the effective mutual inductance is doubled:

```
M_eff = 2 × k × √(L4 × L6)
R_pp = M_eff² × ω² / R_load
```

Currently:

- L4 = L5 = 1.71 µH (plate coils, k4 = 0.75 between them)
- L6 = 2.5 µH (link winding)
- k5 = k6 = 0.80 (each plate coil to link)
- R_load = 300 Ω (after balun, looks like 300 Ω plate-to-plate)
- M_eff = 2 × 0.80 × √(1.71 × 2.5) = 3.30 µH
- Plate-to-plate impedance = ~1642 Ω, matching the design point
  for 50-55 W RF output at η ≈ 51 % efficiency

The tank capacitance C12 + C13 resonates the combined tank
inductance (~5.26 µH effective after L6 loading) at 14.2 MHz.
Simulation value is 39 pF per side; the physical variable cap
covers 10-75 pF per section and tunes against tube and
component tolerances.

## Parasitic suppression

L10 / L11 (1 µH air-core) in parallel with R14 / R15 (47 Ω,
non-inductive) between each plate and the tank node.

At 14.2 MHz, the suppressor impedance is |Z_sup| ≈ 42 Ω —
passes the wanted RF plate current with modest loss. At VHF
(where 6146B internal feedback can drive oscillation), the
inductor's reactance climbs and the resistor damps any
parasitic loop.

## Construction notes — air-core coils required

Toroids are unsuitable for L4, L5, L6. The reasons:

┌──────────────────────────┬──────────────────────────────────────┐
│ Issue                    │ Detail                               │
├──────────────────────────┼──────────────────────────────────────┤
│ Plate-to-chassis voltage │ Up to 925 V peak (600 V DC + 425 V RF│
│ Plate-to-plate RF voltage│ 850 V peak — exceeds magnet wire     │
│                          │ insulation ratings                   │
│ Core losses              │ ~19 A RF circulating current at      │
│                          │ Q = 12; significant heating in any   │
│                          │ core material                        │
│ Q degradation            │ Iron-powder Q ≈ 50-150 vs air-core   │
│                          │ Q ≈ 200-500 at 14.2 MHz              │
└──────────────────────────┴──────────────────────────────────────┘

**Build spec**:

┌────────────────────────┬──────────────────────────────────────┐
│ Coil                   │ Construction                         │
├────────────────────────┼──────────────────────────────────────┤
│ L4 / L5 (1.71 µH each) │ 14-16 AWG silver-plated or bare      │
│                        │ copper. Self-supporting, ~2" dia,    │
│                        │ ~2" long, ~10-12 turns               │
│ L6 (2.5 µH link)       │ 14-16 AWG. Separate coil, concentric │
│                        │ with or adjacent to L4/L5            │
└────────────────────────┴──────────────────────────────────────┘

The plate variable cap (C12 / C13) replaces the fixed
simulation value. Starting range: 10-75 pF per section
(standard transmitting variable). Mount with adequate
spacing from chassis for the ~925 V peak working voltage.

Heavy bare or silver-plated copper for these coils is sourced
separately from the project's #22 AWG enameled magnet-wire
plan — try Westlake Wire, McMaster-Carr, or eBay surplus.

## Neutralization

Cross-coupled neutralization caps C6 / C7 = 0.24 pF, matching
the 6146B's published Cga of 0.24 pF.

- Connect from each plate to the **opposite** grid (cross-coupled)
- Place on the grid side of the stopper resistor (R3 / R7)
- Adjust during alignment for a clean plate-current dip at
  resonance with grid drive removed
- Standard NPO ceramic trimmer caps, or fixed 0.24 pF (rare;
  usually a short PCB overlap or wire stub gives the right value)

## Power dissipation

### Per-tube dissipation budget (OPERATE state)

┌──────────────────┬──────────────────────────┬───────────────────┐
│ Element          │ Calculation              │ Result            │
├──────────────────┼──────────────────────────┼───────────────────┤
│ Heater           │ 6.3 V × 1.25 A           │ 7.9 W             │
│ Plate (avg)      │ V_p × I_p_avg            │ 24 W              │
│ Screen           │ 200 V × ~10 mA           │ ~2 W              │
│ Total per tube   │ plate + screen           │ 26 W (excl heater)│
└──────────────────┴──────────────────────────┴───────────────────┘

6146B rated plate dissipation: 25 W CW. Operating at 24 W per
tube gives ~5 % margin. Bench operation should not exceed this
under sustained key-down. Two-state bias drops standby
dissipation to zero between key-downs.

### Resistor power (worst-case bounds)

┌──────────────┬───────────────────────────┬──────────────────────┐
│ Ref          │ Worst-case P              │ Rating recommendation│
├──────────────┼───────────────────────────┼──────────────────────┤
│ R1, R5 (10Ω) │ I_p² × R = 0.066² × 10    │ 1 W (heat + margin)  │
│              │   = 0.044 W steady-state  │                      │
│ R2, R6 (220Ω)│ I_scrn² × R = 0.022 W     │ 1 W                  │
│ R3, R7 (1kΩ) │ Class-C grid current ≪    │ 1/2 W                │
│ R4, R8 (22k) │ V_bias² / R = ~0.4 mW     │ 1/2 W                │
│ R14, R15(47Ω)│ Negligible at 14 MHz      │ 2 W non-inductive    │
│ R10, R11(1M) │ Negligible                │ 1/4 W                │
└──────────────┴───────────────────────────┴──────────────────────┘

R14 and R15 (parasitic suppressor damping) MUST be
**non-inductive** (carbon composition or metal film), NOT
wirewound — wirewound inductance breaks the whole HF damping
mechanism.

R1 / R5 (cathode sense) at 1 W gives thermal margin during
the brief window between a fault event and the cathode
monitor's hardware trip (~60 µs per `pa_cathode_monitor.md`).
Wirewound is fine here because the resistor is not in the RF
circulating current path.

### Supply currents

┌────────────────┬─────────────────────────┬─────────────────────┐
│ Supply         │ Total draw (OPERATE)    │ Notes               │
├────────────────┼─────────────────────────┼─────────────────────┤
│ +600 V B+      │ 2 × 66 mA = 132 mA avg  │ Peak ~500 mA per    │
│                │                         │ tube during RF      │
│                │                         │ peaks               │
│ +200 V screen  │ 2 × 10 mA = 20 mA       │ Plus margin → 40 mA │
│ Negative bias  │ ~µA via 22 kΩ leak      │ Trivial; rail comes │
│                │                         │ from OPA454 output  │
│ 6.3 V heater   │ 2 × 1.25 A = 2.5 A AC   │ Filament transformer│
└────────────────┴─────────────────────────┴─────────────────────┘

IDLE state draws zero plate and screen current; only nonzero
IDLE draw is the continuous heater current.

## Tube sockets

7-pin "Magnoval" (or B7A) **ceramic** socket for each 6146B.
Ceramic is mandatory — plate dissipation heat-soaks the socket
area, and phenolic sockets char and become resistive after
extended use. Belton VTB9-PT or NOS chassis-mount equivalent.

## Open questions

### Q1 — Per-tube bias control

The hardware bias rail comes from a per-tube OPA454 high-voltage
op-amp (one per tube) driven by a firmware MCP4728 DAC, per
`xmitter_prj/grid_bias.sch` and `Documentation/Grid_Bias_Schematic.pdf`.

The two-state bias scheme (IDLE = −90 V, OPERATE = −60 V) is
firmware-managed; the hardware default rail is set to −90 V
deep cutoff so the tubes are safe even if firmware hangs.
Same fail-safe pattern as the keyer DAC.

Tube-to-tube spread (typically ±2-3 V) is trimmed via the
per-tube DAC during initial alignment.

### Q2 — Bench-time peak grid voltage margin

The 50 W operating point sits at the −150 V grid spec limit
exactly. For continuous operation, firmware should hold
OPERATE bias at **−63 V** instead of −60 V to give ~3 V
cushion against tube spread, supply ripple, and DAC
quantization. Cost: ~1-2 W of output (49 W instead of 50 W).
Recommended per the 2026-06-08 validation doc.

### Q3 — Cathode monitor and fault chain

Documented separately in `Documentation/pa_cathode_monitor.md`.
The 7-layer defensive chain (fuse → series sense R → Schottky
clamp → anti-alias LPF → op-amp buffer → hardware comparator
fast trip → MCU soft trip) gates the HV contactor.

## What is NOT in this stage

- The driver output transformer is upstream — see
  `driver_stage.md` for the T68-6 12+12 / 6+6 bifilar spec
- The 6:1 balun is downstream — see `balun_stage.md`
- The 5-pole LPF is downstream of the balun — see `LPF_stage.md`
- The per-tube grid bias circuit (OPA454 + DAC) lives on the
  PA module board per the PCB partition; full schematic in
  `Documentation/Grid_Bias_Schematic.pdf`
- The cathode-current monitor and fault chain are in
  `Documentation/pa_cathode_monitor.md`

## References

- `xmitter_prj/PA_subcircuit.sch` — current simulation
- `xmitter_prj/6146b_koren.lib` — tube model
- `Documentation/Components/6146b_big.pdf` — RCA 6146B datasheet
- `Documentation/2026-06-08-pa-validation.md` — operating-point
  derivation, sweep results, two-state bias scheme rationale
- `Documentation/Grid_Bias_Schematic.pdf` — per-tube OPA454 bias
- `Documentation/pa_cathode_monitor.md` — fault chain
- `Documentation/driver_stage.md` — upstream driver and output
  transformer
- `Documentation/balun_stage.md` — downstream balun
- `Documentation/LPF_stage.md` — downstream output LPF

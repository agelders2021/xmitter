# Driver Stage — Current State

Push-pull pair of 12HG7 beam pentodes (TV horizontal-sweep tubes,
class A1 grounded-cathode). Takes the differential RF signal from
the control board's LM7171 post-amps and amplifies it to the level
required by the 6146B PA grids via the driver output transformer.

Source of truth: `xmitter_prj/Driver_subcircuit.sch`. Pin order in
the 12HG7 Koren-style model is `A S G K` (plate, screen, grid 1,
cathode) per `xmitter_prj/12hg7_koren.lib`.

## Block diagram

```
                                      ┌──── +275 V (plate)
                                      │
                                     L2 / L4   1 mH plate RFC
                                      │
                                     L1 / L3   1 µH parasitic supp
                                      │
                                  ┌───┴───┐
                                  │ plate │
[in +] → C6 → R1 → R2 → ── grid ──┤ 12HG7 ├── plate ── C5 → [out +]
                          │       │  (1)  │
                          R4      │ scrn ─┼── R3 ── + 150 V (screen)
                          │       │ cath ─┼── GND
                       V11 +3V    └───────┘            (with C2 bypass)
                          │
                          └─ same for upper tube ─ R6, R7, R8, R9
                                                   C2 → C4,  L1 → L3,
                                                   L2 → L4, V1 → V5,
                                                   V2 → V6

[in -] → C7 → R8 → R6 → grid of upper 12HG7 (symmetric)
```

End-to-end signal flow:

- Differential RF input from the control-board LM7171 post-amps
- AC-coupled through C6/C7 (0.01 µF) to each grid
- R1/R8 (100 Ω) provides a low-Z series element at the input
- R2/R6 (1 kΩ) is the grid stopper — kills VHF parasitics in the
  grid lead
- R4/R7 (47 kΩ) returns the grid to the bias voltage V11 = +3 V
- Cathodes grounded
- Screens fed through R3/R9 (100 Ω) from +150 V, bypassed to GND
  by C2/C4 (see component selection — each is two caps in hardware)
- Plates feed through L1/L3 (1 µH parasitic suppressors) and
  L2/L4 (1 mH plate RFCs) to +275 V
- Plate outputs AC-coupled through C5 (0.01 µF) to the
  Driver_output_transformer_subcircuit (T68-6 bifilar 12+12 / 6+6)

## Component values

### Grid path (per tube; lower index = lower tube)

┌────────────┬─────────┬─────────────────────────────────────────┐
│ Ref        │ Value   │ Role                                    │
├────────────┼─────────┼─────────────────────────────────────────┤
│ C6, C7     │ 0.01 µF │ AC coupling, control-board output → grid│
│ R1, R8     │ 100 Ω   │ Series input resistor                   │
│ R2, R6     │ 1 kΩ    │ Grid stopper (parasitic suppression)    │
│ R4, R7     │ 47 kΩ   │ Grid leak / bias return                 │
│ V11        │ +3 V    │ Grid bias supply                        │
└────────────┴─────────┴─────────────────────────────────────────┘

### Screen path (per tube — see C2/C4 split below)

┌────────────┬──────────┬────────────────────────────────────────┐
│ Ref        │ Value    │ Role                                   │
├────────────┼──────────┼────────────────────────────────────────┤
│ R3, R9     │ 100 Ω    │ Screen feed resistor                   │
│ C2, C4     │ see split│ Screen bypass to GND                   │
│ V1, V5     │ +150 V   │ Screen supply (same node in hardware)  │
└────────────┴──────────┴────────────────────────────────────────┘

### Plate path (per tube)

┌────────────┬─────────┬──────────────────────────────────────────┐
│ Ref        │ Value   │ Role                                     │
├────────────┼─────────┼──────────────────────────────────────────┤
│ L1, L3     │ 1 µH    │ Parasitic suppressor in plate lead       │
│ L2, L4     │ 1 mH    │ Plate RFC, feeds DC plate supply         │
│ V2, V6     │ +275 V  │ Plate supply (same node in hardware)     │
│ C5         │ 0.01 µF │ Output coupling, plate → output xfmr     │
└────────────┴─────────┴──────────────────────────────────────────┘

### C2 and C4 are two physical caps each

The simulation models C2 and C4 with the single value 0.01001 µF
(the odd trailing digit is just to give ngspice a distinct number,
the schematic comment reads "0.01001 uF reminds me to use two
caps here"). In hardware, each one expands to a pair of parallel
caps in the standard split-frequency bypass arrangement used on
the 6146B screens too:

┌─────────────┬──────────────────────┬───────────────────────────────┐
│ Hardware ref│ Value                │ Purpose                       │
├─────────────┼──────────────────────┼───────────────────────────────┤
│ C2_LF       │ 0.01 µF X7R ≥ 200 V  │ Low-freq screen bypass        │
│ C2_HF       │ 1 nF NPO ≥ 500 V     │ HF / parasitic screen bypass  │
│ C4_LF       │ 0.01 µF X7R ≥ 200 V  │ Low-freq screen bypass (upper)│
│ C4_HF       │ 1 nF NPO ≥ 500 V     │ HF / parasitic screen bypass  │
└─────────────┴──────────────────────┴───────────────────────────────┘

Four physical capacitors total for the screen-bypass function.
Mount each pair close to the tube socket's screen pin with short
leads — lead inductance is the whole reason for the split.

## Driver output transformer (T68-6)

The driver plate outputs connect to the 6146B PA grids through a
push-pull output transformer. The transformer simulation lives in
`xmitter_prj/Driver_output_transformer_subcircuit.sch`; the
component spec below is the build spec.

**Core**: T68-6 iron powder (yellow, type 6, AL ≈ 11.5 nH/t²,
useful to ~50 MHz)

**Windings** (all on the same core, bifilar pairs):

┌────────────────────┬──────────────┬──────────┬───────────────────────────┐
│ Winding            │ Turns        │ L (each) │ Connection                │
├────────────────────┼──────────────┼──────────┼───────────────────────────┤
│ Primary half A     │ 12 t bifilar │ 6.3 µH   │ Plate of lower tube       │
│ Primary half B     │ 12 t bifilar │ 6.3 µH   │ Plate of upper tube       │
│ Primary CT         │ —            │ —        │ B+ via plate RFC          │
│ Secondary half A   │ 6 t bifilar  │ 1.5 µH   │ Grid 1 of 6146B (lower)   │
│ Secondary half B   │ 6 t bifilar  │ 1.5 µH   │ Grid 2 of 6146B (upper)   │
│ Secondary CT       │ —            │ —        │ PA grid bias return       │
└────────────────────┴──────────────┴──────────┴───────────────────────────┘

**Turns ratio** (primary : secondary): 2 : 1 (voltage step-down)
**Coupling**: K = 0.95 conservative; well-wound bifilar achieves 0.95-0.99
**Total turns on core**: 36 (12+12 primary, 6+6 secondary)
**Wire**: #22 AWG enameled per the project single-gauge wire plan
**Core power**: ~100-200 mW; far below T68-6 saturation/loss limits

**Winding technique**:

- Wind the primary first: 24 turns of two parallel wires (bifilar)
  spread evenly around the core, then connect the end of wire A
  to the start of wire B to form the center tap. The start and
  finish of the pair are the two plate connections.
- Wind the secondary over the primary (or interleaved with it):
  12 turns bifilar, same center-tap technique. Start and finish
  are the two PA grid connections.
- Uniform distribution around the toroid improves coupling and
  symmetry between the two halves.

**History note**: this spec was originally derived for the earlier
6CL6 driver design (see `legacy/driver_output_xfmr_analysis.md`
for the full derivation and the 6CL6-specific signal-level
analysis). The same T68-6 transformer applies unchanged to the
current 12HG7 driver because the secondary load (6146B grids) and
the operating frequency (14.2 MHz) are both unchanged. Only the
upstream driver tube changed.

## Power dissipation

Estimates below assume class A1 operation at I_plate ≈ 40 mA per
tube with the simulated supplies. Bench measurement at the actual
operating point will refine these.

### Per-tube tube dissipation

┌─────────────────┬──────────────────────────────┬────────────────┐
│ Element         │ Calculation                  │ Result         │
├─────────────────┼──────────────────────────────┼────────────────┤
│ Heater          │ 6.3 V × 0.9 A                │ 5.67 W         │
│ Plate           │ 275 V × 40 mA                │ 11.0 W         │
│ Screen          │ 150 V × 4 mA                 │ 0.60 W         │
│ Total per tube  │ sum (less heater, internal) │ 11.6 W         │
└─────────────────┴──────────────────────────────┴────────────────┘

12HG7 rated plate dissipation is **17.5 W**; current operating
point sits at ~63 % of rating, ~37 % margin. Rated screen
dissipation is **3.5 W**; sits at ~17 % of rating, comfortable.

### Resistor power dissipation

All driver-stage resistors run well under their typical 1/4 W
ratings. Numbers below are bounding estimates:

┌──────────────┬─────────────────────────┬──────────────────────┐
│ Ref          │ Worst-case P            │ Rating recommendation│
├──────────────┼─────────────────────────┼──────────────────────┤
│ R2, R6 (1k)  │ I_grid² × R, negligible │ 1/4 W carbon film    │
│ R1, R8 (100) │ V_drive² / R, ~0.01 W   │ 1/4 W carbon film    │
│ R3, R9 (100) │ I_scrn² × R, ~1.6 mW    │ 1/4 W carbon film    │
│ R4, R7 (47k) │ V_bias² / R, ~0.2 µW    │ 1/4 W carbon film    │
└──────────────┴─────────────────────────┴──────────────────────┘

### Supply currents needed

┌────────────────┬─────────────────────────┬──────────────────────┐
│ Supply         │ Total draw              │ Notes                │
├────────────────┼─────────────────────────┼──────────────────────┤
│ +275 V plate   │ 2 × 40 mA = 80 mA       │ Plus margin → 100 mA │
│ +150 V screen  │ 2 × 4 mA = 8 mA         │ Plus margin → 15 mA  │
│ +3 V grid bias │ ~ µA, trivial           │ Easy LDO from +12 V  │
│ 6.3 V heater   │ 2 × 0.9 A = 1.8 A AC    │ Filament transformer │
└────────────────┴─────────────────────────┴──────────────────────┘

These get folded into the overall supply spec in
`2026-06-16-supply-and-pcb-strategy.md`; the driver currents are
already included in the T3 driver/LV transformer secondary.

## Component selection notes

### Resistors

- All driver-stage resistors: 1/4 W carbon film is fine
- **Do NOT use wirewound** for the grid stoppers (R2, R6) or the
  plate parasitic suppressor inductors' damping resistors —
  wirewound inductance breaks the HF stability story
- Carbon composition is fine if available; metal film also fine

### Capacitors

- **C6, C7** (grid coupling, 0.01 µF): 100 V X7R ceramic, no
  special requirements
- **C2_LF, C4_LF** (screen bypass LF, 0.01 µF): 200 V X7R ceramic
  or polypropylene film. Sees screen-voltage transients during
  key-down dynamics.
- **C2_HF, C4_HF** (screen bypass HF, 1 nF): 500 V NPO ceramic.
  Low ESL is critical — short leads, mount directly at the screen
  pin.
- **C5** (plate output coupling, 0.01 µF): **HIGH VOLTAGE PART.**
  Sees the full plate swing of ~550 V peak-to-peak (275 V supply
  ± 275 V RF swing in class A1). Spec at **1 kV minimum**, either
  NPO ceramic, silver mica, or polypropylene film with HV rating.
  Do not skimp here — a shorted coupling cap puts +275 V on the
  output transformer primary.

### Inductors

- **L1, L3** (1 µH parasitic suppressor): air-wound on a small
  form, or a ferrite-bead-on-wire equivalent. Low Q is fine; the
  purpose is damping VHF parasitics in the plate lead, not
  efficient RF transfer. ~50-100 mA rating.
- **L2, L4** (1 mH plate RFC): must handle plate DC (≥ 50 mA per
  tube) with self-resonant frequency well above 14 MHz. Hammond
  1532-style molded RFC works; air-core honeycomb-wound also
  fine. Verify SRF > 20 MHz on the chosen part.

### Sockets

- 9-pin noval (B9A) tube socket for each 12HG7
- Ceramic preferred over phenolic for sustained heat from the
  plate dissipation
- Belton VT9-PT or similar

## Open questions

### Q1 — Grid bias polarity

The simulation has V11 = **+3 V** as the grid bias. For a
grounded-cathode pentode in class A1 this is unusual — grid bias
is typically 0 V or slightly negative to keep the tube out of
grid-current operation. Verify against design intent during
bench bring-up. If the +3 V is a sim convenience rather than
the design value, replace with 0 V (grid leak to ground) or a
small negative bias from the −105 V rail via a divider.

### Q2 — Plate supply voltage tolerance

Plate dissipation calculation assumes V_p = 275 V exactly. If the
T3 driver transformer secondary plus rectifier delivers more
(e.g., 300 V no-load), plate dissipation scales linearly with the
voltage difference. Recheck at the actual measured supply
voltage during bring-up.

### Q3 — Heater wiring (series vs parallel)

12HG7 heater is 6.3 V at 0.9 A per tube. Both tubes can run on
the shared 6.3 V filament winding in parallel (1.8 A total) per
the supply doc, OR series-wired for 12.6 V at 0.9 A. The PA also
uses 6.3 V heaters — parallel wiring matches the rest of the
project. No reason to deviate.

## What is NOT in this stage

- The 6146B PA grids are downstream and live on the PA board.
  The driver output transformer (specified above) is the
  interface between the driver-board plates and the PA-board grids.
- Differential RF input comes from the control board's LM7171
  post-amps, AC-coupled — see `vfo_input_stage.md` for the
  upstream chain

## References

- `xmitter_prj/Driver_subcircuit.sch` — current simulation
- `xmitter_prj/12hg7_koren.lib` — tube model
- `Documentation/Components/12HG7.pdf` — RCA 12HG7 datasheet
- `Documentation/vfo_input_stage.md` — upstream signal chain
- `Documentation/legacy/driver_output_xfmr_analysis.md` — original
  6CL6-driver analysis from which the T68-6 transformer spec was
  derived (historical; the transformer spec itself is current and
  is in the section above)
- `Documentation/2026-06-08-pa-validation.md` — overall design
  history
- `Documentation/2026-06-16-supply-and-pcb-strategy.md` — supply
  rail spec (driver draws are folded in)

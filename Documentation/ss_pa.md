# Solid-State PA Board — Current State

10 W QRP class-AB push-pull PA at 14 MHz, running from the 13.8 V shack
supply. Replaces the shelved tube PA (see `PA_stage.md` for historical
reference). Topology adapted from the QRP Labs 10 W Linear kit —
output stage only; the kit's driver stage is omitted because the
analog board's LM7171 PP already provides balanced differential drive.

Source of truth: `KiCAD/ss_pa/`. Started 2026-10-09.

## Design intent at a glance

- Push-pull IRF510 pair in class-AB, Idq ≈ 125 mA per FET
- Drive: differential +RF / −RF from LM7171 push-pull on analog board,
  AC-coupled directly into the gate network (no input transformer)
- Drain supply: +13.8 V shack supply direct, large bulk electrolytic
  at board entry for keying stiffness; no on-board LDO or buck
- Bias control: software (MCP4728 VA/VB → DAC outputs `Bias_A_Raw` and
  `Bias_B_Raw` fed to this board over the umbilical). Firmware zeros
  the DACs during RX — no hardware TX_ENABLE / PMOS gate
- Source current sensing (per FET) for closed-loop bias servo,
  overcurrent protection, and tune-up diagnostics
- Hardware overcurrent latch on this board shuts down bias
  independently of firmware
- 4-band LPF lives on this same board (not the analog board) so
  high-current RF never traverses the umbilical

## Hierarchical sheet layout

- `ss_pa.kicad_sch` — root; references three sub-sheets
- `pa_stage.kicad_sch` — PA core (populated as of 2026-10-10):
  push-pull FETs, drain-feed xfmr, output xfmr, bias network per
  FET, drain-gate feedback per FET, input DC-blocks, bulk cap,
  source-sense resistors
- `lpf.kicad_sch` — 4-band low-pass filter bank (skeleton, to be
  migrated from the analog project)
- `fault_shutdown.kicad_sch` — overcurrent latch (skeleton as of
  2026-10-11, spec pinned, population pending)

## Signal interface

### To / from analog board — RJ45 umbilical (Cat5e, shielded)

Pin mapping chosen so that every signal that benefits from a GND
return gets one via a natural T568B twisted pair (pins 3-6 are the
green pair, not adjacent on the connector but physically twisted):

- Pin 1 — `Source_Sense_A` (orange pair, paired with GND on pin 2)
- Pin 2 — GND
- Pin 3 — `FAULT` (green pair, paired with GND on pin 6)
- Pin 4 — `Source_Sense_B` (blue pair, paired with GND on pin 5)
- Pin 5 — GND
- Pin 6 — GND
- Pin 7 — `Bias_A_Raw` (brown pair, two signals sharing one pair —
  OK because bias is low-impedance DC from the DAC)
- Pin 8 — `Bias_B_Raw`

Shield grounded at the PA-board end only (one-end-only termination
to avoid ground loops).

### Power — screw terminal

- J2 pin 1 — `+13.8V` (shack supply, direct)
- J2 pin 2 — GND

### RF — coax connectors

- J3 — RF input from LM7171 +RF output (center) + GND (shield)
- J4 — RF input from LM7171 −RF output (center) + GND (shield)
- J1 — RF output to antenna / dummy load / separate SWR meter

## Component inventory — pa_stage sheet (populated)

### Push-pull core

- `Q3`, `Q4` — IRF510 (TO-220, dot pins 2 & 3 of T2 per KiCad
  Transformer_1P_1S convention). Pinout G=1, D=2 (also metal tab),
  S=3. Custom symbol in `xmitter:IRF510`; KiCad stock libs don't
  ship an IRF510

### Transformers

- `T1` — output transformer, BN43-202 binocular ferrite, 2:3 turns.
  Primary across drains, secondary single-ended to J1
- `T2` — drain feed, T50-43 powdered iron, bifilar wound. In the
  schematic, pins 1 & 4 tie together to form the CT (connects to
  +13.8 V); pins 2 & 3 go to Q4 and Q3 drains respectively. Gives
  `V(Q3_D) + V(Q4_D) = 2 × V_CT`, which is proper push-pull

### Supply decoupling (at J2 power entry)

- `C6` — 4700 µF 25 V electrolytic, radial THT, polarity: pin 1 (+)
  at +13.8 V, pin 2 (−) at GND. Sized for ~210 mV droop during a
  1 A keying step (10 W PA full-RF step)
- `C1`, `C2` — 1 µF ceramic HF bypass pair, between +13.8 V and GND
- No RFC between +13.8 V and the T2 CT. Matches the QRP Labs kit —
  the kit's L201 is a supply-input RFC at the board edge, not a
  dedicated drain-feed choke

### Snubber

- `C3` — 33 pF C0G across the drain-to-drain primary of T1, damping

### Per-FET gate bias feed (mirrored A ↔ B)

- Bias enters as `Bias_A` / `Bias_B` global labels (will come from
  the fault_shutdown sheet once that is populated — until then,
  tie directly to `Bias_A_Raw` / `Bias_B_Raw` from the umbilical)
- `R8` / `R7` — 47 Ω series damping from bias feed
- `C10` / `C9` — 0.1 µF decoupling at the post-R8/R7 junction to GND
- `L4` / `L3` — 1 µH RFC between the junction and the IRF510 gate

### Per-FET drain-gate feedback

- `C8` / `C7` — 0.1 µF coupling cap
- `R6` / `R5` — 220 Ω
- `L2` / `L1` — 1 µH
- All three in series from drain back to gate. Provides linearity,
  gain-flattening across HF, and stability

### RF input DC-blocks

- `C5` — 0.1 µF between J3 center (+RF from LM7171) and Q3 gate
- `C4` — 0.1 µF between J4 center (−RF from LM7171) and Q4 gate

### Source current sense (per FET)

- Q3 source → `R1` ∥ `R2` (0.22 Ω each, parallel = 0.11 Ω) → GND
- Q4 source → `R3` ∥ `R4` (0.22 Ω each, parallel = 0.11 Ω) → GND
- `Source_Sense_A` tapped at Q3 source
- `Source_Sense_B` tapped at Q4 source
- AC bypass across each parallel pair planned at layout time
  (0.1 µF X7R + 100 pF C0G, short lead, component-side)

## Component inventory — fault_shutdown sheet (planned, not yet populated)

Hardware overcurrent latch that shuts down bias when either FET's
source current exceeds a threshold, independently of firmware:

- `U1` — LM393 dual comparator, powered from +13.8 V on the PA
  board (saves running +5 V across the umbilical)
- `D2` — 1N4728A (3.3 V zener) + bias resistor, forms a stable
  reference regardless of 13.8 V droops
- Divider from the zener node sets threshold at ~300 mV (trips at
  ~2.7 A per FET through the 0.11 Ω sense R; 4.5× the ~600 mA DC
  average at full-RF normal operation)
- Positive feedback (R12 / R13, 10 kΩ) from each LM393 output
  back to its V+ input latches the comparator in the HIGH state
  once tripped. No flip-flop needed
- Two LM393 outputs wire-OR into a single `FAULT` bus (open-drain
  on the PA board — no local pullup, relies on the Metro's
  internal pullup on the far end at 3.3 V, which is Metro-input-safe)
- `Q5`, `Q6` — 2N7000 (one per bias line). Gate = FAULT; drain
  shorts `Bias_A` / `Bias_B` to GND when latched; source to GND
- `R16`, `R17` — 1 kΩ series between `Bias_A_Raw` / `Bias_B_Raw`
  (DAC side) and `Bias_A` / `Bias_B` (PA stage side). Limits the
  current the Q5/Q6 short can draw from the DAC output
- `SW1` — momentary SPST pushbutton; press to clear a latched
  fault. Pulls `FAULT` bus to GND; if sense is below threshold the
  latch stays low on release
- `D1` + `R18` — fault indicator LED

Response time end-to-end: <1 µs from Source_Sense exceeding
threshold to IRF510 gates collapsing to 0 V.

## Operating point and design math

### Current estimates (10 W, 60% efficiency)

- Total DC input: 10 W / 0.6 ≈ 17 W → 17 / 13.8 ≈ 1.2 A
- DC average per FET: ~0.6 A
- Source-sense voltage per FET at full RF: 0.6 × 0.11 Ω ≈ 66 mV
- Overcurrent trip threshold: 300 mV → ~2.7 A per FET (4.5×
  margin against normal full-RF current)
- Bias Idq ≈ 125 mA per FET → 14 mV at source sense (well below
  threshold)

### Gate drive capability

- IRF510 Ciss ≈ 180 pF
- Peak gate current at 10 Vpp drive, 14 MHz: 180 pF × 5 V × 2π ×
  14 MHz ≈ 79 mA — comfortably within LM7171's ~125 mA source
- Gate network parallel LC resonance: 1 µH ∥ 180 pF ≈ 12 MHz.
  Close to operating frequency; the 47 Ω series damps it. Standard
  kit behavior — not a defect, but worth knowing if gain anomalies
  appear at band edges

### Supply droop under keying

- Keying step: Idq → full RF ≈ 1 A step
- 4700 µF bulk holds that step with ~210 mV droop for ~1 ms
  (typical shack-supply recovery time)
- No LDO needed; keying click-attack softening from this droop
  is sub-perceptual for CW

## Pending

- Populate `fault_shutdown.kicad_sch` with the components spec'd
  above
- Populate `lpf.kicad_sch` by migrating the 4-band LPF bank out
  of `KiCAD/analog/` (and removing it from there)
- Add RJ45 umbilical connector on the pa_stage (or a new interface
  sub-sheet) and wire `Bias_A_Raw`, `Bias_B_Raw`, `Source_Sense_A`,
  `Source_Sense_B`, `FAULT`, GND pins
- Add corresponding RJ45 jack on the analog board, with firmware
  wiring to MCP4728 DAC outputs for bias and Metro ADC pins
  A0, A1 for the sense signals
- AC bypass caps across the source-sense resistor pairs (0.1 µF
  X7R + 100 pF C0G, placed at layout time)
- Analog board must be re-labeled: `Bias_A` / `Bias_B` DAC
  outputs will become `Bias_A_Raw` / `Bias_B_Raw` once this
  board's fault_shutdown is in place (the "unraw" names are the
  post-protection outputs on the PA board)
- PCB layout for the ss_pa board — mounting holes and board-edge
  connectors first per project convention
- IRF510 heatsinking: TO-220 metal tab is the drain. Isolating
  silicone pad required for case-to-heatsink; thermal design per
  layout pass

## References

- `Documentation/QRP_Examples/10W PA.pdf` — kit output-stage schematic
  (one page, the primary reference). User's build approach: use the
  kit circuit verbatim from C205/C206 onward
- `Documentation/QRP_Examples/PA_Assembly_200.pdf` — full 28-page
  QRP Labs 10 W Linear PA assembly manual, Rev 3 (2018). Has
  transformer winding specs and BOM for the kit as a build reference
- `Documentation/QRP_Examples/pa_assembly_LT.pdf` — related 5 W kit
  with envelope shaping (informational)
- `KiCAD/ss_pa/` — schematic + PCB
- `KiCAD/xmitter.kicad_sym` — contains the `IRF510` and `+13.8V`
  symbols added for this board
- `Documentation/i2c_bus.md` — MCP4728 address map (0x67)
- `Documentation/PA_stage.md` — HISTORICAL shelved tube PA (6146B
  push-pull) kept for reference in case the SS PA proves
  insufficient

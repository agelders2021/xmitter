# Solid-State PA Board — Current State

10 W QRP class-AB push-pull PA at 14 MHz, running from the 13.8 V shack
supply. **This is the active PA for the project.** Topology adapted
from the QRP Labs 10 W Linear kit — output stage only; the kit's
driver stage is omitted because the analog board's LM7171 PP already
provides balanced differential drive.

**Not retired, kept as potential future upgrade**: the vacuum-tube
high-power path (push-pull 6146B PA, 12HG7 driver, OPA454 grid bias
generator, cathode monitor failsafe chain, HV supply) remains drawn
on the analog board with its output connectors (J17/J18/J19 cathode
sense, J23/J24 grid control) marked DNP. Those signals exist
electrically but aren't wired out. If a tube PA is added later as
a high-power upgrade: un-DNP those connectors, build the external
bias/sense cables, bring up the `KiCAD/bias/` and `KiCAD/power/`
boards (currently drawn but not fabricated), and firmware adds the
`grid_bias_dac.cpp` / `cathode_monitor.cpp` modules per
`Documentation/cw_envelope_keyer.md`. See `PA_stage.md` and
`grid_bias.md` for the tube PA design.

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

Pin mapping chosen so that every signal that benefits from a return
gets one via a natural T568B twisted pair (pins 3-6 are the green
pair, not adjacent on the connector but physically twisted). The
green pair carries `FAULT_N` paired with `+3.3V` — the +3.3V rail
acts as a quiet return for noise-rejection purposes (bypassed to
GND on both board ends):

- Pin 1 — `Source_Sense_A` (orange pair, paired with GND on pin 2)
- Pin 2 — GND
- Pin 3 — `FAULT_N` (green pair, paired with +3.3V on pin 6).
  Active-low — normal state is +3.3V (via local pullup), latched
  fault pulls to 0V. Also powers the V_REF divider on the PA board
  (see fault_shutdown section)
- Pin 4 — `Source_Sense_B` (blue pair, paired with GND on pin 5)
- Pin 5 — GND
- Pin 6 — `+3.3V` from analog board regulator. Powers LM393, U2
  CD74HC4066, and the pullup/divider in fault_shutdown
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

- `L5` — 12 µH RFC (5-6 turns on FT50-43 ferrite toroid), in series
  between J2 pin 1 and the +13.8 V bus. L201-equivalent — filters
  the shack supply input, isolates the PA board's RF switching
  currents from the shack bus. Everything downstream (bulk,
  bypass, T2 CT) sits on the post-L5 node.
- `C6` — 4700 µF 25 V electrolytic, radial THT, polarity: pin 1 (+)
  at +13.8 V, pin 2 (−) at GND. Sized for ~210 mV droop during a
  1 A keying step (10 W PA full-RF step)
- `C1`, `C2` — 1 µF ceramic HF bypass pair, between +13.8 V and GND
- No separate RFC between +13.8 V and T2 CT. T2 CT connects
  directly to the +13.8 V bus (downstream of L5), matching the QRP
  Labs kit's layout — the kit's L201 is a supply-input RFC at the
  board edge, not a dedicated drain-feed choke, and ours plays the
  same role

### Snubber

- `C3` — 33 pF C0G across the drain-to-drain primary of T1, damping

### Per-FET gate bias feed (mirrored A ↔ B)

- Bias enters as `Bias_A` / `Bias_B` global labels — these come
  from the fault_shutdown sheet (post-protection outputs of the
  CD74HC4066 series-pass switches, which pass `Bias_X_Raw` from
  the umbilical through to `Bias_X` when `FAULT_N` is HIGH)
- Bias_A → Q3 gate chain, Bias_B → Q4 gate chain. (Note: A/B
  naming is a wiring convention; both chains are electrically
  identical, and A/B always refers to the same FET consistently
  across Bias, Source_Sense, and feedback paths.)
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

## Component inventory — fault_shutdown sheet (populated)

Hardware overcurrent latch that shuts down bias when either FET's
source current exceeds a threshold, independently of firmware.
**`FAULT_N` is active low: +3.3 V = normal, 0 V = latched fault.**

### Comparator and reference

- `U1` — LM393 dual comparator, powered from +3.3 V (comes in on
  RJ45 pin 6 from the analog board regulator). Open-collector
  outputs on pins 1 and 7 wire-OR'd into the `FAULT_N` bus
- `C14` — 0.1 µF ceramic bypass across U1's +3.3 V ↔ GND
- Both comparator inputs wired as: `V+` = V_REF, `V−` = Source_Sense
  for its channel. Normal (sense < V_REF) → output open → pullup
  takes FAULT_N HIGH. Fault (sense > V_REF) → output pulls LOW
- `R9` — 4.7 kΩ pullup on `FAULT_N` to +3.3 V. Wire-OR topology:
  either channel pulling LOW triggers fault (true OR of two fault
  sources, which is what we want)

### Self-latching V_REF divider — the clever bit

- `R11` (100 kΩ) + `R10` (10 kΩ) divider, powered **from the
  FAULT_N bus**, generates V_REF for both comparator V+ inputs
- Normal state: FAULT_N ≈ 3.165 V (slightly below rail because the
  divider loads the pullup) → V_REF = 3.165 × 10/110 ≈ **288 mV**
  (trip threshold)
- Fault state: FAULT_N = 0 V → V_REF = 0 V → V+ = 0 and V− > 0
  (even leakage keeps V− above 0) → comparator stays LOW →
  **latched by circuit topology, no flip-flop needed**
- Divider impedance (110 kΩ) chosen to be ≥ 10× the pullup (4.7 kΩ)
  so FAULT_N normal voltage stays near +3.3 V

### Power-on reset — avoids needing button press at every boot

- `C12` (1 µF) + `D1` (1N4148, cathode toward V_REF) between
  +3.3 V and V_REF. As +3.3 V rises during power-on, C12 couples
  the rise through D1 to pump V_REF briefly up to ~2.6 V → V+ >
  V− → comparator defaults HIGH → FAULT_N settles HIGH via pullup
  → V_REF settles to its 288 mV steady state via the divider
- After startup D1 is reverse-biased (anode ≈ 988 mV, cathode at
  288 mV, cathode > anode − V_D). C12 holds its charge, doesn't
  interfere with latching when a real fault occurs

### Reset button

- `J5` — 2-pin screw terminal. Pin 1 → +3.3 V, pin 2 → V_REF.
  External momentary pushbutton wires to the screw terminals.
  Pressing shorts +3.3 V to V_REF, forcing V+ > V− → comparator
  un-trips → pullup takes FAULT_N back to +3.3 V → divider resumes
  normal operation. Latch cleared if fault condition no longer
  present

### Noise suppression

- `C11` (0.01 µF) ceramic bypass on FAULT_N bus to GND —
  suppresses noise pickup on the fault line (which runs on an RJ45
  pair back to the analog board)

### Bias-line series switches

- `U2` — CD74HC4066 quad bilateral analog switch (PDIP-14 TH),
  custom symbol `xmitter:CD74HC4066`. Powered from +3.3 V
- `C15` — 0.1 µF ceramic bypass across U2's +3.3 V ↔ GND
- Switch 1: pin 1 (Bias_A_Raw) ↔ pin 2 (Bias_A), control = pin 13
  (1E) → tied to FAULT_N
- Switch 2: pin 4 (Bias_B_Raw) ↔ pin 3 (Bias_B), control = pin 5
  (2E) → tied to FAULT_N
- Switches 3 and 4 unused — their I/O pins (pins 8-11) and
  control pins (pins 6, 12) tied to GND
- CD74HC4066 enable is active HIGH: FAULT_N = +3.3 V → switch
  closed → bias passes. FAULT_N = 0 V → switch open → bias blocked.
  Direct polarity match with the `FAULT_N` active-low scheme

### RJ45 umbilical connector

- `J7` — Amphenol RJE1D-188 shielded 8P8C. Pins per the T568B
  assignment in the Signal Interface section above. Shield (SH
  terminal) tied to GND on the PA-board end

### Why series-pass (not shunt-to-GND)

Earlier design (not used) had 2N7000 N-channel MOSFETs shunting
`Bias_A/B` to GND when fault asserted, with 1 kΩ series resistors
protecting the DAC output. That worked but loaded the MCP4728 DAC
output with ~5 mA continuously during a latched fault (near the
chip's spec limit). The CD74HC4066 series-pass approach fully
isolates the DAC from the gate network when latched — zero DAC
loading. Also cleaner polarity match (switch native "HIGH enable"
matches FAULT_N active-low scheme without needing an inverter).

### Response time

End-to-end: <1 µs from Source_Sense exceeding V_REF to IRF510 gates
collapsing to 0 V (comparator transition + CD74HC4066 open +
gate-network discharge through R7/R8 series resistance into any
stray C).

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

- Populate `lpf.kicad_sch` by migrating the 4-band LPF bank out
  of `KiCAD/analog/` (and removing it from there)
- Add corresponding RJ45 jack on the analog board, with firmware
  wiring: MCP4728 VA/VB → `Bias_A_Raw`/`Bias_B_Raw`; Metro ADC
  pins → `Source_Sense_A` (A0), `Source_Sense_B` (A1), `FAULT_N`
  (A2); analog board +3.3V rail → RJ45 pin 6
- Rename `Bias_A`/`Bias_B` DAC output global labels on the analog
  board to `Bias_A_Raw`/`Bias_B_Raw` to match the PA-board side
  (the "unraw" names are the post-protection outputs on the PA
  board, downstream of the CD74HC4066)
- AC bypass caps across the source-sense resistor pairs (0.1 µF
  X7R + 100 pF C0G, placed at layout time)
- PCB layout for the ss_pa board — mounting holes and board-edge
  connectors first per project convention
- IRF510 heatsinking: TO-220 metal tab is the drain. Isolating
  silicone pad required for case-to-heatsink; thermal design per
  layout pass
- **Wide +13.8V traces on both analog and ss_pa boards.** Rail
  carries up to ~1.5 A continuous at full RF (10 W / 60% eff /
  13.8 V). Target ≥ 1.5 mm (60 mil) trace width at 2 oz copper
  for < 10 °C rise, or ≥ 2.5 mm (100 mil) at 1 oz. Applies to:
  the entire path through analog's K6 heartbeat-safety relay (from
  shack supply input, through K6 contacts, to J33) and the entire
  path on ss_pa from J2 through L5 to the +13.8V bus (C6 bulk, T2
  CT, and bypass caps). The L5-to-T2-CT trace also sees the switched
  drain current of the push-pull pair (DC average ~1 A, with
  current ripple at the RF rate smoothed by C6).
- Firmware: boot-time read of `FAULT_N` on Metro A2. If LOW
  (latched from previous session), either prompt user to press
  reset button, or optionally pulse a Metro GPIO wired to the
  `V_REF` node (via a series resistor through J5) to auto-clear.
  Also implement periodic BIST — briefly command Bias_X above
  threshold, verify FAULT_N drops, restore normal bias; refuse to
  key down if BIST fails

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
- `KiCAD/xmitter.kicad_sym` — contains the `IRF510`, `+13.8V`,
  and `CD74HC4066` symbols added for this board
- `Documentation/i2c_bus.md` — MCP4728 address map (0x67)
- `Documentation/PA_stage.md` — tube PA design (6146B push-pull);
  the circuitry is retained on the analog board (DNP'd) for a
  potential future high-power upgrade
- `Documentation/grid_bias.md` — OPA454 per-tube grid bias
  generator; same retention status
- `Documentation/pa_cathode_monitor.md` — 7-layer cathode-current
  failsafe chain; same retention status

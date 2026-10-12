# Project-wide schematic audit — 2026-10-11

Deep-dive review of all boards (except tube PA bias board, retained
as a potential future upgrade) to check cross-board signal name
consistency, dangling nets, and other errors that might have been
missed by per-project ERC.

## Status as of 2026-10-12

All critical and moderate findings below have been addressed:

- Finding 1 (FAULT vs FAULT_N rename): **resolved** — user renamed
  on analog and protoshield to match ss_pa's FAULT_N.
- Finding 2 (ENC_INT_CLEAN → R6 → ENC_INT signal path): **resolved**
  — user confirmed R6 (330 Ω) sits between the two labels on
  `arduino.kicad_sch`, with R7 (330 Ω) on protoshield continuing to
  ENC_INT_FINAL at the Metro pin. R6's "on_board no" flag cleared.
- Finding 3 (PA_OUTPUT_LEVEL dead signal): **resolved** — user
  deleted the dangling signal; the MCP4922 VoutA is unused but
  the global label is gone.
- Finding 4 (stale analog.net): **resolved** — netlist re-exported.

**New finding discovered during follow-up (2026-10-12):**
Q11 (2N3904 KeyUp mute transistor) directly shorts MCP4922 VoutB
(`Gate 2` net) to GND without a series resistor. This stresses
the DAC output stage during mute. Fix: add a 1 kΩ series resistor
between U4 pin 10 (VoutB) and the Q11 collector / Q2 pin 2
junction. Current limited to 2 mA max (well under the DAC's 15 mA
short-circuit limit). Bandwidth impact negligible (12 MHz corner
with the DGFET's ~5 pF Ciss, versus ~1 kHz envelope rate).

## Scope

- `KiCAD/analog/` — control board (7 sheets: analog, arduino,
  interface, lpf, power, vfo_complete, dac)
- `KiCAD/ss_pa/` — SS PA board (4 sheets: ss_pa, fault_shutdown,
  lpf, pa_stage)
- `KiCAD/protoshield/` — Metro proto-shield (1 sheet)
- `KiCAD/frontpanel/` — front panel (1 sheet)

Skipped: `KiCAD/bias/` (shelved tube PA, per request),
`KiCAD/.history/`, `KiCAD/power/` (standalone sandbox project).

Audit methodology: Python scripts extracted all global/hierarchical
labels per sheet, cross-referenced inter-board signals, flagged
single-node nets in each flattened netlist, and dumped RJ45 pin
mappings for cable-mate verification. See:

- `tools/_signal_audit.py` — signal inventory per board
- `tools/_dangling_nets.py` — single-node nets in each netlist
- `tools/_rj45_dump.py` — RJ45 pin-to-net dump
- `tools/_power_near_j31.py` — power symbols near analog J31

## CRITICAL findings — need fixing

### 1. `FAULT` vs `FAULT_N` cross-board naming mismatch

Same physical signal, three different name usages across boards:

- ss_pa `fault_shutdown.kicad_sch`: `FAULT_N` (5 instances) — the
  active-low name pinned in the latest design pass (see
  `ss_pa.md` and the `[[project-ss-pa-board]]` memory)
- analog `arduino.kicad_sch`: `FAULT` (1 instance, at J31 pin 3)
- protoshield `protoshield.kicad_sch`: `FAULT` (2 instances)

Analog J31 pin 3 is wired via the RJ45 umbilical cable to ss_pa
J7 pin 3 — so the signal is electrically connected. But the KiCad
per-project nets have different names on each side, which is a
documentation / consistency bug.

**Fix:** rename `FAULT` → `FAULT_N` on both the analog arduino
label and both protoshield labels, so the signal name matches
across all boards.

### 2. Broken signal path — `ENC_INT_CLEAN` to `ENC_INT` disconnect on analog

The analog netlist shows:

- `ENC_INT_CLEAN` has exactly ONE node: `J4-5` (coming in from
  the frontpanel umbilical)
- `ENC_INT` has exactly ONE node: `J9-2` (going out to the
  protoshield / Metro header)

Nothing on the analog board connects the two labels. The encoder
interrupt signal enters from the frontpanel and never reaches the
Metro.

Intended flow:

```
frontpanel ENC_INT_RAW → Schmitt trigger → ENC_INT_CLEAN → J1-5
→ cable → analog J4-5 (ENC_INT_CLEAN) → ??? → analog J9-2 (ENC_INT)
→ cable → protoshield (ENC_INT) → ENC_INT_FINAL → Metro GPIO
```

The ??? is missing. The two labels on analog are different nets
and don't merge.

**Fix:** either delete one label and extend the wire so both
endpoints share a single name, OR rename one label so both use
the same name throughout the analog board.

## MODERATE findings — stale / housekeeping

### 3. `PA_OUTPUT_LEVEL` is a dead signal

Appears once in `analog/dac.kicad_sch` as a global_label (shape
"output"), with zero other references anywhere in the project.
Tube-era leftover — was going to drive the tube PA bias
generator or an ALC loop.

**Options:**

- Delete the DAC output pin wire + label if the MCP4922 channel
  is truly unused
- Repurpose for SS PA ALC / drive-level control
- Leave it alone and track as a known orphan

Not blocking. Just noise.

### 4. `analog.net` is stale

`KiCAD/analog/analog.net` doesn't include `Bias_A_Raw`,
`Bias_B_Raw`, `Source_Sense_A`, `Source_Sense_B`, or `FAULT` —
recent J31 RJ45 wiring additions haven't been exported. Any
BOM / netlist tooling run against this file will miss these nets.

**Fix:** re-run Tools → Generate Netlist in Eeschema after the
above renames.

## VERIFIED CORRECT

### J31 on analog ↔ J7 on ss_pa — pin-for-pin match

- Pin 1 — Source_Sense_A on both
- Pin 2 — GND on both
- Pin 3 — FAULT on analog / FAULT_N on ss_pa (physically connects
  but names mismatch; see critical finding #1)
- Pin 4 — Source_Sense_B on both
- Pin 5 — GND on both
- Pin 6 — +3.3V on both
- Pin 7 — Bias_A_Raw on both
- Pin 8 — Bias_B_Raw on both
- Pin SH — GND on both (one-end-only shield termination intact)

Physical cable will work; only critical finding #1 needs a
schematic rename.

### J4 on analog ↔ J1 on frontpanel — pin-for-pin match

- Pin 1 — SDA
- Pin 2 — SCL
- Pin 3 — MBL_A_P
- Pin 4 — +5V
- Pin 5 — ENC_INT_CLEAN (but see critical finding #2 — this
  signal is stuck on the analog side)
- Pin 6 — MBL_A_N
- Pin 7 — MBL_B_P
- Pin 8 — MBL_B_N
- Pin SH — GND

Clean match.

### DNP tube-era items — correctly set

Analog `arduino.kicad_sch` (16 items):

- `C39, C40, C44` (100nF) — likely bypass caps for I_CATHODE
  sensing on tube cathode monitor path
- `C5` (10µF polarized), `C6` (100nF) — tube-era power / bypass
- `J17, J18, J19` (coax) — I_CATHODE_A/B sense inputs
- `J23, J24` (coax) — GRID_CTL_A/B outputs (per
  `[[project-ss-pa-board]]` memory: kept wired for potential
  tube-amp revival)
- `J8` (2-pin screw terminal) — one more tube-era I/O
- `Q6` (2N7000) — switching MOSFET
- `R5` (0R jumper), `R7` (10K) — associated passives

Analog `vfo_complete.kicad_sch` (2 items):

- `C24` (100nF), `C25` (10µF polarized) — tube driver stage
  decoupling

Protoshield (1 item): `R8` (10K).

Zero DNP on ss_pa and frontpanel — expected, both are new boards
with no legacy content.

### Dangling single-node nets — all benign

Reviewed every 1-node net flagged by `tools/_dangling_nets.py`:

- All `unconnected-(U*-NC-*)` entries are intentional NC pins
  on ICs (unused comparator halves, DAC NC pins, GPIO expander
  unused channels, I2C address/interrupt pins on breakout boards)
- `PCF_P5_SPARE` — intentionally reserved spare pin by name
- Protoshield's `CS_DAC`, `LDAC_4728`, `MOSI`, `SCK` dangling to
  J7/J1 — passthrough connector pins to Metro headers, not errors
- Frontpanel's unconnected I2C address/IRQ pins on PCF8575 /
  encoder breakout — standard for breakout board use with defaults

### Signal mirror / variant families — all intentional

- `MBL_A_N` / `MBL_A_P`, `MBL_B_N` / `MBL_B_P` — RS-422
  differential pairs (positive and negative) for the two MBL-600
  encoder channels
- `RLY_10`, `RLY_15`, `RLY_17`, `RLY_20` — per-band select
  relays, four distinct signals (one per band in the 4-band LPF)
- `/LCD_D0`..`/LCD_D7` — display 8-bit parallel data bus,
  hierarchical nets

### Core signal chains verified intact

**Bias path:**
`analog arduino` (MCP4728 DAC output) → `Bias_A_Raw`/`Bias_B_Raw`
→ `analog J31` pin 7/8 → RJ45 cable → `ss_pa J7` pin 7/8 →
`ss_pa fault_shutdown` (CD74HC4066 series-pass gate) →
post-protection `Bias_A`/`Bias_B` → `ss_pa pa_stage` R7/R8 →
gate network → IRF510 gate. Full chain intact.

**Source sense path:**
`ss_pa pa_stage` Q source → 2× 0.22Ω parallel → `Source_Sense_A`
or `Source_Sense_B` → `ss_pa J7` pin 1/4 → RJ45 cable →
`analog J31` pin 1/4 → analog arduino (passthrough to Metro
header) → protoshield → Metro A0/A1. Full chain intact (names
match on all three boards).

**Fault path (name-mismatched but electrically intact):**
`ss_pa fault_shutdown` (LM393 OC output) → `FAULT_N` →
`ss_pa J7` pin 3 → RJ45 cable → `analog J31` pin 3 →
`FAULT` (on analog) → passthrough → protoshield → `FAULT` →
Metro A2. Signal flows, but name differs across boards (see
critical finding #1).

## Recommended fix priority

1. **Rename `FAULT` → `FAULT_N`** on analog `arduino.kicad_sch`
   (one label) and both labels on protoshield. Trivial KiCad
   right-click → Properties → edit name. Zero functional risk.
2. **Connect `ENC_INT_CLEAN` to `ENC_INT`** on analog. Simplest:
   delete the `ENC_INT_CLEAN` label on analog and extend the wire
   from J4-5 into the existing `ENC_INT` net. Encoder won't work
   without this.
3. **Decide on `PA_OUTPUT_LEVEL`** — keep as reserved, delete, or
   repurpose. Low urgency.
4. **Re-export `analog.net`** after items 1-2 are done so BOM /
   netlist tooling sees the current state.

All fixes are schematic-only — no layout rework needed. After
items 1-2, re-run ERC on analog and protoshield as a final sanity
check (ss_pa and frontpanel ERC are already clean).

## Artifacts

Audit scripts and intermediate reports left in `tools/` for
re-running later:

- `tools/_signal_audit.py` — global-label inventory per board
- `tools/_signal_audit.txt` — last run output
- `tools/_dangling_nets.py` — single-node net finder
- `tools/_dangling_nets.txt` — last run output
- `tools/_rj45_dump.py` — RJ45 pin-to-net mapper
- `tools/_power_near_j31.py` — power symbol locator for a region
- `tools/_trace_signals.py` — specific signal node trace helper

Re-run after schematic edits to verify the fixes land cleanly.

# xmitter project — Claude Code project instructions

20 m CW transmitter. **Current design (Rev C, 2026-10 iteration):** DGFET
envelope keyer on the analog board (Si5351 → DGFET with G1=RF, G2=envelope
DAC → Chebyshev LPF → op-amp follower → LM7171 PP inv/non-inv), driving
a full-SS class-AB push-pull output stage (`KiCAD/ss_pa/`, IRF510 pair,
~10 W QRP at 13.8 V). Adafruit Metro ESP32-S3 control. Hardware design in
QUCS-S schematics + KiCad PCBs. ESP-IDF v5.4.4 toolchain installed and
verified on both dev machines (2026-06-12); firmware/ not yet scaffolded.

**Kept as potential future high-power upgrade (not currently built):** the
vacuum-tube high-power path — push-pull 6146B PA, push-pull 12HG7 driver,
OPA454 per-tube grid bias generator, cathode monitor failsafe chain, HV
supply. All related circuitry on the analog board (I_CATHODE sensing,
GRID_CTL_A/B outputs, GRID_BLOCK_CRASH fault signal, bias trimming via
MCP4728 VC/VD) is retained but output connectors (J17/J18/J19/J23/J24)
are marked DNP so the signals exist electrically but aren't wired out
of the board. If a tube PA is ever added later, un-DNP those connectors
and wire the external bias/sense cables. The MC1496 keyer path is NOT
retained — it was retired after Rev A hardware failed and replaced by
the DGFET keyer. See `[[project-revB-topology-pivot]]` memory for the
original pivot history.

This file is read on every session start. Keep it focused on stable project
facts and one-time interactive flows (like fresh-machine onboarding) that
otherwise have nowhere natural to live.

## Directory map

| Directory | What's in it |
|---|---|
| `xmitter_prj/` | QUCS-S schematics (`.sch`) and SPICE libraries (`.lib`) |
| `KiCAD/` | KiCad PCB design files. **Active:** `analog/` (Rev A fabricated 2026-07-14 — MC1496 keyer stage failed; Rev C branch replaced it with DGFET keyer plus RJ45 umbilical to the ss_pa board, awaiting fab), `ss_pa/` (SS PA board — pa_stage + fault_shutdown populated and ERC-clean, lpf sheet pending LPF migration from analog), `frontpanel/` (in development), `protoshield/` (Metro-mounted proto-shield). **Reserved for potential tube-PA upgrade:** `bias/` (OPA454 grid bias generator), `power/` (HV rectifier + filter) — not currently being fabricated. Shared `xmitter.pretty/` footprints and `xmitter.kicad_sym` at `KiCAD/` root, referenced by each project via `${KIPRJMOD}/../`. Reversal recipe in `KiCAD/MULTIBOARD_REVERT.md`. |
| `Documentation/` | Design docs, generated PDFs, sourcing spreadsheets, datasheets |
| `tools/` | Python scripts: sweep_param, gen_*_pdf, gen_parts_list, etc. |
| `firmware/` | ESP-IDF firmware (not yet scaffolded — first task this phase) |

## If the user ever sets up another fresh machine

Both current machines (primary dev + secondary hardware-interface) have
ESP-IDF v5.4.4 installed and verified as of 2026-06-12. If a future
replacement or additional machine needs the toolchain, walk them through
`Documentation/ESP-IDF_Setup_Windows.md` interactively — it's a concise
~125-line reference covering the EIM (ESP-IDF Installation Manager) flow,
the "Activate Anyway" / "Select current ESP-IDF version" wire-up gotchas,
and the path layout.

Verify what's already installed first (`git --version`, `python --version`,
`code --version`) and skip steps that are done. Don't dump the whole doc
at once — one step at a time, verify before moving on.

## Build checklist

`Documentation/build_checklist.md` is the rolling phase-by-phase build list:
items to verify before/after each phase, plus long-lead items to order while
working on the current phase. Edit it as a `- [ ]` / `- [x]` checklist; keep
finished items in place as history.

## Current focus

Rev C branch — SS PA board design in progress, pivoted 2026-09-29 from
tube PA (Rev B tag was the intermediate state after the DGFET keyer
swap but before SS PA started).

**Analog control board (`KiCAD/analog/`):** Rev A fabricated 2026-07-14
(JLCPCB Y2-13077341A) — the MC1496 balanced-modulator keyer stage did
not work on the built board (minimal output, unclean RF, suspected
feedback path in the balance-trim network). Rev C removed
`buffer_keyer.kicad_sch` entirely and replaced the keyer with a DGFET
(dual-gate FET) VCA: G1 receives RF from Si5351, G2 receives the
envelope voltage from the MCP4921 DAC (via Q11/Q12 KeyUp mute path).
Current sub-sheets: `analog.kicad_sch` root, `vfo_complete.kicad_sch`
(Si5351 → DGFET → Chebyshev LPF → op-amp follower → LM7171 PP
inv/non-inv), `arduino.kicad_sch` (Metro carrier, MCP4728 I²C DAC,
MCP4922 SPI DAC, control relays, heartbeat monostable, RJ45 J4 to
frontpanel, RJ45 J31 to ss_pa), `interface.kicad_sch` (frontpanel
umbilical + RS-422 termination + PCF8575 placeholder),
`dac.kicad_sch` (DAC + Q11/Q12 KeyUp mute level shifter),
`power.kicad_sch` (regulators and supply chain), `lpf.kicad_sch` (4-band
LPF bank — PLANNED to migrate to the ss_pa board, see Next work items).
Rev C not yet fabricated — merge gate is a new fab order.

**SS PA board (`KiCAD/ss_pa/`):** Push-pull IRF510 class-AB at ~10 W
QRP, driven by analog's LM7171 PP outputs over coax (J3/J4), biased
by MCP4728 VA/VB (`Bias_A_Raw`/`Bias_B_Raw`) over the RJ45 umbilical.
Current sub-sheets: `ss_pa.kicad_sch` root, `pa_stage.kicad_sch`
(QRP Labs 10W Linear kit output stage — populated with IRF510 pair,
T1 output transformer BN43-202 2:3, T2 bifilar drain feed on T50-43,
L5 supply-input RFC, bias feed per FET, drain-gate feedback per FET,
source current sense per FET with Source_Sense_A/B to Metro ADC),
`fault_shutdown.kicad_sch` (hardware overcurrent latch — LM393 with
self-latching V_REF, CD74HC4066 series-pass bias switch, startup cap
+ diode for power-on auto-reset, RJ45 J7 umbilical), `lpf.kicad_sch`
(skeleton; LPF bank migration from analog pending). ERC clean.

**Frontpanel (`KiCAD/frontpanel/`):** In development. Other end of the
analog→frontpanel RJ45 umbilical (J4 on analog ↔ J1 on frontpanel).
Design carries forward unchanged from the tube-era plan (topology
pivot only affects the RF chain, not the control umbilical).

**Protoshield (`KiCAD/protoshield/`):** Metro-mounted Adafruit Proto
Shield (PID 2077) or Proto Screw Shield. Holds Metro GPIO
signal-conditioning: bypass caps, series R, pull-ups for PADDLE_A/B,
I_CATHODE_A/B (kept wired for potential tube PA revival),
ENC_INT (via R7 series → ENC_INT_FINAL to Metro), MBL600_A/B,
RESET_N. Metro symbol and these components live here; screw terminals
remain on the analog board as the board-boundary connectors.

**Reserved for potential future tube-PA upgrade (not currently fabricated):**
- `KiCAD/bias/` — OPA454 grid bias generator (needs tube grids)
- `KiCAD/power/` — HV rectifier + filter for PA B+ rail
- `Documentation/pa_cathode_monitor.md` — 7-layer failsafe
- `Documentation/grid_bias.md`,
  `Documentation/2026-06-08-pa-validation.md` — tube PA
  operating-point and bias topology
- Firmware modules planned in `Documentation/cw_envelope_keyer.md`
  as tube-only: `grid_bias_dac.cpp`, `cathode_monitor.cpp`,
  hardware fail-safe gate section
- On analog board: DNP'd output connectors (J17/J18/J19 for cathode
  sense; J23/J24 for grid bias control). Signals and routing are in
  place — just un-DNP the connectors to re-enable physical wire-out
  if adding a tube amp later.

Next likely work items:
- Migrate the 4-band LPF bank from `KiCAD/analog/lpf.kicad_sch` to
  `KiCAD/ss_pa/lpf.kicad_sch` (so high-current RF stays on the SS PA
  board rather than passing through the analog↔ss_pa umbilical)
- Fab ss_pa board (schematic complete; needs PCB layout)
- Complete schematic + PCB for `KiCAD/frontpanel/` — start from the
  umbilical pin map in `Documentation/front_panel_interface.md`,
  mirror the PCF8575 / RS-422 receiver pair on the front-panel side
- Scaffold `firmware/` (ESP-IDF project) around the DGFET envelope
  chain — see `Documentation/cw_envelope_keyer.md` for the
  envelope-generation logic (topology-agnostic parts still apply;
  MC1496-specific hardware bits are historical, DGFET-adapted
  equivalents TBD). Modules: `main.cpp`, `keyer_envelope.cpp/h`,
  `keyer_winkey.cpp/h`, `fault_handler.cpp` (reads FAULT_N on A2,
  Source_Sense_A/B on A0/A1, implements bias servo + BIST), plus
  `CMakeLists.txt` and `sdkconfig.defaults`. Set `IDF_TARGET=esp32s3`
  per project (`idf.py set-target esp32s3` inside `firmware/`).

## Existing design references

The design docs are the source of truth for both firmware and PCB work:

| Doc | What it specs |
|---|---|
| `Documentation/cw_envelope_keyer.md` | Envelope-generation firmware (raised cosine LUT, predistortion, 25 µs tick, core-1 pinning), WinKey emulation hook, MCP4921 SPI DAC. **NOTE:** written for the MC1496 keyer topology; the envelope-generation logic (firmware, DAC, LUT, WPM mapping) is topology-agnostic and still applies to the DGFET keyer, but the MC1496-specific hardware sections (PNP null injection, reconstruction filter values, post-keyer LM7171 gain) are historical. DGFET-specific hardware doc TBD. |
| `Documentation/front_panel_interface.md` | RJ45 (Amphenol RJE1D-188-21401) umbilical, T568B pin map, PCF8575 expander, MBL-600 RS-422 termination, RJE1D-188 footprint verification checklist |
| `Documentation/i2c_bus.md` | **Single source of truth** for I²C device addresses across all PCBs. Update this first when an address changes; other docs, firmware `pin_map.h`, and schematic text notes mirror. Includes bus topology, jumper config, expansion slots, and ruled-out configurations |
| `Documentation/pcb_fab_checklist.md` | Consolidated pre-flight gate before analog-board gerbers ship: footprint verification, schematic completeness, ERC/DRC, physical, and BOM sign-offs |
| `Documentation/control_board_functional_blocks.md` | Functional blocks on the analog control board: KeyUp→Gate 2 keying, relay assignments, CD14538B heartbeat watchdog, TR_SENSE interlock, J13 power-migration header |
| `Documentation/ss_pa.md` | SS PA board: topology, RJ45 umbilical pin assignment (T568B pair-aware), pa_stage component inventory, fault_shutdown spec (self-latching V_REF + CD74HC4066 series-pass + startup auto-reset), operating-point math, pending items |

**Tube-era design references** (retained in case a high-power tube PA
is added later as an upgrade — the circuitry is drawn, DNP'd on the
analog board, and the design docs describe the operating point):

| Doc | What it specs |
|---|---|
| `Documentation/grid_bias.md` | OPA454 bias generator topology for tube grids |
| `Documentation/pa_cathode_monitor.md` | 7-layer failsafe chain for tube cathode monitoring |
| `Documentation/2026-06-08-pa-validation.md` | PA operating point for tube PA (V6 = 180 V, bias = −60 V, R17 = 300 Ω) |
| `Documentation/Cathode_Monitor_Schematic.pdf` | PDF render of the cathode monitor + diode-OR + bias-slam path |

## Conventions

- Hardware schematics: QUCS-S 26.1.1 Windows build. Symbol files (`.sym`)
  must be plain ASCII (no em dash, ohm symbol, etc.). QUCS-S symbol parser
  is not Unicode-clean.
- Firmware: **ESP-IDF v5.4.4 LTS** (not Arduino-ESP32). FreeRTOS native,
  C++17, pinned tasks, `esp_timer_get_time()` for µs timing.
- Git: never push without explicit user request; never commit without
  explicit user request.
- KiCad: never use PowerShell `Set-Content -Encoding UTF8` for `.kicad_sym`
  files — adds a BOM that KiCad 10 silently treats as empty. Use
  `[System.IO.File]::WriteAllBytes()` instead.

## Tooling regeneration commands

```bash
# Full BOM from schematics
python tools/gen_parts_list_xlsx.py

# Sourcing references (hand-curated; edit script, not xlsx)
python tools/gen_resistor_sourcing_xlsx.py
python tools/gen_capacitor_sourcing_xlsx.py

# Schematic PDFs
# NOTE: gen_mc1496_schematic_pdf.py generates a diagram of the retired
# MC1496 keyer topology — historical only, do not use for current design
python tools/gen_mc1496_schematic_pdf.py
# gen_grid_bias_schematic_pdf.py and gen_cathode_monitor_schematic_pdf.py
# generate diagrams for shelved tube-PA subsystems — historical only
python tools/gen_grid_bias_schematic_pdf.py
python tools/gen_cathode_monitor_schematic_pdf.py

# Run ngspice on a .cir, write .dat.ngspice for gui_plot
python xmitter_prj/ngspice.py <netlist_stem>

# Parameter sweeps
python tools/sweep_param.py <netlist> --pattern <regex> --values <list> ...

# Assign THT capacitor footprints by value (re-runnable; fills empty
# Footprint fields only, never overwrites). Edit VALUE_TO_FOOTPRINT
# at the top of the script when a new value gets ordered.
python tools/assign_cap_footprints.py KiCAD/analog/vfo_complete.kicad_sch \
       KiCAD/analog/arduino.kicad_sch KiCAD/analog/interface.kicad_sch \
       KiCAD/bias/bias.kicad_sch
```

# xmitter project — Claude Code project instructions

20 m CW transmitter. **Current design (Rev B, 2026-09-29 pivot):** DGFET
envelope keyer on the analog board (Si5351 → DGFET with G1=RF, G2=envelope
DAC → Chebyshev LPF → op-amp follower → LM7171 PP inv/non-inv), driving
a planned full-SS class-AB push-pull output stage (~5–10 W QRP, separate
board TBD). Adafruit Metro ESP32-S3 control. Hardware design in QUCS-S
schematics + KiCad PCBs. ESP-IDF v5.4.4 toolchain installed and verified
on both dev machines (2026-06-12); firmware/ not yet scaffolded.

**Shelved (kept as reference, may return if SS PA insufficient):** the
original vacuum-tube design — push-pull 6146B PA, push-pull 12HG7 driver,
MC1496-based VCA keyer, OPA454 grid bias generator, cathode monitor
failsafe chain, HV supply. MC1496 keyer was retired after Rev A hardware
failed (likely feedback path from the balance-trim network); tubes were
shelved when the transformer spec for a 4-tube rig became untenable.
See `[[project-revB-topology-pivot]]` memory for full context.

This file is read on every session start. Keep it focused on stable project
facts and one-time interactive flows (like fresh-machine onboarding) that
otherwise have nowhere natural to live.

## Directory map

| Directory | What's in it |
|---|---|
| `xmitter_prj/` | QUCS-S schematics (`.sch`) and SPICE libraries (`.lib`) |
| `KiCAD/` | KiCad PCB design files. **Active:** `analog/` (Rev A fabricated 2026-07-14 — MC1496 keyer stage failed; Rev B branch replaced it with DGFET keyer, awaiting SS PA design before next fab), `frontpanel/` (in development), `protoshield/` (Metro-mounted proto-shield). **Not yet designed:** SS output stage board (directory `ss_pa/` or similar TBD). **Shelved (tubes retired for first cut):** `bias/` (OPA454 grid bias generator), `power/` (HV rectifier + filter). Shared `xmitter.pretty/` footprints and `xmitter.kicad_sym` at `KiCAD/` root, referenced by each project via `${KIPRJMOD}/../`. Reversal recipe in `KiCAD/MULTIBOARD_REVERT.md`. |
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

Rev B branch — pivoted 2026-09-29 from tube PA to SS PA.

**Analog control board (`KiCAD/analog/`):** Rev A fabricated 2026-07-14
(JLCPCB Y2-13077341A) — the MC1496 balanced-modulator keyer stage did
not work on the built board (minimal output, unclean RF, suspected
feedback path in the balance-trim network). Rev B branch removed
`buffer_keyer.kicad_sch` entirely and replaced the keyer with a DGFET
(dual-gate FET) VCA: G1 receives RF from Si5351, G2 receives the
envelope voltage from the MCP4728 DAC. Current sub-sheets:
`analog.kicad_sch` root, `vfo_complete.kicad_sch` (Si5351 → DGFET →
Chebyshev LPF → op-amp follower → LM7171 PP inv/non-inv),
`arduino.kicad_sch` (Metro carrier + control relays + heartbeat
monostable), `interface.kicad_sch` (RJ45 umbilical + RS-422
termination + PCF8575 placeholder). Rev B not yet fabricated —
merge gate is a new fab order.

**Frontpanel (`KiCAD/frontpanel/`):** In development. Other end of the
RJ45 umbilical driven by the analog board's `interface.kicad_sch`.
Design carries forward unchanged from the tube-era plan (topology
pivot only affects the RF chain, not the control umbilical).

**Protoshield (`KiCAD/protoshield/`):** Metro-mounted Adafruit Proto
Shield (PID 2077) or Proto Screw Shield. Holds Metro GPIO
signal-conditioning: bypass caps, series R, pull-ups for PADDLE_A/B,
I_CATHODE_A/B (unused post-pivot but wiring stays for later),
ENC_INT, MBL600_A/B, RESET_N. Metro symbol (U2) and these components
were removed from `arduino.kicad_sch`; screw terminals remain on the
analog board as the board-boundary connectors.

**SS output stage — not yet designed.** Will be a new KiCad project
(directory TBD, likely `KiCAD/ss_pa/`). Target: full-SS class-AB
push-pull PA, IRF510 pair on 13.8 V, ~5–10 W into 50 Ω at 14 MHz,
driven by the analog board's LM7171 PP outputs. Includes 7-element
Chebyshev output LPF, bifilar output transformer, drain current
sense, optional VSWR sense.

**Shelved (tubes retired for first cut; may return if SS PA
insufficient):**
- `KiCAD/bias/` — OPA454 grid bias generator (needs tube grids)
- `KiCAD/power/` — HV rectifier + filter for PA B+ rail
- `Documentation/pa_cathode_monitor.md` — 7-layer failsafe (needs
  tube cathodes)
- `Documentation/grid_bias.md`, `Documentation/2026-06-08-pa-validation.md`
  — tube PA operating-point and bias topology
- Firmware modules planned in `Documentation/cw_envelope_keyer.md`
  as tube-only: `grid_bias_dac.cpp`, `cathode_monitor.cpp`,
  hardware fail-safe gate section

Next likely work items:
- Design SS output stage board (schematic + PCB) — new KiCad project
- Complete schematic + PCB for `KiCAD/frontpanel/` — start from the
  umbilical pin map in `Documentation/front_panel_interface.md`,
  mirror the PCF8575 / RS-422 receiver pair on the front-panel side
- Scaffold `firmware/` (ESP-IDF project) around the DGFET envelope
  chain — see `Documentation/cw_envelope_keyer.md` for the
  envelope-generation logic (topology-agnostic parts still apply;
  MC1496-specific hardware bits are historical, DGFET-adapted
  equivalents TBD). Modules: `main.cpp`, `keyer_envelope.cpp/h`,
  `keyer_winkey.cpp/h`, `fault_handler.cpp`, plus `CMakeLists.txt`
  and `sdkconfig.defaults`. Set `IDF_TARGET=esp32s3` per project
  (`idf.py set-target esp32s3` inside `firmware/`).

## Existing design references

The design docs are the source of truth for both firmware and PCB work:

| Doc | What it specs |
|---|---|
| `Documentation/cw_envelope_keyer.md` | Envelope-generation firmware (raised cosine LUT, predistortion, 25 µs tick, core-1 pinning), WinKey emulation hook, MCP4921 SPI DAC. **NOTE:** written for the MC1496 keyer topology; the envelope-generation logic (firmware, DAC, LUT, WPM mapping) is topology-agnostic and still applies to the DGFET keyer, but the MC1496-specific hardware sections (PNP null injection, reconstruction filter values, post-keyer LM7171 gain) are historical. DGFET-specific hardware doc TBD. |
| `Documentation/front_panel_interface.md` | RJ45 (Amphenol RJE1D-188-21401) umbilical, T568B pin map, PCF8575 expander, MBL-600 RS-422 termination, RJE1D-188 footprint verification checklist |
| `Documentation/i2c_bus.md` | **Single source of truth** for I²C device addresses across all PCBs. Update this first when an address changes; other docs, firmware `pin_map.h`, and schematic text notes mirror. Includes bus topology, jumper config, expansion slots, and ruled-out configurations |
| `Documentation/pcb_fab_checklist.md` | Consolidated pre-flight gate before analog-board gerbers ship: footprint verification, schematic completeness, ERC/DRC, physical, and BOM sign-offs |
| `Documentation/control_board_functional_blocks.md` | Functional blocks on the analog control board: KeyUp→Gate 2 keying, relay assignments, CD14538B heartbeat watchdog, TR_SENSE interlock, J13 power-migration header |

**Shelved design references** (tubes retired for first cut; retained
for reference in case SS PA design proves insufficient):

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

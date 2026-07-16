# xmitter project — Claude Code project instructions

20 m CW vacuum-tube transmitter. Push-pull 6146B PA, push-pull 12HG7 driver,
MC1496-based VCA keyer with envelope shaping, Adafruit Metro ESP32-S3 control.
Hardware design in QUCS-S schematics + KiCad PCBs. ESP-IDF v5.4.4 toolchain
installed and verified on both dev machines (2026-06-12); ready to scaffold
`firmware/`.

This file is read on every session start. Keep it focused on stable project
facts and one-time interactive flows (like fresh-machine onboarding) that
otherwise have nowhere natural to live.

## Directory map

| Directory | What's in it |
|---|---|
| `xmitter_prj/` | QUCS-S schematics (`.sch`) and SPICE libraries (`.lib`) |
| `KiCAD/` | KiCad PCB design files. One project per board: `analog/` (fabricated Rev A, 2026-07-14), `bias/` (new), `frontpanel/` (new stub). Shared `xmitter.pretty/` footprints and `xmitter.kicad_sym` at `KiCAD/` root, referenced by each project via `${KIPRJMOD}/../`. Reversal recipe in `KiCAD/MULTIBOARD_REVERT.md`. |
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

Analog control board Rev A fabricated (JLCPCB order Y2-13077341A,
submitted 2026-07-14). Project lives at `KiCAD/analog/`:
`analog.kicad_sch` root, sub-sheets `buffer_keyer.kicad_sch` (MC1496
keyer chain), `vfo.kicad_sch` (Si5351 VFO), `arduino.kicad_sch` (Metro
carrier + control relays + heartbeat monostable), `interface.kicad_sch`
(RJ45 umbilical jack + RS-422 termination + PCF8575 placeholder).
Empty stubs `pa/driver/balun/lpf_output.kicad_sch` still linked at
root — Phase 3-5 RF chain.

Bias board split off to `KiCAD/bias/` (2026-07-15). Started from the
existing `bias.kicad_sch` (OPA454 bias generator + LM393 cathode
monitor + diode-OR + slam handoff). PCB layout not yet started.

Front-panel display + encoders board at `KiCAD/frontpanel/` — empty
stub project (2026-07-15). Other end of the RJ45 umbilical driven by
the analog board's `interface.kicad_sch`. Schematic content to be
drawn.

Next likely work items:
- PCB layout for `KiCAD/bias/` (HV clearances — analog board's
  netclasses were copied over but should be tightened for the HV rails).
- Schematic + PCB for `KiCAD/frontpanel/` — start from the umbilical
  pin map in `Documentation/front_panel_interface.md`, mirror the
  PCF8575 / RS-422 receiver pair on the front-panel side.
- Scaffold `firmware/` (ESP-IDF project) — see
  `Documentation/cw_envelope_keyer.md` for the module breakdown:
  `main.cpp`, `keyer_envelope.cpp/h`, `keyer_winkey.cpp/h`,
  `grid_bias_dac.cpp`, `cathode_monitor.cpp`, `fault_handler.cpp`, plus
  `CMakeLists.txt` and `sdkconfig.defaults`. Set `IDF_TARGET=esp32s3`
  per project (`idf.py set-target esp32s3` inside `firmware/`).

## Existing design references

The design docs are the source of truth for both firmware and PCB work:

| Doc | What it specs |
|---|---|
| `Documentation/cw_envelope_keyer.md` | Envelope generation (raised cosine LUT, predistortion, 25 µs tick, core-1 pinning), WinKey emulation hook, MCP4921 SPI DAC, fail-safe gating |
| `Documentation/grid_bias.md` | OPA454 bias generator topology, supply tree, transfer function, R/C values per tube |
| `Documentation/pa_cathode_monitor.md` | 7-layer failsafe chain: clamps, OPA1641 buffer, LM393 comparator with hysteresis, diode-OR combiner, grid-bias slam handoff, ADC firmware thresholds, NVS fault log |
| `Documentation/2026-06-08-pa-validation.md` | PA operating point (V6 = 180 V, bias = −60 V, R17 = 300 Ω) that determines firmware bias DAC code |
| `Documentation/Cathode_Monitor_Schematic.pdf` | Generated PDF render of the cathode monitor + diode-OR + bias-slam path |
| `Documentation/front_panel_interface.md` | RJ45 (Amphenol RJE1D-188-21401) umbilical, T568B pin map, PCF8575 expander, MBL-600 RS-422 termination, RJE1D-188 footprint verification checklist |
| `Documentation/i2c_bus.md` | **Single source of truth** for I²C device addresses across all three PCBs. Update this first when an address changes; other docs, firmware `pin_map.h`, and schematic text notes mirror. Includes bus topology, jumper config, expansion slots, and ruled-out configurations |
| `Documentation/pcb_fab_checklist.md` | Consolidated pre-flight gate before analog-board gerbers ship: footprint verification, schematic completeness, ERC/DRC, physical, and BOM sign-offs |

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
python tools/gen_mc1496_schematic_pdf.py
python tools/gen_grid_bias_schematic_pdf.py
python tools/gen_cathode_monitor_schematic_pdf.py

# Run ngspice on a .cir, write .dat.ngspice for gui_plot
python xmitter_prj/ngspice.py <netlist_stem>

# Parameter sweeps
python tools/sweep_param.py <netlist> --pattern <regex> --values <list> ...

# Assign THT capacitor footprints by value (re-runnable; fills empty
# Footprint fields only, never overwrites). Edit VALUE_TO_FOOTPRINT
# at the top of the script when a new value gets ordered.
python tools/assign_cap_footprints.py KiCAD/analog/buffer_keyer.kicad_sch \
       KiCAD/analog/vfo.kicad_sch KiCAD/analog/arduino.kicad_sch \
       KiCAD/analog/interface.kicad_sch KiCAD/bias/bias.kicad_sch
```

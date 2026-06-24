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
| `KiCAD/` | KiCad PCB design files |
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

Analog-board schematic is complete (2026-06-24): bias + cathode monitor
on `KiCAD/bias.kicad_sch`, MC1496 keyer chain on `KiCAD/buffer_keyer.kicad_sch`,
Si5351 VFO on `KiCAD/vfo.kicad_sch`, Metro carrier on `KiCAD/arduino.kicad_sch`.
PA / driver / balun / LPF sheets are still empty stubs (Phase 3-5 work).

Next likely work items:
- PCB layout for the analog board (bias + cathode monitor + buffer_keyer
  + arduino + vfo sheets stitched at the root).
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
python tools/assign_cap_footprints.py KiCAD/bias.kicad_sch \
       KiCAD/buffer_keyer.kicad_sch KiCAD/vfo.kicad_sch KiCAD/arduino.kicad_sch
```

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

## Firmware scaffolding (current focus)

Next work item: scaffold `firmware/` with the architecture specified in
`Documentation/cw_envelope_keyer.md` —
`main.cpp`, `keyer_envelope.cpp/h`, `keyer_winkey.cpp/h`,
`grid_bias_dac.cpp`, `cathode_monitor.cpp`, `fault_handler.cpp`, plus
`CMakeLists.txt` and `sdkconfig.defaults`. Set `IDF_TARGET=esp32s3` per
project (`idf.py set-target esp32s3` inside `firmware/`).

## Existing design references for the firmware work

When writing firmware, these design docs are the source of truth:

| Doc | What it specs |
|---|---|
| `Documentation/cw_envelope_keyer.md` | Envelope generation (raised cosine LUT, predistortion, 25 µs tick, core-1 pinning), WinKey emulation hook, MCP4921 SPI DAC, fail-safe gating |
| `Documentation/pa_cathode_monitor.md` | Cathode current monitor, comparator hardware trip, ADC sampling threshold/window, NVS fault log |
| `Documentation/2026-06-08-pa-validation.md` | PA operating point (V6 = 180 V, bias = −60 V, R17 = 300 Ω) that determines firmware bias DAC code |
| `Documentation/Grid_Bias_Schematic.pdf` | Per-tube OPA454 bias + CT_FAULT bias-slam (Q_SLAM 2N7000) |
| `Documentation/Cathode_Monitor_Schematic.pdf` | 7-layer failsafe chain spec |

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
```

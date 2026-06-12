# xmitter project — Claude Code project instructions

20 m CW vacuum-tube transmitter. Push-pull 6146B PA, push-pull 12HG7 driver,
MC1496-based VCA keyer with envelope shaping, Adafruit Metro ESP32-S3 control.
Hardware design in QUCS-S schematics + KiCad PCBs; firmware coming next via
ESP-IDF v5.4 on an Adafruit Metro ESP32-S3.

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
| `firmware/` | ESP-IDF firmware (not yet committed; coming next) |

## If the user opens Claude Code on the dev machine for the first time

If the user mentions any of "dev machine", "new machine", "setting up",
"installing", "fresh install", "fresh clone", or otherwise indicates they're
just starting to use this machine, **walk them through
`Documentation/ESP-IDF_Setup_Windows.md` interactively** rather than dumping
the whole thing on them.

Specifically:

1. **Read the setup doc first** to refresh on what the steps are.
2. **Verify what's already installed** by running `git --version`, `python --version`,
   `code --version`, etc. in PowerShell via the Bash tool. Skip steps that are
   already done.
3. **Walk through ONE STEP AT A TIME**. After each step, **run the verification
   command** for that step before moving on. Don't continue past a broken step.
4. **Troubleshoot in real time** if a verification fails. The setup doc has a
   troubleshooting table at the bottom — use it.
5. After each major install (Git, Python, VS Code, ESP-IDF extension), confirm
   the user is OK to proceed to the next.
6. **At the end**, run through the blink-example verification (build, flash,
   monitor) so the user knows the toolchain works end-to-end before we move
   on to writing xmitter firmware.

The dev machine is fresh (or close to it) and may have been sitting idle for
a while. The walkthrough assumes nothing is installed. If commands suggest
otherwise (e.g., `git` already in PATH), adapt and skip.

After setup is verified working, the user will say so. Then move to scaffolding
out the `firmware/` directory — main.cpp, keyer_envelope.cpp/h, keyer_winkey.cpp/h,
grid_bias_dac.cpp, cathode_monitor.cpp, fault_handler.cpp — per the architecture
already specified in `Documentation/cw_envelope_keyer.md`.

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
- Firmware: **ESP-IDF v5.4** (not Arduino-ESP32). FreeRTOS native, C++17,
  pinned tasks, `esp_timer_get_time()` for µs timing.
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

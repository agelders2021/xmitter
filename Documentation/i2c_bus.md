# I²C bus address plan

**Single source of truth for I²C device addresses across the transmitter's
three PCBs (analog control, bias, front-panel).** Update this file first
when an address changes; other docs, `firmware/main/pin_map.h`, the
schematic text notes, and memory notes should mirror.

## Device inventory

- **0x20 — PCF8575 (main).** Adafruit PID 5904 breakout. Analog control
  board, on the arduino sheet, reference U17. A0/A1/A2 jumpers all open
  (factory default). Drives the relay coil FETs (filament, HV, T/R).

- **0x21 — PCF8575 (front-panel).** Adafruit PID 5904 breakout. Front-panel
  PCB (`KiCAD/frontpanel/`), reference U1. **A0 jumper closed** (pulled
  to 1). Drives the WH2004A LCD in 4-bit mode, front-panel status LEDs,
  and optionally the paddle jack.

- **0x36 — MAX17048 fuel gauge.** Fixed address, on the Metro
  ESP32-S3 module itself. Not a discrete part in the design — comes with
  the Metro. Its presence forced the STEP encoder off its 0x36 default.

- **0x37 — I²C QT Rotary encoder (STEP).** Adafruit PID 4991. Panel-mounted
  via STEMMA QT cable from the front-panel PCB. **A0 jumper closed** to
  move off factory 0x36 (dodges MAX17048).

- **0x38 — I²C QT Rotary encoder (FUNC).** Adafruit PID 4991. Panel-mounted
  via STEMMA QT cable from the front-panel PCB. **A1 jumper closed**.

- **0x60 — Si5351A VFO.** Adafruit PID 5640 breakout. Analog control
  board, chained via STEMMA QT cable from the MCP4728's STEMMA OUT. ADDR
  solder jumper on the breakout is not modified (0402 pad, too small
  for hand soldering).

- **0x62 — MCP4725 DAC (LCD contrast).** Adafruit PID 935 breakout.
  Front-panel PCB, reference TBD. **A0 header pin open (or tied to GND)**
  for the 0x62 address. Generates V0 for the LCD in place of a contrast
  pot; firmware-controllable contrast.

- **0x67 — MCP4728 quad DAC.** Adafruit PID 4470 breakout. Analog
  control board, upstream of the Si5351 in the STEMMA QT chain from the
  Metro. **Reprogrammed from factory 0x60** via the firmware console
  command `mcp4728 reprogram 0x60 0x67 -y` — one-time per build, see
  `build_checklist.md` Phase 1. Provides grid-bias control voltages
  routed to the bias board.

## Bus topology

Whole transmitter runs one shared I²C bus at 100 kHz.

```
Metro ESP32-S3 STEMMA QT port
  │
  ├─ MAX17048 (0x36)              on-board, unavoidable on the shared bus
  │
  └─ STEMMA cable → MCP4728 breakout (0x67) STEMMA IN
                     │
                     ├─ 0.1" header pins 3/4 (SDA/SCL) → analog PCB traces
                     │       │
                     │       ├─ Main-board PCF8575 (0x20)
                     │       │
                     │       └─ RJE1D-188 J4 pins 1/2 → CAT6 pair 2 → front-panel PCB
                     │              │
                     │              ├─ Front-panel PCF8575 (0x21)
                     │              ├─ MCP4725 (0x62)
                     │              └─ STEMMA QT chain to panel-mount encoders:
                     │                     STEP (0x37) ── FUNC (0x38)
                     │
                     └─ STEMMA OUT → Si5351 breakout (0x60)
```

The MCP4728 → Si5351 STEMMA cable is installed **after** the one-time
MCP4728 EEPROM reprogram is done, so no 0x60 address collision during
first bring-up. See `build_checklist.md` Phase 1 for the exact
sequencing.

## Bias board

**No I²C devices.** The bias board (`KiCAD/bias/`) receives analog
control voltages from the MCP4728 (on the analog board) over an
inter-board header, and its LM393 cathode monitor sends digital
comparator outputs back to the Metro over a separate cable. Neither
path uses I²C.

## Reserved / expansion slots

- **0x22 – 0x27** — free for additional PCF8575s if I/O needs grow.
- **0x39 – 0x3D** — free for additional QT rotary encoders (more knobs).
- **0x61, 0x63 – 0x66** — free for additional MCP4725 or MCP4728
  breakouts. 0x63 is the natural next slot (MCP4725 with A0 tied high).

## Ruled-out configurations (do not re-propose)

- **Si5351 ADDR solder jumper.** Physically possible (0402 pad on the
  breakout) but ruled out — hand tremor makes that size unreliable to
  solder.
- **Feeding 3.3 V through the front-panel STEMMA QT chain.** The
  WH2004A LCD needs 4.5 V minimum per its datasheet, so the whole
  front-panel PCB operates at 5 V. STEMMA QT V+ on that PCB carries
  +5 V, not 3.3 V.
- **PCF8574 LCD backpack** and **MCP23017 GPIO expander** — considered
  and dropped in favor of PCF8575 and I²C QT rotary encoders (2026-07).

## Cross-references

- Firmware: `firmware/main/pin_map.h` — `I2C_ADDR_*` constants
- Schematic text notes: `KiCAD/frontpanel/frontpanel.kicad_sch` and
  `KiCAD/analog/interface.kicad_sch`
- One-time procedures: `Documentation/build_checklist.md` Phase 1
  (MCP4728 EEPROM reprogram)
- Front-panel CAT6 pin map + PCF8575 role: `Documentation/front_panel_interface.md`

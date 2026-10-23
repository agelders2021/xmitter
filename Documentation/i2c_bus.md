# I²C bus address plan

**Single source of truth for I²C device addresses across the five Rev D
PCBs (analog, ss_pa, Output LPF, frontpanel, protoshield).** Update this
file first when an address changes; other docs, `firmware/main/pin_map.h`,
schematic text notes, and memory notes should mirror.

Last updated: 2026-10-23 (Rev D Option-C power rail changes).

## Bus voltage architecture

The Metro ESP32-S3 drives I²C natively at 3.3 V. All I²C slaves on the bus
are powered from +5 V (for their V_OUT range or for compatibility with the
non-5V-tolerant Si5351 breakout's own pull-ups to its 5 V V_IN). Rev D
bridges the two voltage domains with a single translator at the Metro I²C
entry:

- **Adafruit #757 BSS138 breakout** (U2 on `analog`, in `xmitter`
  library) at the Metro I²C entry. LV side (pins 1–6) = +3.3 V, HV
  side (pins 7–12) = +5 V. 10 kΩ pull-ups on both sides are built in.
- Downstream of the shifter, every I²C slave sits on a shared +5 V
  "HV bus" across all PCBs that have an I²C device.

Pull-ups on the Si5351 and MCP4728 breakouts (which tie to their own
V_IN) must be **depopulated** so the shifter's internal 10 kΩ pair is
the only HV-side pull-up. See `revD_prelayout_review_handoff.md`
"I²C bus voltage architecture" for the full discussion.

A DPDT slide switch (SW1 on `analog`, C&K JS202011CQN THT) sits between
the HV bus and the Si5351 header, breaking both SDA and SCL together,
so the Si5351 can be isolated from the bus during bringup without
unseating the breakout.

## Device inventory

- **0x20 — PCF8575 (analog, main).** Adafruit PID 5904 breakout. On the
  analog board's `arduino.kicad_sch`, reference U17. A0/A1/A2 jumpers all
  open (factory default). Drives relay coil FETs (band-select /
  envelope-gate / T/R) and provides general-purpose GPIO for the Metro.
  Powered at +5 V from analog's +5 V rail.

- **0x21 — PCF8575 (frontpanel).** Adafruit PID 5904 breakout. On the
  frontpanel PCB, reference U1. **A0 jumper closed** (A0 = 1). Drives
  the WH2004A LCD in 4-bit mode, front-panel status LEDs, button
  matrix. Powered at +5 V (received from analog over the frontpanel
  umbilical, J4 pin 4).

- **0x60 — Si5351A VFO.** Adafruit PID 5640 breakout. On analog's
  `vfo_complete.kicad_sch`, reference U5. ADDR solder jumper on the
  breakout is **not modified** (0402 pad too small for hand soldering —
  see "Ruled-out configurations" below). Powered at +5 V V_IN;
  internal breakout LDO regulates to the Si5351 chip's native 3.3 V.
  I²C arrives via the DPDT bringup switch (SW1).

- **0x62 — MCP4725 DAC (LCD contrast, frontpanel).** Adafruit breakout.
  On the frontpanel PCB, reference U2. A0 header pin tied to GND for
  the 0x62 address. Generates V0 for the LCD in place of a contrast
  trimpot; firmware-controllable contrast. Powered at +5 V.

- **0x67 — MCP4728 quad DAC (analog).** Adafruit PID 4470 breakout. On
  analog's `dac.kicad_sch`, reference U3. **Reprogrammed from factory
  0x60** via one-time firmware command `mcp4728 reprogram 0x60 0x67 -y`
  (resolves the Si5351 collision at factory address 0x60). See
  `build_checklist.md` Phase 1 for the exact sequencing. Powered at
  +5 V (changed from +3.3 V in Rev D Option C to give full 0–5 V output
  span, needed for the IRF510 bias range on ss_pa). Channel assignments:
  A/B = PA_Bias_A/PA_Bias_B (IRF510 pair), C/D = GRID_CTL_A/B (DNP for
  the tube-PA upgrade path).

Metro ESP32-S3 also hosts an on-module **MAX17048 fuel gauge at 0x36**
over its own internal I²C — the external bus does not reach it. 0x36 is
reserved to avoid confusion when adding new devices.

## Bus topology (Rev D)

```
Metro ESP32-S3
  │   (3.3 V native I²C)
  │
  ├─ internal: MAX17048 (0x36)  (on-module, not on external bus)
  │
  ├─ STEMMA QT port ─── encoder chain (3.3 V STEMMA-native devices only)
  │                      no slave on the main HV bus is on STEMMA
  │
  └─ GPIO SDA/SCL ──→ protoshield screw-terminal headers ──→ analog PCB
                                                               │
                                                     Adafruit #757 BSS138
                                                     LV side (3.3 V)
                                                           │
                                                     HV side (5 V, HV bus)
                                                           │
            ┌──────────────────────────────────────────────┼────────────┐
            │                                              │            │
     Si5351 (0x60)                                   PCF8575 (0x20)   MCP4728 (0x67)
     via DPDT bringup SW1                                 analog      analog
     analog                                               U17         U3
     U5
            │                                              │            │
            │     ┌─────── frontpanel umbilical J4 ────────┘            │
            │     │        pair carries HV-side SDA/SCL                 │
            │     ▼                                                     │
            │   PCF8575 (0x21)                                          │
            │   frontpanel U1                                           │
            │     │                                                     │
            │   MCP4725 (0x62)                                          │
            │   frontpanel U2                                           │
            │                                                           │
            └─────────────────── all devices powered from 5 V ──────────┘
```

The HV bus is purely on-PCB and (for frontpanel) over the J4 umbilical.
The ss_pa board does NOT have an I²C device — its CD74HC4066 bias switch
is a logic-level analog switch, not an I²C-controlled part; its control
pin is driven directly by FAULT_N from the ss_pa fault latch.

## Reserved / expansion slots

- **0x22 – 0x27** — free for additional PCF8575s if I/O needs grow.
- **0x39 – 0x3D** — free for additional I²C peripherals (if the
  encoder plan ever reverts to I²C-based rotaries).
- **0x61, 0x63 – 0x66** — free for additional MCP4725 or MCP4728
  breakouts. 0x63 is the natural next slot (MCP4725 with A0 tied high).

## Rotary encoder note (not on I²C bus)

The frontpanel rotary encoder is an **MBL-600 optical encoder with
RS-422 differential outputs** — it is NOT on the I²C bus. The MBL-600 is
received back on analog by an AM26LS32ACN RS-422 receiver (U16), with
120 Ω termination on the analog side per MBL-600 convention. The
differential pair runs on dedicated CAT6 pairs on the frontpanel
umbilical, not on SDA/SCL. See `front_panel_interface.md`.

An earlier plan used Adafruit I²C QT rotary encoders at 0x37 / 0x38 on
the bus; that plan was dropped. Those addresses are now free.

## Ruled-out configurations (do not re-propose)

- **Si5351 ADDR solder jumper.** Physically possible (0402 pad on the
  breakout) but ruled out — hand tremor makes that size unreliable to
  solder reliably.
- **Running the HV bus at 3.3 V to skip the shifter.** The MCP4728 at
  3.3 V V_DD caps its output at 3.3 V, which is below the IRF510 class-AB
  Vgs bias point. Not viable without a separate bias-rail boost.
- **STEMMA QT chain for the main bus (as in Rev C).** Rev C had
  Metro → MCP4728 → Si5351 chained via STEMMA cables, with the Si5351
  header as the PCB bus injection point. Rev D moved power + I²C for
  those breakouts onto PCB header pins and freed STEMMA for the encoder
  chain. The old 0 Ω jumpers that would route STEMMA to those breakouts
  remain unpopulated.
- **PCF8574 LCD backpack** and **MCP23017 GPIO expander** — considered
  and dropped in favor of PCF8575 directly (2026-07).

## Cross-references

- Firmware: `firmware/main/pin_map.h` — `I2C_ADDR_*` constants (not yet
  scaffolded; firmware begins after fab).
- Schematic text notes: `KiCAD/analog/dac.kicad_sch` (MCP4728 reprogram
  note) and `KiCAD/frontpanel/frontpanel.kicad_sch`.
- One-time procedures: `Documentation/build_checklist.md` Phase 1
  (MCP4728 EEPROM reprogram).
- Frontpanel umbilical pin map: `Documentation/front_panel_interface.md`.
- Rev D supply-rail changes: `Documentation/revD_prelayout_review_handoff.md`.

# Control Board Functional Blocks

Captures the *function* of each block on the analog (control) board that
isn't obvious from the schematic. Written 2026-09-29 during a schematic
review pass; complements the wiring visible in the KiCad sub-sheets by
answering "what does this block *do*."

Scope: analog board (`KiCAD/analog/`) sub-sheets `arduino.kicad_sch` and
`vfo_complete.kicad_sch`. The interface sheet is straightforward (RJ45
umbilical + AM26LS32 differential receiver) and doesn't need block-level
prose.

## Keying (KeyUp signal chain)

**KeyUp** is the firmware-driven RF enable/disable line. It exits the
Metro ESP32-S3 through the PCF8575 I²C port expander (U17 P7) and
propagates through the level-shift transistor pair Q3/Q8 into `Gate 2`
on the RCA40673 dual-gate mixer MOSFET in the VFO chain.

Behavior:

- **KeyUp = HIGH → RF muted.** Q3/Q8 pull `Gate 2` low, biasing the
  RCA40673's second gate below its conduction threshold. RF drive to
  the driver stage collapses.
- **KeyUp = LOW → RF enabled.** Gate 2 returns to its bias point and
  the mixer passes the Si5351-derived carrier through to the driver.

Firmware is expected to *also* slam PA grid bias to cutoff during
KeyUp = HIGH (via the MCP4728 → OPA454 bias generator on the bias
board). The two mechanisms are redundant on purpose:

- Fast electronic cutoff via Gate 2 (µs response, precise envelope
  shaping via cw_envelope_keyer.md).
- Deep DC cutoff via grid bias (ms response, keeps the PA idle current
  at zero during long key-up intervals so plate dissipation stays low).

## Relay assignments

Three 12 V coil relays are driven from the analog board. Each coil has a
1N4001 flyback diode across it. Each relay is switched by a 2N7000
MOSFET on the analog board, with the coil supply on pin 2 of the
corresponding screw terminal.

- **J6 → Transmit/Receive relay.** Antenna switching. NO/NC contacts
  route the antenna between the receiver input and the transmitter's
  output LPF.
- **J7 → HV primary contactor.** Switches the AC primary of the
  high-voltage plate transformer. This is the main HV enable.
- **J8 → HV inrush current limiter.** Shorts out the inrush current
  limiter resistor once the HV filter caps have charged. Sequence:
  J7 closes → resistor drops the initial charging current → after a
  firmware delay, J8 closes to short the resistor for full-current
  operation.

Coil-driver MOSFETs on the arduino sheet:

- Q4/Q5/Q6 = 2N7000, drains → J6/J7/J8 pin 1 respectively. Gates
  driven by the PCF8575 U17 (P13/P14/P15).
- **Q7 = HV primary safety cut.** Gate driven by the CD14538B U18
  monostable Q_A output, drain → J7 (HV primary relay). This is
  the hardware kill-switch (see next section).

## Heartbeat watchdog (CD14538B monostable)

Protects the HV rail against firmware hangs. The Metro ESP32-S3 is
expected to periodically toggle PCF8575 U17 P12, which triggers the
CD14538B U18 dual monostable's A-side. As long as the retriggers keep
arriving, Q_A stays asserted and Q7 keeps the HV primary relay
enabled. If the retriggers stop (firmware crash, I²C hang, whatever),
the monostable times out, Q_A drops, Q7 opens, and J7 (HV primary)
opens.

Practical firmware requirement: toggle the P12 line at an interval
comfortably shorter than the monostable's RC time constant (set by
C41 = 1 µF and R30 = 470 kΩ on the arduino sheet, so nominal
`t = 0.7 * R * C ≈ 0.33 s`; firmware should refresh every 100 ms or
faster with margin).

## TR_SENSE (RF-power interlock)

`TR_SENSE` is an input to the Metro (via protoshield J5 pin 2 →
Metro A5). It's driven by a **second pole on the T/R relay** — i.e.,
the same relay whose coil is at J6, using a DPDT (or higher) pole
count so that the second pole gives the firmware a positive
confirmation that the T/R relay is mechanically in the transmit
position.

Purpose: protect the receiver, which shares the antenna. Firmware
must:

1. Command J6 (T/R relay) to the transmit position.
2. Wait for TR_SENSE to assert (relay has actually moved and
   contacts have settled).
3. *Then* enable RF drive (release KeyUp, un-cutoff the PA bias).

If TR_SENSE never asserts (relay stuck, coil open, contact welded),
firmware must not release KeyUp and must log a fault.

TR_SENSE originates on the T/R relay (external to any of the four
boards under design). It arrives on the protoshield via J5 pin 2 as
`TR_SENSE_RAW` (with 10 kΩ pull-up R10 on the protoshield). No
board-side TR_SENSE routing on analog — the wire runs directly from
the relay chassis to the protoshield screw terminal.

## J13 (power distribution header)

Three-pin screw terminal with GND / +5V / +12V on the arduino sheet.
Placed defensively to allow a future migration:

- **Today:** +12V arrives at the board via J7's power header (or
  wherever the current supply enters), +5V is generated on-board
  (LM7805 in vfo_complete). J13 is populated as an **output** —
  distributes those rails to other consumers on this board or to
  jumper wires going elsewhere.
- **Future (power-board migration):** if the +12V and +5V regulators
  move onto the yet-to-be-designed power board, J13 becomes the
  **input** where those rails arrive from the power board. Analog-side
  regulator parts (LM7805, associated bypass caps) would be left
  unpopulated (DNP) in that scenario.

Rationale: adding J13 now, even though it's currently redundant, saves
a full PCB fab spin when the power-board split happens.

## Cross-references

- `Documentation/cw_envelope_keyer.md` — envelope shaping detail
  (raised-cosine LUT, MCP4921 DAC, 25 µs tick). Covers the *shape* of
  the envelope; this doc covers the *gating* signals around it.
- `Documentation/grid_bias.md` — OPA454 bias generator on the bias
  board that the firmware slams to cutoff during KeyUp = HIGH.
- `Documentation/pa_cathode_monitor.md` — cathode-current
  fault chain, feeds the GRID_BLOCK_CRASH signal that appears on
  arduino / bias / protoshield sheets.
- `Documentation/front_panel_interface.md` — RJ45 umbilical pinout.
- `Documentation/i2c_bus.md` — PCF8575 addresses (0x20 on this
  board, 0x21 on the front panel).

## Open items / not yet documented

- **VFO envelope chain topology on `vfo_complete.kicad_sch`** — the
  LM7171 × 3 + MCP4921 + RCA40673 signal flow isn't captured in this
  doc yet. See `cw_envelope_keyer.md` for the design intent; the
  as-built vfo_complete sheet may deviate.
- **Q3/Q7 exact bias network values** — the level-shift and safety-cut
  MOSFET networks are drawn on the arduino sheet but not called out
  here. If bias values become critical (e.g., threshold margin),
  document them here or in a dedicated `keyer_gate2.md`.

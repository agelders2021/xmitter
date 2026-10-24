# Control Board Functional Blocks

> **⚠ 2026-10-23 — KeyUp signal chain retired.**
>
> The entire "Keying (KeyUp signal chain)" section below describes the
> original Q11/Q12 PNP level-shifter mute topology, which was retired
> when sim showed it did not actually cut off the 40673 DGFET (only
> ~2.6:1 on/off ratio — the lower cascode stays conducting with G1
> biased above V_TO). Rev D replaces this with an **LM7171 offset-mute
> op-amp (U10)** that remaps the DAC's 0–5 V output to G2 −3.1 V to
> +5 V via a 5.1 V Zener reference and an R20/R23 feedback network. The
> op-amp's intrinsic DC offset drives G2 below V_TO when the DAC writes
> 0, with no separate KEY_UP GPIO signal. **The KEY_UP net is
> eliminated from the design.** See `revD_prelayout_review_handoff.md`
> "DGFET keyer mute topology" and `Master_Description.md` §2 for the
> current scheme.
>
> Other blocks in this doc (relay assignments, CD14538B heartbeat
> watchdog, TR_SENSE interlock, J13 power-migration header) remain
> current and unaffected.

Captures the *function* of each block on the analog (control) board that
isn't obvious from the schematic. Written 2026-09-29 during a schematic
review pass; updated 2026-10-12 to reflect SS PA integration and
tube-PA-as-future-upgrade framing.

Scope: analog board (`KiCAD/analog/`) sub-sheets `arduino.kicad_sch` and
`vfo_complete.kicad_sch`. The interface sheet is straightforward (RJ45
umbilical + AM26LS32 differential receiver) and doesn't need block-level
prose. For the SS PA board's own blocks (fault_shutdown, pa_stage) see
`Documentation/ss_pa.md`.

### Which blocks are active vs reserved

Blocks described here fall into two groups:

- **Active for the current SS PA build**: KeyUp signal chain,
  T/R relay (J6), TR_SENSE interlock, J13 power distribution,
  RJ45 umbilicals (J4 to frontpanel, J31 to ss_pa)
- **Reserved for potential future tube-PA upgrade (circuitry
  present, output connectors DNP)**: HV primary contactor (J7),
  HV inrush limiter (J8), heartbeat watchdog monostable U18 that
  kills the HV primary on firmware hang, cathode-current sensing
  (I_CATHODE_A/B via J17/J18/J19 DNP), grid bias control
  (GRID_CTL_A/B via J23/J24 DNP). All drawn, net-connected, and
  firmware-ready — un-DNP the connectors and build the external
  cables if a tube amp is added later.

## Keying (KeyUp signal chain)

**KeyUp** is the firmware-driven RF enable/disable line. It exits the
Metro ESP32-S3 through the PCF8575 I²C port expander (U17 P8) and
propagates through the level-shift transistor pair Q12→Q11 (both
2N3904 NPN) into `Gate 2` on the RCA40673 dual-gate mixer MOSFET
(the DGFET keyer) in the VFO chain. The pair is a two-stage cascade:
KeyUp → R50 → Q12 base; Q12 emitter → R48 → Q11 base; Q11 collector
→ Gate 2 (through a 1 kΩ series resistor to the MCP4921 DAC VoutB
— the resistor protects the DAC during mute, see
`Documentation/2026-10-11-project-audit.md` for the design history).

Behavior:

- **KeyUp = HIGH → RF muted.** Q11 saturates and pulls `Gate 2` low,
  biasing the RCA40673's second gate below its conduction threshold.
  RF drive to the LM7171 PP collapses.
- **KeyUp = LOW → RF enabled.** Gate 2 returns to the envelope voltage
  from the MCP4921 DAC and the DGFET passes the Si5351-derived carrier
  through, modulated by the raised-cosine envelope.

**For the SS PA build (current)**: firmware zeros the MCP4728
`Bias_A_Raw`/`Bias_B_Raw` DAC channels during KeyUp = HIGH, which cuts
off the IRF510s. Redundant with the Gate 2 mute path (which cuts RF
drive before it ever reaches the PA).

**If the tube PA upgrade is added later**: firmware would also slam
the OPA454 grid bias generator (MCP4728 VC/VD → GRID_CTL_A/B →
OPA454) to cutoff during KeyUp = HIGH. Two mute mechanisms:

- Fast electronic cutoff via Gate 2 (µs response, precise envelope
  shaping via `cw_envelope_keyer.md`)
- Deep DC cutoff via grid bias (ms response, keeps PA idle current
  at zero during long key-up intervals so plate dissipation stays
  low). Not active until the tube PA is built.

## Relay assignments

Three 12 V coil relays are driven from the analog board. Each coil has a
1N4001 flyback diode across it. Each relay is switched by a 2N7000
MOSFET on the analog board, with the coil supply on pin 2 of the
corresponding screw terminal.

- **J6 → Transmit/Receive relay.** Active. Antenna switching —
  NO/NC contacts route the antenna between the receiver input and
  the transmitter's output LPF.
- **J7 → HV primary contactor.** Reserved for tube-PA upgrade.
  Would switch the AC primary of the high-voltage plate transformer
  (main HV enable). No HV to switch in the current SS PA build;
  coil driver circuitry is populated and firmware can toggle it,
  but the external HV supply doesn't exist until a tube PA is built.
- **J8 → HV inrush current limiter.** Reserved for tube-PA upgrade.
  Would short out the inrush current limiter resistor once the HV
  filter caps have charged. Sequence (when tube PA is built):
  J7 closes → resistor drops the initial charging current → after a
  firmware delay, J8 closes to short the resistor for full-current
  operation.

Coil-driver MOSFETs on the arduino sheet:

- Q4/Q5/Q6 = 2N7000, drains → J6/J7/J8 pin 1 respectively. Gates
  driven by the PCF8575 U17 (P13/P14/P15).
- **Q7 = HV primary safety cut.** Gate driven by the CD14538B U18
  monostable Q_A output, drain → J7 (HV primary relay). This is
  the hardware kill-switch (see next section).

## Heartbeat watchdog (CD14538B monostable) — reserved for tube-PA upgrade

Will protect the HV rail against firmware hangs if a tube PA is
added later. The Metro ESP32-S3 is expected to periodically toggle
PCF8575 U17 P12, which triggers the CD14538B U18 dual monostable's
A-side. As long as the retriggers keep arriving, Q_A stays asserted
and Q7 keeps the HV primary relay enabled. If the retriggers stop
(firmware crash, I²C hang, whatever), the monostable times out, Q_A
drops, Q7 opens, and J7 (HV primary) opens.

Not functionally relevant for the current SS PA build because there
is no HV rail — but the circuitry is in place for the future upgrade.
The SS PA has its own independent hardware fault latch (see
`Documentation/ss_pa.md` fault_shutdown section) that doesn't
depend on this watchdog.

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

- `Documentation/ss_pa.md` — the active PA board (SS, IRF510 PP,
  10 W QRP). RJ45 umbilical to analog J31, bias / sense / fault
  signal flow, hardware overcurrent latch
- `Documentation/cw_envelope_keyer.md` — envelope shaping detail
  (raised-cosine LUT, MCP4921 DAC, 25 µs tick). Covers the *shape* of
  the envelope; this doc covers the *gating* signals around it
- `Documentation/grid_bias.md` — OPA454 bias generator for the
  (future-upgrade) tube PA
- `Documentation/pa_cathode_monitor.md` — cathode-current fault
  chain for the (future-upgrade) tube PA; feeds the GRID_BLOCK_CRASH
  signal that appears on arduino / bias / protoshield sheets
- `Documentation/front_panel_interface.md` — RJ45 umbilical pinout
  (analog ↔ frontpanel)
- `Documentation/i2c_bus.md` — PCF8575 addresses (0x20 on this
  board, 0x21 on the front panel)
- `Documentation/2026-10-11-project-audit.md` — recent project-wide
  signal-consistency audit, including the Q11 series-R finding on
  the KeyUp mute path

## Open items / not yet documented

- **VFO envelope chain topology on `vfo_complete.kicad_sch`** — the
  LM7171 × 3 + MCP4921 + RCA40673 signal flow isn't captured in this
  doc yet. See `cw_envelope_keyer.md` for the design intent; the
  as-built vfo_complete sheet may deviate
- **Q11/Q12 exact bias network values** — the level-shift MOSFET
  network is drawn on the dac sheet but not called out here. If
  bias values become critical (e.g., threshold margin), document
  them here or in a dedicated `keyer_gate2.md`

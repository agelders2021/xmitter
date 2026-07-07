# Design Review — 2026-07-05

End-of-phase conceptual review of the analog control board. Focus:
design flaws, missing safety measures, silent single-points-of-failure,
firmware / hardware boundary consistency. NOT an implementation-nit
review — footprint verification and pin-order checks live in
`front_panel_interface.md` and `pcb_fab_checklist.md`.

Scope of "this phase": the analog control board schematic (bias sheet,
buffer_keyer, VFO, arduino, interface). Excluded: PA / driver / balun /
LPF sheets (Phase 3–5), front-panel sheet population, firmware
implementation, power supply (separate project).

---

## Bottom line

Design is conceptually sound. The 7-layer cathode failsafe, DPDT T/R
relay + TR_SENSE confirmation, RS-422 signal chain with 2.2 k / 10 k
voltage-divider level shift, and the I²C address plan are all
appropriately robust.

Three real concerns worth resolving before PCB fab, plus a small
housekeeping list. No blockers for proceeding to PCB layout.

---

## Real conceptual concerns

### C1. MCP4728 EEPROM reprogram single-point-of-failure — RESOLVED 2026-07-06

**Original concern.** Si5351 factory address is 0x60. MCP4728 factory
address is also 0x60. The original topology had SDA/SCL on the PCB
traces coming from the Si5351 breakout, with MCP4728 chained via
STEMMA QT off the Si5351. Firmware ran a one-time EEPROM reprogram of
the MCP4728 to 0x62 on first boot. If that reprogram failed silently,
both devices remained at 0x60 and the Si5351 became unreachable → no
VFO clock → rig unbootable.

**Resolution (2026-07-06).** Topology flipped so the MCP4728 sits on
the STEMMA QT chain closer to the Metro, and its 0.1" header carries
SDA/SCL to the PCB traces:

    Metro STEMMA QT ─── MCP4728 STEMMA IN
                         │
                         MCP4728 0.1" header (SDA/SCL) ─── PCB traces ─── PCF8575 x2 + RJ45
                         │
                         MCP4728 STEMMA OUT ─── (optional cable) ─── Si5351 STEMMA IN

Corresponding schematic changes: **SDA/SCL board connections removed
from the Si5351 breakout**; MCP4728's SDA/SCL pins (3, 4) are now the
ones that leave the breakout and reach the PCB traces. Si5351 gets I²C
only via a STEMMA QT cable from the MCP4728, and that cable is
installed *after* the reprogram.

**Why this closes the single-point-of-failure:**

- During initial EEPROM reprogram, the MCP4728-to-Si5351 STEMMA cable
  is NOT installed. Only the MCP4728 is on the I²C bus (plus the two
  PCF8575s at 0x20 and 0x21, which don't collide with 0x60). No
  address collision possible.
- Reprogram completes cleanly. MCP4728 is now at 0x62.
- User installs the STEMMA QT cable from MCP4728 OUT to Si5351 IN.
  Bus now has: Si5351 (0x60), MCP4728 (0x62), PCF8575 x2 — all
  distinct addresses, all reachable.
- If the reprogram ever fails, the recovery is trivial: unplug the
  Si5351 cable, retry the reprogram with the MCP4728 alone on the
  bus. No firmware-triggered dance, no hidden state.

**No firmware sanity-check complexity needed** — the topology
guarantees that the bus can't be in a collision state during the
reprogram procedure, so firmware can be minimal.

**Setup checklist added to `build_checklist.md` Phase 1** — physical
"add this cable last" procedure documented step by step.

### C2. K_MAIN mains-interlock relay is not schematically represented

- **What it does.** K_MAIN is an AC relay that gates the primary side
  of the HV transformer. Firmware heartbeats it; a firmware crash /
  reset / power loss drops the relay, killing AC to the HV supply.
  Last-ditch safety.
- **Where it lives.** Per `2026-06-16-supply-and-pcb-strategy.md`, it's
  part of the separate power-supply project.
- **Concern.** Because it protects the outside world (fire, electric
  shock) when firmware fails catastrophically, its interface with the
  analog board is a critical hand-off. That interface is currently only
  documented in `build_checklist.md` Phase 4 — nothing on a schematic.
- **Actionable.** Add a note somewhere (text note on the arduino sheet
  or an addendum to `2026-06-16-supply-and-pcb-strategy.md`) explicitly
  stating: "K_MAIN relay + heartbeat monostable + driver: NOT on the
  analog control board; see [power-supply project] for topology and
  wiring. Analog board provides one GPIO signal `MAINS_HEARTBEAT`
  which needs to route to the K_MAIN driver via [connector TBD]."

### C3. +12 V rail source on the analog board is ambiguous

- **Documented as open** in `grid_bias.md`. Three plausible sources for
  the analog board's +12 V rail:
    - (a) Metro's Vin passthrough (USB or DC jack).
    - (b) Dedicated +12 V supply input via a connector.
    - (c) Local regulation from a higher rail.
- **Failure-mode analysis.**
    - **(a)** puts the Metro's on-board regulator on the safety-critical
      path. A Metro USB disconnect kills +5V downstream (via LM7805)
      which feeds RS-422 receiver, envelope keyer, and cathode monitor
      — all analog-board circuits.
    - **(b)** needs a +12 V connector footprint on the analog board.
      Not currently drawn. Adding after PCB fab is expensive.
    - **(c)** is unlikely given the available rails.
- **Decide now, before PCB layout starts.** If (b), add the connector
  footprint to the Interface sheet or a new "Power In" area on the
  arduino sheet. Cheap to add now; ~$50 respin later.

---

## Correctly deferred (not concerns)

- PA / driver / balun / LPF sheets are stubs — Phase 3–5 work
- Front-panel sheet is partial (PCF8575, Encoder_5734 stub; needs LCD +
  paddle jack + panel LEDs, and Encoder_5734 gets replaced by 2× QT
  rotary encoders when populated)
- HV in-rush bypass relay driver (third 2N7000 + connector) on arduino
  sheet — user flagged
- Paddle inputs (D5, D6) — user flagged
- Firmware scaffold under `firmware/` — first task of next phase

---

## Housekeeping items (already known, not conceptual)

- Text note conflict on the arduino sheet — note [1] still calls J8
  "HV Inrush limiter"; note [2] correctly identifies it as
  TR_SENSE
- Text note [3] references `J50` which no longer exists (replaced by
  J5, the RCA jack)
- Custom footprint dimensions unverified — RJE1D-188 (5 items),
  Adafruit PCF8575 breakout (Y-offset), I²C QT rotary encoder (pin
  order + Y-offset). Blocking for PCB fab per
  `front_panel_interface.md` "Open items"

---

## Confirmed conceptually sound

The following passed audit — listed for the record so future-you knows
they were checked and cleared, not left as unknowns.

- **7-layer cathode failsafe** correctly implemented. Bias-slam via
  Q2/Q3 2N7000 pulls both grid ports to the −85 V rail within µs of
  `GRID_BLOCK_CRASH` asserting.
- **Diode-OR combiner** — either LM393 comparator can fire the crash
  line; correct polarity for open-collector + external pull-up + diode
  isolation. D5/D6 with R19/R25 as pull-ups.
- **Grid-bias default state.** MCP4728 EEPROM code 0 → OPA454 output
  = −85 V (deep cutoff) at cold boot, before firmware runs. Fail-safe.
- **I²C address plan.** 0x20, 0x21, 0x36, 0x37, 0x60, 0x62 — no
  collisions with each other, no collisions with reserved I²C
  addresses.
- **T568B CAT6 pin assignment.** MBL-600 differential pairs on twisted
  pairs 3 and 4 (noise cancellation). SDA/SCL on pair 2. +5V/GND on
  pair 1.
- **Single-point cable-shield ground** at the PCB end (via RJE1D-188
  shell tabs) — prevents ground loops through the aluminum shield can
  or chassis.
- **DPDT T/R relay + TR_SENSE topology.** Both throw contacts of the
  second pole actively driven — NC to +3.3 V, NO to GND. TR_SENSE
  reads HIGH in RX, LOW in TX-confirmed. Firmware waits for the
  falling edge before enabling PA drive. No pull-up dependence, no
  floating states.
- **RS-422 receiver + 2.2 kΩ / 10 kΩ level-shift divider math.** At
  typical V_OH = 3.4 V, ESP32 pin sees 2.79 V (well above V_IH_min
  = 2.475 V). At worst-case V_OH = 4 V, ESP32 pin sees 3.28 V
  (well below abs-max 3.6 V).
- **Cathode-monitor pin choice** — I_CATHODE_A/B on D8/D9 (ADC1).
  Correct per the WiFi/BLE-on-ADC2 concern.
- **AM26LS32ACN enable pins to GND** — active-low ~G enables all
  receivers via OR-logic per datasheet. Routing choice made for GND
  proximity.
- **Bypass cap distribution.** 100 nF ceramic at every IC VCC pin; 10
  µF bulk near LDOs and near noisy loads.
- **Envelope keyer chain.** MC1496 as 4-quadrant multiplier + LM7171
  (~10 MHz GBW) post-amp. Sufficient bandwidth for CW envelope
  (baseband to ~200 kHz), DC-coupled path works.
- **Split DAC role.** MCP4921 SPI DAC for envelope (needs speed),
  MCP4728 I²C DAC for bias (DC only). Correct role assignment.
- **Voltage divider on TR_SENSE at C38.** RF-filter cap right at the
  connector entry, junction-tied with C38 pin 1 + wire to Metro A5 +
  wire from J8 pin 2. Good RF hygiene for a long wire run near the
  PA.

---

## Explore-agent findings that were false-positives

Documented so future audits don't re-raise these:

- **"Dual cathode labels on bias sheet: I_CATHODE_A/B vs
  CATHODE_SENSE_A/B are in conflict."** Not a conflict. Two distinct
  signal-chain nodes:
    - `CATHODE_SENSE_A/B` (input to bias sheet): raw sense voltage
      from the PA sheet's cathode sense resistor, routed to bias sheet
      via shielded coax per `pa_cathode_monitor.md` "Sense cable"
      section
    - `I_CATHODE_A/B` (output from bias sheet): level-conditioned
      analog voltage going to Metro's ADC1 for firmware monitoring
    - Both labels legitimately exist on the bias sheet — one at the
      buffer input, one at the buffer output. Not stale.
- **"Interface sheet's RS-422 receiver is not yet wired."** It is —
  U15 AM26LS32ACN, R100/R101 (120 Ω termination across differential
  pairs), R26/R27/R28/R29 (voltage dividers 2.2 kΩ + 10 kΩ), bypass
  caps (10 µF + 100 nF), enable pins to GND, VCC/GND, hierarchical
  outputs `MBL600_A` and `MBL600_B` at the divider midpoints. All in
  place.
- **"Second PCF8575 on the main board is not yet wired."** It is — U17
  on the arduino sheet at address 0x21 (A0 jumper closed), SDA/SCL
  hierarchical labels at U17's I²C pins, bypass caps C36 (100 nF) +
  C37 (10 µF).
- **"TR_SENSE not yet drawn."** It is — J8 connector with C38 filter
  cap at the connector entry, wired via junction to Metro A5. J8 pin 1
  to +3.3 V for the DPDT NC contact; NO contact to GND at the relay
  itself.

---

## Recommended next-phase work order

Before PCB layout starts:

1. ~~Address MCP4728-reprogram single-point-of-failure~~ **RESOLVED**
   2026-07-06 by flipping the STEMMA QT chain so MCP4728 is the
   PCB-trace anchor and Si5351 is the "add-last" cable (**C1**)
2. Decide +12 V source and add connector footprint if needed (**C3**)
3. Document K_MAIN interlock boundary (**C2**)
4. Verify custom footprint dimensions against physical parts or
   datasheet drawings (see `front_panel_interface.md` "Open items")

During or after PCB layout:

5. Text-note housekeeping on arduino sheet (J8, J50 → J5)
6. Fill in pending items — paddle inputs (D5, D6), third relay driver
   for HV in-rush bypass, TX LED wiring

None of the above are design flaws. Just polish and physical
verification before gerbers ship.

**Verdict: proceed to PCB layout with confidence once items 1–4 are
addressed.**

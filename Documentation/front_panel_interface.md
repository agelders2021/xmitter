# Front-Panel Interface

The transmitter's front panel (display, encoders, indicator LEDs, paddle
input) connects to the main PCB through a single shielded CAT6 umbilical
terminated in a shielded RJ45. This doc describes the physical topology,
signal map, and — most importantly — the open items that must be verified
before PCB fab.

Related docs:

- `Documentation/2026-06-16-supply-and-pcb-strategy.md` — larger-scope PCB
  partition (which board this interface lives on).
- `Documentation/cw_envelope_keyer.md` — firmware side of the paddle and
  console I/O.

Related schematic: `KiCAD/interface.kicad_sch` (page 10 of the root
schematic hierarchy). Was added 2026-07-02.

Related footprint: `KiCAD/xmitter.pretty/Amphenol_RJE1D-188_Horizontal_Shielded.kicad_mod`.

---

## Physical topology

- **Front panel** holds: WH2004A 20×4 LCD, MBL-600 optical encoder (VFO
  tuning), 2× Bourns PEC11-4 mechanical encoders (STEP and FUNC), the
  paddle jack, and front-panel status LEDs.
- **Vector-board module** mounts directly behind the LCD, inside a small
  aluminum shield can that the builder will fabricate. Holds:
    - Adafruit PCF8575 I²C 16-GPIO expander (drives the LCD in 4-bit mode
      and reads the two mechanical encoders + paddle + spare LEDs).
    - Bypass caps: 10 µF electrolytic + 100 nF ceramic on both PCF8575 Vcc
      and LCD Vcc, physically close to each part.
- **Cable**: shielded CAT6 (STP), one end factory-terminated in an RJ45
  plug, the other end cut off and soldered directly into the vector
  board. Cable shield is grounded only at the PCB end (see below).
- **Main-PCB socket**: **Amphenol RJE1D-188-21401**
  (Mouser 523-RJE1D18821401). Shielded 8P8C, right-angle THT, tab-down,
  CAT5e-rated, 50 µ" gold contacts, no LEDs, no integrated magnetics.
  2 pcs in the current Mouser cart.

## T568B pin map

CAT6 has four twisted pairs; assigning signals to pairs correctly is what
makes the wiring noise-immune. Using T568B:

- Pin 1 (white/orange) — **SDA** (pair 2)
- Pin 2 (orange) — **SCL** (pair 2)
- Pin 3 (white/green) — **MBL_A_P** (pair 3)
- Pin 4 (blue) — **+5V** (pair 1)
- Pin 5 (white/blue) — **GND** (pair 1)
- Pin 6 (green) — **MBL_A_N** (pair 3)
- Pin 7 (white/brown) — **MBL_B_P** (pair 4)
- Pin 8 (brown) — **MBL_B_N** (pair 4)

Rationale for the pairing choices:

- **Pair 3 (green) and pair 4 (brown)** carry the MBL-600 A± and B±
  differential outputs. RS-422 differential gets the full noise-rejection
  benefit of the twist.
- **Pair 1 (blue) — +5V / GND.** Center pair position; keeps the power
  return tightly coupled to +5V.
- **Pair 2 (orange) — SDA / SCL.** Not ideal (both are active open-drain,
  no natural common return) but works fine at 100 kHz over ~1 m. The
  PCF8575's SDA/SCL inputs are 5V-tolerant, so no level shifter is needed
  in-line.

## Grounding rule (SINGLE-POINT)

- Cable shield ties to chassis GND **only at the main-PCB end**, through
  the RJE1D-188 shell tabs.
- Do NOT connect the shield to the aluminum shield can at the vector-board
  end — that would create a ground loop through the enclosure.
- The vector-board module is grounded via pin 5 of the RJ45 (GND
  conductor), NOT via the shield.

## RS-422 termination

The MBL-600 puts out RS-422 differential from a line driver. Termination
is at the **receiver end** (main PCB), not the source:

- **R100 = 120 Ω** across MBL_A_P and MBL_A_N
- **R101 = 120 Ω** across MBL_B_P and MBL_B_N

Both live on `KiCAD/interface.kicad_sch`. Footprint
`R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal` (matches the axial
resistor stock used elsewhere on the analog board).

The RS-422 **receiver chip** (AM26LS32ACN quad receiver or 74LVC2G17 dual
Schmitt buffer) is **not yet placed** on the schematic. See open items.

---

## Open items (verify before PCB fab)

Any of these can wait, but each must be resolved before the analog-board
PCB gerbers ship to the fab house.

### RJE1D-188 footprint verification

`KiCAD/xmitter.pretty/Amphenol_RJE1D-188_Horizontal_Shielded.kicad_mod`
was drafted from the datasheet text; only the signal-pin array was
derivable exactly. Everything else needs a caliper or datasheet-drawing
check.

- [x] **Signal pin array (P1–P8)** — exact from datasheet: 8.89 mm total
      span, 1.27 mm row offset, 2.54 mm in-row pitch. No verification
      required.
- [ ] **Shield mount post X-spacing** — assumed 10.00 mm (posts at
      x = ±5.00 mm). Verify against datasheet p.2 "RECOMMENDED PCB LAYOUT".
- [ ] **Shield mount post Y-offset from pin array** — assumed +3.96 mm.
      *Least confident dimension* — this is where the drawing's leader
      lines are ambiguous from OCR text.
- [ ] **Alignment peg X-spacing** — assumed 8.80 mm (pegs at x = ±4.40 mm).
- [ ] **Alignment peg Y-offset from pin array** — assumed −3.96 mm. Also
      only lightly grounded in the datasheet text.
- [ ] **Four shield-tail hole positions** — placed at (±6.50, ±2.54) as
      pure guess. Verify against the "12 PLCS Ø0.90" callout in the
      datasheet drawing; likely at the shell's tab feet.

If any of these is wrong, open the footprint in KiCad's footprint editor
and drag the offending pad to the right coordinate. It's ~1 minute per
pad.

### Schematic — Interface sheet is not yet complete

`interface.kicad_sch` currently has:

- Hierarchical labels (6): SDA, SCL, MBL_A_P/N, MBL_B_P/N.
- Termination resistors R100 / R101.
- Text notes with the T568B pin map and future-control-function
  placeholders.

**Still to add:**

- [ ] The RJE1D-188 RJ45 jack symbol itself (currently a text-only
      placeholder). Symbol lives in KiCad standard library as
      `Connector:8P8C_Shielded` (already linter-injected into the sheet's
      `lib_symbols` block, per the file's current state).
- [ ] The RS-422 receiver — pick between:
    - **AM26LS32ACN** (DIP-16 quad differential-line receiver). Legacy,
      widely stocked, ±7 V common-mode range. Overkill (only 2 channels
      used) but familiar.
    - **74LVC2G17** (SOT-23-6 dual Schmitt buffer). Not a true RS-422
      receiver but works fine if the MBL-600 line driver's common-mode is
      near 3.3 V. Doesn't need a 5 V rail. Requires SMT — probably a
      no-go for this builder (hand tremor).
    - Default choice: AM26LS32ACN in a DIP-16 socket unless there's a
      supply reason to skip 5 V.
  Receiver inputs connect to MBL_A_P/N and MBL_B_P/N (across the 120 Ω
  terminators R100/R101). Receiver outputs become two new hierarchical
  labels (`MBL_A_QUAD`, `MBL_B_QUAD` — single-ended 3.3 V TTL) that route
  up to the Arduino sheet and land on ESP32-S3 PCNT inputs.
- [ ] Add **SDA** and **SCL** hierarchical labels to the Arduino sheet —
      they exist on the Buffer/Keyer sheet and now on Interface, but not
      yet on Arduino. Currently missing, per the summary of prior-session
      pending items.
- [ ] Add **GRID_BLOCK_CRASH** hierarchical label to the Arduino sheet
      (already exposed by the Bias sheet). Enables firmware ADC-based
      fault logging.
- [ ] **MCP4728 LDAC pin** — wire to a spare Arduino GPIO. Required for
      the one-time I²C EEPROM address-reprogram (0x60 → 0x62) to resolve
      the Si5351 address collision. See `build_checklist.md` Phase 1 for
      the collision rationale.

### Control functions — not yet designed

The Interface sheet has a text-note placeholder listing these; none are
schematically drawn or wired.

- [ ] Filament supply on/off relay drive (probably 2N7000 low-side driver
      into a 12 V DPDT or SPDT relay coil, with catch diode) + front-panel
      status LED.
- [ ] HV supply on/off relay drive (similar, sized for whichever K_MAIN
      relay is chosen — see Phase 4 checklist).
- [ ] T/R relay drive — protects the receiver during TX. Fast enough to
      hand off before the envelope starts (< 5 ms). Coax relay body TBD.
- [ ] Front-panel indicator LEDs (TX, fault, VFO-lock). Can hang off spare
      PCF8575 GPIOs, no dedicated wiring needed.

### Ordering

- [x] **Amphenol RJE1D18821401** shielded RJ45 socket — Mouser
      523-RJE1D18821401, 2 pcs. In the current Mouser cart as of
      2026-07-02.
- [ ] **Adafruit PCF8575 breakout** — PID 5904, one for the front panel.
      Not yet ordered.
- [ ] **AM26LS32ACN** RS-422 receiver (if that's the chosen receiver) —
      not yet ordered. Digi-Key or Mouser.
- [x] ~~**BSS138** level shifter~~ — determined NOT needed. PCF8575 has
      5V-tolerant I²C inputs, so 3.3 V Metro can talk to it natively
      without translation. Removed from the working Mouser cart.
- [x] ~~**MCP23017** GPIO expander~~ — determined NOT needed. PCF8575
      alone covers the LCD (7 pins) + both PEC11-4 encoders (6 pins) +
      spare (3 pins). Removed from the working Mouser cart.

### Fabrication (vector board + shield can)

- [ ] Cut and terminate the CAT6 cable to the vector-board end — solder
      each conductor to a labelled pad on the perfboard.
- [ ] Fabricate the aluminum shield can (~50 × 30 × 15 mm minimum) to
      cover the vector-board module. Ensure it does NOT touch the cable
      shield (grounding rule above).
- [ ] Mount the vector board behind the LCD; route encoder + paddle wires
      to the PCF8575 pins.

---

## Signal chain (end-to-end, for reference)

MBL-600 encoder (front panel, +5 V bus power)
  → RS-422 line driver inside the encoder
  → 4 conductors through the CAT6 cable (pairs 3 and 4)
  → RJE1D-188 socket on main PCB
  → 120 Ω terminators R100 / R101 (interface sheet)
  → AM26LS32ACN differential receivers
  → 2× single-ended 3.3 V quadrature signals
  → ESP32-S3 PCNT peripheral inputs (Arduino sheet)

LCD + PEC11-4 encoders (front panel, +5 V bus power)
  → PCF8575 I²C GPIO expander on vector board (also +5 V)
  → 2 conductors through CAT6 (pair 2, SDA and SCL)
  → RJE1D-188 socket on main PCB
  → I²C bus (shared with Si5351 at 0x60 and MCP4728 at 0x62)
  → ESP32-S3 SDA/SCL pins (Arduino sheet)

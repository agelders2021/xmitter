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

Related footprints (all custom, in `KiCAD/xmitter.pretty/`):

- `Amphenol_RJE1D-188_Horizontal_Shielded.kicad_mod`
- `Adafruit_PCF8575_Breakout.kicad_mod`
- `Adafruit_I2C_QT_Rotary_Encoder.kicad_mod`

Related symbols (in `KiCAD/xmitter.kicad_sym`):

- `Adafruit_PCF8575_Breakout`
- `Adafruit_I2C_QT_Rotary_Encoder`

---

## Physical topology

- **Front panel** holds: WH2004A 20×4 LCD, MBL-600 optical encoder (VFO
  tuning), 2× Bourns PEC11-4 mechanical encoders (STEP and FUNC), the
  paddle jack, and front-panel status LEDs.
- **Vector-board module** mounts directly behind the LCD, inside a small
  aluminum shield can that the builder will fabricate. Holds:
    - Adafruit PCF8575 I²C 16-GPIO expander (I²C addr 0x20) drives the LCD
      in 4-bit mode and reads the paddle + front-panel LEDs. **No longer
      handles the mechanical encoders** — see next item.
    - 2× Adafruit I²C QT Rotary Encoder breakouts (PID 4991), one for STEP
      and one for FUNC. Each carries a PEC11-pinout mechanical encoder
      whose quadrature decoding + button debounce lives on the breakout's
      onboard SAMD09 (seesaw firmware). This drops ~200 lines of
      quadrature/debounce/state-machine code in the ESP32-S3 firmware
      down to a couple of I²C reads per encoder. Addresses:
        - STEP: **0x36** (default, no jumpers soldered)
        - FUNC: **0x37** (A0 address jumper soldered closed on the back
          of the breakout)
    - Bypass caps: 10 µF electrolytic + 100 nF ceramic on **LCD Vcc only**,
      physically close to the LCD's Vcc pin. The PCF8575 and both QT
      encoder breakouts already have VCC bypassing and 10 kΩ I²C pull-ups
      on-board (per each breakout's datasheet), so no additional caps at
      those parts.
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

## Interrupt handling (decision: polling now, INT hardware reserved)

**No INT cable on first build. Firmware polls at 100 Hz. Hardware
provisions exist to add INT later without touching the PCB.**

Reserved on the analog board (added 2026-07-03):

- **Metro D4** — reserved as `ENC_INT` input (open-drain, active-low).
  Was previously labeled `D4/DIT` in the Metro symbol; freed up when the
  paddle moved to the PCF8575.
- **R102 = 10 kΩ pull-up** from D4 to +3.3 V — makes D4 idle high when
  no cable is connected, so ERC/DRC and firmware bring-up are clean
  even without a cable installed.
- **J50 = 2-pin 0.1"-pitch header** on the arduino sheet, labeled
  `ENC_INT_CABLE`. Pin 1 = ENC_INT signal, pin 2 = GND. **Leave
  unpopulated on first build.** When (if) the INT cable is added later,
  install the header, run a shielded 2-conductor cable from J50 to the
  vector board, and tie both QT encoder INTs + the PCF8575 INT together
  at the vector board end.
- Footprint chosen: `PinHeader_1x02_P2.54mm_Vertical`. Standard 0.1" pin
  header slot. Fits any 2-pin plug or dupont wires or gets skipped and
  wired direct.

Firmware bring-up with no cable installed:

    // D4 configured as input; external 10K pull-up holds it high.
    // No internal pull-up needed. Nothing else to do.
    // If a cable is added later, configure attachInterrupt(D4, FALLING).

Decision made 2026-07-03 after evaluating whether to add a second
shielded cable for the wired-OR'd INT signals from the two QT rotary
encoders and the PCF8575. Skipped because:

- The seesaw SAMD09 inside each QT encoder has a **hardware quadrature
  decoder with an internal 32-bit accumulator**. Every tick is captured
  on the seesaw side regardless of when the Metro reads. Polling never
  misses ticks; it only delays the moment the Metro *notices* a change.
- At 100 Hz poll rate, the worst-case knob-turn-to-VFO-update latency is
  10 ms — well below human perception (~50 ms feels instant).
- I²C bandwidth cost is trivial: STEP + FUNC + PCF8575 reads total
  ~400 µs per poll cycle; at 100 Hz that's 4 % bus utilization.
- The Metro is USB-powered, so idle-CPU-load savings from interrupts
  don't matter here.
- The RJ45 has no spare conductors; adding INT means either upgrading
  to a DE-9 connector or running a second shielded cable, both of which
  cost more mechanical work than the polling loop saves in firmware.

**Velocity-adaptive tuning** (rate-based step multiplier — turn fast,
each tick moves the VFO more) is handled entirely in firmware from the
poll loop:

    velocity = (current_position - last_position) / (now - last_poll_us)
    multiplier = table_lookup(velocity)   // e.g., 1× / 10× / 100×
    step_hz = delta_ticks * base_step * multiplier

This is exactly how Kenwood / Yaesu / Icom rigs implement their VFO
accelerator. INT would give sub-poll-period timing on **when** a change
happened but adds nothing to velocity measurement itself — you still
compute `Δposition / Δtime` either way.

If firmware measurement later shows polling isn't adequate (unlikely),
adding INT is a small hardware change:

- Add a wired-OR at the vector board (all three open-drain INTs
  tied together)
- Add a second shielded 2-conductor cable (RG-174 or similar) with any
  small connector (RCA / 2.5 mm TRS / JST)
- Add a 10 kΩ pull-up to +3.3 V on the Metro side
- Wire to one spare Metro GPIO

Not blocking the current design. Just documented so future-me knows the
option exists and why it wasn't taken.

---

## Open items (verify before PCB fab)

Any of these can wait, but each must be resolved before the analog-board
PCB gerbers ship to the fab house.

### RJE1D-188 footprint verification — RESOLVED 2026-07-12

`KiCAD/xmitter.pretty/Amphenol_RJE1D-188_Horizontal_Shielded.kicad_mod`
was reworked on 2026-07-12 after the builder read the actual datasheet
drawing (`Documentation/Components/p-rje1d-188-x1x01.pdf`) and gave the
exact coordinates directly. Original interpretation (extracted from
datasheet OCR text) was wrong on multiple dimensions.

Final layout, in order from PCB edge to pin block, along the Y axis:

- **PCB edge** at Y = −8.8 mm (dashed reference on Dwgs.User)
- **2 Ø1.57 plated shield tails** at Y = −6.79 mm, X = ±7.425 mm
  (14.85 mm spacing). Tied to GND — this is the shield ground.
- **2 Ø3.00 NPTH plastic locating posts** at Y = 0, X = ±5.0 mm
  (10.00 mm spacing). Housing alignment; no electrical connection.
- **Front pin row (odd 1, 3, 5, 7)** at Y = +3.96 mm.
- **Back pin row (even 2, 4, 6, 8)** at Y = +6.50 mm.
- Rows staggered by 1.27 mm in X. Total pin 1 → pin 8 X span 8.89 mm.

**Key correction from the original draft:**

- Original interpretation had the Ø3.00 holes as shield ground (plated)
  and the Ø1.57 holes as plastic pegs (NPTH). The datasheet actually
  reverses these — Ø3.00 are the plastic housing pegs, Ø1.57 are the
  metal shield tails. The current footprint has this right.
- There are only 2 shield tails (not 4 as originally guessed).

- [x] All footprint coordinates match datasheet dimensions.
- [x] Ø3.00 marked NPTH.
- [x] Ø1.57 marked plated, tied to GND for shield ground.

### PCF8575 breakout footprint verification

`KiCAD/xmitter.pretty/Adafruit_PCF8575_Breakout.kicad_mod`.

- [x] **Board outline (40.64 × 17.78 mm) and mounting-hole X/Y (1.40 × 0.50 in
      spacing)** — exact from datasheet page 22 fab print. No verification
      needed.
- [x] **Pin count, labels, and X spacing (12 pins per row, 2.54 mm pitch)** —
      exact from the pinout page. No verification needed.
- [ ] **Pin row Y offset from board edge** — I placed both rows at
      `y = ±6.35 mm` (0.10 in, same Y as the mounting holes, offset only in
      X). If the fab print shows a different offset (0.05 in outer edge is
      also common), measure and drag the 24 pads to the correct Y.

### Adafruit I²C QT Rotary Encoder footprint + pin-order verification

`KiCAD/xmitter.pretty/Adafruit_I2C_QT_Rotary_Encoder.kicad_mod` and the
`Adafruit_I2C_QT_Rotary_Encoder` symbol in `xmitter.kicad_sym`.

- [x] **Board outline (25.4 × 25.4 mm) and 4 corner mounting holes on 0.90 in
      spacing** — exact from datasheet page 23 fab print.
- [ ] **6-pin header order** — I placed the 6 THT pads as
      **VIN, GND, SCL, SDA, INT, 3Vo** (left to right) based on the datasheet
      pinout text. The fab-print thumbnail on page 23 is too small to read
      the silkscreen definitively. Compare against the physical breakout's
      bottom-edge silkscreen when it arrives; if any pin is out of order,
      rename the pads in the footprint. The symbol pin numbers use the same
      names, so a footprint rename automatically re-links.
- [ ] **Header row Y offset from board edge** — I placed the row at
      `y = +10.16 mm` (same Y as the bottom mounting holes). Verify from the
      physical part.
- [ ] **FUNC encoder A0 jumper** — solder the A0 pad closed on the back of
      the second breakout to move it from 0x36 to 0x37. Confirmed via I²C
      scan before installing on the front panel.
- [ ] **Encoder body clearance** — the PEC11 encoder sits at 45° on the
      breakout to fit the 1 × 1 in board. Confirm knob/shaft clearance and
      panel-cutout diameter (encoder shaft nut is standard M7).

### Schematic — Interface sheet complete (2026-07-13)

`interface.kicad_sch` now has all the elements needed for the analog
board fab pass:

- **RJ45 jack J4** — `Connector:8P8C_Shielded` symbol with
  `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded` footprint. Wired per
  T568B: pins 1/2 = SDA/SCL, 3/6 = MBL_A_P/N, 4/5 = +5V/GND,
  7/8 = MBL_B_P/N, shield tabs to GND.
- **RS-422 receiver U16** — AM26LS32ACN in a DIP-16 socket. Enable
  pins tied to GND (~G active-low). Bypass C34 100 nF + C35 10 µF.
- **Termination R100 / R101 = 120 Ω** across the two differential
  pairs.
- **Level-shift dividers R26/R27 = 2.2 kΩ + R28/R29 = 10 kΩ** from
  receiver outputs to Arduino inputs — brings 5 V TTL down to 3.3 V.
- **Output labels** `MBL600_A` and `MBL600_B` (global) that reach the
  Arduino sheet's PCNT inputs.

Cross-sheet integration done on the Arduino sheet:

- SDA, SCL, GRID_BLOCK_CRASH, LDAC_4728 labels all present and routed
  to their intended Metro pins.

Still deferred (not blocking this fab pass):

- [~] Filament / HV / T/R relay drivers — text-note placeholders on the
      Interface sheet. Populate later as a daughtercard or hand-wire.

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
      covers the LCD + paddle + panel LEDs; the two mechanical encoders
      moved to dedicated I²C QT encoder breakouts. Removed from the
      working Mouser cart.
- [ ] **2× Adafruit I²C QT Rotary Encoder breakout** — PID 4991, one for
      STEP and one for FUNC. Solder the A0 jumper on the second unit to
      move it from 0x36 to 0x37. Not yet ordered.
- [ ] **2× Bourns PEC11-4 mechanical encoder** (with pushbutton, 24
      detents / 24 pulses) — solder onto the two QT breakouts. May already
      be on hand from the pre-QT-encoder plan; if not, order to match.

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

LCD + paddle + panel LEDs (front panel, +5 V bus power)
  → PCF8575 I²C GPIO expander on vector board (also +5 V)
  → 2 conductors through CAT6 (pair 2, SDA and SCL)
  → RJE1D-188 socket on main PCB
  → I²C bus (shared with Si5351 at 0x60, MCP4728 at 0x62,
    main-board PCF8575 at 0x21, STEP QT at 0x36, FUNC QT at 0x37)
  → ESP32-S3 SDA/SCL pins (via MCP4728 STEMMA QT chain, see below)

STEP + FUNC mechanical encoders (front panel, +5 V bus power)
  → PEC11-pinout encoder on Adafruit I²C QT Rotary Encoder breakout
  → seesaw SAMD09 does quadrature decoding + button debounce on-board
  → same 2 I²C conductors through CAT6 (pair 2, SDA and SCL)
  → RJE1D-188 socket on main PCB
  → I²C bus (STEP at 0x36, FUNC at 0x37; joins the shared bus)
  → ESP32-S3 SDA/SCL pins

I²C bus topology on the main board (2026-07-06):

  Metro STEMMA QT port  ──── STEMMA cable ────  MCP4728 breakout STEMMA IN
                                                      │
                                                      MCP4728 0.1" header (pins 3, 4)
                                                      │
                                                      PCB traces (SDA / SCL)
                                                      │
                                                      ├── Main-board PCF8575 @ 0x21
                                                      └── RJE1D-188 pins 1, 2 → CAT6 pair 2
                                                              │
                                                              ├── Front-panel PCF8575 @ 0x20
                                                              ├── STEP QT rotary @ 0x36
                                                              └── FUNC QT rotary @ 0x37

  MCP4728 STEMMA OUT ── STEMMA cable ── Si5351 breakout STEMMA IN
      (Si5351's own 0.1" header SDA/SCL pads are NOT wired to the PCB.)

The Si5351 STEMMA cable is installed *after* the one-time MCP4728
EEPROM address reprogram procedure — see the reprogram procedure in
`build_checklist.md` Phase 1 for the physical sequencing.

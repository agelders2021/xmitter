# Power Supply and PCB Strategy — 2026-06-16

First-cut decisions on the power supply topology and the PCB partitioning
for the xmitter project, captured during a strategy session.

This is design-intent, not yet drawn or built. The numbers are sized to
the validated PA operating point in `2026-06-08-pa-validation.md`.

## Summary of decisions made this session

- Power supply: **three separate transformers** (filament, HV, driver/LV).
- Inrush limiting: **NTC thermistor + bypass relay** on the HV transformer
  primary. Filaments do not need dedicated inrush limiting.
- PCB partitioning: **two physical boards** — control board (VFO + display
  + MCU + keyer logic) and PA module board (grid bias + cathode monitor).
- Fab house: **JLCPCB** for both boards.
- Surface finish: **HASL** for both boards (cheapest, adequate for the
  pitch and component mix used here).
- EDA tool: **KiCad** for both boards (over DipTrace Free).

The rest of this document captures the reasoning behind each decision so
the trade-offs are recoverable later.

## Power supply

### Rail inventory

The full rail list required by the rig, derived from the design docs.

**B+ (PA plate)**
- Voltage: 600 V DC
- Current: 200 mA average, ~500 mA peak
- Loads: 6146B plate center tap (push-pull pair)
- Tolerance: +/-5% under load

**Screen (PA)**
- Voltage: +200 V (some docs say +225 V)
- Current: ~40 mA total
- Loads: 6146B screens via 100 ohm feed resistors
- Tolerance: +/-10%, well-bypassed

**Driver plate**
- Voltage: +250 V
- Current: ~60 mA
- Loads: 12HG7 plate center tap
- Tolerance: +/-5%

**Driver screen**
- Voltage: +150 V
- Current: ~15 mA
- Loads: 12HG7 screens
- Tolerance: +/-10%

**Negative bias rail**
- Voltage: -105 V raw, -90 V regulated/clean
- Current: ~30 mA
- Loads: OPA454 V- input; bias DACs swing the output between -50 V
  (OPERATE) and -90 V (IDLE) per the two-state bias scheme
- Tolerance: low ripple required (50 mV or better)

**Filament 6.3 V**
- Voltage: 6.3 V AC
- Current: ~4.3 A (2 x 6146B at 1.25 A = 2.5 A, plus 2 x 12HG7 at
  0.9 A = 1.8 A)
- Loads: all four tube heaters
- Tolerance: +/-5%, hum-balanced via filament transformer center tap

**+12 V**
- Voltage: +12 V regulated
- Current: ~500 mA
- Loads: MC1496, LM7171 (x2), TL071, relay coils
- Tolerance: regulated

**-8.3 V**
- Voltage: -8.3 V
- Current: ~50 mA
- Loads: MC1496 VEE pin, TL071 V-, LM7171 V-
- Derivation: zener-clamp off the -105 V bias rail (existing design
  in `20m-leveled-keyed-buffer.md`)

**+5 V**
- Voltage: +5 V regulated
- Current: ~500 mA
- Loads: OPA1641 buffer, LM393 comparators, ADS1115 ADC, MCP4921
  reference

**+3.3 V**
- Voltage: +3.3 V
- Current: ~500 mA
- Loads: Metro ESP32-S3 (via its USB or external power), cathode
  monitor clamp rail
- Notes: stiff bypass needed at clamp node (10 uF bulk) so a fault
  clamp event does not brown out the MCU

### Topology — three transformers

Three separate transformers, each energized in a deliberate sequence.

**T1 — Filament transformer (energized first)**
- Secondary: 6.3 V AC at ~5 A, with center tap for hum balance
- Feeds: all four tube heaters
- Purpose: warmup time of ~30 to 60 seconds before HV is applied
- Suggested Hammond: 167S6 (6.3 V CT at 6 A) or 166L6 (6.3 V CT at
  5.6 A)

**T2 — HV transformer (energized after filament warmup, inrush-limited)**
- Secondary: 500-0-500 V center-tapped
- Filter: choke-input or CLC filter
- Output: B+ at 600 V DC
- Auxiliary secondary: 175-0-175 V for screen rail (regulated to
  +200 V); also a 100 V AC tap for the bias supply (voltage doubler
  to -150 V, regulated to -90 V)
- Suggested Hammond: 270EX (600 V CT at 200 mA) or 272FX (700 V CT
  at 200 mA)
- Gated by: T1-warmup relay, with NTC + bypass relay limiting inrush

**T3 — Driver / LV transformer (energized with T2 or separately)**
- Secondary: 200-0-200 V for driver plate (+250 V) and driver screen
  (+150 V)
- Auxiliary secondary: 12 V AC at ~2 A for the +12 V / -12 V rails
  via LM78xx / LM79xx or LDOs
- +5 V and +3.3 V derived from +12 V via LM2596 buck + LDO, or use
  a single multi-output module (Mean Well RT-65B is a reasonable
  pre-built option for the LV cluster)
- Suggested Hammond: 269BX (250-0-250 at 50 mA, plus 6.3 V winding
  available) for driver plates

### Sequencing

The startup sequence must protect the tubes from cold-cathode HV stress
and protect the rig from inrush surges.

1. Mains on -> +5 V comes up immediately so the ESP32-S3 is awake and
   can run the sequencer
2. T1 (filament) energized -> filament warmup timer starts (30 to
   60 seconds)
3. After warmup -> firmware closes K1 (HV contactor) with NTC still in
   series
4. ~200 ms after K1 -> firmware closes K2 (bypass relay shorting the
   NTC)
5. Bias supply rises first (small RC delay), plate supply last
6. Cathode monitor fault chain (per `pa_cathode_monitor.md`) gates the
   HV contactor; any fault drops K1

### Inrush limiting

Three options considered for the HV transformer primary; recommendation
in bold.

**Option 1 — NTC thermistor + bypass relay (recommended)**
- CL-60 NTC (5 ohms cold, ~0.5 ohms hot) in series with primary
- After ~200 ms a relay shorts it out to eliminate steady-state loss
- Cheap (~$2 part), passive, well-proven, no thermal-cycling concerns
  because the user's cycle time is much longer than the NTC thermal
  time constant

**Option 2 — Bucking auxiliary winding**
- Small 24 V CT secondary on T2, wired in series with primary,
  polarity-reversed
- Reduces primary voltage to ~80% for the first 200 ms via a relay
- More involved transformer spec; better repeatability than NTC

**Option 3 — Triac soft-start / phase control**
- MCU-controlled, ramps RMS over ~10 cycles
- Overkill for this build

### Tube filament inrush

Both the 6146B and 12HG7 are indirectly-heated cathode tubes. The
inrush-limiting literature in the ham/transmitter world is for
directly-heated thoriated-tungsten filaments (3-500Z, 4-1000A class).

Neither the 6146B nor the 12HG7 data sheet calls out a filament inrush
limit. Standard practice is to apply rated heater voltage directly from
a transformer at switch-on. The 12HG7 may have a controlled-warmup
heater designation (RMA-11 second standard, typical for series-string
TV sweep tubes) which would self-limit inrush to a degree; worth
verifying on the GE/Sylvania datasheet but not load-bearing.

Real worry on the filament side is the transformer itself: a cold
toroidal or large E-I primary has 10x inrush regardless of what is
connected. The CL-60 NTC on the filament transformer primary (separate
from the HV NTC) is cheap insurance, but not required.

## PCB partitioning

### Decision: two boards

**Control board** (front-panel area, cool, accessible)
- VFO (Si5351 + buffer)
- Display
- ESP32-S3 Metro (envelope DAC + keyer logic)
- Front-panel I/O, paddle input
- WinKey serial interface

**PA module board** (chassis aft, hot, near tubes)
- 6146B sockets and tank circuit
- Grid bias OPA454 (one per tube)
- Bias DAC (MCP4728)
- Cathode monitor chain (clamp + buffer + comparator + ADS1115)
- Fault interlock to HV contactor

Connected by a short umbilical carrying SPI/I2C and DC supplies.

### Why this partition (not "VFO sensitivity to HV")

The user's initial concern was unintended RF feedback between the bias
circuit and the VFO. After analysis the dominant reason to split is
physical placement and safety creepage, not RF coupling.

The bias and cathode-monitor circuits are mostly slow DC. The OPA454
bias output slews 40 V in 200 us during key transitions — that is
200 V/ms, electrically silent at 14.2 MHz. The cathode monitor
bandwidth is at most 5 kHz (envelope rate).

The actual noise sources near the bias circuit are:

- SPI to the bias DAC (~MHz traffic)
- I2C to the ADS1115 (~400 kHz)
- ESP32-S3 internal clocks, WiFi if enabled
- 120 Hz plate-supply ripple via shared ground

None of these come from the OPA454 itself.

What the VFO actually wants:

- Quiet local ground reference and clean +3.3 V (Si5351 jitter is
  supply-noise-modulated)
- Physical distance from the PA tank (radiated coupling from a 50 W
  class-C cavity is louder than anything from a bias opamp)
- Thermal stability (no warm tubes nearby)
- Shielded enclosure

The natural partition is driven by where things physically have to
live: bias and monitor circuits must be at the tube sockets, VFO and
front-panel logic must be where the operator and cool air are. This
matches the Heathkit / Drake / Collins layout convention.

### Umbilical considerations

- Shielded twisted pair for SPI/I2C (the bias DAC SPI is the loudest
  digital signal in the rig)
- Bias DAC SPI clock at the slowest rate that still settles in 200 us
- Separate clean +3.3 V regulator for the VFO board (do not share an
  LDO with the MCU)
- Star-ground at the PA module end (chassis is the ground reference
  for plate current; control board ties to chassis through a single
  deliberate point)
- One ground return per signal pair on the umbilical

### Board stackup and rules

**Control board**
- 2-layer FR4
- All signals at or below 12 V
- 1 oz outer copper
- HASL finish

**PA module board**
- 2-layer FR4
- HV creepage zones on the bias rail (-105 V) and screen rail
  (+200 V if brought on-board)
- 2 oz outer copper (heater current returns through the board)
- HASL finish
- Recommend keeping +600 V plate supply OFF the PCB if possible;
  bring it directly to the tank circuit via standoff wiring

## Fab house decision

**JLCPCB** chosen as the fab house.

Rationale:

- 5 boards at 100 x 100 mm, 2-layer, HASL, green soldermask: ~$15
  delivered total
- 1-day fab + ~5-10 day shipping from China
- Quality is production-grade; the price reflects volume, not
  cut corners
- Free DFM check
- Customs handled by them; under US de-minimis ($800) threshold
- KiCad has a JLCPCB-specific community plugin
  (`kicad-jlcpcb-tools`) that handles their footprint rotation
  conventions for PCBA

Alternatives considered:

- PCBWay: slight quality and customer-service edge, slightly more
  expensive, better for non-standard stackups; appropriate if JLC
  cannot handle a future requirement
- OSHPark (US): 5-10x more expensive but no customs hassle, fast
  US shipping; worth it for one-off prototypes when shipping time
  matters
- Aisler (EU), Bay Area Circuits, Advanced Circuits (4PCB): more
  expensive, niche use cases

## Surface finish decision

**HASL** chosen for both boards.

Rationale:

- Smallest part pitch in this design is ~0.5 mm (MSOP-10 for the
  MCP4728 bias DAC), comfortably within HASL's range
- Through-hole tube sockets, DIP-8 opamps, and standard SMT
  passives all solder cleanly on HASL
- Hand-soldering or hot-plate reflow does not benefit from ENIG at
  this pitch
- Saves $5-10 per 5-board order

ENIG would be worth the upcharge for:

- 0.4 mm pitch parts or finer
- QFN / BGA packages
- Card-edge connectors
- Repeatedly-probed test points
- Boards that must be hand-soldered cleanly months after arrival

None of those apply here.

## EDA tool decision

**KiCad** chosen for both boards over DipTrace Free.

Rationale:

- DipTrace Free is limited to 300 pins per project. The control
  board (Metro header + Si5351 + LM7171 x2 + TL071 + envelope DAC +
  display + ~80 passives) almost certainly exceeds this. Each
  passive counts as 2 pins. Easy to hit 250-350 pins.
- DipTrace Free is limited to 2 layers (acceptable here, but no
  headroom for a future ground/power split)
- KiCad files are text format — git-friendly, meaningful diffs, OK
  to merge. DipTrace files are binary blobs.
- KiCad has the JLCPCB plugin ecosystem (`kicad-jlcpcb-tools`)
- KiCad library ecosystem (SnapEDA, UltraLibrarian, manufacturer
  downloads) has much wider footprint coverage
- KiCad files are openable forever by anyone, no license required
- DipTrace lives on the hardware-interface machine; primary
  edit/build machine has KiCad

Where DipTrace would still earn its keep: quick breakout boards or
test fixtures during bench bring-up, where ~300 pins is enough, no
need to commit to git, and the autorouter saves an afternoon. Not
the production boards.

## KiCad project structure

For the two-board project, the recommended directory layout in
`KiCAD/` is:

```
KiCAD/
  lib/
    xmitter.kicad_sym       (shared custom symbols)
    xmitter.pretty/         (shared custom footprints)
    3dmodels/               (shared STEP / WRL files)
  control_board/
    control_board.kicad_pro
    control_board.kicad_sch (top sheet)
    vfo.kicad_sch           (subsheet)
    controller.kicad_sch    (subsheet, renamed from arduino.kicad_sch)
    display.kicad_sch       (subsheet)
    envelope_dac.kicad_sch  (subsheet)
    control_board.kicad_pcb
    fab/                    (gitignored)
  pa_module/
    pa_module.kicad_pro
    pa_module.kicad_sch
    grid_bias.kicad_sch
    cathode_monitor.kicad_sch
    pa_module.kicad_pcb
    fab/
```

The shared `lib/` directory means both boards reference one symbol
set. Library tables in each project use `${KIPRJMOD}/../lib/...` so
the references are portable.

### Net classes for the PA module board

The HV creepage rules belong in net classes so DRC catches violations
automatically.

```
Class       Track   Clearance   Used for
Default     0.25mm  0.20mm      Digital, low-V signals
Power       0.50mm  0.20mm      +5V, +12V, GND
HV_BIAS     0.25mm  2.0mm       -105V bias rail
HV_SCREEN   0.30mm  3.0mm       +200V if brought on-board
HV_PLATE    0.50mm  6.0mm       +600V (try to keep off the board)
```

The 2/3/6 mm clearances are conservative; IPC-2221 Table 6-1 gives
the strict numbers if a future revision wants to tighten them.

## Open items for next session

- Verify 12HG7 controlled-warmup heater designation on the original
  GE or Sylvania datasheet
- Decide between choke-input and capacitor-input filter for B+
- Specify the screen regulator topology (series-pass IC stack vs
  simple zener clamp)
- Add a bias-rail-OK signal back to firmware so collapse of the
  -90 V rail is detected before the cathode monitor sees runaway
- Pick the actual Hammond part numbers and lock them into the BOM
- Decide whether to source LV supplies (+12, +5, +3.3) from a
  single Mean Well module or build them on the control board
- Restructure `KiCAD/` directory per the layout above before
  drawing begins

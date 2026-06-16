# Control Board BOM + Magnet Wire Plan — 2026-06-16

Sourcing-ready parts list for the control board (VFO + keyer + envelope
DAC + MCU interfaces) and a unified magnet-wire plan covering every
toroidal inductor in the project (control board, driver, PA, output LPF).

Updated 2026-06-16 to reflect:
- Removal of the obsolete FT37-43 keyer T1 transformer (superseded by
  LM7171 post-amps + 12HG7 driver topology)
- Removal of the driver input transformer T_in (proposed but never
  simulated; not needed with the differential LM7171 outputs driving
  the 12HG7 grids directly through coupling caps)
- Switch to single-gauge #22 AWG enameled magnet wire throughout
- T68-6 substitution option for the VFO LPF (user has T68-6 on hand,
  easier to wind than T50-6)

Order this list, then build. Resistors marked with `*` are critical-value
(impedance matching, op-amp gain setting, or filter element) and want
1% tolerance or better. Unmarked resistors can be the nearest value
from your assortment.

## Suppliers used in this list

**Mouser** (mouser.com) — primary for active devices, sockets, connectors,
regulators, capacitors. US warehouse, ships fast, no minimum order.

**Digi-Key** (digikey.com) — secondary for the same parts; use whichever
has the value/package in stock when you check. Same-day shipping for
US orders.

**Adafruit** (adafruit.com) — pre-built breakouts (Si5351, BSS138,
optionally Metro ESP32-S3).

**Kits and Parts** (kitsandparts.com) — toroidal cores and magnet wire.
Hobbyist-friendly, ham radio focused, the best single source for
iron-powder cores in small quantities.

**Amidon** (amidoncorp.com) — alternative for toroidal cores if Kits
and Parts is out of stock. Larger minimum quantities, slightly higher
prices, broader inventory.

**eBay / SurplusSales / etc** — variable trimmer caps, vintage sockets,
catch-as-catch-can specialty parts.

## Active devices (control board)

**ESP32-S3 Metro module**
- Adafruit P/N 5500 - already owned per project notes
- Goes on board as 2x 14-pin headers + power header. No need to re-order.

**Si5351A clock generator**
- Adafruit P/N 2045 (Si5351A clock generator breakout)
- ~$8 from Adafruit
- One per board. Already ordered per memory.

**MCP23017-E/SP** - 16-bit I2C GPIO expander, SPDIP-28
- Mouser 579-MCP23017-E/SP - ~$2.30 each
- Order 3 (one for board, two for sacrificial bring-up spares)
- Through-hole socket recommended (28-pin DIP socket, see below)

**BSS138 4-channel I2C level converter**
- Adafruit P/N 757 - ~$4
- Provides 3.3V to 5V level shifting on the I2C bus so the MCP23017
  (at 5V) can talk to the ESP32-S3 (at 3.3V)
- One per board

**MC1496** - balanced modulator/VCA, DIP-14
- Mouser 511-MC1496P (ST Micro) or 595-MC1496P (TI) - ~$3 each
- Through-hole DIP-14. Order 2 (one + spare).

**LM7171** - high-speed op-amp, DIP-8
- Mouser 926-LM7171AIN/NOPB (TI) - ~$8 each
- Two on the board (one per differential side of the keyer post-amp).
  Order 3 (two + spare).

**TL071** - JFET-input op-amp, DIP-8
- Mouser 595-TL071CP or 595-TL071ACP - ~$0.70 each
- One on the board (AGC integrator per the cw_envelope_keyer.md spec).
  Order 3 (one + two spares; useful in other projects).

**MCP4921** - 12-bit SPI DAC, PDIP-8
- Mouser 579-MCP4921-E/P - ~$2.50 each
- One on the board (envelope DAC). Order 2.

**6N137 optocouplers** - high-speed optoisolators, DIP-8
- Mouser 782-6N137 (Vishay) or 630-6N137SDM (Lite-On) - ~$1.20 each
- Two on the board (one per paddle input: dit, dah). Order 3.

**LM7805** - +5V linear regulator, TO-220
- Mouser 595-LM7805CT or similar - ~$0.70 each
- Order 2.

**LM7812** - +12V linear regulator, TO-220
- Order if external supply will be unregulated +15-18V. If you bring
  in regulated +12V from the supply chassis, skip this part.

**1N4738A** - 8.2V Zener diode for -8.3V rail derivation
- Mouser 512-1N4738A - ~$0.20 each
- Order 5

**1N5711** - Schottky detector diode for AGC detector
- Mouser 78-1N5711 - ~$0.60 each
- Order 5

## Passives - resistors (control board)

Critical-value items marked with `*`. Use 1% metal film for the marked
ones; carbon film or 5% from your assortment is fine for the rest.

**Pi-pad attenuator** (sets 20 dB precisely - `*` all three)
- `*` RP1 = 62 ohm - Mouser 71-CMF6062R000FKEK or any 1% metal film
- `*` RP2 = 240 ohm - same
- `*` RP3 = 62 ohm - same

**LM7171 post-amp feedback network** (sets differential gain of 5.8 - `*`)
- `*` R_F = 47k 1% (two needed, one per op-amp)
- `*` R_G = 10k 1% (two needed)
- R_B = 100k input bias (two needed) - value not critical

**MC1496 RF / modulator port impedance** (50 ohm match - `*`)
- `*` R1 = 51 ohm (carrier port termination)
- `*` R3 = 51 ohm (modulator port)
- `*` R4 = 51 ohm (modulator port)

**MC1496 load resistors** (set output level; matched pair preferred)
- `*` RLa = 3.9k 1% (matched pair with RLb)
- `*` RLb = 3.9k 1% (matched pair with RLa)

**MC1496 PNP null-injection symmetry** (semi-critical, matched pairs help)
- R5 = 8.2k (PNP T1 base resistor)
- R7 = 8.2k (PNP T2 base resistor - pair with R5)
- R9 = 8.2k
- R10 = 8.2k
- R6 = 2.7k (PNP T1 collector bias)
- R8 = 2.7k (PNP T2 collector bias - pair with R6)

**MC1496 bias setting** (not critical)
- R2 = 6.8k (Iee setting)
- R11 = 22k (carrier bias divider top)
- R12 = 22k (carrier bias divider bottom)
- R13 = 1.5k (modulator input divider)
- Re = 2k (emitter degen on modulator port)

**Envelope DAC output network** (`*` R_F sets attenuation ratio)
- `*` R_F = 1.5k 1% (MCP4921 output to MC1496 pin 1)
- `*` R4_atten = 51 ohm 1% (shunt at MC1496 pin 1; sets ~108 mV scale)

**TL071 AGC integrator**
- R_INT = 100k (V_DET to TL071 pin 2)
- R_FB = 470k (parallel with C_INT, sets DC gain ~4.7x)
- R_BIAS = 330k (D1 forward-bias from VDD)
- R_KEY = 4.7k (keying RC)

**-8.3V supply derivation from -90V bias rail**
- R_DROP = 15k, 1W (drops from -90V to -8.2V zener) - needs 1W rating

**MCP23017 / I2C bus**
- I2C pull-ups: 2 x 4.7k (these are on the BSS138 breakout already;
  add only if you don't use the breakout)
- MCP23017 address pins: 3 x 10k to GND (set I2C address to 0x20)
- MCP23017 RESET: 10k pullup to VDD

**WH2004A LCD contrast**
- VR1 = 10k trim pot (sets LCD V0 contrast). 3296W cermet, side-adjust,
  through-hole. Mouser 652-3296W-1-103LF - ~$1.40.

**WH2004A LCD backlight current limit**
- R_BL = 47-100 ohm 1/4W (sets backlight LED current; verify exact
  value from WH2004A datasheet for your backlight color choice).
  Get a small assortment if uncertain.

**Paddle optocoupler current limit**
- R_DIT_IN = 470 ohm (limits LED current at +5V key voltage)
- R_DAH_IN = 470 ohm
- R_DIT_OUT = 10k (output pull-up to MCU pin)
- R_DAH_OUT = 10k

**RF output termination at vfo_subcircuit RF_OUT**
- `*` RT = 50 ohm 1% (terminates the differential output)
- `*` RGL = 1M (grid-leak return)
- `*` RS1 = 270 ohm (J310 source resistor - but if Si5351 replaces J310,
  this becomes a Si5351 output coupling resistor; verify when you commit
  the topology)

Total resistor count: ~45 distinct values; most can come from your
assortment.

## Passives - capacitors (control board)

**7-pole Chebyshev LPF** (silver mica or NPO ceramic, 5% - `*` values)
- `*` CF1 = 220 pF silver mica or NPO ceramic 100V
- `*` CF3 = 390 pF silver mica or NPO ceramic 100V
- `*` CF5 = 390 pF silver mica or NPO ceramic 100V
- `*` CF7 = 220 pF silver mica or NPO ceramic 100V
- Mouser stocks silver mica (Cornell Dubilier CD15/CD19 series)
  and NPO ceramic (Kemet/AVX) in these values; either works.

**MC1496 coupling and bypass**
- C_IN = 10 nF NP0 ceramic (RF_IN to MC1496 pin 8)
- C2 = 0.1 uF X7R ceramic (bypass)
- C1 = 330 pF NP0 (modulator port coupling)

**LM7171 coupling and bypass**
- C_IN = 100 nF X7R (input AC couple), two needed
- C_OUT = 100 nF X7R (output AC couple), two needed
- 2 x 10 uF aluminum electrolytic 25V (bulk bypass +12V and -8.3V)
- 4 x 100 nF X7R (local supply bypass)

**TL071 AGC integrator**
- C_INT = 1 uF film (MKt or MKP, NOT electrolytic)
- C_DET_IN = 1000 pF NP0
- C_DET_OUT = 10 nF film
- C_KEY = 1 uF film

**Power rail bypass (per IC supply pin)**
- 100 nF X7R ceramic ~12 needed (one per active IC supply pin)
- 10 uF tantalum or aluminum electrolytic ~6 needed (bulk on each rail)

**ESP32-S3 / digital section**
- 10 uF + 100 nF on each digital rail (3.3V, 5V)

## Toroidal inductors (control board)

The control board has THREE toroidal inductors total - the VFO LPF
section. No transformers on the control board (the obsolete FT37-43
keyer T1 has been removed; the MC1496 outputs use resistive loads
and RC-couple into the LM7171 post-amps).

**7-pole Chebyshev LPF** - two core options:

Option A (original spec, T50-6):
- LF2 = 13 turns on T50-6 = ~647 nH
- LF4 = 14 turns on T50-6 = ~715 nH
- LF6 = 13 turns on T50-6 = ~647 nH

Option B (T68-6 substitution, recommended since user has these on hand):
- LF2 = 8 turns on T68-6 = ~736 nH
- LF4 = 8 turns on T68-6 = ~736 nH
- LF6 = 8 turns on T68-6 = ~736 nH
- Cutoff shifts from 17.5 MHz to ~16.4 MHz; 14.2 MHz operating
  frequency remains well in the passband; harmonic suppression
  unchanged. T68-6 is meaningfully easier to wind than T50-6.

If using Option B and you want the original 17.5 MHz cutoff exactly,
rescale the caps:
- CF1 / CF7 - 220 pF down to 200 pF (or 195 pF if you have it)
- CF3 / CF5 - 390 pF down to 360 pF

Order 3 T68-6 cores + 2 spares (5 total) if going Option B, or
3 T50-6 + 2 spares if going Option A.

## Cores and inductors - other project boards

For the magnet-wire planning. These get built later but order the
cores now if you want to combine shipping.

**Driver output transformer** - on the driver board, between the
12HG7 plates and 6146B grids. The only bifilar-wound transformer
in the toroidal stuff.
- T68-6 iron powder core
- 12+12 turn bifilar primary, 6+6 turn bifilar secondary
- Order 3 x T68-6 cores (one needed + 2 spare for redos)

**Note on driver input**: there is no input transformer in the
current design. The differential LM7171 outputs on the control
board drive the 12HG7 grids directly via coupling caps and grid
stoppers, as simulated in Driver_subcircuit.sch.

**Balun (6:1)** - on the PA board or its own board, between the
PA tank and the output LPF. Core size TBD; will likely be FT82-43
or FT114-43 ferrite for power handling. Order when the balun
schematic settles on a specific core.

**Output LPF after PA** - on its own board. 50 ohm version per
LPF_stage.md (300 ohm variant dropped). Full spec is in
Documentation/LPF_stage.md.

- L1, L2 = 540 nH each on T68-6, 7 turns each
- Order 4 x T68-6 (2 needed + 2 spare for redos)

**PA plate tank** (air-core, NOT toroidal)
- L4, L5 = 1.71 uH each, ~10-12 turns, 14-16 AWG silver-plated or
  bare copper, self-supporting
- L6 = 2.5 uH link, 14-16 AWG
- See PA_stage.md "Construction notes" section for full spec
- Heavy bare or silver-plated copper, NOT magnet wire; sourced
  separately (Westlake Wire, McMaster-Carr, or eBay surplus)

## Magnet wire plan - single gauge throughout

The constraint that drove the original two-gauge recommendation
(needing to fit bifilar windings on tiny FT37-43 cores) has been
removed. With the FT37-43 keyer T1 gone and the driver input
transformer deferred, the tightest fit in the project is the
driver output transformer on T68-6: 36 wire passes around a 29.5 mm
inner circumference.

**#22 AWG enameled magnet wire** - works everywhere in the project:

VFO LPF (8 turns on T68-6): trivial fit, plenty of window left
Driver output transformer (T68-6, 12+12/6+6 bifilar): 13% margin,
   fits with careful uniform winding
Output LPF inductors (~8 turns on T68-6 or ~14 turns on T50-6):
   plenty of room
ATU inductors when that board comes online: ample current capacity

Q penalty vs #24 AWG is negligible at 14 MHz (core loss dominates;
the ~10% Q improvement from heavier wire disappears into the
core-loss floor). Current handling for the output LPF at 50 W
output (1 A RMS) is comfortable.

If the driver output transformer's 13% bifilar margin feels too
tight, that single transformer can move to a larger T94-6 core
without affecting any other inductor spec.

**Order**: 1 lb spool of #22 AWG enameled magnet wire from Kits
and Parts (~$15). Covers every winding on every board with
generous redo margin. Magnet wire stores indefinitely if kept dry.

NOT a good source: hardware store / general electronics catalog.
Magnet wire from non-RF suppliers is often thicker-insulated
"transformer wire" that gives the wrong turn density and is harder
to strip cleanly with heat (a soldering iron melts proper
single-build enamel; thick polyurethane needs solvent).

## Sockets and connectors

**DIP sockets** (use sockets for all DIP devices - first board, easy
swap-out during bring-up)
- 28-pin DIP socket x 1 (MCP23017)
- 14-pin DIP socket x 1 (MC1496)
- 8-pin DIP socket x 5 (LM7171 x2, TL071, MCP4921, 6N137 x2 = 6,
  order 8 with spares)
- Mouser 575-1102873 (Aries 28-pin) or equivalent

**Headers (board-mounted)**
- 2x 14-pin female header for ESP32-S3 Metro mounting
- 1x 7-pin female header for Si5351 breakout
- 1x 6-pin female header for BSS138 breakout
- 1x 16-pin male header for WH2004A LCD ribbon
- 1x 5-pin male header for rotary encoder (when chosen)
- 1x 4-pin male header for I2C pass-through (or use STEMMA QT JST-SH)
- 1x 3-pin male header for differential RF output (HOT+, HOT-, GND)
- 1x 2-pin or 4-pin power input header (depending on rails brought in)
- 1x 2-pin male header for paddle inputs (dit, dah, common)
- Order an assortment from Mouser (3M, Sullins, or Mill-Max brands)

**Power connector** for external supply input
- Terminal block (5-position screw, 5.08 mm pitch) for +12V, -90V,
  +5V, GND, chassis - Mouser 651-1715022
- OR a Phoenix MSTB-style polarized connector if you want pluggable

**RF output** - see PCB strategy doc for choices; if going with the
3-pin header recommendation, no special connector needed.

**STEMMA QT cables** (if using Adafruit modules' built-in connectors)
- Adafruit P/N 4209 (50 mm) and 4210 (100 mm) - order 5 mixed lengths

## Trim caps for tuning

**LCD contrast pot** - already in resistor list (3296W 10k)

**No on-board RF trim caps required** for the control board - the
VFO LPF uses fixed silver-mica / NPO caps. The only variable cap
in the project is the PA plate tank variable (downstream on the
PA board).

## Summary by supplier

**Mouser order** (single shopping cart):
- MCP23017-E/SP x 3
- MC1496P x 2
- LM7171AIN x 3
- TL071CP x 3
- MCP4921-E/P x 2
- 6N137 x 3
- 1N4738A x 5
- 1N5711 x 5
- LM7805 x 2 (LM7812 if needed)
- DIP sockets: 28-pin x 2, 14-pin x 2, 8-pin x 8
- Headers: full assortment per list above
- Resistor 1% metal film kit (or individual values from list)
- Silver mica caps: 220 pF x 4, 390 pF x 4 (200/360 pF if going
  T68-6 retune option)
- NPO ceramic caps: 10 nF x 5, 330 pF x 5, 1 nF x 5
- X7R ceramic caps: 100 nF x 25, 10 uF x 10
- Aluminum electrolytic 10 uF / 25V x 10
- Film caps: 1 uF x 4, 10 nF x 4
- 3296W 10k trim pot x 2
- Terminal blocks per list

**Adafruit order**:
- Si5351 breakout (P/N 2045) - confirm if already on hand
- BSS138 4-ch level converter (P/N 757)
- STEMMA QT cables 50 mm x 3, 100 mm x 2
- (WH2004A already on hand per user notes)

**Kits and Parts order** (combined with magnet wire):

Core selection depends on the substitution decisions above. Two
viable shopping lists:

Option A - keep T50-6 for VFO LPF:
- T50-6 cores x 5 (VFO LPF 3 + 2 spare)
- T68-6 cores x 3 (driver output xfmr 1 + 2 spare)
- T68-2 cores x 4 (300 ohm output LPF path, optional)
- T68-6 cores x 4 (50 ohm output LPF path, OR use the T68-6 spares
  above for this too if not building the 300 ohm version)
- 1 lb spool #22 AWG enameled magnet wire

Option B - T68-6 for VFO LPF too (recommended since user has them):
- T68-6 cores x 10 (VFO LPF 3 + driver output xfmr 1 + output LPF 4
  + 2 spare)
- T68-2 cores x 4 (300 ohm output LPF path, optional)
- 1 lb spool #22 AWG enameled magnet wire

Option B has a smaller bill of core types and consolidates inventory
to one iron-powder type for the small-signal stuff.

**eBay / SurplusSales** (deferred until needed):
- Plate tank variable cap 10-75 pF/section (PA board)
- Vintage tube sockets if not already sourced
- 14-16 AWG silver-plated or bare copper for PA tank coils
  (also try McMaster-Carr or Westlake Wire)

## Open items

- Confirm WH2004A backlight current-limit resistor value from
  datasheet (varies by backlight color/voltage; +5V LED with R_BL
  in the 47-150 ohm range is typical)
- Decide on rotary encoder make/model before finalizing the
  encoder header pinout
- Confirm whether external supply brings in regulated +12V and -90V,
  or whether on-board regulation is required
- The vfo_subcircuit J310 source-follower may or may not be needed
  with the Si5351 (its 8 mA push-pull output is already low-impedance);
  decide before committing the parts list to a final BOM
- Specify the balun core size (FT82-43 vs FT114-43) once the balun
  subcircuit is updated; current Balun_6to1_subcircuit.sch validates
  the topology but not the specific core

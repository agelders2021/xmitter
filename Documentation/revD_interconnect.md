# Rev D Interconnect Reference

Single source of truth for every signal that crosses a board boundary
in the Rev D xmitter architecture. If a connector pinout changes on
any board, update the matching section here **before** regenerating
the netlist so this doc never lags the schematics.

**Status markers:**
- `[OK]`      pin assignment complete, both ends match, no open items
- `[PARTIAL]` some pins defined, some still TBD
- `[TBD]`     no pin assignment yet, placeholder only

Last updated: 2026-10-23 (Rev D Option-C power rail changes).

## Board inventory (Rev D architecture)

- **Analog board** (`KiCAD/analog/`) — DGFET keyer, RC filter, Chebyshev
  LPF, LM7171 PP driver, Metro ESP32-S3 control (via protoshield),
  I²C/SPI DACs (MCP4728 at 5 V, MCP4922 at 5 V with 74HCT125 SPI
  shifter), Adafruit #757 BSS138 I²C level shifter at Metro entry,
  Si5351 bringup DPDT isolation switch (SW1), bias generation,
  shack-input fuse + Schottky, all onboard regulators.
- **ss_pa board** (`KiCAD/ss_pa/`) — QRP Labs 10 W Linear kit RF
  topology on custom PCB. BS170 PP pre-driver → T201 → T202 → IRF510
  PP → T204. Integrates per-FET source-sense telemetry + self-latching
  `fault_shutdown` chain (LM393 + CD74HC4066 bias switch). Entire
  board runs at +5 V via LM2936Z-5.0 LDO (Option C, 2026-10-23).
- **Output LPF board** (`KiCAD/Output LPF/`) — 4-band switched LPF
  (40/20/17/15 m — 10 m band deliberately dropped). One DPDT Omron
  G6K-2P-Y-T1 DC12 relay per band, pole 1 switches output, pole 2
  switches input. 50 Ω swamp Rs on NC side of each pole.
- **Frontpanel board** (`KiCAD/frontpanel/`) — WH2004A LCD, MBL-600
  RS-422 differential rotary encoder (NOT I²C), PCF8575 for button
  matrix + LED, MCP4725 for LCD contrast, local MCP1700x-330 LDO
  for 3.3 V from the +5 V umbilical rail.
- **Protoshield** (`KiCAD/protoshield/`) — Metro-mounted Adafruit
  Proto Shield PID 2077. Carries Metro socket plus GPIO signal
  conditioning (series Rs, pull-ups, Zener clamps, RC filters,
  bypass caps). Screw-terminal connectors are the signal boundary
  to the analog board.

## Interconnect index

- **J1** — Analog → ss_pa : RF signal (SMA)  [OK]
- **J2** — Analog → Output LPF : +12 V coil supply + 4 band-select
  drives (RJ45)  [OK, 4 bands wired after 10 m drop]
- **J4** — Analog → Frontpanel : control umbilical (RJ45)  [OK, see
  `front_panel_interface.md` for details]
- **J31** — Analog ↔ ss_pa : bias, sense, fault, control (RJ45)  [OK]
- **J35** — Analog → (future tube PA) : all tube control signals
  consolidated on one RJ45  [DNP, no destination today]
- **ss_pa → Output LPF** — RF out, high level (SMA)  [TBD]
- **Output LPF → Antenna** — RF out (SMA)  [TBD]
- **Power distribution** — +13.8 V primary + ground scheme  [TBD]

---

## J1 — Analog → PA (RF signal, SMA)  [OK]

- **Connector type:** Conn_Coaxial_Small, footprint
  `xmitter:SMA_Cinch_142-0701-201_Vertical_JackPCB`
- **Mates with:** matching SMA jack on PA board (TBD — probably J-TBD
  on PA PCB)
- **Shield:** chassis ground, bonded to both board GNDs

### Pins

- **Center — RF_OUT_ANALOG:** analog → PA. Single-ended, 50 Ω,
  14.0–30.0 MHz (full HF band coverage).
  Driver: U1 (LM7171 non-inverting amp) via R2=50 Ω back-match.
  DC-blocked by C1 (100 pF) in the RC snubber plus the amp's
  own output characteristics.
  **Build-time gain hedge:** R_f = 3 kΩ in the feedback path is
  installed by default; R_g (to GND from inverting input) is
  intentionally LEFT UNPOPULATED. With R_g open the formula
  `gain = 1 + R_f/R_g` collapses to unity gain (LM7171 input bias
  current is ~2 µA, nothing to force a drop across R_f). Default
  nominal signal level into the PA is **~500 mVpp**. To get more
  drive -- e.g. to push the IRF510 PA into class-C operation when
  firmware sets PA_Bias_A/B low via MCP4728 U3 -- **populate R_g**:
    R_g = 1 kΩ -> gain = 4 -> ~2 Vpp into PA (max useful before
    the LM7171 ±11 V clean swing starts to limit)
    R_g = 3 kΩ -> gain = 2 -> ~1 Vpp
    R_g = 333 Ω -> gain = 10 -> hits rails on signal peaks, not
    recommended
  Amplitude control at runtime is via **G2 of Q2 (40673 DGFET)**
  driven by MCP4921 U4 ch A through an LM7171 offset-mute op-amp
  (U10 on `dac.kicad_sch`) that remaps DAC 0–5 V to G2 −3.1 V to +5 V.
  G2 acts as a VCA on the carrier; CW envelope shaping (raised-cosine,
  5 ms rise/fall) is applied in firmware. DAC = 0 drives G2 below the
  DGFET V_TO = −2 V, giving a clean cutoff — **no separate KEY_UP
  net** (replaces the retired Q11/Q12 PNP mute path).
- **Shield — GND**

---

## J2 — Analog → LPF (band select, RJ45)  [OK]

- **Connector type:** 8P8C Shielded, footprint
  `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded`
- **Mates with:** matching RJE1D-188 on LPF board (TBD)
- **Cable:** CAT6 shielded patch, chassis-length (~30 cm max)
- **Wire-pair layout:** T568B

### Pins

- **Pin 1 — RLY_10:** analog → LPF, 3.3 V CMOS from PCF8575 (U17)
  pin P2. High = energize 10 m band's input AND output relays.
- **Pin 2 — RLY_15:** analog → LPF, 3.3 V CMOS from PCF8575 P3.
- **Pin 3 — RLY_17:** analog → LPF, 3.3 V CMOS from PCF8575 P4.
- **Pin 4 — RLY_20:** analog → LPF, 3.3 V CMOS from PCF8575 P5.
- **Pin 5 — RLY_40:** analog → LPF, 3.3 V CMOS from PCF8575 P6.
  Wired through this connector; LPF board 40 m filter population
  still optional (user may defer stocking the 40 m toroids/caps).
- **Pin 6 — GND**
- **Pin 7 — unconnected** (spare; could carry a 6th band later)
- **Pin 8 — unconnected** (spare; could carry a 6th band later)
- **Shield (SH) — GND**

**Note:** Earlier revD had GRID_CTL_A/B squatting on J2 pins 7, 8
as a tube-PA future provision. That was retired when **J35 was
added as a dedicated tube-PA control umbilical** — J2 is now
purely band-select, and the two spare pins are available for
future expansion (6th band, aux relay, etc.).

---

## J4 — Analog → Frontpanel (control umbilical, RJ45)  [OK]

Details in `Documentation/front_panel_interface.md`. Carries:
- I²C SDA/SCL (3.3 V, from analog's PCF8575 bus)
- MBL-600 RS-422 differential pair for encoder (MBL_A_P/N, MBL_B_P/N)
- +5 V to front-panel electronics
- GND, Shield

Do not change pinout without updating `front_panel_interface.md`
first — it is the authoritative doc for J4.

---

## J31 — Analog ↔ PA (bias + sense + fault + control, RJ45)  [TBD]

- **Connector type:** 8P8C Shielded, footprint
  `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded`
- **Mates with:** matching RJE1D-188 on PA board (TBD)
- **Cable:** CAT6 shielded patch, chassis-length

### Needed signals (Rev D with kit-compatible bias scheme)

- **Bias_A_Raw** — analog → PA. 0 to ~5 V DC from MCP4728 ch A.
  Sets the trim DAC voltage that overrides the kit's R211 trimmer
  for IRF510 Q207 bias. Needs level shift / isolation at the PA end
  since the kit's bias network expects a trimmer wiper (slow DC).
- **Bias_B_Raw** — analog → PA. Same, for Q208 via MCP4728 ch B /
  R215 position.
- **Source_Sense_A** — PA → analog. DC voltage proportional to
  Q207 average source current. From a low-value sense R (0.1 to
  0.33 Ω typical) in series with the IRF510 source, filtered on
  the PA board to kill RF, then up to the Metro's ADC. Expected
  range: 0–500 mV DC for 0–5 A drain current.
- **Source_Sense_B** — PA → analog. Same, for Q208.
- **FAULT_N** — PA → analog (active low). From the LM393
  self-latching comparator in fault_shutdown. Latches on
  overcurrent; cleared by TX_ENABLE cycling. Metro reads this as a
  digital input; also pulls down the kit's bias enable to kill
  conduction immediately.
- **TX_ENABLE** — analog → PA. 3.3 V CMOS. High = PA bias
  on (keyed); low = PA biased off (RX / fault). Drives the
  kit's Q206 bias switch at the PA end.
- **+13.8 V** — power from PA board back to analog? OR analog's
  +13.8 V input shared from PA? See Power distribution below.
- **GND** — common return.
- **Shield (SH) — GND**

### Open on J31

- Pin assignment: unassigned pending kit-compatible bias design
  review. Current revC J31 pinout was built for the LM7171 PP
  driver scheme and is now obsolete.
- Whether +13.8 V is carried through J31 or on a separate power
  connector depends on current budget (CAT6 wire is ~24 AWG, limited
  to ~1 A per conductor; PA draws 3–5 A, so power on J31 would need
  multiple parallel conductors or a separate heavier connector).
- Whether the kit's Q206 BIAS line is accepted on the PA board as
  a simple 3.3 V logic input, or needs a level-shift/driver stage.

---

## J35 — Analog → (future tube PA) : all tube control signals (RJ45)  [OK]

Dedicated RJ45 added 2026-10-19 to consolidate every signal needed
to drive a future tube-PA upgrade. **No electrical destination
today** — the connector sits on the analog board as a provisioned
cable exit so that a tube PA can be added later without re-fabbing
analog. All five tube-PA control signals that would otherwise be
scattered across multiple SMA jacks or screw terminals are gathered
here on one CAT6-mateable connector.

- **Connector type:** 8P8C Shielded, footprint
  `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded`
- **Mates with:** matching RJE1D-188 on a future tube-PA board
- **Wire-pair layout:** T568B

### Pins

- **Pin 1 — I_CATHODE_A:** (future) tube PA → analog. Cathode
  current sense for tube A, back to Metro ADC via a divider/filter.
  Also brought out on J22 screw terminal for bench probing.
- **Pin 2 — GND**
- **Pin 3 — I_CATHODE_B:** (future) tube PA → analog. Same for
  tube B.
- **Pin 4 — GRID_CTL_A:** analog → (future) tube PA. From
  MCP4728 U3 ch C (pin 9). Sets tube-A grid bias setpoint.
  Also still present on J23 SMA (bench access).
- **Pin 5 — GRID_CTL_B:** analog → (future) tube PA. From
  MCP4728 U3 ch D (pin 10). Sets tube-B grid bias setpoint.
  Also still present on J24 SMA (bench access).
- **Pin 6 — GND**
- **Pin 7 — GND**
- **Pin 8 — GRID_BLOCK_CRASH:** analog → (future) tube PA.
  Hardware fault signal; when asserted (polarity TBD by future
  tube-PA design) commands the grid-bias generator to crash the
  bias to full-negative, cutting tube conduction immediately.
  Routed through J22 pin 2 as well (bench access).
- **Shield (SH) — GND**

### Notes

- GRID_CTL_A/B were formerly living on J2 pins 7, 8 as a stop-gap
  future-tube provision; they moved to J35 pins 4, 5 as part of
  this consolidation, freeing J2's pins 7, 8 for other use.
- Signals also appear on J22 (4-pin screw terminal) and J23/J24
  (SMA) as bench/test access points. These are **intentional**
  parallel paths, not duplicate wiring errors — J35 is the
  production path for the cable to a future tube PA; the SMAs
  and terminals exist for direct probing without unplugging
  anything.
- MCP4728 channel A/B are the IRF510 PA bias (not tube); channels
  C/D are the tube grid bias (routed to J35). So the single DAC
  chip handles both the solid-state PA bias and the future tube
  PA bias; firmware can hold either side's bias chain in a safe
  state while the other is active.

---

## PA → LPF (RF out, SMA)  [TBD]

- **Connector type:** Likely SMA both ends; PA output is high-power
  (~10 W, ~22 V peak) so coax jacket + proper torque spec matter.
- **Signal:** Full RF output of the IRF510 push-pull stage, through
  T204 secondary, into the LPF board's input. 50 Ω.
- **TBD:** cable type (RG316 vs RG400 for the thermal margin at 10 W).

---

## LPF → Antenna (RF out, SMA)  [TBD]

- **Connector type:** SMA (chassis-mount jack preferred for
  external access).
- **Signal:** Clean filtered RF, 50 Ω, up to ~10 W.
- **TBD:** chassis-mount vs board-mount; which board provides the
  final SMA jack (LPF board edge, or separate chassis bulkhead
  with short pigtail from LPF board).

---

## Power distribution  [TBD]

- **Primary input:** +13.8 V DC, up to ~6 A peak (PA transmit).
  Enters at... (TBD — probably PA board since it's the heaviest
  load, with a heavy-gauge tap to the analog board).
- **Secondary rails generated on analog board:**
  - +12 V (LM2940CT-12, U8) — op-amp positive rail, relay drivers
  - −12 V (LT1054 charge pump, U7) — op-amp negative rail
  - +5 V (LM2940CT-5, U6) — PCF8575, misc logic
  - +3.3 V (MCP1700 LDO, U13) — Metro, I²C bus, logic
- **LPF board:** only needs +12 V (for relay coils) and GND. Comes
  in on J2 (TBD — J2 has no power pin currently; may need +12 V
  tap or local regulation on LPF board).

### Open on power

- Where does +13.8 V enter the system? PA board, analog board, or
  dedicated power entry point?
- How does +12 V reach the LPF board relay coils? Via J2 (needs
  pin reassignment) or dedicated supply pigtail?
- Current budget audit still outstanding: Metro + I²C + ADC + DAC +
  LM7171 + relay drivers should fit well under 500 mA from analog;
  PA transmit is 3–5 A; LPF relay coils are low-µA (reed) once
  pulled in but ~50 mA inrush each.

---

## Change log

- 2026-10-18: U1 gain-hedge documented in J1. Default R_g unpopulated
  = unity gain = ~500 mVpp drive. Populate R_g = 1 kΩ to get gain = 4
  = ~2 Vpp drive for class-C PA operation. Amplitude control via
  Q2 G2 (DGFET VCA) + MCP4921 U4 envelope DAC. Decision made to
  skip relay-switched gain/class-mode selection -- firmware DAC
  control + DGFET VCA cover both class-AB and class-C regimes.
- 2026-10-19: J35 added — new RJ45 on analog that consolidates
  ALL tube-PA control signals (I_CATHODE_A/B, GRID_CTL_A/B,
  GRID_BLOCK_CRASH) onto one umbilical. J2 pins 7/8 freed up:
  GRID_CTL_A/B moved OFF J2 and ONTO J35; J2 pins 7/8 now
  unconnected spares. RLY_40 now wired on J2 pin 5 (replaced a
  former GND). Separate bench-access paths (J22 screw terminal,
  J23/J24 SMAs) deliberately retained for probing.
- 2026-10-18: U1 gain-hedge documented in J1. Default R_g unpopulated
  = unity gain = ~500 mVpp drive. Populate R_g = 1 kΩ to get gain = 4
  = ~2 Vpp drive for class-C PA operation. Amplitude control via
  Q2 G2 (DGFET VCA) + MCP4921 U4 envelope DAC. Decision made to
  skip relay-switched gain/class-mode selection -- firmware DAC
  control + DGFET VCA cover both class-AB and class-C regimes.
- 2026-10-16: Initial doc created. J1, J2 complete; J4 by
  reference; J31 and all RF/power downstream are TBD pending PA
  and LPF board design.

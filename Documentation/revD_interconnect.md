# Rev D Interconnect Reference

Single source of truth for every signal that crosses a board boundary
in the Rev D xmitter architecture. If a connector pinout changes on
any board, update the matching section here **before** regenerating
the netlist so this doc never lags the schematics.

**Status markers:**
- `[OK]`      pin assignment complete, both ends match, no open items
- `[PARTIAL]` some pins defined, some still TBD
- `[TBD]`     no pin assignment yet, placeholder only

Last updated: 2026-10-25.

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

**Umbilicals (RJ45 / SMA):**

- **J1** — Analog → ss_pa : RF signal (SMA)  [OK]
- **J2** — Analog → Output LPF : +12 V coil supply + 4 band-select
  drives + T/R + status sense (RJ45, 8-pin)  [OK]
- **J4** — Analog → Frontpanel : control umbilical (RJ45)  [OK, see
  `front_panel_interface.md` for details]
- **J31** — Analog ↔ ss_pa : bias, sense, fault, DRIVER_BIAS (RJ45)  [OK]
- **J35** — Analog → (future tube PA) : all tube control signals
  consolidated on one RJ45  [DNP, no destination today]

**Analog ↔ Protoshield screw-terminal harness (6 pairs, all 1:1):**

See the dedicated section `Analog ↔ Protoshield harness table` below.

**RF chain:**

- **ss_pa → Output LPF** — RF out, high level (SMA, J1 ss_pa → J28 LPF)  [OK]
- **Output LPF → Antenna** — RF out, filtered (SMA, J1 LPF)  [OK]
- **Output LPF → Receiver** — isolated RX port with Schottky clamp
  protection (SMA, J3 LPF)  [OK]

**Power distribution:**

- +13.8 V enters via analog J5 (shack supply, 3 A fuse + Schottky)
- Analog generates +12 V, −12 V, +5 V, +3.3 V locally
- ss_pa gets +13.8 V from J33 analog → J2 ss_pa (via heartbeat relay
  K5); generates its own +5 V locally (LM2936Z-5.0, U13)
- LPF gets +12 V from J2 analog pin 8 (shared umbilical with band
  selects)
- Frontpanel gets +5 V from J4 analog pin 4 (shared umbilical);
  generates its own +3.3 V locally

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

### Pins (as wired 2026-10-25)

- **Pin 1 — T/R:** analog → LPF, open-drain FET sink drive for the
  T/R relay (K5 on LPF). Low = energized = TX; high = de-energized
  = RX (fail-safe default).
- **Pin 2 — RLY_15:** analog → LPF, open-drain FET sink from analog's
  PCF8575 (U17) via Q7. Low = energize 15 m band's K1 relay.
- **Pin 3 — RLY_17:** analog → LPF, same, 17 m band K2.
- **Pin 4 — RLY_20:** analog → LPF, same, 20 m band K3.
- **Pin 5 — RLY_40:** analog → LPF, same, 40 m band K4.
- **Pin 6 — RECEIVE_N:** LPF → analog, open contact from K5 pole 1
  pulled LOW when K5 in RX state (de-energized). Metro reads via
  PCF8575 input (U17) with internal pullup giving HIGH when inactive.
- **Pin 7 — TRANSMIT_N:** LPF → analog, open contact from K5 pole 1
  pulled LOW when K5 in TX state (energized). Metro reads via PCF8575
  input, HIGH via internal pullup when inactive.
- **Pin 8 — +12 V:** analog → LPF, coil supply for all five relays.
- **Shield (SH) — GND**

**Note:** 10 m band deliberately dropped from Rev D. The T/R relay
sense pair (RECEIVE_N / TRANSMIT_N) replaces what used to be spare
pins on J2 in earlier revisions — now carrying real signals.

---

## J4 — Analog → Frontpanel (control umbilical, RJ45)  [OK]

### Pins (as wired 2026-10-25)

- **Pin 1 — SDA:** I²C data, +5 V HV bus (post Adafruit #757 shifter on analog)
- **Pin 2 — SCL:** I²C clock, +5 V HV bus
- **Pin 3 — MBL_A_P:** MBL-600 encoder channel A, differential positive
- **Pin 4 — +5 V:** power to frontpanel electronics
- **Pin 5 — ENC_INT_CLEAN:** encoder interrupt (level-shifted to 3.3 V)
- **Pin 6 — MBL_A_N:** MBL-600 encoder channel A, differential negative
- **Pin 7 — MBL_B_P:** MBL-600 encoder channel B, differential positive
- **Pin 8 — MBL_B_N:** MBL-600 encoder channel B, differential negative
- **Shield (SH) — GND**

Further details in `Documentation/front_panel_interface.md`. Do not
change pinout without updating `front_panel_interface.md` first — it
is the authoritative doc for J4.

---

## J31 — Analog ↔ ss_pa (bias + sense + fault + control, RJ45)  [OK]

- **Connector type:** 8P8C Shielded, footprint
  `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded`
- **Mates with:** matching RJE1D-188 on ss_pa board (J31)
- **Cable:** CAT6 shielded patch, chassis-length

### Pins (as wired 2026-10-25)

- **Pin 1 — Source_Sense_A:** ss_pa → analog. DC voltage proportional
  to IRF510A source current (R1||R2 = 0.11 Ω sense). RF-filtered on
  ss_pa (L8 1 µH + C23 100 nF) before leaving the board. Expected
  range 0–500 mV DC for 0–4.5 A drain current. On analog, divided
  down for Metro ADC via the protoshield J3 → J9 harness.
- **Pin 2 — GND**
- **Pin 3 — FAULT_N:** ss_pa → analog. Open-collector from LM393
  self-latching comparator, pulled up to +5 V on ss_pa (R9 = 4.7 kΩ).
  Low = latched fault; high = no fault. On analog, divided down
  (R3 10 K + R4 20 K) to FAULT_N_CLEAN (max 3.3 V) before reaching
  the Metro via protoshield.
- **Pin 4 — Source_Sense_B:** same as pin 1, for IRF510B.
- **Pin 5 — GND**
- **Pin 6 — DRIVER_BIAS:** analog → ss_pa. DC from MCP4922 ch B,
  shifted through 74HCT125 (U9) to 5 V, buffered. Sets BS170 driver
  bias point via T201 center-tap. On ss_pa: R20 100 Ω series + C19
  0.1 µF + C20 100 pF bypass at J31 entry.
- **Pin 7 — PA_Bias_A_Raw:** analog → ss_pa. From MCP4728 ch A
  (I²C DAC, 0 to 5 V). On ss_pa: L6 1 µH + C13 100 nF + C26 100 pF
  bypass at J31 entry, then through CD74HC4066 (U2) series switch
  for fault-triggered kill, then through 220 Ω series into IRF510A
  gate.
- **Pin 8 — PA_Bias_B_Raw:** same as pin 7, for IRF510B via MCP4728
  ch B.
- **Shield (SH) — GND**

### Design notes

- **Power is NOT on J31.** ss_pa draws +13.8 V on a dedicated screw
  terminal pair (analog J33 → ss_pa J2) and generates its own +5 V
  locally (LM2936Z-5.0 LDO, U13). This keeps umbilical conductors
  low-current.
- **No TX_ENABLE signal.** The MCP4728 bias DACs are driven to zero
  by firmware for RX (and FAULT_N automatically opens the
  CD74HC4066 bias switch via hardware when a fault latches), so a
  separate enable isn't needed.

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

## Analog ↔ Protoshield harness table

Six 1:1 screw-terminal pairs between the analog board and the Metro-mounted
protoshield. Every pair below has matching pin count AND matching pin order
AND matching signal set, verified in the netlist 2026-10-25.

Build the harness as six independent terminal-to-terminal patch runs,
one connector pair at a time. Keep the pair references labeled on the
cable to simplify re-plug after service.

| Pair | Analog ref | Protoshield ref | Pins | Signals (pin 1 → pin N) | Function |
|---|---|---|---|---|---|
| 1 | **J8** | **J7** | 3 | GND, SDA_IN, SCL_IN | I²C bus to analog HV side (post Adafruit #757 shifter) |
| 2 | **J16** | **J16** | 5 | GND, SCK, MOSI, CS_DAC, DAC_LDAC_N | SPI to MCP4922 envelope DAC (shifted 3.3→5 V by 74HCT125) |
| 3 | **J9** | **J4** | 2 | GND, ENC_INT | Encoder interrupt (from analog's AM26LS32 → shifted → protoshield → Metro) |
| 4 | **J11** | **J11** | 4 | GND, GRID_BLOCK_CRASH, I_CATHODE_B, I_CATHODE_A | Tube-PA monitor signals (**DNP** for first fab; connectors in place for future tube-PA upgrade) |
| 5 | **J12** | **J13** | 4 | GND, MBL600_B, MBL600_A, LDAC_4728 | MBL-600 encoder PCNT inputs + MCP4728 LDAC strobe |
| 6 | **J3** | **J9** | 4 | GND, FAULT_N_CLEAN, Source_Sense_B, Source_Sense_A | PA telemetry back to Metro (fault latch state + per-FET source current) |

### Protoshield-only connectors (not harnessed to analog)

- **J1** (2-pin: GND, RESET_N) — reset pushbutton plugs directly here
- **J6** (3-pin: GND, PADDLE_B, PADDLE_A) — CW paddle jack plugs directly here (text note on protoshield schematic)

### Analog-only connectors (not harnessed to protoshield)

Umbilicals / RF: J1 (SMA ss_pa), J2 (RJ45 LPF), J4 (RJ45 frontpanel), J31 (RJ45 ss_pa), J35 (RJ45 future tube-PA, DNP). Power: J5 (shack supply in), J13 (power header spare), J33 (SS_PA_Power out). Discrete: J6 (TX LED cathode), J7 and J10 (DNP future tube-PA relay drives), J21/J32/J34 (spare 2-pin terminals).

**Note on duplicate protoshield connectors.** Protoshield schematic currently has both J3 (4-pin tube signals via conditioning Rs) and J11 (4-pin tube signals direct) — these carry the same signal set. If this is a leftover from an earlier revision, J3 can be deleted. Verify intent before fab.

---

## Change log

- 2026-10-25: Added analog↔protoshield harness table (6 pairs, all 1:1
  matching). Rewrote J2, J31 pin lists to reflect current wiring
  (T/R and sense signals added on J2, DRIVER_BIAS and PA_Bias on J31).
  Added J4 pin list. Rewrote top-of-doc board inventory and
  interconnect index. Removed stale "TBD / needed signals"
  placeholders now that the signals are assigned.
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

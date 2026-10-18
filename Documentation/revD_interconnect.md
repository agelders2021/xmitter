# Rev D Interconnect Reference

Single source of truth for every signal that crosses a board boundary
in the Rev D xmitter architecture. If a connector pinout changes on
any board, update the matching section here **before** regenerating
the netlist so this doc never lags the schematics.

**Status markers:**
- `[OK]`      pin assignment complete, both ends match, no open items
- `[PARTIAL]` some pins defined, some still TBD
- `[TBD]`     no pin assignment yet, placeholder only

Last updated: 2026-10-16.

## Board inventory (Rev D architecture)

- **Analog board** — DGFET keyer, RC filter, LM7171 buffer, Metro
  ESP32-S3 control, I²C/SPI DACs, bias generation. Branch active.
- **PA board (custom, pre-fab)** — follows QRP Labs 10W Linear kit
  RF topology (BS170 predriver → T201 → BS170 PP driver → T202 →
  IRF510 PP → T204) on a custom PCB to integrate `source_sense`
  telemetry + the `fault_shutdown` latch chain. Schematic in progress.
- **LPF board (new, pre-fab)** — 4-band switched LPF (10/15/17/20m)
  with 40m provision, dual relays per band (input + output
  isolation). Schematic in progress.
- **Frontpanel board** — encoder, display, LEDs, buttons via PCF8575
  + MBL-600 RS-422 encoder termination.

## Interconnect index

- **J1** — Analog → PA : RF signal (SMA)  [OK]
- **J2** — Analog → LPF : band select + spare (RJ45)  [PARTIAL]
- **J4** — Analog → Frontpanel : control umbilical (RJ45)  [OK, see
  `front_panel_interface.md` for details]
- **J31** — Analog ↔ PA : bias, sense, fault, control (RJ45)  [TBD]
- **PA → LPF** — RF out, high level (SMA)  [TBD]
- **LPF → Antenna** — RF out (SMA)  [TBD]
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
  ~500 mVpp (nominal) at 14.0–30.0 MHz (full HF band coverage).
  Driver: U1 (LM7171 unity-gain follower) via R2=50 Ω back-match.
  DC-blocked by C1 (100 pF) in the RC snubber plus the follower's
  own output characteristics. Expect peak levels to vary with
  envelope DAC setting (G2 of Q2 40673 DGFET).
- **Shield — GND**

---

## J2 — Analog → LPF (band select + spare, RJ45)  [PARTIAL]

- **Connector type:** 8P8C Shielded, footprint
  `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded`
- **Mates with:** matching RJE1D-188 on LPF board (TBD)
- **Cable:** CAT6 shielded patch, chassis-length (~30 cm max)
- **Wire-pair layout:** T568B

### Pins

- **Pin 1 — RLY_10:** analog → LPF, 3.3 V CMOS from PCF8575 (U17)
  pin P2. High = energize 10 m band's input AND output relays.
- **Pin 2 — RLY_15:** analog → LPF, 3.3 V CMOS from PCF8575 P3.
  High = 15 m band enable.
- **Pin 3 — RLY_17:** analog → LPF, 3.3 V CMOS from PCF8575 P4.
  High = 17 m band enable.
- **Pin 4 — GND**
- **Pin 5 — GRID_CTL_A:** analog → LPF (passthrough). Reserved
  spare for potential future tube-PA upgrade. Driven by Metro
  pin (TBD) but not currently used by any destination. **The LPF
  board should pass this pin through to a labeled test point / 
  spare header, not connect it to any LPF function.**
- **Pin 6 — RLY_20:** analog → LPF, 3.3 V CMOS from PCF8575 P5.
  High = 20 m band enable.
- **Pin 7 — GND**
- **Pin 8 — GRID_CTL_B:** analog → LPF (passthrough). Same note
  as GRID_CTL_A — reserved spare, pass through only.
- **Shield (SH) — GND**

### Open on J2

- **RLY_40** label exists on `arduino.kicad_sch` but has no J2 pin
  allocation yet (J2 is fully assigned). Options being considered:
  reassign one of the GND pins (loses a reference return), reassign
  a GRID_CTL pin (loses future tube-PA provision), or add a second
  LPF connector. **Decision pending.** Current J2 handles 4 bands
  (10/15/17/20); 40 m is schematic-provisioned but not wired.

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

- 2026-10-16: Initial doc created. J1, J2 complete; J4 by
  reference; J31 and all RF/power downstream are TBD pending PA
  and LPF board design.

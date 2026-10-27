# Rev D pre-layout fixes — status handoff (2026-10-24, updated 2026-10-25)

Handoff from the claude.ai review sessions (2026-10-22 → 10-24) to Claude Code.
It records what was reviewed, what was decided, what Al has already changed in
the schematics, and what is still to do. Item IDs (A1, P2, F3, …) match the
"xmitter Rev D Fix Implementation Plan" doc; M/S/N IDs are the review findings.

**Ground truth:** the KiCad schematics. The last netlists reviewed were dated
2026-10-23 (analog, ss_pa, protoshield) and 2026-10-22 (Output LPF,
frontpanel). Several changes below were made after those netlists, so
regenerate all five before checking anything.

**2026-10-25 progress update.** The majority of the §3 "still to do" items
have been closed since this doc was written. See the per-item strikethroughs
and the "Verified in netlist 2026-10-25" rows added in §2. The remaining
open items are flagged at the bottom of §3 and in a new §3.1.

---

## 1. Decisions made (do not re-propose)

- **No Wi-Fi in firmware for now** — but the pin map no longer depends on it:
  every analog read is on ADC1. ADC2-capable pins are used only as digital GPIO,
  which Wi-Fi does not affect.
- **Keep the −12 V rail** (LT1054, U7). Needed by the new G2 mute circuit.
- **ENC_INT stays on the frontpanel RJ45, pin 5** (analog J4 / frontpanel J1).
  It is the wired-OR INT of the STEMMA QT rotary encoders (not on any
  schematic). Pin 4 (+5 V, bypassed at the jack) is its AC reference; DC ground
  return is the cable shield. True STP cable; SH bonded to GND on both boards
  (as netlisted). The "float the frontpanel shield" rule in
  `front_panel_interface.md` is withdrawn.
- **Fault latch reset is manual only** (J5 pushbutton on ss_pa). No firmware
  reset wire. Firmware reads FAULT_N_CLEAN, displays the fault, and refuses to
  key until cleared.
- **No bypass caps across the source-sense resistors** (R1∥R2, R3∥R4 on
  ss_pa). The sense-path RC does the RF filtering; bypassing would reduce
  source degeneration for no benefit.
- **Power:** normal operation everything from the barrel connector / shack
  supply. During testing USB may be connected first. Protoshield +3.3 V
  (pull-ups) comes from the Metro's 3V3 pin.
- **R7 / J34 on analog** is a PA-off indicator LED on K5's NC contact, not a
  pre-charge.
- **Frontpanel 3.3 V LDO** (now U13 after re-annotation; U4 in the old
  netlist) is kept — it feeds the R4 ENC_INT pull-up.
- **Frontpanel J2** is not buttons: PCF8575 P13–P15 spares for status LEDs
  (or Path 2 paddle, not used — paddle is on protoshield J6).

---

## 2. Done (reported by Al in this session)

| Item | Change |
| --- | --- |
| M4 / N1 (partly) | ss_pa U13 is LM2936Z-5.0 (40 V in). **Symbol/pinout still to verify — see P1.** |
| M5 | 3 A slow-blow (Keystone 3568, F2) + series Schottky D1 at J5. |
| M6 | Adafruit #757 BSS138 shifter at Metro I²C entry; HV bus at 5 V. |
| M7 | 74HCT125 (U9) SPI 3.3 → 5 V shifter; MCP4922 at 5 V. |
| M8 (range) | MCP4728 at 5 V; ss_pa logic rail 5 V. |
| A2 / N3 / M3 | **KeyUp / Q11 / Q12 discrete mute deleted.** G2 now driven by an op-amp (non-inverting) + zener network to −12 V; key-up cutoff confirmed in QUCS-S. KEY_UP signal removed system-wide. |
| U6 thermal | 15 Ω (≥ 3 W) in series ahead of LM2940CT-5.0, plus 10 µF + 0.47 µF at U6 VI. |
| Inrush | Second (bypass) relay populated on the previously DNP Q6 / PCF8575 P13 / TP18 "Inrush" path. **Topology still to verify — see A10.** |
| P2 (partly) | 1 µH RFC in the source-sense filter replaced by 1 kΩ. Raw nodes renamed Source_Sense_Raw_A/B; filtered Source_Sense_A/B feed the comparator and the umbilical. **Comparator branch / latch fix still to do — see P2/P3.** |
| FAULT_N_CLEAN | 10 nF to GND added. |
| PS1 pin map (partial) | Source_Sense_A = D7 (ADC1), Source_Sense_B = D8 (ADC1), I_CATHODE_A = D9 (ADC1), I_CATHODE_B = A5 (ADC1), TR_SENSE = A1 (digital), LDAC_4728 = A3 (digital). Strapping pins (GPIO0/3/45/46) checked clear. |

### Verified in netlist 2026-10-25

| Item | Verified state |
| --- | --- |
| A3 | R17 = 200K (−10.9 V target per the doc). |
| A5 | D1 value = `1N5822`, footprint `Diode_THT:D_DO-201AD_P15.24mm_Horizontal`. L1 (270 nH, Bourns 78F) footprint `Inductor_THT:L_Axial_L7.0mm_D3.3mm_P10.16mm_Horizontal_Fastron_MICC`. |
| A6 | 74HCT125 (U9) pulldowns R23/R24/R25 = 10 K to GND on MOSI/SCK/DAC_LDAC_N; pullup R37 = 10 K to +3.3 V on CS_DAC. |
| A7 (M14) | CD74HC4050E (U10) placed, powered from +3.3 V. MBL_A_P/N and MBL_B_P/N routed through it. Unused inputs tied to GND. |
| A9 | **All relays have flyback diodes:** analog K5 (G6RL-1) = D5 (1N4001); analog K6 (G6RL-1, inrush bypass) = D7 (1N4001); Output LPF K1/K2/K3/K4 band-select = D8/D9/D7/D11 (1N4148); Output LPF K5 (T/R) = D10 (1N4148). |
| L1 (M15) | G6K relay Description text corrected on K1-K4 instances and the embedded lib symbol: pole 2 = NO/COM/NC. User confirmed wiring. |
| L2 (S7) | Each coil driver Q1/Q5/Q8/Q10: 10 nF debounce cap to GND + 470 K gate pulldown to GND + 10 K series from the RLY_xx signal (10 K instead of the doc's 1 K; PCF8575 can easily drive the FET gate through 10 K). |
| L3 (partial) | "2 in parallel" text stripped from CF7/8/12/16. L6-L20 inductor Descriptions updated T68-6 → T50-6. BOM tagging (100 V C0G for CFx) **deferred** — see follow-up note in §3.1. |
| P1 | ss_pa U13 pin-to-signal map rewired for LM2936 (not MCP1700) pinout. +5 V bulk cap C30 = 22 µF added. |
| P2 (decision) | Keep 1 µH RFC in the source-sense filter (do NOT swap to 1 K). Comparator-branch 10 K resistors added (R21, R22). |
| P3 | BAT85 added on ss_pa fault latch; 4.7 M comparator floor resistors added (×2 for A and B channels). |
| P4 | R12, R19 both = 2.2 K (was 100 K). |
| P5 | R9 = 4.7 K confirmed. |
| F2 (M12) | Backlight resistors moved to drain side: R1 (200 Ω) between LCD red and Q1 drain, R2 (120 Ω) between LCD green and Q2 drain, R3 (120 Ω) between LCD blue and Q3 drain. |
| F4 | Frontpanel J2 is 5-pin. |
| F5 | RJE1D-188-21401 footprint — works in Rev A as fabricated, carrying over unchanged. |
| MCP4725 | Voltage domain confirmed. |
| PS2 (via J7) | New J7 (3-pin: GND, SDA_IN, SCL_IN) placed on protoshield. Analog J8 (3-pin: GND, SDA_IN, SCL_IN) matches pin-for-pin. |
| PS3 | Protoshield C8/C9 = 100 pF (was 100 nF). |
| PS4 | PADDLE R11/R12 = 4.7 K pullups ✓. TR_SENSE and FAULT_N_CLEAN RC verified by user. |
| PS5 (via J16) | Protoshield J16 and analog J16 both 5-pin: GND, SCK, MOSI, CS_DAC, DAC_LDAC_N — pin orders identical. |
| S8 harness (partial) | Confirmed matching pin orders on: J8↔J7 (SDA/SCL, 3-pin) and J16↔J16 (SPI, 5-pin). Full harness-pair table still to be published in `revD_interconnect.md`. |

### Decisions made 2026-10-25

- **A4**: SW1 stays as the slide switch (keep DPDT; no 2×2 header + shunts swap).
- **A5**: D1 updated to 1N5822 with DO-201AD footprint — closed.
- **A10**: Inrush topology confirmed OK.
- **P2**: Keep the 1 µH RFC in source-sense; do NOT swap to 1 K.
- **P6**: Mechanical only — document in assembly notes (see §3.1).
- **PS1**: Skip (Metro symbol will not be placed on the protoshield schematic). The Metro socket is physical only; signals go through the shield's screw terminals.

---

## 3. Still to do — schematics

### Analog (`KiCAD/analog/`)

- [ ] **A1 (N2/M2)** — confirm U1 input is AC-coupled: 10 nF C0G between the
      Q2 drain node and R1; U1 pin 3 to GND via 10 k. Output DC block C4 exists.
      (Check this still holds with the new G2 op-amp circuit.)
- [ ] **A3** — LT1054 feedback. Formula R17 = R16 × (|V_OUT|/1.21 + 1) is
      correct. Present 20 k / 240 k targets −13.3 V, which the LT1054 cannot
      reach from ≈ 13.3 V in (up to 1.6 V loss at 100 mA) → runs unregulated.
      **Set R17 = 200 k (−10.9 V)** or 180 k (−9.7 V). Then recheck the G2
      zener-network bias resistor and U1 negative swing at that voltage.
      Budget: U1 neg-rail current + zener network ≤ 100 mA.
- [ ] **A4 (N4)** — SW1 (Si5351 I²C isolation): replace with 2×2 header + two
      shunts, or bench-verify with a meter that pins 1–2 and 5–6 close in the
      same slider position.
- [ ] **A5 (N5)** — D1: value 1N5822, footprint
      `Diode_THT:D_DO-201AD_P15.24mm_Horizontal` (≈ 1.5 W at 3 A; copper on
      both leads). L1 (270 nH): assign a footprint.
- [ ] **A6 (N6)** — U9 74HCT125: 10 k pull-downs on pins 2 (MOSI), 5 (SCK),
      12 (DAC_LDAC_N); 10 k pull-up to +3.3 V on pin 9 (CS_DAC).
- [ ] **A7 (M14)** — encoder level shift. AM26LS32 outputs are LS-TTL
      (V_OH 2.5 V min … ~4 V), so no divider ratio works. Add **CD74HC4050E**
      (DIP-16) powered from analog +3.3 V (U13): U16 pin 3 → 4050 in → MBL600_A,
      U16 pin 5 → 4050 in → MBL600_B. Delete R26–R29. Unused 4050 inputs to GND;
      100 nF at its VCC. (Protoshield zeners D3/D4 may stay — harmless with the
      4050.)
- [ ] **A8** — add 100 nF from J4 pin 4 (+5 V) to GND at the jack. Keep R6, J9,
      ENC_INT / ENC_INT_CLEAN.
- [ ] **A9** — 1N4148 flyback across J6 (T/R relay output, Q4 drain) and
      across the new inrush bypass relay coil (J8). Delete orphan net
      PCF_P5_SPARE (J14 pin 4) or wire to a spare PCF8575 port. Clean up the
      KeyUp leftovers: R51, J14 pin 5, PCF8575 P8 now free. Name C8 as U9
      bypass. J16 pin order → GND, SCK, MOSI, CS_DAC, DAC_LDAC_N.
- [ ] **A10** — inrush relay topology: the bypass relay must be **downstream of
      K5**, shorting a series resistor (suggest 4.7 Ω, 10 W wirewound), not a
      path in parallel with K5 — Q6 is driven straight from PCF8575 P13, outside
      the heartbeat stack, so a parallel path would defeat the watchdog. R7
      (PA-off LED) ½ W. Layout: PA return (J33 pin 1) on its own heavy copper to
      J5 pin 1; J5→F2→D1→K5→J33 ≥ 2.5 mm at 1 oz; U6 tab to GND pour or small
      sink; 15 Ω resistor stood off the board.

### ss_pa (`KiCAD/ss_pa/`)

- [ ] **P1 (N1)** — U13 LM2936Z-5.0 is still on the MCP1700 symbol/pin map.
      Make a real LM2936Z symbol from the TI TO-92 drawing and verify pins
      before layout (wrong pinout = 13.8 V on the 5 V rail). Add 22 µF on +5 V
      (LM2936 needs ≥ 10 µF). 100 nF at VIN pin in layout.
- [ ] **P2 (M9)** — per channel: Source_Sense_Raw → 1 k → Source_Sense,
      **10 nF** to GND (τ 10 µs, ≈ −59 dB at 14 MHz; 100 nF also acceptable,
      τ 100 µs). Source_Sense → J31 (telemetry, no offset). Comparator gets its
      own branch: **10 k from Source_Sense to LM393 −in** (pin 2 ch A, pin 6
      ch B).
- [ ] **P3 (M10)** — latch holding. After a trip V_REF = V_OL × 6.8/106.8 ≈
      6–25 mV while sense → 0 V, so the latch self-releases. Fix: **BAT85 in
      series with R11, anode at FAULT_N** (V_REF goes to exactly 0 V in fault),
      and **4.7 M from +5 V to each comparator −in** (≈ 10 mV floor, comparator
      branch only). Trip becomes ≈ 0.28 V sense (≈ 2.5 A/device); optionally
      R10 6.8 k → 7.5 k to restore ≈ 0.318 V. C12/D1 power-on reset unchanged.
- [ ] **P4 (M8)** — R12, R19 100 k → 2.2 k (gate discharge ≈ 220 µs instead of
      10 ms once the 4066 opens).
- [ ] **P5** — keep R9 = 4.7 k (gives ≈ 4.3 V FAULT_N with analog's 30 k
      divider; 10 k would give 3.75 V, marginal for HC4066). Document.
- [ ] **P6** — IRF510 tabs are drains at opposite phase: insulated pads +
      shoulder washers on the shared heatsink; note on assembly drawing.

### Output LPF (`KiCAD/Output LPF/`)

- [ ] **L1 (M15)** — confirm G6K pin function from the Omron bottom-view
      drawing: wiring needs pins 4 & 5 = NO (RF busses), 2 & 7 = NC (swamps).
      Fix the symbol description text (or swap nets if wrong). Plain G6K-2P DC12
      or -Y DC12 both fine (1.315 kΩ, 9.1 mA).
- [ ] **L2 (S7)** — each coil driver Q1/Q5/Q8/Q10: 1 k series from J2 pin to
      gate, then **10 nF X7R + 470 k** gate to GND (470 k, not 100 k: PCF8575
      high is a weak quasi-bidirectional pull-up).
- [ ] **L3** — CFx caps: 100 V C0G in BOM. Remove "2 in parallel" text on
      CF7/8/12/16. Inductor descriptions T68-6 → T50-6 (or change footprints).

### Frontpanel (`KiCAD/frontpanel/`)

- [ ] **F2 (M12)** — backlight resistors to the drain side: LCD 16 → R1 200 Ω
      → Q1 D; LCD 17 → R2 120 Ω → Q2 D; LCD 18 → R3 120 Ω → Q3 D; sources to GND.
- [ ] **F4** — J2 → 5-pin: P13, P14, P15, +5 V, GND. LEDs wired
      +5 V → R → LED → Pn (PCF8575 sinks; sources only µA).
- [ ] **F5** — close the RJE1D-188-21401 footprint fit check (flagged wrong
      2026-07-15); fix the shared footprint once; re-import on analog and
      frontpanel. **Blocking for fab.**
- [ ] Verify PCF8575 / MCP4725 power and I²C are on the 5 V HV bus as intended.

### Protoshield (`KiCAD/protoshield/`)

- [ ] **PS1** — place and wire the Metro symbol so the schematic records the
      pin map. Confirmed rows in §2. Still to confirm/assign:
      D2/D3 MBL600_A/B (PCNT), D4/D5 PADDLE_A/B, D6 DAC_LDAC_N, D10 CS_DAC,
      D11 MOSI, D13 SCK, D12 FAULT_N_CLEAN (falling-edge IRQ), **ENC_INT_FINAL
      (needs a pin)**, **GRID_BLOCK_CRASH (DNP; A3 now taken — use A2/A4/A0)**,
      SDA/SCL, RESET. Avoid strapping GPIOs 0/3/45/46.
- [ ] **PS2 (N6)** — add J18 3-pin (GND, SDA_IN, SCL_IN); analog J10 to match.
- [ ] **PS3** — C8/C9 (encoder lines) 100 nF → ≤ 100 pF.
- [ ] **PS4 (S9)** — PADDLE_A/B: R11/R12 10 k → 4.7 k, 1 k series to Metro,
      10 nF at J6. TR_SENSE: 1 k series + 10 nF. FAULT_N_CLEAN: 1 k series
      (10 nF already added).
- [ ] **PS5 (S8)** — J17 order → GND, SCK, MOSI, CS_DAC, DAC_LDAC_N.

### Harness (S8)

- [ ] Make every analog ↔ protoshield terminal pair identical in pin count and
      order (table in the plan doc). Delete the KeyUp row (signal removed).
      Put the final table in `revD_interconnect.md` as the authoritative map.
      **2026-10-25 status:** two pairs verified identical in the netlist —
      J8↔J7 (SDA/SCL 3-pin) and J16↔J16 (SPI 5-pin). Remaining pairs
      (paddle, encoder, T/R drive, source sense, etc.) still need the
      authoritative table published.

---

## 3.1 Follow-ups outside the schematic (added 2026-10-25)

- [ ] **L3 BOM tagging** — "100 V C0G" tag for CFx caps on Output LPF cannot
      be captured in the current workflow (no BOM-generation tool wired in
      yet). **Action: add the C0G / 100 V requirement to the parts-order
      checklist when placing capacitor orders for the LPF fab.** Also
      track whether the T50-6 toroid turn counts (from the L6-L20
      Description text) match the physical cores being wound; a BOM would
      cross-check this automatically.
- [ ] **P6 IRF510 insulation (mechanical)** — IRF510 tabs are drains at
      opposite phase on ss_pa. On the shared heatsink: insulated pads
      (silicone or mica) + shoulder washers under each IRF510, and a
      "do not share metal between device tabs" note on the assembly
      drawing. Not a schematic edit; needs to land in the assembly /
      mechanical doc when that's created.

---

## 4. Still to do — documentation (same commit as schematic edits)

- `revD_prelayout_review_handoff.md`: remove on-analog Chebyshev LPF and "LM7171
  PP U4/U5" (one LM7171 U1, single-ended); MCP4922 VoutA = DRIVER_BIAS, VoutB =
  G2 envelope; new G2 op-amp mute; fault-kill time ≈ 220 µs; R9 = 4.7 k;
  protoshield facts (R7 330 Ω, Source_Sense RC not zener); umbilical pin lists
  from netlists; frontpanel R2/R3 are backlight, RGB from frontpanel PCF8575;
  KeyUp removed.
- `ss_pa.md`: rewrite topology (J3 → T201 → BS170 → T202 → IRF510, J31 not J7,
  K5 not K6, T203 is 43-mix ferrite); response time; sense RC + latch fix; no
  sense-resistor bypass; manual-only reset.
- `front_panel_interface.md`: move QT-encoder / J50 / STEMMA-chain / "BSS138
  not needed" text to history; shield bonded both ends; paddle on protoshield
  J6; J2 = P13–P15 + 5 V + GND.
- `i2c_bus.md`: drop "depopulate breakout pull-ups" (six 10 k ≈ 1.7 kΩ accepted);
  SDA/SCL path Metro → protoshield J18 → analog J10 → U2; verify whether Metro
  STEMMA QT and header SDA/SCL are the same pins — if so, the QT encoders
  (0x37/0x38) are on the same logical bus; add them to the inventory.
- `revD_interconnect.md`: J2 pin 1 NC (no RLY_10); J31 assigned (no
  TX_ENABLE); C4 is J1's DC block; LPF relays are G6K; +12 V to LPF on J2
  pin 8; add harness table.
- Tube-path docs: if the tube PA is built, the cathode monitor (I_CATHODE on
  D9/A5, ADC1) is already Wi-Fi-safe.

---

## 5. Firmware notes captured

- No Wi-Fi assumed; all analog on ADC1. Source_Sense_A/B share one ADC unit /
  calibration handle; 0 dB attenuation.
- Boot: probe analog PCF8575 (0x20). No ACK → analog board unpowered (USB-only
  testing): hold SPI, LDAC and other outputs low, skip hardware init, retry.
- PCF8575 written to a safe state before K5 is enabled.
- K5 sequence: K5 closes → wait ≥ 100 ms → inrush bypass closes; open bypass
  with or before K5. Close K5 only with PA bias at zero.
- FAULT_N_CLEAN falling-edge ISR: mute envelope, zero bias, disable the
  interrupt (slow RC edge), re-arm only after manual latch clear. Optional
  "test fault latch" menu item instead of boot-time BIST.
- Band change only key-up with envelope at zero.
- MCP4728 0x60 → 0x67 reprogram with Si5351 isolated (SW1/header open).
- Heartbeat (CD14538B, ~0.47 s) retriggered at ≥ 3 Hz.

---

## 6. Pre-layout verification (run after all edits)

- [ ] Regenerate all five netlists; every diff traces to an item above.
- [ ] ERC clean; every symbol has value + footprint.
- [ ] No 5 V output reaches a Metro pin without shifting (FAULT_N_CLEAN divider,
      MBL600 via 4050, I²C via U2).
- [ ] QUCS-S: Q2 keyed I_D 10–14 mA; key-up I_D < 1 µA with the op-amp mute;
      −12 V rail regulated under keyed load.
- [ ] ss_pa: LM2936Z pinout verified; latch hand-trace (trip holds; J5 releases).
- [ ] LPF relay NO/NC confirmed; gate networks on all four drivers.
- [ ] Frontpanel: backlight R in drain legs; J2 5-pin.
- [ ] Harness pin orders identical both ends.
- [ ] STP cable shell-to-shell continuity < 0.5 Ω.
- [ ] Power budget per rail written down (U6 ≈ 250–300 mA on +5 V).
- [ ] RJE1D-188 footprint fit check closed.

---

Reference docs (claude.ai, may not be reachable from Claude Code):
review — https://claude.ai/artifact/W7UHRY9tDgVs7WLfbq9xMK ;
fix plan — https://claude.ai/artifact/KxkGQZYK2qHkAUwykU4jkr

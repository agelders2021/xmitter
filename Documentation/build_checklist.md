# Build Checklist

Phase-by-phase tracking for the xmitter build. Each phase has three lists:

- **Verify before starting** — what would block this phase if wrong.
- **Verify before declaring done** — what would block downstream phases if missed.
- **Procure now for later** — long-lead-time items to order while the current
  phase is in progress, so they're on the bench when needed.

Check off items by changing `- [ ]` to `- [x]`. Leave the originating phase
even after you check the item — it's history. Add new items freely; this list
is meant to grow.

The build order assumed below:

1. VFO (current focus)
2. User Interface (encoders + console)
3. Driver
4. PA + Grid Bias + Cathode Monitor (bias-slam fault path replaces the
   old separate "Watchdog Gate" phase — the slam lives on the bias sheet)
5. Balun + Output LPF + ATU
6. Integration / first light

Power supply design is being handled in a separate chat. Slots are reserved
in each phase for power-supply items that gate that phase.

---

## Phase 1 — VFO

**Status: in progress (2026-06-14)**

### Verify before starting

- [ ] Adafruit Metro ESP32-S3 confirmed on hand and verified working
      (`idf.py build && flash && monitor` shows boot banner).
- [x] Adafruit Si5351A breakout on hand (PID 5640). Stays at factory
      default **0x60** (no ADDR jumper — solder bridge is too small for
      this builder's hand tremor).
- [x] **MCP4728 vs Si5351 (0x60) collision RESOLVED via topology +
      one-time EEPROM reprogram.** Resolution (updated 2026-07-06):
      MCP4728 sits on the STEMMA QT chain closer to the Metro; its
      0.1" header carries SDA/SCL to the PCB traces. Si5351 gets I²C
      only via a STEMMA cable chained off the MCP4728's OUT port,
      and that cable is installed **after** the reprogram is done.
      Reprogram procedure — first-boot only, per rig:
        1. Assemble the board fully with **only** the Metro→MCP4728
           STEMMA cable installed. Do NOT install the MCP4728→Si5351
           cable yet.
        2. Power on. Bus has: MCP4728 alone at 0x60, plus the two
           PCF8575s at 0x20 and 0x21 (no collision).
        3. Run the one-time MCP4728 address-write sequence over
           USB-CDC (LDAC pin toggled by firmware on ESP32-S3 D7,
           I²C write commands to 0x60 per Microchip datasheet).
        4. Probe 0x62 to confirm; log "reprogrammed" flag to Metro
           NVS.
        5. Power off. Install the STEMMA QT cable from MCP4728 OUT
           to Si5351 IN.
        6. Power on. Bus now has Si5351 (0x60), MCP4728 (0x62),
           PCF8575 x2 (0x20, 0x21) — all distinct.
      Wiring requirement: MCP4728 LDAC pin still needs to reach an
      ESP32-S3 GPIO (D7) via PCB trace; the I²C reprogram command
      needs LDAC held low regardless of the STEMMA topology.
      Update `pin_map.h`: `I2C_ADDR_NULL_DAC = 0x62` (replaces
      `I2C_ADDR_BIAS_DAC` placeholder — first MCP4728 is for null
      DAC, bias DAC is deferred).
- [ ] MBL-600-100P-5L optical encoder on hand. Confirm it's the L
      (line-driver) variant per the model code — that determines whether
      U_ENC_RX is needed.
- [ ] AM26LS32ACN (or DS26C32AN) RS-422 receiver on hand, OR confirm a
      74LVC2G17 single-ended level shifter is the chosen fallback.
- [ ] +5 V rail available for the encoder Vcc (encoder needs 5 V min).

### Verify before declaring done

- [ ] `vfo freq 14200000` over the USB-CDC shell produces 14.200 MHz at
      CLK0 on a frequency counter or scope. Spot-check 14.000 and
      14.350 MHz too.
- [ ] CLK0 amplitude into the 50 Ω pad input matches the 8 mA drive-strength
      expectation. (`Documentation/20m-leveled-keyed-buffer.md` calls for
      ~380 mV pk before the 20 dB pad → ~38 mV pk after.)
- [ ] 7-pole LPF passband flat ≤0.1 dB across 14.0–14.35 MHz (VNA sweep).
- [ ] 7-pole LPF stopband: ≥28 dB at 28.4 MHz, ≥60 dB at 42.6 MHz.
- [ ] FREQ encoder ticks through the step table at the rates expected
      (with the step encoder still unwired, force with `step <idx>`).
- [ ] FREQ encoder respects the 14.000–14.350 MHz band-edge clamps in
      both directions.
- [ ] No spurs on CLK0 from MCU activity coupling onto the I²C bus
      (sanity sweep on a spectrum analyzer).

### Procure now for later phases

- [ ] **12HG7 driver tubes** — eBay / antique radio sellers; can take
      1–3 weeks. Match pair if possible (Driver phase).
- [ ] **6146B PA tubes** — eBay; match pair (PA phase). Long lead.
- [ ] **OPA454** — HV op-amp, sometimes on extended lead at Mouser/DigiKey
      (Grid Bias phase).
- [ ] **PA tank variable cap(s)** — old radio gear; 10–75 pF per section,
      2 kV+ working voltage. (PA phase.)
- [ ] **Toroid cores**: T50-6 (VFO LPF — already needed this phase if not
      yet on hand), T68-6 (alternate), T106-2 (PA tank), FT37-43 (keyer
      T1), FT82-43 (balun primary core), FT114-61 (balun alt).
      Kits & Parts / Amidon. Usually quick but plan a single buy.
- [ ] **#22 AWG enamelled magnet wire** — VFO LPF inductors.
- [ ] **#14–16 AWG silver-plated or bare copper** — PA tank coils
      (PA phase).
- [ ] **Knobs** that fit M7×0.75 threaded encoder shafts (UI phase).
- [ ] **ESP32-S3 / Metro spares** — only one board exists today
      (memory: `project-machine-roles.md`).

---

## Phase 2 — User Interface (encoders + front panel)

**Status: not started**

### Verify before starting

- [ ] Bourns PEC11-4 encoder(s) for STEP and FUNC selection ordered or
      on hand. The 24-detents / 24-pulses variant matches the firmware's
      `÷4` quadrature-to-click logic.
- [ ] Front-panel material decided (machined aluminum vs 3D print vs
      hand-drilled), shaft hole + LCD cutout pattern marked.
- [ ] Winstar WH2004A 20×4 LCD on hand (`Documentation/Display/`).
- [x] ~~PCF8574 I²C LCD backpack on hand~~ **Replaced 2026-07-02 by
      PCF8575 breakout** on a front-panel vector board. The PCF8575 (16
      GPIO, addr 0x20) drives the LCD in 4-bit mode AND both PEC11-4
      encoders + paddle + spare LEDs, saving a chip. See
      `Documentation/front_panel_interface.md`.
- [ ] Adafruit PCF8575 breakout (PID 5904) on hand.
- [x] ~~PCA9685 for RGB backlight~~ Not planned — the WH2004A gets a
      single-color backlight driven via a PCF8575 GPIO (or tied always-on
      through a series resistor).
- [x] ~~18-pin 0.1" header (or ribbon) for the LCD edge connector.~~ LCD
      connects to the PCF8575 on the same vector-board module; no
      separate LCD-header wiring back to the main PCB.
- [ ] Shielded CAT6 cable + 2× Amphenol RJE1D-188-21401 shielded RJ45
      sockets on hand (Mouser 523-RJE1D18821401; on the 2026-07-02
      Mouser cart, 2 pcs).
- [ ] RJ45 footprint verified against datasheet page 2 — see
      `Documentation/front_panel_interface.md` "Open items" for the
      specific dimensions still to check.
- [ ] Encoder pull-up strategy: rely on ESP32-S3 internal pullups
      (already in `encoders.cpp`) or add external 10 kΩ — internal is
      enough for short on-board wiring, external preferred for ≥30 cm
      runs. Note: the two mechanical encoders now hang off PCF8575 GPIOs
      on the front-panel vector board, not the ESP32-S3 directly.
- [ ] Paddle keyer jack chosen (1/4" TRS vs 3.5 mm); confirm tip = dit,
      ring = dah, sleeve = GND. Paddle wires terminate at the PCF8575 on
      the front-panel vector board (not routed back over the umbilical
      as separate conductors).
- [ ] MBL-600 optical encoder confirmed as the RS-422 line-driver
      variant. RS-422 receiver (AM26LS32ACN default, or 74LVC2G17 SMT
      fallback) picked and on hand. Receiver lives on the Interface
      schematic sheet — not yet drawn; see
      `Documentation/front_panel_interface.md`.
- [ ] MCP4728 LDAC pin wired to a spare ESP32-S3 GPIO on the Arduino
      sheet (required for the one-time EEPROM address reprogram; see
      Phase 1 collision note).

### Verify before declaring done

- [ ] FREQ encoder direction matches user expectation (CW = up). If
      reversed, swap A/B in `pin_map.h`.
- [ ] STEP encoder cycles 1 → 5 → 10 → 20 → 50 → 100 → 500 → 1k Hz
      smoothly with single clicks; no missed or doubled steps over a
      full revolution.
- [ ] STEP encoder pushbutton debounced cleanly (no double-fires).
- [ ] FUNC encoder counts come through `func_delta()` in the firmware.
- [ ] USB-CDC `status` command reflects encoder state.
- [ ] Optical encoder level-translator (RS-422 receiver or LVC buffer)
      drives clean 3.3 V signals to the GPIOs — verify on scope. NEVER
      connect the 5 V encoder outputs directly to the S3.
- [ ] LCD shows boot banner + live VFO / step / power / fault state.
- [ ] RJ45 umbilical wired end-to-end per T568B (see
      `Documentation/front_panel_interface.md`). Continuity check each
      of the 8 conductors + shield-drain path before powering the front
      panel for the first time.
- [ ] Aluminum shield can fabricated and mounted over the vector-board
      module WITHOUT touching the cable shield (single-point ground rule
      — grounding both ends creates a loop through the enclosure).
- [ ] Cable shield grounded ONLY at the main-PCB end (through RJE1D-188
      shell tabs). Vector-board GND arrives via pin 5 of the RJ45, NOT
      via the shield.

### Procure now for later phases

- [ ] (Carry over) 12HG7 / 6146B / PA tank cap / cores if not yet
      sourced.
- [x] ~~**MCP4728** alt-address parts.~~ Resolved via EEPROM re-program;
      the existing 0x60 part moves to 0x62 in firmware bring-up.
- [x] ~~**ADS1115 breakout** (Cathode Monitor phase).~~ No longer needed;
      cathode monitor uses built-in ESP32-S3 ADC1 (decided 2026-06-23).
- [x] ~~**IRF9540** P-MOSFET (Watchdog Gate phase).~~ No longer needed;
      watchdog is grid-bias slam via 2N7000 on the bias sheet.

---

## Phase 3 — Driver (push-pull 12HG7)

**Status: not started**

### Verify before starting

- [ ] 12HG7 tubes on hand, matched pair.
- [ ] 9-pin Magnoval (B9D) sockets on hand.
- [ ] +150 V screen supply available (separate power-supply chat).
- [ ] LM7171 post-keyer amp stage built and bench-verified (delivers
      ~8 V p-p differential into 100 Ω load) — that's the input the
      driver expects.

### Verify before declaring done

- [ ] Driver tubes biased to their operating point; idle plate
      current matches the design (cross-check `Documentation/driver_pushpull_6CL6.pdf`
      / `Documentation/PA_design_5_21_26.md`).
- [ ] Driver output transformer secondary delivers the V6 = 180 V peak
      drive into a 6146B grid load (or representative dummy load) for
      the 50 W operating point.
- [ ] No parasitic oscillation at any setting of the drive amplitude.

### Procure now for later phases

- [ ] (Carry over) PA tubes / tank caps / cores if not yet sourced.
- [ ] **Variable bias trim pots** (per-tube, if not handling entirely in
      firmware via MCP4728).
- [ ] **Heat sinks / sockets / chassis hardware** for 6146Bs.

---

## Phase 4 — PA + Grid Bias + Cathode Monitor (bias-slam fault path)

**Status: schematic complete (2026-06-24); awaiting parts + PCB layout**

The watchdog is now **grid-bias slam** (Q2/Q3 2N7000s on the bias sheet),
not a screen-voltage interrupter. See `Documentation/pa_cathode_monitor.md`
"Watchdog gate" section for the rationale.

### Verify before starting

- [ ] 6146B PA tubes on hand, matched pair.
- [ ] PA tank variable caps on hand, 10–75 pF range, ≥2 kV rating.
- [ ] +600 V plate / +200 V screen / −90 V bias rails available from
      the power-supply chat.
- [x] ~~OPA454 (×2) on hand for grid-bias chain.~~ Ordered; SOIC-8 chips
      to mount on SOIC-to-DIP adapters and plug into 8-pin DIP sockets.
- [x] ~~MCP4728 (with the alt-address question resolved in Phase 1) on
      hand.~~ Adafruit MCP4728 breakout in hand, re-programmed to 0x62
      to avoid Si5351 collision (see Phase 1 entry).
- [x] ~~ADS1115 ADC + OPA1642 buffer + LM393 comparator + LM4040DIZ-1.2~~
      **Revised topology (2026-06-23):** built-in ESP32-S3 ADC1 (no
      ADS1115), OPA1641 buffers (one per tube; SOIC-to-DIP adapter into
      8P socket), LM393 dual comparator (DIP-8, Mill-Max socket), **shared
      LM4040DIZ-5.0** with a R17/RV1/R18 trim divider (27 k / 10 k 25-turn
      pot / 10 k) producing a 1.06–2.13 V threshold range. Parts in hand
      per the Mouser 2026-06-19 invoice and the pending 2026-06-24 cart.
- [x] ~~Bourns MF-R010 PTC fuses (×2) on hand.~~ On the in-progress order.
- [x] ~~BAT54 Schottkys (×4, two per tube) on hand.~~ Replaced by **1N5817**
      (8× ordered on the 2026-06-19 invoice) — current rating margin is
      huge (1 A / 25 A surge vs 60 mA F1-limited fault).
- [x] ~~IRF9540 P-MOSFET + 2N3904 NPN on hand for watchdog gate.~~ Watchdog
      now uses **2N7000 bias-slam** (Q2, Q3 on bias sheet) instead of the
      old screen-voltage interrupter. No P-MOSFET or NPN-pulldown needed.
- [x] ~~Hardware-vs-firmware SR latch decision made.~~ **No latch** —
      diode-OR + bias-slam holds until cathode current drops below
      threshold (50 mV hysteresis). Firmware records the event via ADC1.
- [ ] **Mains interlock** parts on hand: K_MAIN AC relay (sized for
      transformer inrush — Omron G7L-2A-T or equivalent, 10 A min),
      74HC4538 monostable, driver transistor + flyback diode.
      (Separate watchdog from cathode monitor; gates AC to HV
      transformers on firmware heartbeat.)
- [ ] **U11 LM4040 shared reference — verify physical pinout before
      soldering.** The schematic uses `Reference_Voltage:LM4040LP-5`
      whose symbol has only 2 pins (K = 2, A = 3). The assigned
      footprint `Package_TO_SOT_THT:TO-92_Inline` has 3 pads, so pad 1
      is intentionally unrouted (Update-PCB-from-Schematic warns "no
      net found for U11 pad 1" — expected). For the TI LM4040LP-5
      variant, datasheet lists pin 1 = NC, pin 2 = cathode, pin 3 =
      anode. **BEFORE installing**, match the on-hand part's package
      marking to its own datasheet; some LM4040 package variants
      (DBZ, ZFT, DCK) map anode/cathode to different lead positions.
      Bend the two live leads into pads 2 and 3, leave pad 1 empty
      (or trim the physical NC lead if the part has one).

### Verify before declaring done

- [ ] Grid-bias DAC range covers IDLE (−85 V at code 0) and OPERATE
      (~−60 V at code ~1400) with ~2 V firmware trim margin around the
      OPERATE setpoint. Transfer function: V_out = 18·V_DAC − 85.
- [ ] OPA454 swings cleanly to −85 V and back to −60 V under DAC step.
      No oscillation, no overshoot past −90 V at any time.
- [ ] Q2/Q3 (2N7000) bias-slam path forces both grids to the −85 V rail
      within < 5 µs of `GRID_BLOCK_CRASH` being asserted (oscilloscope
      check on each grid output).
- [ ] Cathode monitor ADC1 reads ~1.0 V at nominal 100 mA per tube
      (V_sense = I_cathode × R_C = I × 10 Ω).
- [ ] LM393 comparator trips at the trimmed threshold (~1.5 V_sense =
      150 mA cathode); fault propagates through diode-OR (D5/D6) onto
      GRID_BLOCK_CRASH; bias slam fires; tubes cut off in < 100 µs.
- [ ] Bias supply default (with firmware off, MCP4728 EEPROM = 0) parks
      tubes in deep cutoff (no plate current).
- [ ] Drive level + bias combination produces 50 W output without
      exceeding the −150 V peak grid spec (verify with envelope-peak
      capture; cross-check `2026-06-08-pa-validation.md`).
- [ ] **Mains interlock** — K_MAIN relay does NOT pull in at MCU
      power-up; only pulls in after firmware completes boot AND begins
      heartbeating MAINS_HEARTBEAT. Verify with a meter on the relay
      coil at boot.
- [ ] **Mains interlock — failure test:** halt the firmware (e.g., kill
      the heartbeat task via the shell, or force-reset the MCU). Relay
      must drop within ~200 ms (audible click) and AC must drop to all
      HV transformers. Repeat for: panic, watchdog timeout, power-loss
      to MCU (unplug USB / LV supply). All four paths must drop AC.

### Procure now for later phases

- [ ] **Balun core** (FT82-43 or FT114-61 — already on the list from
      Phase 1, double-check).
- [ ] **Output LPF caps / cores** (NP0/C0G 500 V, T50-2 or T50-6).
- [ ] **ATU variable caps** (8–100 pF and 8–140 pF, ganged).

---

## Phase 5 — Balun + Output LPF + ATU

**Status: not started**

### Verify before starting

- [ ] Balun core in hand (FT82-43 for 6:1, or per-design choice).
- [ ] Output LPF caps + cores in hand.
- [ ] ATU variable caps in hand.

### Verify before declaring done

- [ ] Balun SWR <1.2:1 across 14.0–14.35 MHz on a VNA into 50 Ω
      dummy load.
- [ ] LPF passband flat to 14.35 MHz; stopband ≥47 dB at 28.4 MHz
      (FCC Part 97 requirement).
- [ ] ATU tunes the folded-dipole impedance (163–566 Ω resistive +
      reactive) cleanly per the ATU tuning guide in
      `Documentation/ATU_LPF_README_5_21_26.md`.

### Procure now for later phases

- [ ] Antenna feedline + connectors (twin-line if matching the design).

---

## Phase 6 — Integration / first light

**Status: not started**

### Verify before starting

- [ ] All previous phases checked off.
- [ ] Dummy load capable of dissipating 60 W CW + power meter / scope
      probe set up.
- [ ] Independent CW receiver to monitor on-air signal (in another room
      or via attenuated tap).

### Verify before declaring done

- [ ] Keyed CW produces clean envelope edges with no key clicks on the
      receiver.
- [ ] 50 W into a 50 Ω dummy load over a 1-minute key-down test, no
      bias drift, no faults.
- [ ] Two-state bias sequencing: IDLE bias clamps tubes during key-up;
      envelope starts only after 200 µs settle; key-up reverses the
      sequence with 1 ms guard.
- [ ] Cathode monitor displays plausible per-tube current in real time
      via the console / future UI.
- [ ] Fault simulation: ground one cathode-sense input, verify the
      hardware comparator fires the watchdog gate and the firmware logs
      the event to NVS.
- [ ] WinKey emulator decodes paddle input and drives the envelope
      module correctly.
- [ ] Full band scan 14.000 → 14.350 MHz with no spurious birdies or
      mode hops.

---

## Reference

- `Documentation/BOM.xlsx` — the curated bill of materials.
- `Documentation/Parts_List.xlsx` — auto-generated parts list from
  the QUCS-S schematics (run `python tools/gen_parts_list_xlsx.py`).
- `Documentation/cw_envelope_keyer.md` — firmware module rationale.
- `Documentation/pa_cathode_monitor.md` — 7-layer failsafe design.
- `Documentation/2026-06-08-pa-validation.md` — PA operating point + two-state bias scheme.
- `Documentation/front_panel_interface.md` — RJ45 umbilical, PCF8575,
  RJE1D-188 footprint verification checklist, RS-422 receiver TBD.
- `Documentation/pcb_fab_checklist.md` — final pre-flight gate before
  submitting analog-board gerbers. Consolidates footprint verification,
  schematic completeness, ERC/DRC, physical, and BOM sign-offs.
- `firmware/main/pin_map.h` — current GPIO assignments.

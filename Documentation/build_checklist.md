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
4. PA + Grid Bias + Cathode Monitor + Watchdog Gate
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
- [ ] Adafruit Si5351A breakout on hand. Identify which I²C address it
      uses (0x60 default; some boards have a jumper for 0x61).
- [ ] **MCP4728 address vs. Si5351 (0x60) collision check.** Inventory
      the MCP4728s already ordered — what factory address are they
      programmed with? If they collide with the Si5351, options are:
      (a) program the MCP4728 to an alternate address before first use,
      (b) put the MCP4728 on a second I²C peripheral (the S3 has one
      available), or (c) use an I²C multiplexer. Note in `pin_map.h`:
      `I2C_ADDR_BIAS_DAC = 0x61` is currently a placeholder.
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
- [ ] PCF8574 I²C LCD backpack on hand (I²C addr 0x27 or 0x3F, solder-
      jumper selectable — confirm choice doesn't collide with other I²C
      peripherals).
- [ ] PCA9685 16-channel I²C PWM driver on hand for the RGB backlight,
      OR decision made to tie pins 16/17/18 together for monochrome
      backlight (and skip the PCA9685).
- [ ] 18-pin 0.1" header (or ribbon) for the LCD edge connector.
- [ ] Encoder pull-up strategy: rely on ESP32-S3 internal pullups
      (already in `encoders.cpp`) or add external 10 kΩ — internal is
      enough for short on-board wiring, external preferred for ≥30 cm
      runs.
- [ ] Paddle keyer jack chosen (1/4" TRS vs 3.5 mm); confirm tip = dit,
      ring = dah, sleeve = GND.

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
- [ ] PCA9685 cycles backlight R/G/B as a power-on sanity check, then
      settles on the chosen idle colour. Skip if monochrome.

### Procure now for later phases

- [ ] (Carry over) 12HG7 / 6146B / PA tank cap / cores if not yet
      sourced.
- [ ] **MCP4728** alt-address parts if Phase 1 inventory check showed a
      collision (Grid Bias phase).
- [ ] **ADS1115 breakout** (Cathode Monitor phase).
- [ ] **IRF9540** P-MOSFET (Watchdog Gate phase).

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

## Phase 4 — PA + Grid Bias + Cathode Monitor + Watchdog

**Status: not started**

### Verify before starting

- [ ] 6146B PA tubes on hand, matched pair.
- [ ] PA tank variable caps on hand, 10–75 pF range, ≥2 kV rating.
- [ ] +600 V plate / +200 V screen / −85 V bias rails available from
      the power-supply chat.
- [ ] OPA454 (×2) on hand for grid-bias chain.
- [ ] MCP4728 (with the alt-address question resolved in Phase 1) on
      hand.
- [ ] ADS1115 ADC + OPA1642 buffer + LM393 comparator + LM4040DIZ-1.2
      reference all on hand.
- [ ] Bourns MF-R010 PTC fuses (×2) on hand.
- [ ] BAT54 Schottkys (×4, two per tube) on hand.
- [ ] IRF9540 P-MOSFET + 2N3904 NPN on hand for watchdog gate.
- [ ] Hardware-vs-firmware SR latch decision made
      (`pa_cathode_monitor.md` Open Items §1). If hardware, 74HC74 on
      hand.
- [ ] **Mains interlock** parts on hand: K_MAIN AC relay (sized for
      transformer inrush — Omron G7L-2A-T or equivalent, 10 A min),
      74HC4538 monostable, driver transistor + flyback diode.

### Verify before declaring done

- [ ] Grid-bias DAC range covers IDLE (−90 V) and OPERATE (−50 V) with
      ~2 V firmware trim margin around each setpoint.
- [ ] OPA454 swings cleanly to −90 V and back to −50 V under DAC step.
      No oscillation, no overshoot past −100 V at any time.
- [ ] Q_SLAM (2N7000) bias-slam path forces grids to the −85 V rail
      within 1 µs of `CT_FAULT` being asserted (oscilloscope check on
      the bias node).
- [ ] Cathode monitor ADC reads ~1.0 V at nominal 100 mA per tube.
- [ ] LM393 comparator trips at exactly 1.5 V_sense (150 mA), latches,
      and drops the screen-voltage gate within <100 µs of fault.
- [ ] Watchdog gate (IRF9540) opens and screen voltage falls to 0 V on
      every fault path:
      - hardware comparator trip,
      - `fault::assert_fault()` from firmware,
      - `esp_task_wdt` timeout.
- [ ] Bias supply default (with firmware off) parks tubes in deep
      cutoff (no plate current).
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
- `firmware/main/pin_map.h` — current GPIO assignments.

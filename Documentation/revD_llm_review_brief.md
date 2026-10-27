# xmitter Rev D — External LLM Review Brief

**Purpose.** This document, together with the five board netlists listed
below, is intended to be given to a reviewing LLM as a self-contained
package. The reviewer is asked to perform a **deep technical dive** on
the entire Rev D xmitter design across three axes, and to flag any
design flaws they identify.

**Review axes requested from the reviewer:**

1. **Function.** For every stage, confirm that the circuit topology
   actually performs the intended function. Walk the signal path from
   Si5351 output to antenna, from each DAC to its load, and from each
   telemetry/fault signal back to the Metro.
2. **Component values.** Sanity-check every passive, bias point,
   divider, filter corner, impedance match, and transformer ratio.
   Spot values that are off by an order of magnitude, obviously
   mis-typed, inconsistent across sheets, or sized for the wrong rail.
3. **Power dissipation.** For every resistor, FET, LDO, relay coil,
   and transformer winding, estimate worst-case continuous
   dissipation and compare to the rated part. Call out any part that
   lacks sufficient margin at the operating points described in
   §Operating classes.
4. **Design flaws.** Anything else — stability, race conditions,
   grounding, start-up order, decoupling adequacy, EMI/radiation,
   fault-chain reach-ability, firmware/hardware interlock gaps.

**Format expected from the reviewer:** a narrative report keyed to
reference designators (`R23 is too hot at 220 mW on a 250 mW part`,
`U17 start-up sequence violates I²C spec — SDA floats for 2 ms before
SCL stabilises`, etc.). No need to redraw schematics; cite nets and
pin numbers.

---

## 1. Project in one paragraph

**xmitter** is a ~10 W QRP CW transmitter covering the **40 m, 20 m,
17 m, and 15 m** amateur HF bands, with a switched output low-pass
filter bank selecting the correct harmonic-suppression filter for
each band. The RF chain is: Si5351A clock
→ 40673 dual-gate MOSFET keyer (G2 modulated by an envelope DAC for
raised-cosine CW shaping) → RC snubber → LM7171 unity-gain buffer
(build-time gain hedge available) → short coax → BS170 push-pull
pre-driver → interstage transformer → IRF510 push-pull final →
output transformer → 4-band Chebyshev LPF → antenna. The MCU is an
Adafruit Metro ESP32-S3. All bias points (BS170 driver bias, both
IRF510 gate biases) are DAC-controlled from firmware so the operator
can experiment with class-AB and class-C operation on-the-fly. A
hardware fault chain (LM393 self-latching comparator + CD74HC4066
bias switch + 100 kΩ pulldowns) kills PA conduction within tens of
microseconds on overcurrent, independently of the MCU. Supply is
13.8 V DC from a shack supply; the design has no mains-side
circuitry. Through-hole construction throughout.

## 2. Operating bands

Rev D is laid out to support four amateur HF bands via four
dedicated 7-pole Chebyshev low-pass banks selected by band-select
relay drives from a PCF8575 I/O expander. **10 m was deliberately
dropped from Rev D** (the operator has a main transceiver covering
that band; dropping 10 m saved one LPF bank and shrank the LPF
board). The retained bands are:

- **40 m** (7.000–7.300 MHz) — LPF Fc ≈ 10.5 MHz
- **20 m** (14.000–14.350 MHz) — LPF Fc ≈ 17.09 MHz
- **17 m** (18.068–18.168 MHz) — LPF Fc ≈ 20.90 MHz
- **15 m** (21.000–21.450 MHz) — LPF Fc ≈ 25.07 MHz

The band-select logic routes RF through exactly one LPF at a time
via **one DPDT relay per band** — pole 1 switches the input end of
the filter, pole 2 switches the output end simultaneously. Both
poles throw together on the same coil energization, so unused
filters are fully isolated at both ports (no shunt loading or
resonance leakage into the active path).

## 3. Boards and their roles

- **Analog board** (`KiCAD/analog/`). The Metro ESP32-S3 is **not
  mounted on the analog board** — it plugs into the protoshield, and
  the protoshield exchanges signals with the analog board over the
  six-pair screw-terminal harness (see §Umbilicals and board
  boundaries). The analog board itself hosts the Si5351 clock, DGFET
  keyer (Q2 40673), RC snubber,
  LM7171 output buffer (U1) with build-time gain hedge, both DACs
  (U3 MCP4728 I²C 4-ch for bias, U4 MCP4922 SPI 2-ch for envelope and
  driver bias), U10 LM7171 offset-mute op-amp that remaps the
  envelope DAC's 0–5 V output to −3.1 V…+5 V at the DGFET G2, the
  PCF8575 I/O expander (U17) for band selects and misc control, the
  AM26LS32 RS-422 receiver (U16) for the MBL-600 encoder differential
  pair, all onboard regulators (LM2940CT-12 for +12 V, LT1054 charge
  pump for −12 V, LM2940CT-5 for +5 V, MCP1700x-330 for +3.3 V), the
  CD14538B hardware heartbeat watchdog, an Adafruit #757 BSS138 I²C
  level shifter at the Metro I²C entry, the Si5351 bringup DPDT
  isolation switch (SW1), and a 3 A slow-blow fuse + 1N5822 Schottky
  at the shack supply input (J5). Entire logic rail downstream of
  the Metro I²C entry is +5 V (both DACs moved to +5 V V_DD in the
  Option-C power-rail revision of 2026-10-23).

- **ss_pa board** (`KiCAD/ss_pa/`). **Almost a direct copy of the
  QRP Labs 10 W Linear PA kit** — same RF topology, same transformer
  core choices and winding ratios, same drain-gate feedback network
  per IRF510, same reference-designator numbering (T201–T204, etc.)
  — laid out on a custom 4-layer PCB. Signal flow: BS170 PP
  pre-driver (Q2, Q6) → input transformer T201 (BN61-2402, 2:3
  bifilar) → interstage transformer T202 (BN61-2402) → IRF510 PP
  final (Q3, Q4) → bifilar drain feed T203 (Amidon T50-43) → output
  transformer T204 (BN43-202, 2:3).
  The **only two deliberate departures** from the kit are:
    1. **DAC-controlled bias** replacing the kit's mechanical
       trimmers. BS170 driver bias comes from MCP4922 (U4 on analog)
       ch B via the J31 umbilical; each IRF510 gate bias comes from
       MCP4728 (U3 on analog) ch A/B via J31. All three bias
       setpoints are firmware-adjustable at run time.
    2. **Per-FET source-sense resistors.** R1||R2 for Q3 and
       R3||R4 for Q4 (0.22 Ω Yageo RSF200 2 W in parallel = 0.11 Ω
       effective per final) replace the kit's direct source-to-GND
       connection. The source voltage is RF-filtered on-board and
       routed back to the Metro ADC as Source_Sense_A/B. The
       **self-latching hardware fault chain** (U1 LM393 comparator
       with self-latching V_REF, U2 CD74HC4066 series bias switch,
       100 kΩ pulldowns R12/R19 that collapse the IRF510 gate charge
       in ~18 µs on fault) is a direct consequence of this
       departure — it exists specifically because the sense
       resistors make hardware overcurrent detection possible, and
       is not an independent deviation from the kit.
  Supporting hardware for the above two deltas (a local
  LM2936Z-5.0 +5 V LDO powering the fault chain, the RJ45 umbilical
  routing the bias and sense signals cleanly off-board) is on the
  schematic but is purely in service of the two deltas, not a
  separate RF-topology change.

- **Output LPF board** (`KiCAD/Output LPF/`). 4-band 7-pole 0.1 dB
  Chebyshev LPF bank with 50 Ω source/load impedance. One DPDT Omron
  G6K-2P-Y-T1 (DC12) relay per band selects the active LPF (pole 1
  switches RF output, pole 2 switches RF input). 50 Ω swamp
  resistors on the NC side of each pole for proper termination of
  unused banks. A fifth relay (K5) performs the TX/RX bypass
  function (RECEIVE_N / TRANSMIT_N status pins feed back to the
  analog board for Metro telemetry).

- **Frontpanel board** (`KiCAD/frontpanel/`). User interface. Hosts
  a WH2004A 20×4 LCD, the MBL-600 differential RS-422 rotary encoder
  socket, a PCF8575 I/O expander (@ 0x21) for a button matrix and
  LEDs, an MCP4725 for programmable LCD contrast, and a local
  MCP1700x-330 LDO generating +3.3 V from the +5 V umbilical rail.

- **Protoshield** (`KiCAD/protoshield/`). An Adafruit Proto Shield
  (PID 2077) mounted on top of the Metro. Carries all per-pin signal
  conditioning that would otherwise clutter the analog board PCB:
  bypass caps on power pins, series Rs, pull-ups for paddles and
  encoder interrupt, Zener clamps, small RC filters. Screw terminals
  on both the protoshield and the analog board form the harness
  boundary; see §Analog↔Protoshield harness.

- **Historical / shelved (do not review as live).** `KiCAD/bias/`
  (OPA454 grid bias generator) and `KiCAD/power/` (HV rectifier +
  filter) are retained as drawings for a possible future tube-PA
  upgrade. They are not being fabricated and are not covered by
  this review. Their netlists are not included in the review
  package.

## 4. Netlists for review (five files)

- `KiCAD/analog/analog.net`
- `KiCAD/ss_pa/ss_pa.net`
- `KiCAD/Output LPF/Output LPF.net`
- `KiCAD/frontpanel/frontpanel.net`
- `KiCAD/protoshield/protoshield.net`

Each netlist is a standard KiCad s-expression export containing full
component listing (ref, value, footprint, description) and the net
list (each net name followed by its node list of ref/pin). The
reviewer should cross-reference boards by signal name — most
umbilical signals keep the same net name on both ends.

## 5. RF chain, stage by stage (deep-dive map)

1. **Si5351A** output pin drives Q2 (40673 DGFET) **Gate 1** through
   100 nF AC coupling cap. G1 is DC-biased to roughly +2.45 V by a
   39 kΩ / 10 kΩ divider from +12 V. R21 = 1 MΩ gate return.
2. **Gate 2 of Q2** receives the envelope voltage. MCP4921 (U4) ch A
   outputs 0–5 V; this feeds U10 (LM7171) configured as an offset-mute
   op-amp whose transfer function is `V_G2 = V_DAC × 1.62 − 3.13`,
   mapping the DAC's 0–5 V to G2's −3.1 V…+5 V. The negative DC
   offset is set by a 1N4733A 5.1 V Zener (D2) reference and the
   R20/R23 feedback ratio (6.2 kΩ / 10 kΩ). At DAC = 0 V the DGFET
   sits well below V_TO = −2 V (simulated I_D = 12 pA, on/off ratio
   ~10⁹). At DAC = +5 V the DGFET is fully conducting (I_D ≈ 13 mA,
   V_D ≈ +5.9 V). The **KEY_UP GPIO net was deliberately removed**
   from the design — firmware controls RF on/off entirely by what it
   writes to the envelope DAC.
3. **DGFET drain** → **R1 (50 Ω) + C1 (100 pF) snubber** → single-
   pole 32 MHz LPF to tame Si5351's sub-nanosecond CMOS edges
   (prevents broadband EMI into the signal path; final harmonic
   suppression is the output LPF's job).
4. **U1 LM7171** non-inverting amp with **build-time gain hedge**:
    - R_f = 3 kΩ installed in the feedback path
    - R_g to GND intentionally **left unpopulated by default**
    - Default: gain = 1 (R_g open → formula collapses to unity)
    - Populate R_g = 1 kΩ for gain = 4 → ~2 Vpp drive to the PA
   The build-time choice lets the operator decide whether to run
   the PA class-AB (gentle drive, R_g open) or class-C (hard drive,
   R_g = 1 kΩ).
5. **R2 (50 Ω) series output back-match** into the coax, then SMA J1
   on analog → short RG316 → SMA J3 on ss_pa.
6. **ss_pa T201 (BN61-2402)** input transformer, 2-turn primary and
   3-turn bifilar secondary, with DRIVER_BIAS injected at the
   center-tap. Phase-splits single-ended RF into opposite-polarity
   push-pull drive for the BS170 pair.
7. **BS170 PP pre-driver (Q2, Q6)**. Each gate driven from one end
   of T201 secondary via R17/R18 (220 Ω each). Each source grounded
   through **R15/R16 (2.2 Ω, 1/4 W Yageo MFR-25FBF52-2R2)** for
   source degeneration. No bypass cap in parallel — the ~1.7 dB
   gain cost is accepted to buy stability and matched behavior
   against FET-to-FET β spread.
8. **ss_pa T202 (BN61-2402)** interstage transformer. 3-pin bifilar
   primary (CT fed from +12 V through L18 ferrite choke; outer pins
   to the two BS170 drains); 2-pin secondary (5 T) drives the IRF510
   gates.
9. **IRF510 PP finals (Q3, Q4)**. Each gate: driven from T202 2°
   through a classic QRP-Labs drain-gate feedback network (C7/C8 +
   R5/R6 + L1/L2) for bandwidth flattening and VHF stability,
   DC-biased by PA_Bias_A/B through R7/R8 (47 Ω each). Each source:
   through **R1||R2 or R3||R4 (0.22 Ω Yageo RSF200JT-73-0R22, 2 W
   each, so 0.11 Ω effective)** for both current sensing and thermal
   degeneration. Source voltage is RF-filtered and routed back to
   the Metro ADC via the J31 umbilical as Source_Sense_A/B.
10. **ss_pa T203 (Amidon T50-43)** bifilar drain feed, carries DC
    +13.8 V to each IRF510 drain while being transparent to the
    differential-mode push-pull RF.
11. **ss_pa T204 (BN43-202)** output transformer, 2:3 primary-to-
    secondary ratio → impedance step-up of 2.25×. 50 Ω antenna load
    reflects back as ~22 Ω drain-to-drain, matched to the IRF510 pair
    at ~10 W output. Pin 3 of secondary = GND; pin 4 = RF out.
12. **Coax to Output LPF board** via SMA J1 (ss_pa) → SMA input of
    the LPF board. ~22 V peak into 50 Ω at 10 W.
13. **Output LPF — 7-pole Chebyshev, 0.1 dB ripple, CLCLCLC** (3
    series inductors, 4 shunt caps, symmetric). One bank per band;
    band selected by relay. 50 Ω source/load impedance. Simulated
    20 m bank rejects 3rd harmonic by 68 dB and 5th by 84 dB — all
    harmonics sit > 27 dB below the FCC Part 97 −43 dBc floor.
14. **Antenna** via SMA chassis-mount jack.

## 6. Control architecture

### 6.1 Microcontroller

Adafruit Metro ESP32-S3 (ESP32-S3-WROOM-1 on Metro Arduino form
factor). Firmware runs ESP-IDF v5.4.4 LTS natively (not Arduino),
C++17, FreeRTOS tasks pinned to specific cores for determinism.
Firmware will **actively monitor the IRF510 PA final** via the
Source_Sense_A/B ADC inputs and the FAULT_N input — this telemetry
is a core part of the design because **both class-AB and class-C
operation will be explored**, and firmware needs to adapt bias setpoints,
log drain current waveforms, and respond to overcurrent trips that
differ between the two classes.

### 6.2 I²C bus

Single I²C bus. The Metro's native I²C (3.3 V) is level-shifted up
to the +5 V HV bus by an Adafruit #757 BSS138 breakout at the Metro
I²C entry. The HV +5 V bus serves:

- **Si5351A** at **0x60** (factory default)
- **MCP4728 (U3)** at **0x67** (reprogrammed from factory 0x60 on
  first boot — both parts default to 0x60 so one must be moved;
  procedure described in `Documentation/i2c_bus.md`)
- **PCF8575 (U17)** on analog at **0x20** (A0/A1/A2 all open)
- **PCF8575** on frontpanel at **0x21** (A0 soldered high)
- **MCP4725** on frontpanel (LCD contrast) — address TBD
- **Metro on-board MAX17048** fuel gauge at 0x36 (hard-wired)
- **Up to 3 rotary encoders** (see §6.4)

The I²C bus leaves the analog board via **J4 (RJ45)** to the
frontpanel on pins 1 (SDA) and 2 (SCL), with +5 V on pin 4 and GND
on the shield.

### 6.3 SPI bus

Metro native SPI (3.3 V) drives **MCP4922 (U4)** on the analog
board. MCP4922 runs on +5 V V_DD, so the SPI lines (SCK, MOSI,
CS_DAC, LDAC_N) are level-shifted 3.3→5 V by a **74HCT125 quad
buffer (U9)** before reaching the DAC. MCP4922 channels:

- **Ch A → envelope** → U10 LM7171 offset-mute op-amp → DGFET Q2
  Gate 2. Updated at ~40 kHz (25 µs tick) during CW rise/fall
  edges following the raised-cosine LUT.
- **Ch B → DRIVER_BIAS** → J31 pin 6 → ss_pa board → RC filter →
  T201 secondary center-tap. Sets BS170 driver bias, updated at
  TX/RX transitions.

### 6.4 Rotary encoders (deliberately unusual, flag anything suspicious)

Rev D supports **up to three I²C rotary encoders** plus **one
RS-422 MBL-600 encoder**, as follows:

- **Up to 3 Adafruit I²C QT Rotary encoders**, chained via STEMMA-QT
  on the frontpanel board. Each has a 7-bit address (0x37, 0x38,
  0x39 planned by solder-jumper selection on the breakout). Their
  **INT output pins are wire-OR'd together on the frontpanel into a
  single signal `ENC_INT_RAW`**, which exits the frontpanel on
  **connector J4** (the frontpanel's RJ45 socket, mated to the
  analog board's J4). The analog board level-shifts/conditions this
  shared interrupt and delivers it to the Metro so the firmware
  can wake up on any encoder motion and then poll the three I²C
  devices to figure out which encoder actually moved. Rationale:
  three encoders on one shared interrupt line keeps the J4 pin
  count manageable and matches the way Adafruit's QT Rotary breakout
  is designed to be used.
- **One MBL-600 RS-422 differential rotary encoder** (primary
  frequency-tuning knob). It outputs quadrature A/B on two
  RS-422 differential pairs that run over the J4 umbilical to the
  analog board. On the analog board, an **AM26LS32 RS-422 receiver
  (U16)** converts the differential pair to CMOS; the receiver's
  output is then **level-shifted 5 V → 3.3 V** to be safe for the
  Metro, and routed to the ESP32-S3's PCNT (pulse counter) peripheral
  for hardware-accelerated quadrature decode. The MBL-600 is thus
  handled directly by the Metro (no I²C intermediary), which gives
  the lowest jitter for the main tuning knob and lets firmware
  track motion at full encoder bandwidth.

### 6.5 PCF8575 outputs

The 16-bit PCF8575 (U17) on the analog board drives the band-select
FET sinks for the output LPF (RLY_15, RLY_17, RLY_20, RLY_40 on J2
pins 2–5), the T/R control line (J2 pin 1), and various on-analog
relay drives. Current analog board uses K5 (heartbeat watchdog
output) to gate the +13.8 V rail to the ss_pa.

### 6.6 Fault chain (hardware, independent of firmware)

> **Note on prior review (2026-10-26).** An earlier LLM review of this
> design identified that the fault chain **did not actually latch**
> as-drawn. Two fixes were applied before this review package was
> frozen:
> - **R21 and R22 raised from 10 kΩ to 100 kΩ.** The 10 kΩ series
>   drop into the LM393 inverting inputs was too low an impedance;
>   combined with R24/R25 = 4.7 MΩ it was starving the latching
>   positive-feedback loop. 100 kΩ gives the self-latching path
>   enough loop gain.
> - **New R26 = 100 kΩ placed across C12** (the 1 µF startup / power-
>   on auto-reset cap). Without R26, C12 held its charge indefinitely
>   after rail removal, so power-cycling did not reliably reset the
>   latch. R26 discharges C12 in ~100 ms once +5 V is removed,
>   guaranteeing a clean reset on every power-on. (R26 currently
>   has an empty footprint field — needs assignment before fab.)
>
> The description below reflects the **post-fix** design. Reviewer
> is still invited to critique it fresh.

- **U1 (LM393)** open-collector dual comparator on ss_pa. Each
  comparator takes **Source_Sense_A or B on its − input** (through
  R21 or R22 = 100 kΩ series, with R24/R25 = 4.7 MΩ to +5 V acting
  as weak hysteresis / bias) and **V_REF on its + input**. Trip
  logic: when either Source_Sense exceeds V_REF, the corresponding
  open-collector output pulls LOW. The two outputs are wire-OR'd
  (pin 1 and pin 7 tied together on Net-(R23-Pad1), pulled up to
  +5 V by R9 = 4.7 kΩ).
- **V_REF** is set by R10 (6.8 kΩ to GND) + R11 (100 kΩ from
  FAULT_N to V_REF). In the HIGH-FAULT_N state (no fault, FAULT_N
  ≈ +4.7 V), V_REF ≈ FAULT_N × 6.8 / (100 + 6.8) ≈ 0.30 V — the
  trip threshold at the IRF510 source. On fault, FAULT_N collapses
  low; V_REF then also collapses low; the comparator remains
  tripped even if the source current briefly drops back — this is
  the self-latching positive feedback loop.
- **Startup / auto-reset path:** C12 = 1 µF with its +5 V plate on
  the rail and its other plate feeding D1 (1N4148) anode; D1
  cathode on V_REF. At rail turn-on, the capacitor couples the +5 V
  edge forward through D1, briefly pulling V_REF high and resetting
  any latched state. **R26 = 100 kΩ across C12** (added
  2026-10-26) ensures C12 discharges within ~100 ms after rail
  removal so the next power-on reliably sees the forward-coupling
  edge again.
- **R9 (4.7 kΩ)** pulls Net-(R23-Pad1) up to +5 V. This node drives
  **D3 (BAT85 Schottky)**, which couples the open-collector logic
  into FAULT_N — see §6.6.1 below for D3's role.
- **FAULT_N** exits ss_pa on J31 pin 3. On the analog board, it is
  divided by R3 (10 kΩ) + R4 (20 kΩ) to produce FAULT_N_CLEAN at
  3.3 V level for the Metro GPIO.
- **U2 CD74HC4066** quad analog switch, control pin on FAULT_N. Two
  of its switches are the series pass elements for PA_Bias_A and
  PA_Bias_B. When FAULT_N goes LOW, the switches open, severing the
  bias path. **R12 / R19 = 100 kΩ** pulldowns on the IRF510 gate
  side of the switch discharge C_iss (~180 pF) in ~18 µs → cuts
  PA conduction well inside the thermal-damage window.

### 6.6.1 D3 function (specifically)

**D3 (BAT85 Schottky)** sits between the LM393 open-collector output
node (via R23 = 100 Ω series + C25 = 100 pF bypass) and FAULT_N. Its
pins are: pin 2 (anode) on Net-(D3-A); pin 1 (cathode) on FAULT_N.

D3 is a **one-way "pull-up only" coupler**:

- **Normal (no fault):** LM393 outputs are high-Z (open). R9 pulls
  Net-(R23-Pad1) up to +5 V. R23 couples +5 V to D3's anode. D3
  forward-conducts, pulling FAULT_N up to approximately
  (+5 V − 0.3 V) ≈ +4.7 V. The Schottky Vf (vs ~0.7 V for a
  silicon diode) preserves logic-high margin on FAULT_N.
- **Fault (LM393 trips LOW):** LM393 outputs sink. Net-(R23-Pad1)
  pulls low through the comparator's open-collector. R23 pulls
  Net-(D3-A) low. **D3 is now reverse-biased relative to FAULT_N**
  (which, at the trip instant, is still high) — **D3 blocks**. It
  does NOT pull FAULT_N down directly. Instead FAULT_N drops
  because R11 (100 kΩ to V_REF) is no longer being counter-driven
  through D3, and V_REF itself is collapsing — the FAULT_N ↔ V_REF
  pair falls together via the R10/R11 divider dynamics.

So D3's purpose is:
1. **Isolate the fault assertion from the LM393 output.** The
   LM393's open-collector low cannot "yank" FAULT_N through a stiff
   path; FAULT_N drops only as the latching feedback loop (R11 ↔
   V_REF) resolves. This produces a clean, loop-gain-controlled
   fault assertion rather than an abrupt sink that could pull FAULT_N
   below the CD74HC4066 input abs-min.
2. **Permit the HIGH-side push.** Allows R9 (via R23) to actively
   drive FAULT_N high in normal operation — gives FAULT_N a stiff
   logic-high even though the open-collector LM393 cannot source
   current.
3. **Prevent reverse injection.** If a transient on FAULT_N (e.g.
   ESD on the J31 pin 3 cable) exceeds +5 V, D3 reverse-biases and
   isolates the LM393 output node from the overvoltage, protecting
   the comparator.

## 7. Resistor wattage convention (please apply during review)

**All resistors are 1/4 W unless the Value field explicitly carries a
different wattage.** Convention is `nnR xW` or `nnK xW` — for
example `R44 = "15R 5W"` or `R1 = "0.22R 2W"`. If the Value is just
`"15R"` or `"4.7K"`, assume 1/4 W. This mirrors common ham-radio
schematic practice but is worth flagging explicitly so the reviewer
can treat an un-tagged value as a 1/4 W part when computing
dissipation margin.

Known non-1/4 W resistors in Rev D (as of 2026-10-26):

- **R1–R4 on ss_pa** — 0.22 Ω, 2 W (Yageo RSF200JT-73-0R22).
  Source-sense + thermal degeneration on the IRF510 pair. In
  parallel, 0.11 Ω per final.
- **R44 on analog power sheet** — 15 Ω, 5 W. Current-limit /
  inrush resistor on the +12 V primary rail (see power.kicad_sch).

Every other resistor in the five netlists should be interpreted as
a standard 1/4 W axial carbon-film or metal-film part (DIN0207
case).

## 8. LPF inductor value convention

The LPF schematic puts **two inductance values and a turn count** on
each L reference designator in the fixed format `TARGET/ACTUAL nH,
NT`, where:

- **TARGET** (left of the slash) is the Chebyshev-prototype target
  value — the "ideal" inductance the design asks for.
- **ACTUAL** (right of the slash) is the realizable value with
  integer turn count **N** on the chosen toroid core — what the
  operator will actually hand-wind, dip-measure, and trim.
- **NT** is the integer turn count that produces the ACTUAL value.

Example: `L7 = "542/576nH, 12T"` → Chebyshev target 542 nH, actual
inductance of 576 nH when wound as 12 T on the chosen core.

Both numbers appear on the schematic for transparency during
manual winding and verification against a VNA. The % offset
between TARGET and ACTUAL is < 10 % in all cases and tunable by
spreading/bunching the winding around the toroid circumference.
Capacitor values are standard E12 ceramic NP0 parts (or
two-cap-in-parallel combinations for the non-E12 Chebyshev
targets); the schematic shows the as-ordered part value.

The reviewer is asked to confirm the integer turn counts round
sensibly from the Chebyshev prototype (`N = round(√(L_target /
A_L))`, A_L = 4.0 nH/N² for T50-6, 4.7 nH/N² for T68-6).

## 9. Operating classes (both will be explored in firmware)

The design is deliberately set up so the operator can run the IRF510
PA in **either class-AB or class-C** without any hardware changes
other than optionally populating R_g on U1. Firmware will switch
between modes at run time by changing MCP4728 bias setpoints, and
will log telemetry (per-FET source current, FAULT_N state, bias
servo potential) differently in each mode to characterize PA
behavior.

- **Class-AB (default build):**
    - PA_Bias_A/B set to ~3.8 V by MCP4728 — each IRF510 conducts
      slightly above threshold at idle, smooth sinusoidal conduction
      across the full RF cycle.
    - U1 at unity gain (R_g unpopulated) → ~500 mVpp drive.
    - Approximate efficiency 50 %, output ~5 W.
- **Class-C (alternate build / later experiment):**
    - PA_Bias_A/B dropped to ~1–2 V by MCP4728 — IRF510s off at
      idle; only strong signal peaks drive them above threshold.
    - R_g populated at 1 kΩ on U1 → gain = 4 → ~2 Vpp drive, enough
      to push the gates well above V_GS(th) during peaks.
    - Approximate efficiency 75–80 %, output ~10 W.
    - Harmonic content is worse but caught by the output LPF.

The firmware's PA monitoring is therefore not optional — the
operator needs real-time per-FET current readings in both modes to
tune bias safely without burning IRF510s.

## 10. Umbilicals and board boundaries (quick reference)

- **J1** Analog → ss_pa — RF signal (SMA, 50 Ω).
- **J2** Analog → Output LPF — RJ45 CAT6; carries +12 V coil rail
  (pin 8), four band selects (pins 2–5), T/R control (pin 1), T/R
  status back (pins 6, 7). Shield = GND.
- **J4** Analog ↔ Frontpanel — RJ45 CAT6; carries +5 V (pin 4),
  I²C SDA/SCL (pins 1, 2), the MBL-600 differential pairs
  (pins 3/6 and 7/8), and the shared encoder interrupt
  **ENC_INT_RAW** out of frontpanel (originated by the wired-OR of
  up to 3 QT rotary encoders on the frontpanel STEMMA-QT chain —
  see §6.4). Shield = GND.
- **J31** Analog ↔ ss_pa — RJ45 CAT6; carries Source_Sense_A/B
  (pins 1, 4), FAULT_N (pin 3), DRIVER_BIAS (pin 6), PA_Bias_A_Raw
  (pin 7), PA_Bias_B_Raw (pin 8), and GNDs. **No power on this
  umbilical** — ss_pa gets +13.8 V on dedicated screw terminals and
  generates its own +5 V locally.
- **J33 (analog) → J2 (ss_pa)** — dedicated 2-pin screw-terminal
  pair carrying +13.8 V and GND to ss_pa, gated upstream by the
  heartbeat relay K5.
- **J35** Analog → (future tube PA) — RJ45 provisioned on analog
  but with no destination today. Carries I_CATHODE_A/B, GRID_CTL_A/B,
  GRID_BLOCK_CRASH for a future tube-PA upgrade. Not part of this
  review.

## 11. Known open issues the reviewer should NOT re-flag

To keep the review focused on new findings, these issues are
already tracked and will be addressed:

- Metro ESP32-S3 custom footprint on the protoshield is not yet
  drawn (U2 on protoshield has an empty footprint field).
- J35 on analog will connect to a **future tube-PA board that has
  not yet been designed**. The connector sits on analog as a
  provisioned cable exit (DNP today) so a tube PA can be added
  later without re-fabbing analog. Signals it carries
  (I_CATHODE_A/B, GRID_CTL_A/B, GRID_BLOCK_CRASH) are routed
  on-board but have no electrical destination outside analog
  today.
- `KiCAD/bias/` and `KiCAD/power/` are shelved and not being
  fabricated.

## 12. Deliverables expected from the reviewer

A single report, organized by board, that for each board
addresses the four review axes (function, component values, power
dissipation, design flaws). Within each board, the reviewer may
further group by functional block (e.g. "ss_pa / fault chain",
"analog / DGFET keyer", "LPF / 20 m bank") if that makes the
findings easier to action. Please cite reference designators and
pin numbers so the designer can jump directly to the schematic
or netlist location.

Thank you.

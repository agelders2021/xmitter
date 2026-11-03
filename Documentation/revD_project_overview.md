# xmitter Rev D — Project Overview and Review Brief

This document is a self-contained description of the xmitter Rev D
design, written to be handed to a reviewing LLM together with the
four board netlists listed below. The reviewer is asked to perform
a technical review across four axes:

1. **Function.** Confirm that every circuit block performs its
   intended function. Walk the signal path from Si5351 clock output
   to the antenna connector, trace each DAC output to its load, and
   trace each telemetry or fault signal back to the Metro.
2. **Component values.** Sanity-check every passive, bias point,
   divider, filter corner, impedance match, and transformer ratio.
   Flag values that are off by an order of magnitude, obviously
   mis-typed, inconsistent across sheets, or sized for the wrong
   rail.
3. **Power dissipation.** For every resistor, FET, LDO, relay coil,
   and transformer winding, estimate worst-case continuous
   dissipation and compare to the rated part.
4. **Design flaws.** Anything else — stability, race conditions,
   grounding, start-up order, decoupling adequacy, EMI/radiation
   paths, firmware/hardware interlock gaps.

**Where this document and the schematic disagree, the schematic is
the gold standard.** This brief orients the reviewer; the KiCad
schematics and their exported netlists are authoritative.

**Format requested from the reviewer:** a narrative report keyed to
reference designators (`R7 is too hot at 220 mW on a 250 mW part`,
`U17 start-up violates I²C spec — SDA floats for 2 ms before SCL
stabilises`, etc.). Cite nets and pin numbers.

---

## 1. Project in one paragraph

**xmitter** is a ~10 W QRP CW transmitter covering the **40 m, 20 m,
17 m, and 15 m** amateur HF bands. A switched 4-band output low-pass
filter bank selects the correct harmonic-suppression filter for the
active band. The RF chain is: **Si5351A** clock → **40673 dual-gate
MOSFET keyer** (G1 = RF, G2 = envelope voltage from an SPI DAC via an
offset-mute op-amp, giving raised-cosine CW shaping and ~10⁹ on/off
contrast) → RC snubber → **LM7171 unity-gain buffer** (build-time
gain hedge available) → short coax to the SS PA board → **BS170
push-pull pre-driver** → interstage transformer → **IRF510 push-pull
final** → output transformer → short coax to the LPF board →
**4-band Chebyshev LPF** → antenna. The MCU is an **Adafruit Metro
ESP32-S3**. All three bias points (BS170 driver bias and both IRF510
gate biases) are DAC-controlled from firmware so the operator can
experiment with class-AB and class-C operation on the fly. A
hardware fault chain (LM393 self-latching comparator with
negative-reference latch + CD74HC4066 bias switch + per-FET gate
pull-downs) kills PA conduction within tens of microseconds on
overcurrent, independently of the MCU, and remains latched until a
firmware-triggered 1 ms hardware reset pulse releases it. Supply is
13.8 V DC from a shack supply; the design has no mains-side
circuitry. Through-hole construction throughout except for a small
number of SMT 0805 bypass caps on RF-critical nodes.

## 2. Operating bands

Rev D supports four amateur HF bands via four dedicated 7-pole
Chebyshev LPFs selected by band-select relay drives from a PCF8575
I/O expander. **10 m is deliberately not covered** by this design.
The retained bands are:

- **40 m** (7.000–7.300 MHz) — LPF Fc ≈ 8.0 MHz
  *(7.3 MHz sits at 0.91·Fc — in-band but tolerance margin is tight;
  component tolerances could shift the passband edge toward 7.3 MHz)*
- **20 m** (14.000–14.350 MHz) — LPF Fc ≈ 17.09 MHz
- **17 m** (18.068–18.168 MHz) — LPF Fc ≈ 20.90 MHz
- **15 m** (21.000–21.450 MHz) — LPF Fc ≈ 25.07 MHz

The band-select logic routes RF through exactly one LPF at a time
via **one DPDT relay per band** (Omron G6K-2P-Y-T1, DC12 coil) —
pole 1 switches the LPF input, pole 2 switches the LPF output. Both
poles throw together on the same coil energization, so unused
filters are fully isolated at both ports.

## 3. Boards

Rev D is **three PCBs** plus a Metro-mounted protoshield:

### 3.1 Analog board (`KiCAD/analog/`)

The Metro ESP32-S3 is **not** mounted on the analog board — it
plugs into the protoshield, and the protoshield plugs onto the
analog board through a set of mating screw-terminal headers
(multiple screw connectors along the shared edge). These screw
terminals are the physical boundary where every protoshield signal
crosses onto analog.

The analog board hosts:

- **Si5351A** clock generator (I²C controlled)
- **DGFET keyer** — Q2 40673 dual-gate MOSFET; G1 receives RF from
  Si5351 through a 100 nF AC coupling cap; G2 receives the envelope
  voltage
- **RC snubber** on the DGFET drain (50 Ω + 100 pF, single-pole
  ~32 MHz LPF to tame Si5351 CMOS edges)
- **LM7171 output buffer** (U1), non-inverting, build-time gain
  hedge via a stuffing option on the R_g resistor to GND (default
  R_g unpopulated → unity gain; populate R_g = 1 kΩ → gain = 4)
- **MCP4728** (U3) — I²C 4-channel DAC on the +5 V rail, drives
  bias setpoints
- **MCP4922** (U4) — SPI 2-channel DAC on the +5 V rail, drives the
  envelope voltage and the BS170 driver bias
- **U10 LM7171 offset-mute op-amp** — remaps the envelope DAC's
  0 V…+5 V output to −3.1 V…+5 V at the DGFET G2 (so DAC = 0 drives
  G2 below V_TO ≈ −2 V for clean cutoff)
- **TL071CP** (U11) and other op-amps for DAC post-filtering /
  level translation
- **PCF8575** (U17) — 16-bit I²C I/O expander at address `0x20`,
  handles band selects, T/R, button input, fault clear, and other
  slow digital I/O
- **AM26LS32** (U16) — RS-422 differential receiver for the MBL-600
  rotary encoder
- **CD14538B** (U18) — dual retriggerable monostable; half-A is the
  hardware heartbeat watchdog that gates the SS PA power rail,
  half-B generates the 1 ms fault reset pulse
- **Fault chain** (sub-sheet `fault_shutdown.kicad_sch`) — U201
  LM393 dual comparator, U202 CD74HC4066 quad bilateral switch,
  reference generator and series-pass bias switches; see §6.6
- **Front panel** sub-sheets — LCD interface, encoder sockets,
  button matrix, LED indicators, local +3.3 V LDO (there is no
  separate front-panel PCB)
- **Regulators** (sub-sheet `power.kicad_sch`):
    - **LM2940CT-12** (U8) → +12 V from 13.8 V shack supply
    - **LT1054** (U7) → −12 V charge pump
    - **LM2940CT-5.0** (U6) → +5 V
    - **MCP1700x-330** (U13) → +3.3 V (local to the front-panel
      sub-sheet)
- **Power sequencing hardware**:
    - 3 A slow-blow fuse (F2) + 1N5822 Schottky (D1) at the shack
      input (J5)
    - **24 Ω 10 W inrush resistor** (R42) in series with the SS PA
      power feed, bypassed in normal operation by relay K6
    - **K5 and K6** (G6RL-1-DC12) — K5 gated by the CD14538B
      heartbeat; K6 bypasses the inrush resistor
- **BSS138 I²C level shifter** (Adafruit #757 breakout) at the Metro
  I²C entry so the Metro's 3.3 V I²C talks to the +5 V bus
- **74HCT125** quad buffer for level-shifting SPI 3.3 → 5 V to the
  MCP4922
- **Si5351 bringup DPDT isolation slide switch** (SW1,
  Switch:SW_Slide_DPDT, footprint `SW_CK_JS202011CQN_DPDT_Straight`)
  — mechanical disconnect for the Si5351 clock during bringup

### 3.2 SS PA board (`KiCAD/ss_pa/`)

**Almost a direct copy of the QRP Labs 10 W Linear PA kit** — same
RF topology, same transformer core choices and winding ratios, same
drain-gate feedback network per IRF510 — laid out on a custom
4-layer PCB. Signal flow:

- BS170 PP pre-driver (Q2, Q6)
- Input transformer **T201** (BN61-2402, 2:3 bifilar) with
  DRIVER_BIAS injected at the center-tap
- Interstage transformer **T202** (BN61-2402)
- IRF510 PP final (Q3, Q4)
- Bifilar drain feed **T203** (Amidon T50-43), carries DC +13.8 V to
  each IRF510 drain while being transparent to differential-mode RF
- Output transformer **T204** (BN43-202, 2:3) → 2.25× impedance
  step-up, 50 Ω antenna load reflects as ~22 Ω drain-to-drain

**Deliberate departures** from the QRP Labs kit:

1. **DAC-controlled bias** replaces the kit's mechanical trimmers.
   BS170 driver bias comes from MCP4922 (U4 on analog) ch B via the
   J31 umbilical; each IRF510 gate bias comes from MCP4728 (U3 on
   analog) ch A/B via J31. All three setpoints are
   firmware-adjustable at run time.
2. **Per-FET source-sense resistors.** R1||R2 for Q3 and R3||R4 for
   Q4 (0.22 Ω Yageo RSF200JT-73-0R22, 2 W each in parallel = 0.11 Ω
   effective per final) replace the kit's direct source-to-GND
   connection. The source voltage is RF-bypassed on-board by two
   220 nF 0805 X7R caps per source node (C11||C12 at Q3 source,
   C13||C15 at Q4 source — same value to parallel ESL without
   anti-resonance) and routed back to the Metro ADC via J31 as
   Source_Sense_A/B. The source-sense signals also feed the
   hardware fault chain on the analog board.

**No LDO, no comparators, no bias switch on ss_pa.** The entire
fault chain and its +5 V local supply live on the analog board.
ss_pa carries only RF stages, the bias feeds, the passive
source-sense networks, and the J31 umbilical connector.

### 3.3 Output LPF board (`KiCAD/Output LPF/`)

4-band 7-pole 0.1 dB Chebyshev LPF bank with 50 Ω source/load
impedance. One DPDT **Omron G6K-2P-Y-T1 (DC12)** relay per band
selects the active LPF (pole 1 switches input, pole 2 switches
output). A fifth relay (K5) performs the TX/RX bypass function
(RECEIVE_N / TRANSMIT_N status pins feed back to analog for Metro
telemetry). Band-select coil drives come from the analog PCF8575
through 2N7000 open-drain FET sinks on the LPF board.

Topology per band: **CLCLCLC** (3 series inductors on T50-6 toroid
cores, 4 shunt capacitors to ground, symmetric). Capacitor values
are standard E12 C0G/NP0 ceramic discs on a uniform
`C_Disc_D7.5mm_W2.5mm_P5.00mm` footprint (sized for 200 V C0G
bodies across the full 150 pF–820 pF value range). Capacitor
voltage rating is specified as 200 V.

### 3.4 Protoshield (`KiCAD/protoshield/`)

An Adafruit Proto Shield (PID 2077) mounted on top of the Metro
ESP32-S3, which plugs onto the analog board through the shared
screw-terminal edge. The protoshield carries per-pin signal
conditioning that would otherwise clutter the analog board PCB:
bypass caps on power pins, series Rs, pull-ups for paddles and
encoder interrupt, Zener clamps, small RC filters.

### 3.5 Historical (do not review)

`KiCAD/bias/` (OPA454 grid bias generator) and `KiCAD/power/`
(HV rectifier + filter) are retained drawings for a possible future
tube-PA upgrade. They are **not being fabricated** and are **not**
part of this review package. Their netlists are not included.

## 4. Netlists for review

- `KiCAD/analog/analog.net` — includes the front-panel sub-sheet
- `KiCAD/ss_pa/ss_pa.net`
- `KiCAD/Output LPF/Output LPF.net`
- `KiCAD/protoshield/protoshield.net`

Each netlist is a standard KiCad s-expression export containing the
full component list (ref, value, footprint, description) and the
net list (each net name followed by its node list of ref/pin). The
reviewer should cross-reference boards by signal name — most
umbilical signals keep the same net name on both ends.

## 5. RF signal chain, stage by stage

1. **Si5351A** output pin drives Q2 (40673 DGFET) **Gate 1** through
   a 100 nF AC coupling cap. G1 is DC-biased to roughly +2.45 V by
   a 39 kΩ / 10 kΩ divider from +12 V. R21 = 1 MΩ gate return.
2. **Gate 2 of Q2** receives the envelope voltage. MCP4921 (U4) ch
   A outputs 0 V…+5 V; this feeds **U10 (LM7171)** configured as an
   offset-mute op-amp whose transfer function is
   `V_G2 = V_DAC × 1.62 − 3.13`, mapping 0 V…+5 V DAC output to
   −3.1 V…+5 V on G2. The negative DC offset is set by a 1N4733A
   5.1 V Zener (D2) reference and the R20/R23 feedback ratio
   (6.2 kΩ / 10 kΩ). At DAC = 0 V the DGFET sits well below
   V_TO = −2 V (simulated I_D = 12 pA, on/off ratio ~10⁹). At
   DAC = +5 V the DGFET is fully conducting (I_D ≈ 13 mA,
   V_D ≈ +5.9 V). **There is no separate KEY_UP GPIO.** Firmware
   controls RF on/off entirely by what it writes to the envelope DAC.
3. **DGFET drain** → **R1 (50 Ω) + C1 (100 pF) snubber** → single-
   pole ~32 MHz LPF to tame Si5351's sub-nanosecond CMOS edges.
4. **U1 LM7171** non-inverting amp with **build-time gain hedge**:
    - R_f = 3 kΩ installed in the feedback path
    - R_g to GND left **unpopulated by default** → unity gain
    - Populate R_g = 1 kΩ → gain = 4, ~2 Vpp drive to the PA
   The build-time choice lets the operator pick between class-AB
   (R_g open, gentle drive) and class-C (R_g = 1 kΩ, hard drive).
5. **R2 (50 Ω) series back-match** into coax, SMA J1 on analog →
   short RG316 → SMA J3 on ss_pa.
6. **ss_pa T201** (BN61-2402) input transformer, 2-turn primary,
   3-turn bifilar secondary, with DRIVER_BIAS injected at the
   center-tap. Phase-splits single-ended RF into push-pull drive for
   the BS170 pair.
7. **BS170 PP pre-driver** (Q2, Q6). Each gate driven from one end
   of T201 secondary via 220 Ω series. Each source grounded through
   **2.2 Ω, 1/4 W** for source degeneration (no bypass cap — the
   ~1.7 dB gain cost is accepted to buy stability and matched
   behavior against FET-to-FET β spread).
8. **ss_pa T202** (BN61-2402) interstage transformer. 3-pin bifilar
   primary (CT fed from +12 V through an L18 ferrite choke; outer
   pins to the two BS170 drains); 2-pin secondary (5 T) drives the
   IRF510 gates.
9. **IRF510 PP finals** (Q3, Q4). Each gate: driven from T202
   secondary through a classic QRP-Labs drain-gate feedback network
   (C/R/L) for bandwidth flattening and VHF stability, DC-biased by
   PA_Bias_A/B through 47 Ω each. Each source: through R1||R2 or
   R3||R4 (0.22 Ω × 2 in parallel = 0.11 Ω effective) for current
   sensing and thermal degeneration. Source voltage is RF-filtered
   on-board (four 220 nF 0805 X7R caps, two per source node) and
   routed to the Metro ADC via J31 as Source_Sense_A/B.
10. **ss_pa T203** (Amidon T50-43) bifilar drain feed, DC +13.8 V to
    each IRF510 drain, transparent to differential-mode RF.
11. **ss_pa T204** (BN43-202) output transformer, 2:3 ratio →
    2.25× impedance step-up. 50 Ω antenna load reflects as ~22 Ω
    drain-to-drain, matched to the IRF510 pair at ~10 W output.
12. **Coax to Output LPF board** via SMA J1 (ss_pa) → SMA input of
    LPF.
13. **Output LPF** — 7-pole Chebyshev CLCLCLC, 0.1 dB ripple, 50 Ω
    source/load. One bank per band selected by the band's G6K
    relay. Simulated 20 m bank rejects 3rd harmonic by 68 dB and
    5th by 84 dB — all harmonics sit > 27 dB below the FCC Part 97
    −43 dBc floor.
14. **Antenna** via SMA chassis-mount jack.

## 6. Control architecture

### 6.1 Microcontroller

**Adafruit Metro ESP32-S3** (ESP32-S3-WROOM-1 on Metro Arduino form
factor). Firmware runs **ESP-IDF v5.4.4 LTS natively** (not
Arduino), C++17, FreeRTOS tasks pinned to specific cores for
determinism. Firmware actively monitors the IRF510 PA finals via
Source_Sense_A/B ADC inputs and the FAULT_N input — this telemetry
is a core part of the design because **both class-AB and class-C
operation will be explored**, and firmware needs to adapt bias
setpoints, log drain current waveforms, and respond to overcurrent
trips that differ between the two classes.

### 6.2 I²C bus

Single I²C bus. The Metro's native I²C (3.3 V) is level-shifted up
to the +5 V HV bus by an Adafruit #757 BSS138 breakout at the Metro
I²C entry. The HV +5 V bus serves:

- **Si5351A** at `0x60` (factory default)
- **MCP4728** (U3) at `0x67` (reprogrammed from factory `0x60` on
  first boot — both parts default to `0x60` so one must be moved;
  procedure in `Documentation/i2c_bus.md`)
- **PCF8575** (U17) at `0x20` (A0/A1/A2 all open)
- **MCP4725** for LCD contrast on the front-panel sub-sheet —
  address TBD
- **Metro on-board MAX17048** fuel gauge at `0x36` (hard-wired)
- **Up to 3 I²C QT rotary encoders** on the front-panel chain

### 6.3 SPI bus

Metro native SPI (3.3 V) drives **MCP4922 (U4)** on the analog
board. MCP4922 runs on +5 V V_DD, so SPI lines (SCK, MOSI, CS_DAC,
LDAC_N) are level-shifted 3.3 → 5 V by a **74HCT125 quad buffer**
(U9) before reaching the DAC. MCP4922 channels:

- **Ch A → envelope** → U10 LM7171 offset-mute op-amp → DGFET Q2
  Gate 2. Updated at ~40 kHz (25 µs tick) during CW rise/fall edges
  following the raised-cosine LUT.
- **Ch B → DRIVER_BIAS** → J31 pin 6 → ss_pa → RC filter → T201
  secondary center-tap. Sets BS170 driver bias.

### 6.4 Rotary encoders

- **Up to 3 Adafruit I²C QT Rotary encoders** on the STEMMA-QT
  chain in the front-panel sub-sheet. Each has a 7-bit address
  selected by solder-jumper on the breakout. **INT pins are
  wire-OR'd** into a single `ENC_INT_RAW` signal, level-shifted
  on the analog board, and delivered to the Metro so firmware can
  wake up on any encoder motion and then poll the three I²C
  devices to figure out which encoder moved.
- **One MBL-600 RS-422 differential rotary encoder** (primary
  frequency-tuning knob). Outputs quadrature A/B on two RS-422
  differential pairs. On analog, an **AM26LS32 RS-422 receiver**
  (U16) converts the differential pair to CMOS; the output is then
  level-shifted 5 V → 3.3 V and routed to the ESP32-S3's PCNT
  (pulse counter) peripheral for hardware-accelerated quadrature
  decode.

### 6.5 PCF8575 (U17) I/O map

- **Band-select FET sink drives** for the Output LPF (`RLY_15`,
  `RLY_17`, `RLY_20`, `RLY_40`) over the J2 umbilical.
- **T/R control** for the LPF board's K5 relay.
- **FAULT_CLEAR** output on **P11** — PCF8575 outputs power up
  HIGH. A firmware-generated HIGH → LOW → HIGH pulse on P11
  generates a trailing-edge trigger on U18B (second half of
  CD14538B) → 1 ms monostable → opens the fault-reset switch (see
  §6.6).
- **BUTTON** input on **P10** — J15 utility screw-terminal pair with
  a 10 kΩ pull-up to +5 V (R60); press pulls the net to GND.

### 6.6 Fault chain (hardware, independent of firmware)

Entirely on the analog board, in sub-sheet
`fault_shutdown.kicad_sch`. Reference designators in the +200
series (U201, U202, R-series, C-series) distinguish fault-chain
parts from main analog refs.

**Comparator input RF filter:**

Each Source_Sense input from the J31 umbilical runs through a
two-stage LC filter before it reaches the LM393 to strip any
residual RF riding on the DC source-current voltage:

- **L208 (1 µH)** series between `Source_Sense_A_Raw` (from J31)
  and `Source_Sense_A` (the filtered node)
- **C223 (100 nF)** and **C229 (100 pF)** both from
  `Source_Sense_A` to GND — parallel bypass pair, 100 nF handles
  AF/HF, 100 pF handles VHF+
- **L209 / C224 / C228** are the identical filter on the B channel

**Comparator and input conditioning:**

- **U201 LM393** dual open-collector comparator. Both halves are
  used — one per filtered Source_Sense input.
    - **Half A**: pin 2 (−in) via R221 = 100 kΩ series from
      `Source_Sense_A` (post-filter), with R224 = 4.7 MΩ pull-up
      to +5 V (sets input bias current reference and pre-biases the
      − input slightly positive at zero source current); pin 3
      (+in) = V_REF; pin 1 (output) = FAULT_N_RAW.
    - **Half B**: pin 6 (−in) via R222 = 100 kΩ from
      `Source_Sense_B`, with R225 = 4.7 MΩ to +5 V; pin 5 (+in) =
      V_REF; pin 7 (output) = FAULT_N_RAW (wire-OR'd with half A).
    - Pin 8 = +5 V, pin 4 = GND, decoupled by **C214 = 0.1 µF**.
- Trip condition: `V(Source_Sense) × (R224 / (R221+R224)) +
  (+5 V × R221 / (R221+R224))` compared to V_REF.

**Output pullup and bias switch coupling:**

- FAULT_N_RAW node has **R209 = 100 kΩ** pullup to +5 V (defensive;
  defines idle level when CD74HC4066 switch 3 is open during a
  reset pulse).
- **U202 CD74HC4066** quad bilateral switch:
    - **Switch 3** (pins 9, 8, 6): FAULT_N_RAW (3Z, pin 9) ↔
      FAULT_N (3Y, pin 8), enabled by FAULT_N_OVERRIDE_N on 3E
      (pin 6). Closed in normal operation; opened for 1 ms during
      a fault reset.
    - **Switch 1** (pins 1, 2, 13): PA_Bias_A_Raw (1Z) ↔ PA_Bias_A
      (1Y), enabled by FAULT_N on 1E (pin 13). Opens on fault →
      PA bias A collapses.
    - **Switch 2** (pins 4, 3, 5): PA_Bias_B_Raw (2Z) ↔ PA_Bias_B
      (2Y), enabled by FAULT_N on 2E (pin 5). Opens on fault →
      PA bias B collapses.
    - **R219 = 2.2 kΩ** (PA_Bias_A to GND) and **R212 = 2.2 kΩ**
      (PA_Bias_B to GND) are stiff gate pull-downs on the IRF510
      side of switches 1 and 2. When the switch opens on fault,
      the IRF510 gate discharges through 2.2 kΩ: C_iss (~180 pF)
      collapses in **τ ≈ 0.4 µs** → PA conduction cuts well inside
      the thermal-damage window. In normal operation the DAC-fed
      PA_Bias_Raw voltage (~3.8 V in class-AB) sources ~1.7 mA
      through each 2.2 kΩ to GND, which the MCP4728 handles easily
      (24 mA output capability).
    - CD74HC4066 pin 14 (V_DD) is decoupled by **C215 = 0.1 µF**.
- FAULT_N has **R46 = 2.2 kΩ** pullup to +5 V (dominant pullup),
  **R3 = 100 kΩ + R4 = 200 kΩ** divider to GND (produces
  FAULT_N_CLEAN at 3.3 V levels for the Metro's digital input), and
  two RF/noise bypass capacitors to GND: **C14 = 0.01 µF** and
  **C225 = 100 pF**.

**V_REF generator (self-latching via negative reference):**

The latch mechanism makes V_REF go **negative** when FAULT_N
drops. Values:

- **R16 = 100 kΩ** — hysteresis coupling from FAULT_N to V_REF
- **R17 = 3.3 kΩ** — V_REF to NODEX
- **R41 = 2.7 kΩ** — NODEX to GND
- **R59 = 180 kΩ** — NODEX to −12 V
- **RV1 = 1.5 kΩ** — Bourns 3296W-152 top-adjust trimmer in series
  between R17 and R41, with the wiper tapped to R59. Rotating RV1
  shifts the −12 V tap along the R17–R41 chain, giving an
  **operator-adjustable trip current of approximately
  1.5 A to 4.2 A per FET** (verified in a QUCS-S simulation
  mirroring the fault-chain topology).

In the no-fault state, FAULT_N is near +5 V (via R46), V_REF is
positive (a few hundred mV, settable by RV1), and the LM393 output
is high-Z. In the fault state, LM393 pulls FAULT_N_RAW low →
switch 3 is closed → FAULT_N drops → R16 drags V_REF toward NODEX
(which is slightly negative via R59/R41) → V_REF goes negative →
the LM393 + input is below the − input even with zero source
current → **comparator cannot un-trip itself.** This is a true
self-latch, not just Schmitt hysteresis.

**Hardware-timed reset path (CD14538B second half):**

- Firmware pulses PCF8575 **P11 (FAULT_CLEAR)** low (HIGH is idle).
- The **trailing edge** triggers **U18B** (second half of the dual
  monostable CD14538B), configured for negative-edge trigger via
  −TR_B with +TR_B tied HIGH.
- Timing network: **R61 = 10 kΩ, C19 = 0.1 µF** → pulse width
  **T = R × C = 1.00 ms** per CD14538B datasheet.
- Inverting output **−Q_B** goes LOW for 1 ms → drives
  FAULT_N_OVERRIDE_N → U202 switch-3 enable goes LOW → 3Y/3Z path
  becomes high-Z → FAULT_N is released from the comparator path and
  rises to +5 V via R46.
- With FAULT_N HIGH for 1 ms, V_REF returns to its positive natural
  value and switches 1/2 close → PA bias is restored.
- At the trailing edge of the 1 ms pulse, switch 3 reconnects. The
  comparator then sees the actual Source_Sense values:
    - If the fault cleared → the comparator stays released, V_REF
      stays positive, PA conducts normally.
    - If the fault is still present → the comparator re-latches
      immediately, V_REF collapses again, PA bias cuts within
      18 µs.
- The first half of U18 (U18A) is the ESP32-S3 heartbeat watchdog
  (separate function). R48 = 10 kΩ pulls U18A RST_A up to +5 V.
  R62 = 10 kΩ pulls U18B RST_B up to +5 V.

## 7. Resistor convention — wattage AND footprint

**All resistors are 1/4 W DIN0207 axial case unless the Value field
explicitly carries a different wattage tag.** Convention is `nnR xW`
or `nnK xW` — for example `R44 = "15R 5W"` or `R1 = "0.22R 2W"`. If
the Value is just `"15R"` or `"4.7K"`, assume 1/4 W DIN0207.

**Values marked `xR yW` or `xK yW` use NON-DIN0207 footprints**:

- **0.22 Ω 2 W** → `Resistor_THT:R_Axial_DIN0516_L15.5mm_D5.5mm_P20.32mm_Horizontal`
- **4.7 Ω 10 W, 15 Ω 5 W, 24 Ω 10 W** → `Resistor_THT:R_Axial_Power_L25.0mm_W9.0mm_Px.xxmm_Horizontal`
  (exact footprint variant depends on the specific vendor part)

The reviewer is asked to flag any `xR yW` resistor whose assigned
`(footprint ...)` in the netlist looks inconsistent with its
wattage tag (e.g. a 2 W part still showing `DIN0207`, or a
pitch value that does not match the stated wattage).

Known non-1/4 W resistors in Rev D:

- **ss_pa R1–R4** — 0.22 Ω, 2 W (Yageo RSF200JT-73-0R22). Source
  sense + thermal degeneration on the IRF510 pair. In parallel,
  0.11 Ω per final.
- **analog R42** — 24 Ω, 10 W. Bringup inrush limiter (bypassed by
  K6 in normal operation).
- **analog R44** — 15 Ω, 5 W. Current limit on the +12 V primary
  rail.

## 8. LPF cap and inductor conventions

**Capacitors.** All 16 CF* caps across the four LPF banks use the
same footprint, `Capacitor_THT:C_Disc_D7.5mm_W2.5mm_P5.00mm`. Values
are standard E12 C0G/NP0 ceramic discs, rated **200 V**. Values in
the design: 150, 180, 220, 270, 330, 390, 470, 820 pF.

**Inductors.** The LPF schematic puts **two inductance values and a
turn count** on each L reference designator in the format
`TARGET/ACTUAL nH, NT`:

- **TARGET** (left of the slash) = Chebyshev prototype target value
- **ACTUAL** (right of the slash) = realizable value with integer
  turn count N on the chosen toroid
- **NT** = integer turn count that produces the ACTUAL value

Example: `L7 = "542/576nH, 12T"` → Chebyshev target 542 nH, actual
inductance ~576 nH when wound 12 T on the chosen core. All LPF
inductors use **T50-6** iron-powder toroids. The % offset between
TARGET and ACTUAL is < 10 % in all cases and is tunable by
spreading or bunching the winding around the core circumference.

The reviewer is asked to confirm the integer turn counts round
sensibly from the Chebyshev prototype
(`N = round(√(L_target / A_L))`, A_L = 4.0 nH/N² for T50-6).

## 9. Operating classes (both will be explored in firmware)

The design is deliberately set up so the operator can run the
IRF510 PA in **either class-AB or class-C** without any hardware
changes other than optionally populating R_g on U1 (the LM7171
output buffer).

- **Class-AB (default build):**
    - PA_Bias_A/B set to ~3.8 V by MCP4728 — each IRF510 conducts
      slightly above threshold at idle
    - U1 at unity gain (R_g unpopulated) → ~500 mVpp drive
    - Approximate efficiency 50 %, output ~5 W
- **Class-C (alternate build):**
    - PA_Bias_A/B dropped to ~1–2 V by MCP4728 — IRF510s off at
      idle; only strong signal peaks drive them above threshold
    - R_g populated at 1 kΩ on U1 → gain = 4 → ~2 Vpp drive
    - Approximate efficiency 75–80 %, output ~10 W
    - Harmonic content is worse but caught by the output LPF

The firmware's PA monitoring is therefore not optional — the
operator needs real-time per-FET current readings in both modes
to tune bias safely without burning IRF510s.

## 10. Umbilicals and board boundaries

- **J1** Analog → ss_pa — RF signal (SMA, 50 Ω).
- **J2** Analog → Output LPF — RJ45 CAT6; carries +12 V coil rail,
  four band selects (RLY_15/17/20/40), T/R control, T/R status
  back. Shield = GND.
- **J31** Analog ↔ ss_pa — RJ45 CAT6; carries Source_Sense_A/B,
  FAULT_N, DRIVER_BIAS, PA_Bias_A_Raw, PA_Bias_B_Raw, GNDs.
  **No power on this umbilical** — ss_pa gets +13.8 V on dedicated
  screw terminals (J33 on analog → J2 on ss_pa) gated upstream by
  the inrush limiter and the heartbeat relay K5.
- **Analog ↔ protoshield** — multiple screw-terminal headers along
  the shared board edge (no RJ45, no ribbon cable).
- **J35** Analog → (future tube PA) — RJ45 provisioned on analog
  but DNP today. Carries I_CATHODE_A/B, GRID_CTL_A/B,
  GRID_BLOCK_CRASH for a possible future tube-PA upgrade. Not part
  of this review.

## 11. Bringup power sequencing

- **24 Ω 10 W inrush limiter** (R42) is in series with the +13.8 V
  feed to ss_pa during initial bringup. Limits ss_pa draw to
  roughly 500 mA worst-case for the first validation session,
  enough current to verify DAC bias control, source-sense ADC
  path, and fault-chain latching without risking an IRF510 if bias
  is set wrong.
- After bringup validation, **K6** (bypass relay, G6RL-1-DC12)
  shorts out the inrush resistor and ss_pa sees the full +13.8 V
  rail through **K5** (heartbeat watchdog relay, also G6RL-1-DC12).
- The heartbeat watchdog is driven by **U18A** (first half of the
  CD14538B dual monostable); the Metro periodically retriggers the
  monostable, and if firmware hangs the monostable times out and
  K5 drops, cutting the SS PA rail.

## 12. Physical-part verification pending (reviewer, please pay attention)

Two specific items will be checked against the actual physical parts
before PCB layout is released to the board house. The reviewer is
asked to apply their own judgement from the netlist as a parallel
check.

### 12.1 Non-DIN0207 resistor footprints (`xR yW`)

See §7. Values carrying an explicit wattage tag (`"0.22R 2W"`,
`"15R 5W"`, `"24R 10W"`) use physically larger axial cases.
Reviewer should flag any instance where the netlist's `(footprint ...)`
line for one of these parts appears inconsistent with the wattage
tag.

### 12.2 DPDT slide switch (SW1 on analog, `vfo_complete.kicad_sch`)

**SW1** is the Si5351 bringup isolation switch — a mechanical DPDT
slide switch used to disconnect the Si5351 clock from the downstream
RF path during initial bringup.

- Library symbol: `Switch:SW_Slide_DPDT`
- Footprint: `Button_Switch_THT:SW_CK_JS202011CQN_DPDT_Straight`
- Pin assignments split across pole A and pole B

The schematic wiring of SW1 may not match the actual C&K
JS202011CQN pin numbering. The reviewer is asked to ignore any connectivity issues.
The actual part will be compared to the KiCad footprint prior to fab.

## 13. Known open items the reviewer should NOT re-flag

- **Metro ESP32-S3 custom footprint** on the protoshield is not yet
  drawn (U2 on protoshield has an empty footprint field).
- **J35 on analog** will connect to a future tube-PA board that has
  not yet been designed. The connector sits on analog as a
  provisioned cable exit (DNP today). Signals it carries
  (I_CATHODE_A/B, GRID_CTL_A/B, GRID_BLOCK_CRASH) are routed on-
  board but have no electrical destination outside analog today.
- `KiCAD/bias/` and `KiCAD/power/` (tube-era subsystems) are
  shelved, not being fabricated, and not part of this review.
- `KiCAD/analog/test.kicad_sch` is an orphan scratch file (not
  referenced from any other sheet). Any components inside it are
  not in the active design.

## 14. Deliverables

A single report, organized by board, that for each board addresses
the four review axes (function, component values, power dissipation,
design flaws). Within each board, the reviewer may further group by
functional block (e.g. "ss_pa / IRF510 PA stage", "analog / fault
chain", "LPF / 40 m bank") if that makes the findings easier to
action.

Please cite reference designators and pin numbers so the designer
can jump directly to the schematic or netlist location. Specific
feedback on the two §12 items (non-standard resistor footprints and
SW1 wiring) is particularly valued, since those are the two items
the designer will be physically cross-checking before PCB layout is
released.

Thank you.

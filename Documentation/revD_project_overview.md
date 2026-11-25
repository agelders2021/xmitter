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
contrast) → LC post-drain LPF → **LM7171 gain-of-4 non-inverting
buffer** → short coax to the SS PA board → **BS170
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

- **40 m** (7.000–7.300 MHz) — LPF Fc ≈ **8.5 MHz**
  *(Fc raised from 8.0 to 8.5 MHz to give adequate band-edge margin
  — 7.3 MHz now at 0.86·Fc with ~1.1 dB attenuation at the edge
  under nominal cap/L tolerance. 2nd harmonic at 14.6 MHz still sees
  ~47 dB rejection, comfortably above the FCC Part 97 43 dBc floor.
  Caps CF4/CF26 = 430 pF 200V C0G and CF6/CF8 = 750 pF 200V C0G
  (both E24). Inductors L18/L20 = 18 T on T50-6 (1296 nH),
  L19 = 19 T on T50-6 (1444 nH).)*
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
- **Post-drain 2-pole LC lowpass** (R1 49.9 Ω + L1 270 nH series,
  C1 120 pF shunt at the LM7171 input, fc ≈ 28 MHz) — tames Si5351
  CMOS edges and drain-switching harmonics before the op-amp.
- **LM7171 gain-of-4.2 non-inverting amp** (U1) with R8 = 1.5 kΩ
  feedback and R5 = 470 Ω to GND; C23 = 2 pF across R8 compensates
  the feedback above ~53 MHz for stability margin. See §5.4.
- **MCP4728** (U3) — I²C 4-channel DAC on the +5 V rail, drives
  bias setpoints
- **MCP4922** (U4) — SPI 2-channel DAC on the +5 V rail, drives the
  envelope voltage and the BS170 driver bias
- **U11 TL071CP offset-mute op-amp** — remaps the envelope DAC's
  0 V…+5 V output to −3.1 V…+5 V at the DGFET G2 (so DAC = 0 drives
  G2 below V_TO ≈ −2 V for clean cutoff)
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
    - **24 Ω 10 W inrush resistor** (R42) between SS_PWR_PRE and
      SS_PA_POWER, bypassed in normal operation by relay K5
    - **K5 and K6** (G6RL-1-DC12): **K6 is the master +13.8 V enable**
      for SS_PWR_PRE (K6 common = SS_PWR_PRE, K6 NO = +13.8 V — closed
      = rail live, open = SS_PWR_PRE floats). **K5 is the inrush
      bypass** across R42 (K5 contact in parallel with the inrush
      resistor between SS_PWR_PRE and SS_PA_POWER). **Both K5 and K6
      coil-sink paths are gated by Q7**, a 2N7000 cascode whose gate
      is driven by the CD14538B heartbeat monostable Q_A output
      (`HEARTBEAT_CTL`). Q5 (K5 driver) and Q6 (K6 driver) share a
      common source node (`Net-(Q5-S)`) that connects to Q7's drain;
      Q7's source is GND. If the heartbeat is not running, Q7 is OFF
      and neither K5 nor K6 can energize regardless of the PCF8575
      drive state. This also means the LPF band-select rail
      (`SS_PWR_PRE`, carried out on J2 pin 8) is dead at power-up until
      firmware (a) starts the heartbeat and (b) asserts P13
      (SS_PA_INRUSH_CTL) HIGH, so LPF coil relays cannot accidentally
      energize before firmware takes control.
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
   anti-resonance).
3. **On-board 10× sense pre-amplifier (U1 MCP6002).** A dual
   RRIO op-amp amplifies each source voltage 10× (R_g = 1 kΩ to
   GND, R_f = 9 kΩ in feedback) before the signal crosses the J31
   umbilical to analog. Powered from +5 V delivered by J31 pin 3
   (0.1 µF bypass at pin 8). Boosting at the sensor dramatically
   reduces the impact of GND-return IR drop on the sense accuracy.
   Op-amp outputs are routed to J31 pins 1 and 4 as
   `Source_Sense_A/B_Raw` (10× scale). The analog board attenuates
   back to 5× via a 2:1 divider before the LM393/ADC consumers
   (keeps the ADC within the ESP32's 3.3 V range).

**No LDO, no comparators, no bias switch on ss_pa.** The entire
fault chain lives on the analog board. ss_pa carries only RF
stages, bias feeds, the passive source-sense networks, the MCP6002
sense op-amp, and the J31 umbilical connector.

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
   a 39 kΩ / 10 kΩ divider from +12 V. R21 = 100 kΩ gate return. An
   input RC filter (R97 = 150 Ω series + C77 = 33 pF shunt to GND)
   sits immediately in front of G1, forming a single-pole ~32 MHz
   LPF to shave Si5351's sub-nanosecond CMOS edges before they hit
   the DGFET.
   ⚠ **Probing caveat at J9 pin 3 (Q2_PIN_3 test point):** J9.3 is
   electrically on the G1 node, which means it sits across C77.
   A standard passive scope probe (~15 pF tip capacitance) adds
   significantly to the 33 pF of C77 and shifts the filter corner
   down by roughly 30 %. Measurements at J9.3 are "circuit-
   perturbing" — useful for sanity-checking that the input path is
   alive during bringup, but not quantitatively representative of
   the un-probed signal. Prefer a FET / active probe (sub-pF tip)
   at J9.3, or measure further upstream at J9.1 (SI5351_OUT,
   source Z ~50 Ω — tolerant of passive-probe loading).
2. **Gate 2 of Q2** receives the envelope voltage. MCP4922 (U4) ch
   **B** (VoutB, pin 10) outputs 0 V…+5 V; this feeds **U11
   (TL071CP)** configured as an offset-mute op-amp whose transfer
   function is `V_G2 = V_DAC × 1.62 − 3.13`, mapping 0 V…+5 V DAC
   output to −3.1 V…+5 V on G2. The negative DC offset is set by a
   1N4733A 5.1 V Zener (D3) reference and the R20/R23 feedback ratio
   (6.2 kΩ / 10 kΩ). At DAC = 0 V the DGFET sits well below
   V_TO = −2 V (simulated I_D = 12 pA, on/off ratio ~10⁹). At
   DAC = +5 V the DGFET is fully conducting (I_D ≈ 13 mA,
   V_D ≈ +5.9 V). **There is no separate KEY_UP GPIO.** Firmware
   controls RF on/off entirely by what it writes to the envelope DAC
   channel.
3. **DGFET drain → LC LPF → LM7171 input.** The drain signal passes
   through **C9 = 10 nF C0G** (AC coupling, DC-blocks the ~5.9 V drain
   rest voltage), then **R1 = 49.9 Ω series** (Thevenin source 50 Ω),
   then **L1 = 270 nH series**, then arrives at the LM7171 (+) input
   with **C1 = 120 pF shunt to GND**. This is a 2-pole L-C lowpass
   with fc ≈ `1/(2π·√(L1·C1)) = 28 MHz` — passes 15 m (21 MHz) with
   <0.5 dB loss, rolls off Si5351 edge content and drain-switching
   harmonics above fc.
4. **U1 LM7171 non-inverting amp, fixed gain = 4.2.** As-built:
    - **R8 = 1.5 kΩ** in the feedback path (pin 6 → pin 2)
    - **R5 = 470 Ω** from pin 2 to GND
    - Gain = `1 + R8/R5 = 4.19`
    - **C23 = 2 pF** across R8 adds a feedback compensation zero;
      gain rolls off above `1/(2π·R8·C23) = 53 MHz`, well outside
      the HF bands but inside the LM7171's 200 MHz GBW so it stabilises
      the amplifier against VHF oscillation
   Produces ~2 Vpp drive to the PA chain given a typical ~500 mVpp
   signal at the LM7171 input. (Earlier builds used a "stuff R_g at
   build time" hedge between unity gain and gain-of-4; Rev D commits
   to the gain-of-4 configuration — R_g = R5 is always populated.)
5. **R2 (50 Ω) series back-match** into coax, SMA J1 on analog →
   short RG316 → SMA J3 on ss_pa.
6. **ss_pa T201** (BN61-2402) input transformer, 2-turn primary,
   3-turn bifilar secondary, with DRIVER_BIAS injected at the
   center-tap. Phase-splits single-ended RF into push-pull drive for
   the BS170 pair.
7. **BS170 PP pre-driver** (Q2, Q6). Each gate driven from one end
   of T201 secondary via **47 Ω series (R17, R18) + mix-43 ferrite
   bead (Fair-Rite / Amidon FB-43-2401, hand-assembled: slip the
   bead over one lead of the 47 Ω resistor before soldering, no
   PCB footprint needed)**. The hybrid stopper gives roughly
   120 Ω of effective impedance at 21 MHz (most of it from the R)
   but climbs to ~280 Ω at 100 MHz and ~500 Ω at 500 MHz where
   BS170 self-oscillation lives. Compared to a flat 220 Ω
   resistor (previous design), this recovers ~1 dB of drive at
   the operating frequency while improving VHF damping. Each
   source grounded through **R15/R16 = 2.2 Ω, 1 W** (axial,
   `R_Axial_DIN0411_L9.9mm_D3.6mm_P12.70mm_Horizontal`) for
   source degeneration (no bypass cap — the ~1.7 dB gain cost
   is accepted to buy stability and matched behavior against
   FET-to-FET β spread). The 1 W rating is a 3–6× margin over
   worst-case class-C hard-drive dissipation (~140 mW in the
   resistor), well inside the de-rating curve for a DIN0411
   axial carbon- or metal-film part running on this PCB.
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
   on-board (four 220 nF 0805 X7R caps, two per source node).
9a. **ss_pa Source_Sense gain stage** (U1 MCP6002 dual op-amp,
    powered from +5 V via J31 pin 3). Each source voltage goes to
    one op-amp half configured as a non-inverting 10× amp
    (R_g = 1 kΩ to GND, R_f = 9 kΩ in feedback). Output =
    `Source_Sense_X_Raw = 10 × V(source resistor)`. Boosting the
    signal before it crosses the J31 umbilical greatly reduces
    error from GND-return IR drop between ss_pa and analog.
    Op-amp output goes to J31 pins 1 (A) and 4 (B).
9b. **Analog-side 2:1 divider at LM393 input**: R65 + R68 = 10 kΩ
    each form a 2:1 attenuator from `Source_Sense_A_Raw` to GND
    with the midpoint feeding the existing LC input filter
    (L208/C223/C229). Same for channel B (R66/R67/L209/C224/C228).
    **Net effective gain seen at the LM393 input (and at the Metro
    ADC tap on `Source_Sense_X`) = 5×**, i.e. 10× op-amp divided
    by the 2:1 divider. The 5× scaling keeps the signal within the
    ESP32-S3 ADC's 3.3 V range (worst-case 4.2 A × 0.11 Ω × 5 =
    2.3 V) and keeps the fault chain's trip-current math scaled
    cleanly (see §6.6). **Firmware ADC note:**
    `I_source = ADC_voltage / (5 × 0.11 Ω) = ADC_voltage / 0.55`.
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

**⚠ ADC scaling (firmware): Source_Sense_A/B signals arrive at
the Metro ADC pre-amplified by 5×** (10× op-amp at ss_pa divided
by the 2:1 attenuator at analog). To recover the actual per-FET
source current from the ADC reading:

```c
float I_source_amps = adc_voltage_volts / (5.0f * 0.11f);  // = V / 0.55
```

With the current V_REF generator values (§6.6), the actual RV1-
adjustable trip range is roughly **1.3 A to 3.5 A per FET**, which
maps to channel-A ADC readings of **0.80 V to 2.0 V**. That span
lives squarely inside the ESP32-S3 SAR ADC's reliable "sweet spot"
of approximately **150 mV to 2450 mV** (with 11 dB attenuation and
`esp_adc_cal` eFuse calibration enabled, uncalibrated INL is
±30-50 mV in this band; calibrated, ±10-20 mV). Below ~150 mV the
ADC compresses toward 0 and noise dominates; above ~2.45 V the INL
grows and the response eventually saturates. The 5× scaling was
originally sized against an older 4.2 A trip ceiling; with the
tighter trip range the signal never approaches the saturation end,
so **no additional attenuator on Source_Sense is needed** on
channel A.

**Channel B caveat.** R66/R67 (the channel-B 2:1 attenuator pair)
are marked DNP in Rev D — see §6.6. Until those are populated,
channel B's ADC sees the un-divided Source_Sense_B_Raw, so its
reading at the same FET current is 2× channel A's. At the drawn
3.5 A trip ceiling that would be ~3.85 V, saturating the ADC.
When tuning R66/R67 at bringup, pick divider values that keep the
B-channel ADC reading ≤ 2.4 V across the full expected current
range — the simplest choice is R66 = R67 = 10 kΩ to match channel
A, unless the measured signal dictates a different ratio.

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

- **Ch A (VoutA, pin 14) → DRIVER_BIAS** → J31 pin 6 → ss_pa →
  RC filter → T201 secondary center-tap. Sets BS170 driver bias
  (slow, per-TX setting).
- **Ch B (VoutB, pin 10) → envelope** → U11 TL071CP offset-mute
  op-amp → DGFET Q2 Gate 2. Updated at ~40 kHz (25 µs tick) during
  CW rise/fall edges following the raised-cosine LUT.

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
drops. Values (as of 2026-11-24 QUCS-S sim validation, see
`xmitter_prj/test_vref/test.sch`):

- **R16 = 100 kΩ** — hysteresis coupling from FAULT_N to V_REF
- **R17 = 100 kΩ** — V_REF to NODEX
- **R41 = 2.7 kΩ** — NODEX to GND
- **R59 = 15 kΩ** — NODEX to −12 V
- **RV1 = 10 kΩ** — Bourns 3296W-103LF top-adjust trimmer in series
  between R17 and R41, with the wiper tapped to R59. Rotating RV1
  shifts the −12 V tap along the R17–R41 chain, giving an
  **operator-adjustable trip current of approximately 1.3 A to
  3.5 A per FET** (QUCS-S simulated; mirrors the fault-chain
  topology including the 5× effective gain seen at the LM393 input —
  see §5.9b for signal conditioning details).

**⚠ Design is touchy — build-time tuning expected.** The ratio of
R17/R59/RV1 strongly affects both the center and span of the trip
range, and small resistor changes can push V_REF negative (immediate
latch at power-up) or above the max V_SS reach (no trip possible).
The values above were reached after iterating against several R
combinations in QUCS-S. Final trip-range tuning on the built board
is planned at the Source_Sense signal-conditioning stage (§5.9b)
rather than here — R65/R68 on channel A and R66/R67 on channel B
are the 2:1 attenuator pairs where the actual trip point will be
trimmed. **R66 and R67 are marked DNP in the Rev D schematic** as a
physical reminder to measure the live signal first and pick divider
ratios (which can be asymmetric — e.g., 10K/4.7K for 3:1 — instead
of the drawn symmetric 10K/10K default) before populating them.

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
  0.11 Ω per final. Footprint: `R_Axial_DIN0516_L15.5mm_D5.0mm_P20.32mm_Horizontal`.
- **ss_pa R15, R16** — 2.2 Ω, 1 W. BS170 source degeneration (one
  per BS170). Upsized from the original 1/4 W after a thermal
  review showed worst-case class-C hard-drive dissipation at ~140
  mW, which left no derating margin on 1/4 W.  Footprint:
  `R_Axial_DIN0411_L9.9mm_D3.6mm_P12.70mm_Horizontal`.
- **analog R42** — 24 Ω, 10 W. Bringup inrush limiter (bypassed by
  K5 in normal operation; see §11 for why 24 Ω and not smaller).
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

The design is set up so the operator can run the IRF510 PA in
**either class-AB or class-C** with no hardware changes between
modes — only the PA_Bias_A/B DAC setpoint moves. The LM7171 is
hard-wired to gain = 4.2 (see §5.4); there is no build-time
gain-stuffing option in Rev D.

- **Class-AB:**
    - PA_Bias_A/B set to ~3.8 V by MCP4728 — each IRF510 conducts
      slightly above threshold at idle
    - LM7171 gain = 4.2 delivers ~2 Vpp at the BS170 driver input;
      the PA runs lean at this drive, producing ~5 W out at ~50 %
      efficiency
- **Class-C:**
    - PA_Bias_A/B dropped to ~1–2 V by MCP4728 — IRF510s off at
      idle; only strong signal peaks drive them above threshold
    - Same ~2 Vpp drive but with low Q-point, the PA hard-switches
      into class-C → ~10 W out at ~75-80 % efficiency
    - Harmonic content is worse but caught by the output LPF

The firmware's PA monitoring is therefore not optional — the
operator needs real-time per-FET current readings in both modes
to tune bias safely without burning IRF510s.

## 10. Umbilicals and board boundaries

- **J1** Analog → ss_pa — RF signal (SMA, 50 Ω).
- **J2** Analog → Output LPF — RJ45 CAT6; carries **SS_PWR_PRE** on
  pin 8 (the +13.8 V node after K6 — see §3.1 — and in parallel with
  the R42 inrush path to SS_PA_POWER) for the relay coils, plus four
  band selects (RLY_15/17/20/40), T/R control, T/R status back.
  Shield = GND. **Rationale for using SS_PWR_PRE rather than +12 V:**
  this rail is dead at power-up because both K5 and K6 are gated by
  the Q7 heartbeat cascode (see §3.1), so no band-select relay can
  accidentally energize before firmware (a) starts the heartbeat and
  (b) sets P13 (SS_PA_INRUSH_CTL) HIGH to close K6. A **62 Ω 1/2 W
  current-limit resistor (R28)** on the Output LPF board brings the
  G6K coil current back into spec at the higher 13.8 V rail (G6K is
  a 12 V coil nominal). R28 downsized from 1 W to 1/2 W after a
  dissipation review — steady-state power is only ~17 mW with one
  band + T/R energized (~3.4 % of a 1/2 W rating); worst-case
  simultaneous energize of all 5 relays during the brief boot
  transient is ~104 mW (~21 % of 1/2 W). Footprint:
  `R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal`.
  **Cosmetic note:** the downstream relay-coil rail on the LPF
  board is labeled `+12V` in the LPF schematic. This label collides
  with the analog board's actual regulated +12 V (LM2940CT-12
  output) — they are **different nets** that happen to share a
  name. Treat the LPF-local `+12V` as a renamed instance of
  "SS_PWR_PRE after R28 drop" (typically ~12.8 V with one band
  relay energized). A future cleanup pass should rename the LPF
  net to `LPF_COIL_PWR` or similar to avoid the collision.
- **J31** Analog ↔ ss_pa — RJ45 CAT6:
  - Pins 1, 4: `Source_Sense_A_Raw`, `Source_Sense_B_Raw` (10×
    pre-amplified source voltage, ss_pa → analog)
  - Pin 3: **+5 V** supply to the ss_pa MCP6002 sense op-amp
    (analog → ss_pa; only logic-level supply this umbilical carries)
  - Pin 6: `DRIVER_BIAS` (analog → ss_pa)
  - Pins 7, 8: `PA_Bias_A`, `PA_Bias_B` (analog → ss_pa)
  - Pins 2, 5, shield: GND
  Note: `FAULT_N` does **not** cross this umbilical — the fault
  signal and its latch live entirely on analog. The +13.8 V main
  supply for the ss_pa RF stages goes through dedicated screw
  terminals (J33 on analog → J2 on ss_pa) gated upstream by the
  K6 master enable relay and then through the K5/R42 pair
  (K5 bypasses the 24 Ω 10 W inrush resistor R42 when closed). Both
  K5 and K6 share the Q7 heartbeat-cascode enable — see §3.1.
- **Analog ↔ protoshield** — multiple screw-terminal headers along
  the shared board edge (no RJ45, no ribbon cable).
- **J35** Analog → (future tube PA) — RJ45 provisioned on analog
  but DNP today. Carries I_CATHODE_A/B, GRID_CTL_A/B,
  GRID_BLOCK_CRASH for a possible future tube-PA upgrade. Not part
  of this review.

## 11. Bringup power sequencing

- **K6** (G6RL-1-DC12, master +13.8 V enable) is the first relay in
  the chain. Its contact is between +13.8 V and SS_PWR_PRE. K6 is
  energized by Q6 (2N7000) on net SS_PA_INRUSH_CTL from PCF8575 P13,
  with the coil-sink path gated by the Q7 heartbeat cascode. Until
  firmware both (a) starts the heartbeat monostable and (b) asserts
  P13 HIGH, SS_PWR_PRE is isolated from +13.8 V.
- **24 Ω 10 W inrush limiter** (R42) sits between SS_PWR_PRE and
  SS_PA_POWER. During initial bringup, K5 is open and ss_pa is fed
  through R42, limiting ss_pa draw to roughly 500 mA worst-case
  while verifying DAC bias control, source-sense ADC path, and
  fault-chain latching.
- After bringup validation, **K5** (G6RL-1-DC12, inrush bypass)
  closes under firmware control (PCF8575 P14 → Q5 → K5 coil, gated
  by the Q7 heartbeat cascode) to short R42. ss_pa then sees the
  full +13.8 V rail at SS_PA_POWER.
- **Heartbeat watchdog** — U18A (first half of the CD14538B dual
  monostable) drives HEARTBEAT_CTL. Firmware periodically retriggers
  it; if firmware hangs, the monostable times out, HEARTBEAT_CTL
  goes LOW, Q7 opens, and the Q5/Q6 common source floats — both K5
  and K6 drop, cutting the SS PA rail in one event rather than two.

**Why R42 is 24 Ω and not smaller (e.g. 10 Ω):** the primary job of
R42 is inrush-limiting into the ~4700 µF filter cap on ss_pa when
K6 first closes — at 24 Ω the peak charge current is 575 mA,
τ = R·C = 113 ms, cap-energy of ~0.45 J dissipated as ~4 W average
for ~100 ms (comfortably inside a 10 W wirewound's thermal
envelope). A smaller R42 (e.g. 10 Ω) would still charge the cap
fine but would allow 1.4 A of steady current into a downstream
dead-short — enough to smoke the resistor long before any external
breaker reacts if, for some reason, the LM393 fault-latch path has
also failed. **The 24 Ω value is deliberately chosen to survive
indefinitely against an ss_pa short when the hardware fault chain
isn't covering it.** The trade-off: during bringup (K5 open), ss_pa
is limited to ~500 mA before the R42 voltage drop collapses the
rail below LM7171 / MCP6002 dropout. This restricts bringup
validation to quiescent-current operation (DAC bias control,
source-sense ADC path, fault-chain latching) rather than
live-RF validation — which is fine, since real RF validation
needs K5 closed anyway.

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

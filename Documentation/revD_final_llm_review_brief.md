# xmitter Rev D — Final External LLM Review Brief

> **⚠ Superseded.** This document is kept as a historical snapshot
> of the Rev D design at an earlier point. The current standalone
> brief, reflecting the live schematics, is
> **`revD_project_overview.md`** — use that one for any new review.
>
> Known staleness in this file (not corrected): R17 shown as 3.3 kΩ
> (now 6.8 kΩ), R46 shown as 10 kΩ (now 2.2 kΩ), RV1 trim pot not
> mentioned (now Bourns 3296W-502LF, 5 kΩ), trip values quoted at
> ~1 A/FET (now operator-adjustable 1.7–4.2 A/FET via RV1).

**Purpose.** This is the **final** pre-fab review package. Given to a
reviewing LLM, together with the four board netlists listed below, it
is intended to be self-contained. The reviewer is asked to perform a
**deep technical dive** on the entire Rev D xmitter design across four
axes, and to flag any design flaws they identify.

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

**Reviewer, please pay special attention to §12 (physical-part
verification pending items).** Two specific concerns are flagged there
that the designer will cross-check against the actual parts before
PCB layout is released to fab — the reviewer's judgement on these two
items is particularly welcome.

**Where this document and the schematic disagree, the schematic is
the gold standard.** This brief is a written summary intended to
orient the reviewer; the four netlists (and the KiCad schematics
they are exported from) are authoritative. If the reviewer spots a
disagreement, flag it so the designer can resolve it, but assume
the schematic is correct when choosing what to analyze.

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
each band. The RF chain is: Si5351A clock → 40673 dual-gate MOSFET
keyer (G2 modulated by an envelope DAC for raised-cosine CW shaping)
→ RC snubber → LM7171 unity-gain buffer (build-time gain hedge
available) → short coax → BS170 push-pull pre-driver → interstage
transformer → IRF510 push-pull final → output transformer → 4-band
Chebyshev LPF → antenna. The MCU is an Adafruit Metro ESP32-S3. All
bias points (BS170 driver bias, both IRF510 gate biases) are
DAC-controlled from firmware so the operator can experiment with
class-AB and class-C operation on-the-fly. A hardware fault chain
(LM393 self-latching comparator with negative-reference latch +
CD74HC4066 bias switch + 100 kΩ pulldowns) kills PA conduction within
tens of microseconds on overcurrent, independently of the MCU, and
latches until a firmware-triggered 1 ms hardware reset pulse releases
it. Supply is 13.8 V DC from a shack supply; the design has no
mains-side circuitry. Through-hole construction throughout except for
a small number of SMT 0805 bypass caps on RF-critical nodes.

## 2. Operating bands

Rev D is laid out to support four amateur HF bands via four
dedicated 7-pole Chebyshev low-pass banks selected by band-select
relay drives from a PCF8575 I/O expander. **10 m was deliberately
dropped from Rev D** (the operator has a main transceiver covering
that band; dropping 10 m saved one LPF bank and shrank the LPF
board). The retained bands are:

- **40 m** (7.000–7.300 MHz) — LPF Fc ≈ 8.0 MHz
  *(7.3 MHz sits at 0.91·Fc — in-band but tolerance margin is tight;
  component tolerances could shift the passband edge toward 7.3 MHz)*
- **20 m** (14.000–14.350 MHz) — LPF Fc ≈ 17.09 MHz
- **17 m** (18.068–18.168 MHz) — LPF Fc ≈ 20.90 MHz
- **15 m** (21.000–21.450 MHz) — LPF Fc ≈ 25.07 MHz

The band-select logic routes RF through exactly one LPF at a time
via **one DPDT relay per band** (Omron G6K-2P-Y-T1, DC12) — pole 1
switches the input end of the filter, pole 2 switches the output end
simultaneously. Both poles throw together on the same coil
energization, so unused filters are fully isolated at both ports.

## 3. Boards and their roles

Rev D is **three PCBs** (analog, ss_pa, Output LPF) plus a
Metro-mounted protoshield. **The front panel is no longer a separate
board** — all of its circuitry (LCD interface, encoder sockets,
button matrix, LED indicators, local +3.3 V LDO, etc.) has been
absorbed into the analog board as sub-sheets. There is no
`frontpanel/` project directory and no `frontpanel.net` in this
review package.

- **Analog board** (`KiCAD/analog/`). The Metro ESP32-S3 is **not
  mounted on the analog board** — it plugs into the protoshield.
  The protoshield in turn **plugs onto the analog board through a
  set of mating screw-terminal headers** (multiple screw connectors
  along the shared edge, not a single ribbon cable or RJ45). These
  screw terminals are the board boundary where every protoshield
  signal crosses onto analog. The analog board itself hosts:
    - Si5351 clock, DGFET keyer (Q2 40673), RC snubber
    - LM7171 output buffer (U1) with build-time gain hedge
    - Both DACs (U3 MCP4728 I²C 4-ch for bias, U4 MCP4922 SPI 2-ch
      for envelope and driver bias)
    - U10 LM7171 offset-mute op-amp that remaps the envelope DAC's
      0–5 V output to −3.1 V…+5 V at the DGFET G2
    - PCF8575 I/O expander (U17) for band selects, button input,
      heartbeat, and fault clear
    - AM26LS32 RS-422 receiver (U16) for the MBL-600 encoder
      differential pair
    - All onboard regulators (LM2940CT-12 for +12 V, LT1054 charge
      pump for −12 V, LM2940CT-5 for +5 V, MCP1700x-330 for +3.3 V)
    - CD14538B hardware heartbeat watchdog (U18)
    - Adafruit #757 BSS138 I²C level shifter at the Metro I²C entry
    - Si5351 bringup DPDT isolation slide switch (SW1) — **see §12.2**
    - 3 A slow-blow fuse + 1N5822 Schottky at the shack supply input
    - Fault chain (U201 LM393, U202 CD74HC4066, latching V_REF
      generator) — migrated from ss_pa to analog in 2026-10
    - Front-panel sub-sheet (WH2004A LCD interface, MBL-600 socket,
      button matrix, LED indicators)
  Entire logic rail downstream of the Metro I²C entry is +5 V (both
  DACs on +5 V V_DD).

- **ss_pa board** (`KiCAD/ss_pa/`). **Almost a direct copy of the
  QRP Labs 10 W Linear PA kit** — same RF topology, same transformer
  core choices and winding ratios, same drain-gate feedback network
  per IRF510 — laid out on a custom 4-layer PCB. Signal flow: BS170
  PP pre-driver (Q2, Q6) → input transformer T201 (BN61-2402, 2:3
  bifilar) → interstage transformer T202 (BN61-2402) → IRF510 PP
  final (Q3, Q4) → bifilar drain feed T203 (Amidon T50-43) → output
  transformer T204 (BN43-202, 2:3). The **only two deliberate
  departures** from the kit are:
    1. **DAC-controlled bias** replacing the kit's mechanical
       trimmers. BS170 driver bias comes from MCP4922 (U4 on analog)
       ch B via the J31 umbilical; each IRF510 gate bias comes from
       MCP4728 (U3 on analog) ch A/B via J31. All three bias
       setpoints are firmware-adjustable at run time.
    2. **Per-FET source-sense resistors.** R1||R2 for Q3 and
       R3||R4 for Q4 (0.22 Ω Yageo RSF200JT-73-0R22, 2 W each in
       parallel = 0.11 Ω effective per final) replace the kit's
       direct source-to-GND connection. The source voltage is
       RF-filtered on-board (four 220 nF 0805 X7R caps, two per source
       node to parallel ESL without anti-resonance) and routed back
       to the Metro ADC via J31 as Source_Sense_A/B. These sense
       resistors feed the hardware fault chain (now located on
       analog) and the firmware bias servo.
  **No LDO on ss_pa, and the entire hardware fault chain has been
  moved to the analog board.** ss_pa carries only the RF stages, the
  bias feeds, the source-sense networks (passive), and the J31
  umbilical connector — no comparators, no bias switch, no local
  regulator.

- **Output LPF board** (`KiCAD/Output LPF/`). 4-band 7-pole 0.1 dB
  Chebyshev LPF bank with 50 Ω source/load impedance. One DPDT Omron
  G6K-2P-Y-T1 (DC12) relay per band selects the active LPF. A fifth
  relay (K5) performs the TX/RX bypass function (RECEIVE_N /
  TRANSMIT_N status pins feed back to analog for Metro telemetry).
  Band-select coil drives come from the analog PCF8575 (U17) through
  open-drain FET sinks on the LPF board.

- **Protoshield** (`KiCAD/protoshield/`). An Adafruit Proto Shield
  (PID 2077) mounted on top of the Metro, which in turn **plugs
  onto the analog board through a set of mating screw-terminal
  headers** (multiple screw connectors — not one ribbon cable).
  Carries all per-pin signal conditioning that would otherwise
  clutter the analog board PCB: bypass caps on power pins, series
  Rs, pull-ups for paddles and encoder interrupt, Zener clamps,
  small RC filters. The screw terminals are the board boundary
  where every protoshield signal transitions onto analog.

- **Historical / shelved (do not review as live).** `KiCAD/bias/`
  (OPA454 grid bias generator) and `KiCAD/power/` (HV rectifier +
  filter) are retained as drawings for a possible future tube-PA
  upgrade. They are not being fabricated and are not covered by
  this review. Their netlists are not included in the review package.

## 4. Netlists for review (four files)

- `KiCAD/analog/analog.net` — includes the absorbed front-panel sub-sheet
- `KiCAD/ss_pa/ss_pa.net`
- `KiCAD/Output LPF/Output LPF.net`
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
   degeneration. Source voltage is **RF-bypassed on-board by two
   220 nF 0805 X7R caps per source node (C11||C12 on Q3 source,
   C13||C15 on Q4 source) — same value to tame the ~10 nH lead
   inductance of the DIN0516 body without introducing an
   anti-resonance notch** — then routed back to the Metro ADC via
   the J31 umbilical as Source_Sense_A/B.
10. **ss_pa T203 (Amidon T50-43)** bifilar drain feed, carries DC
    +13.8 V to each IRF510 drain while being transparent to the
    differential-mode push-pull RF.
11. **ss_pa T204 (BN43-202)** output transformer, 2:3 primary-to-
    secondary ratio → impedance step-up of 2.25×. 50 Ω antenna load
    reflects back as ~22 Ω drain-to-drain, matched to the IRF510 pair
    at ~10 W output. Pin 3 of secondary = GND; pin 4 = RF out.
12. **Coax to Output LPF board** via SMA J1 (ss_pa) → SMA input of
    the LPF board.
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
Firmware **actively monitors** the IRF510 PA final via the
Source_Sense_A/B ADC inputs and the FAULT_N input — this telemetry
is a core part of the design because **both class-AB and class-C
operation will be explored**, and firmware needs to adapt bias
setpoints, log drain current waveforms, and respond to overcurrent
trips that differ between the two classes.

### 6.2 I²C bus

Single I²C bus. The Metro's native I²C (3.3 V) is level-shifted up
to the +5 V HV bus by an Adafruit #757 BSS138 breakout at the Metro
I²C entry. The HV +5 V bus serves:

- **Si5351A** at **0x60** (factory default)
- **MCP4728 (U3)** at **0x67** (reprogrammed from factory 0x60 on
  first boot — both parts default to 0x60 so one must be moved;
  procedure described in `Documentation/i2c_bus.md`)
- **PCF8575 (U17)** on analog at **0x20** (A0/A1/A2 all open)
- **MCP4725** for LCD contrast on the front-panel sub-sheet — address TBD
- **Metro on-board MAX17048** fuel gauge at 0x36 (hard-wired)
- **Up to 3 I²C QT rotary encoders** on the front-panel chain

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
RS-422 MBL-600 encoder**:

- **Up to 3 Adafruit I²C QT Rotary encoders**, chained via STEMMA-QT
  on the front-panel sub-sheet. Each has a 7-bit address (planned
  by solder-jumper selection on the breakout). Their **INT output
  pins are wire-OR'd together into a single signal `ENC_INT_RAW`**,
  which is level-shifted/conditioned on the analog board and
  delivered to the Metro so firmware can wake up on any encoder
  motion and then poll the three I²C devices to figure out which
  encoder actually moved.
- **One MBL-600 RS-422 differential rotary encoder** (primary
  frequency-tuning knob). Outputs quadrature A/B on two RS-422
  differential pairs that reach the analog board. On the analog
  board, an **AM26LS32 RS-422 receiver (U16)** converts the
  differential pair to CMOS; the receiver's output is then
  level-shifted 5 V → 3.3 V and routed to the ESP32-S3's PCNT
  (pulse counter) peripheral for hardware-accelerated quadrature
  decode. The MBL-600 is thus handled directly by the Metro (no
  I²C intermediary), giving the lowest jitter for the main tuning
  knob.

### 6.5 PCF8575 (U17) assignments

The 16-bit PCF8575 (U17) on the analog board drives / senses, among
other things:

- **Band-select FET sinks** for the output LPF (RLY_15, RLY_17,
  RLY_20, RLY_40) and T/R control, over J2 to the LPF board.
- **FAULT_CLEAR** output on **P11** → trailing-edge-triggered 1 ms
  monostable pulse via U18 (see §6.6).
- **BUTTON** input on **P10** — J15 utility screw-terminal pair with
  a 10 kΩ pull-up to +5 V; press pulls the net to GND.
- **FAULT_N_OVERRIDE_N** — not currently a direct PCF8575 output.
  (Reviewer: confirm by inspection — the reset path is entirely
  through the CD14538B monostable; no software override is wired
  that bypasses the hardware timing.)

### 6.6 Fault chain (hardware, independent of firmware)

**Location: entirely on analog**, in sub-sheet
`fault_shutdown.kicad_sch`. The chain was migrated from the ss_pa
board to analog in 2026-10 so the ss_pa could drop its local +5 V
LDO entirely. Reference designators in the fault chain are in the
+200 series (U201, U202, R-series, C-series, D203) to keep them
distinct from the main analog refs.

**Comparator and bias switch:**

- **U201 (LM393)** open-collector dual comparator. Each comparator
  takes **Source_Sense_A or B on its + input** and **V_REF on its −
  input**. Trip logic: when either Source_Sense exceeds V_REF, the
  corresponding open-collector output pulls LOW, becoming the
  FAULT_N_RAW aggregator.
- **U202 (CD74HC4066)** quad bilateral switch provides series-pass
  elements for PA_Bias_A, PA_Bias_B, and the fault-reset path.
  Switches 1 and 2 pass PA_Bias_A/B when FAULT_N is HIGH; switch 3
  passes FAULT_N_RAW to FAULT_N when the FAULT_N_OVERRIDE_N
  (monostable output) is HIGH.
- Dedicated 100 kΩ pull-downs on each IRF510 gate collapse C_iss
  (~180 pF) in ~18 µs when their 4066 switch opens → cuts PA
  conduction well inside the thermal-damage window.
- **D203** (BAT85 Schottky) sits in the comparator-to-FAULT_N
  coupling path. (In earlier revisions this diode was `D3` on
  ss_pa; after the fault-chain migration the reference designator
  is **D203** on analog's `fault_shutdown.kicad_sch` sub-sheet.
  Any mention of "D3" in older documentation refers to this part.)

**True-latching V_REF generator:**

The latch mechanism relies on V_REF going **negative** when FAULT_N
is low. Values (all simulated in ngspice, see
`xmitter_prj/fault_vref_no_pullup.cir`):

- **R16 = 100 kΩ** — hysteresis coupling from FAULT_N to V_REF
- **R17 = 3.3 kΩ** — V_REF to NodeX
- **R59 = 180 kΩ** — NodeX to −12 V
- **R41 = 2.7 kΩ** — NodeX to GND
- **R46 = 10 kΩ** — FAULT_N pullup to +5 V (also the comparator
  wire-OR termination)

NodeX sits at a bias point around −177 mV from the R59/R41 divider.
V_REF then shifts around NodeX depending on where FAULT_N sits:

- **No-fault state** (FAULT_N ≈ +5 V): V_REF ≈ +0.114 V →
  trip threshold at Source_Sense ≈ 0.114 V = ~1.04 A per FET
- **Latched state** (FAULT_N ≈ +0.05 V): V_REF ≈ −0.165 V → below
  GND, so the LM393 + input is below the − input even with zero
  source current → **comparator cannot un-trip itself**

Hysteresis = 278 mV. The ngspice sweep confirms both operating
points. V_REF going negative is what makes this a true latch rather
than Schmitt-trigger hysteresis — a comparator with − input above +
input cannot flip back on its own.

**Hardware-timed reset path (CD14538B second half):**

- Firmware pulses PCF8575 **P11 → FAULT_CLEAR** low (HIGH is idle).
- The **trailing edge** triggers **U18B** (second half of the dual
  monostable CD14538B), configured for negative-edge trigger via
  −TR_B with +TR_B tied HIGH. The trailing-edge choice is
  deliberate: PCF8575 outputs power-up HIGH, so an idle-HIGH input
  with a trailing-edge trigger means the monostable does not fire
  spuriously on boot.
- Timing network: **R61 = 10 kΩ, C19 = 0.1 µF** → pulse width
  T = R × C = **1.00 ms** per CD14538B datasheet.
- Inverting output **−Q_B** goes LOW for 1 ms → drives
  **FAULT_N_OVERRIDE_N** → U202 switch-3 enable goes LOW → the
  3Y–3Z path becomes high-Z → FAULT_N is released from the
  comparator output and rises to +5 V via R46 pull-up.
- With FAULT_N HIGH for 1 ms, V_REF rises to +0.114 V and the
  CD74HC4066 bias switches close → PA_Bias_A/B are restored.
- At the trailing edge of the 1 ms pulse, 3Y–3Z reconnects. The
  comparator then sees the actual Source_Sense values:
    - **If fault condition cleared** → comparator stays un-tripped,
      V_REF holds at +0.114 V, PA conducts normally.
    - **If fault still present** → comparator re-latches immediately,
      V_REF collapses back to −0.165 V, PA bias cuts within 18 µs.
- The first-half of U18 (U18A) is the ESP32-S3 heartbeat watchdog —
  separate function, unrelated to fault reset. R48 = 10 kΩ pulls
  U18A RST_A up to +5 V; no RC on RST_A since the heartbeat input
  is idle-HIGH already.

**Known open item in fault chain** — see §13.

## 7. Resistor convention — wattage AND footprint (please apply)

**All resistors are 1/4 W DIN0207 axial case unless the Value field
explicitly carries a different wattage.** Convention is `nnR xW` or
`nnK xW` — for example `R44 = "15R 5W"` or `R1 = "0.22R 2W"`. If the
Value is just `"15R"` or `"4.7K"`, assume 1/4 W DIN0207.

**Critical note for the reviewer:** values marked `xR yW` are
**NOT the usual DIN0207 footprint**. They are physically larger
axial-leaded parts whose footprint has been hand-assigned to the
larger case:

- **0.22R 2W** → `Resistor_THT:R_Axial_DIN0516_L15.5mm_D5.5mm_P20.32mm_Horizontal`
- **4.7R 10W** (inrush limiter) and **15R 5W** (current limit) →
  `Resistor_THT:R_Axial_Power_L25.0mm_W9.0mm_Px.xxmm_Horizontal` or
  similar

The reviewer is asked, **to the extent possible from the netlist
alone**, to flag any `xR yW` resistor whose assigned footprint field
looks inconsistent with its wattage (e.g. a 2 W part still showing
`DIN0207`, or a mismatched hole pitch). The designer will **cross-check
every non-1/4 W resistor against the actual physical part in-hand
before PCB layout is released to fab** — this reviewer flag is a
belt-and-braces check against a dropped footprint reassignment during
schematic edits.

Known non-1/4 W resistors in Rev D (as of this brief):

- **R1–R4 on ss_pa** — 0.22 Ω, 2 W (Yageo RSF200JT-73-0R22).
  Source-sense + thermal degeneration on the IRF510 pair. In
  parallel, 0.11 Ω per final.
- **R44 on analog power sheet** — 15 Ω, 5 W. Current-limit resistor
  on the +12 V primary rail.
- **R-inrush on analog power sheet** — 24 Ω, 10 W. Bringup inrush
  limiter (used only during SS PA 500 mA bringup validation; shorted
  out by relay in normal operation).

Every other resistor in the four netlists should be interpreted as
a standard 1/4 W DIN0207 part.

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
servo potential) differently in each mode.

- **Class-AB (default build):**
    - PA_Bias_A/B set to ~3.8 V by MCP4728
    - U1 at unity gain (R_g unpopulated) → ~500 mVpp drive
    - Approximate efficiency 50 %, output ~5 W
- **Class-C (alternate build / later experiment):**
    - PA_Bias_A/B dropped to ~1–2 V by MCP4728
    - R_g populated at 1 kΩ on U1 → gain = 4 → ~2 Vpp drive
    - Approximate efficiency 75–80 %, output ~10 W

The firmware's PA monitoring is therefore not optional — the
operator needs real-time per-FET current readings in both modes to
tune bias safely without burning IRF510s.

## 10. Umbilicals and board boundaries (quick reference)

- **J1** Analog → ss_pa — RF signal (SMA, 50 Ω).
- **J2** Analog → Output LPF — RJ45 CAT6; carries +12 V coil rail
  (pin 8), four band selects (pins 2–5), T/R control (pin 1), T/R
  status back (pins 6, 7). Shield = GND.
- **J31** Analog ↔ ss_pa — RJ45 CAT6; carries Source_Sense_A/B
  (pins 1, 4), FAULT_N (pin 3), DRIVER_BIAS (pin 6), PA_Bias_A_Raw
  (pin 7), PA_Bias_B_Raw (pin 8), and GNDs. **No power on this
  umbilical** — ss_pa gets +13.8 V on dedicated screw terminals
  (J33 → ss_pa J2).
- **Analog ↔ protoshield** — six-pair screw-terminal harness.
- **J35** Analog → (future tube PA) — RJ45 provisioned on analog
  but with no destination today. DNP in Rev D. Carries
  I_CATHODE_A/B, GRID_CTL_A/B, GRID_BLOCK_CRASH for a possible
  future tube-PA upgrade. Not part of this review.

## 11. Bringup power sequencing

- **24 Ω 10 W inrush limiter** (relay-bypassed) is in series with
  the +13.8 V feed to ss_pa during initial bringup. Limits ss_pa
  draw to ~500 mA worst case for the first validation session —
  enough current to verify DAC bias control, source-sense ADC
  path, and fault-chain latching without risking an IRF510 if the
  bias is set wrong.
- After bringup validation, K6 (bypass relay) shorts out the
  inrush resistor and the ss_pa sees the full +13.8 V rail
  through K5 (heartbeat watchdog relay).

## 12. Physical-part verification pending (reviewer, please pay attention here)

These two items will be checked against the actual physical parts
before PCB layout is released to the board house. The reviewer is
asked to apply their own judgement from the netlist as a parallel
check — anything that looks off in the netlist is worth flagging
even if the designer plans a physical cross-check.

### 12.1 Non-DIN0207 resistor footprints (`xR yW`)

See §7. Values carrying an explicit wattage tag (`"0.22R 2W"`,
`"15R 5W"`, `"4.7R 10W"`, `"24R 10W"`) use physically larger axial
cases — DIN0516 for 2 W, Axial_Power for 5 W / 10 W. The reviewer
is asked to flag any instance where the netlist's `(footprint ...)`
line for one of these parts appears inconsistent with the wattage
tag, e.g.:

- A 2 W resistor still showing `R_Axial_DIN0207_L6.3mm` footprint
- An "xW" resistor whose footprint field is **blank**
- A pitch value (`P10.16mm` vs `P20.32mm`) that does not match
  the stated wattage

The designer will match every `xR yW` part to its actual physical
sample before fab, but a netlist-side sanity check is welcome.

### 12.2 DPDT slide switch (SW1 on analog, `vfo_complete.kicad_sch`)

**SW1** on the analog board is the Si5351 bringup isolation switch
— a mechanical DPDT slide switch used to disconnect the Si5351 clock
and VFO buffer from the downstream RF path during initial bringup
of the carrier board. Current schematic:

- **Library symbol:** `Switch:SW_Slide_DPDT`
- **Footprint:** `Button_Switch_THT:SW_CK_JS202011CQN_DPDT_Straight`
- **Reference:** SW1
- Pin assignments split across the two poles (A and B sections).

**Flag:** the designer suspects the schematic wiring of SW1 may be
incorrect — specifically, the pin assignments (common, NO, NC per
pole, and the handedness of each pole) may not match the actual
C&K JS202011CQN part. The actual switch will be physically
verified against the schematic footprint before PCB layout is
released, but the reviewer is asked to:

1. Walk the connectivity through SW1 in both switch positions and
   confirm the intended function (Si5351 clock reaches the DGFET
   G1 in one position; is disconnected in the other).
2. Flag any pin assignment that looks mirrored, swapped between
   poles, or crosses pole-A and pole-B inappropriately.
3. Flag any net that routes through SW1 but whose other end
   looks like it was meant to be a different pole.

The schematic symbol's pin numbering convention and the C&K
datasheet's physical pin numbering must agree, and that is the
specific thing the designer will physically verify.

## 13. Known open issues the reviewer should NOT re-flag

To keep the review focused on new findings, these issues are
already tracked and will be addressed before fab:

- **Metro ESP32-S3 custom footprint** on the protoshield is not
  yet drawn (U2 on protoshield has an empty footprint field).
- **J35 on analog** will connect to a **future tube-PA board that
  has not yet been designed**. The connector sits on analog as a
  provisioned cable exit (DNP today) so a tube PA can be added
  later without re-fabbing analog. Signals it carries
  (I_CATHODE_A/B, GRID_CTL_A/B, GRID_BLOCK_CRASH) are routed
  on-board but have no electrical destination outside analog
  today.
- `KiCAD/bias/` and `KiCAD/power/` are shelved and not being
  fabricated.

## 14. Deliverables expected from the reviewer

A single report, organized by board, that for each board addresses
the four review axes (function, component values, power dissipation,
design flaws). Within each board, the reviewer may further group by
functional block (e.g. "ss_pa / IRF510 PA", "analog / fault chain",
"LPF / 40 m bank") if that makes the findings easier to action.

Please cite reference designators and pin numbers so the designer
can jump directly to the schematic or netlist location. Specific
feedback on the two §12 items (non-standard resistor footprints
and SW1 wiring) is particularly valued, since those are the two
items the designer will be physically cross-checking before PCB
layout is released.

Thank you.

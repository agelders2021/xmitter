# xmitter — Master Design Description

A single human-readable overview of the entire project. Current as of
2026-10-19, Rev D branch active. Where this document and a schematic
disagree, the schematic wins and this file should be updated.

> **⚠ 2026-10-23 update.** Several architecture-level changes have landed
> since 2026-10-19 (Rev D Option-C power rail changes). This document
> still describes the pre-change state in some sections. For the
> authoritative current state, see
> `Documentation/revD_prelayout_review_handoff.md`. Specific items that
> changed:
> - **Band list**: 10 m deliberately dropped. Operating bands are now
>   **40 / 20 / 17 / 15 m** only (not 10/15/17/20/40 m as described below).
> - **I²C bus architecture**: single-point level translation at the
>   Metro I²C entry via Adafruit #757 BSS138 breakout. HV bus at +5 V
>   serves Si5351, MCP4728, PCF8575 (both), MCP4725. The old STEMMA
>   chain (Metro → MCP4728 → Si5351) is retired; STEMMA port now
>   serves the encoder chain only.
> - **MCP4728 and MCP4922 moved to +5 V V_DD** (both were previously
>   at +3.3 V); MCP4728 for full 0–5 V bias output span, MCP4922 for
>   full V_OUT range. MCP4922's 3.3 V SPI from Metro is shifted up
>   through a 74HCT125 quad buffer (U9).
> - **ss_pa entire logic rail at +5 V** via new LM2936Z-5.0 LDO (U13).
>   LM393 fault latch V_REF divider re-sized (R10 10 K → 6.8 K) to
>   preserve the ~0.30 V trip threshold. FAULT_N pulled to +5 V on
>   ss_pa, divided down to 3.3 V on analog (R3/R4 = 10 K / 20 K)
>   before reaching the Metro.
> - **Shack supply input protection**: 3 A slow-blow blade fuse
>   (Keystone 3568) + 1N5822 Schottky added at J5.
> - **Si5351 bringup DPDT isolation switch** (SW1) added on
>   HV-side SDA/SCL at the Si5351 header.

---

## 1. What this project is

A **~10 W QRP CW transmitter for the 20 m amateur band** (14.0–14.35
MHz), with provision for operation on **15, 17, and 40 m** through
switched output low-pass filters (10 m was dropped — user has a main
transceiver that covers it, so dropping saved one entire LPF bank
and shrank the output LPF board). Powered from a 13.8 V DC supply.
Keyed by a hand paddle or by WinKey-emulation over USB.

Design goals, in rough priority order:
- Clean on-air signal (meets FCC Part 97 harmonic-suppression floor
  of −43 dBc with comfortable margin on all operating bands)
- Firmware-tunable bias and drive (DAC-controlled, not trimmers) so
  the operator can experiment with class-AB vs. class-C operation
  without physical adjustments
- Hardware fault protection against overcurrent (self-latching, cuts
  PA bias within tens of microseconds)
- Through-hole construction throughout (hand-solderable, repairable)
- A level of built-in telemetry (per-FET source current, fault state,
  bias servo potential) that commercial QRP kits don't offer

Non-goals:
- SSB operation (the chain is kept class-C-capable, but no linear-
  envelope specific design work is being done; SSB upgrade is a
  future possibility)
- High power (100 W+ was explored and shelved; see §9 for history)
- SMT construction (hand-tremor accommodation; see user profile)

---

## 2. System block diagram

Reading left to right, lowest-level signal to antenna:

```
+-----------------------+     RF (~500 mVpp..~2 Vpp)       +------------------+
|  Analog board         |---------------------------------->|  ss_pa board    |
|  Si5351 clock         |         single coax (J1 SMA)      |  BS170 driver   |
|  DGFET keyer (Q2)     |                                   |  IRF510 PP      |
|  RC snubber           |                                   |  fault_shutdown |
|  LM7171 buffer (U1)   |                                   +--------+---------+
|  DACs (U3 MCP4728,    |                                            |
|   U4 MCP4922)          |<==== umbilical J31 (bias+sense+fault) ====+
|  Metro ESP32-S3       |                                            |
|  I2C/SPI/GPIO         |                                      RF (~22 Vpk)
+-----------+-----------+                                            |
            | band select                                            v
            | (J2 RJ45)                                   +----------+---------+
            |                                             |  Output LPF board  |
            v                                             |  4 bands + 40m     |
     +------+------+                                      |  dual relays/band  |
     | Output LPF  |<-- band select pass-through -----+   +----------+---------+
     +------+------+                                                 |
            ^ (band select from J2 lands here)                       | RF out (filtered)
            |                                                        v
   +--------+--------+                              +---------------+
   | Frontpanel      |<== umbilical J4 (CAT6) ====>|  SMA antenna   |
   | encoder+display |     I2C + RS-422 encoder    |  jack          |
   | paddles + LEDs  |                             +----------------+
   +-----------------+
```

The analog board hosts the microcontroller, all logic rails, both
DACs, and the low-level RF generation chain. The ss_pa board is the
power amplifier and its fault chain. The Output LPF board is a
dedicated board for the band-switched output filtering (needs its own
PCB because the LPF relays and heavy-gauge filter components want
physical isolation from both the fine control logic and the hot PA).
Frontpanel handles user interaction over a CAT6 umbilical.

---

## 3. RF signal chain, stage by stage

Carrier starts as a 3.3 V CMOS square wave from the Si5351A clock
generator chip, programmable from ~2.5 kHz to ~200 MHz with 1 Hz
resolution.

### Stage 1 — Si5351 → DGFET keyer (analog board)

The Si5351 output goes directly into Gate 1 of **Q2 (40673 dual-gate
MOSFET)**, used here as a voltage-controlled amplifier (VCA). The
DGFET conducts current from +12 V (through drain-load resistor R31 =
470 Ω) when BOTH gates are above cutoff:

- **G1 (Si5351 CMOS):** carries the carrier. DC-biased to +2.45 V via
  a 39 K / 10 K divider from +12 V with 100 nF bypass, R21 = 1 MΩ feed;
  C26 AC-couples the Si5351 RF.
- **G2 (envelope DAC):** modulated by MCP4922 ch B (VoutB, pin 10)
  → routed through a **TL071CP offset-mute op-amp (U11)** that remaps
  DAC 0–5 V to G2 −3.1 V to +5 V. Transfer: `V_G2 = V_DAC × 1.62 − 3.13`.
  The negative DC offset is set by a 1N4733A 5.1 V Zener (D3)
  reference and the R20/R23 feedback ratio (6.2 K / 10 K).

At key-up, firmware writes 0 to the DAC → the op-amp's intrinsic
offset drives G2 to **−3.1 V** (V_G2S well below the 40673 V_TO of
−2 V) → DGFET fully cut off. Sim shows I_D = 12 pA in this state and
V_D stays at +12.000 V — on/off ratio ~10⁹. At key-down max, DAC
writes +5 V → G2 = +5 V → I_D ≈ 13 mA, V_S ≈ 2.9 V, V_D ≈ 5.9 V.
During CW rise/fall transitions, firmware ramps the DAC through a
raised-cosine shape (5 ms edge) so the on-air envelope is smoothly
shaped — no key clicks.

Note: the **KEY_UP GPIO net has been eliminated** in favor of this
op-amp DC-offset mute. The firmware controls RF enable/disable
entirely by what it writes to the MCP4922 envelope channel — there is
no separate hardware mute path. Replaces the prior Q11/Q12 PNP level
shifter which failed to achieve CW-grade cutoff in simulation (only
~2.6:1 on/off ratio because biasing G1 above V_TO kept the lower
cascode device sourcing current regardless of G2 state).

The DGFET drain produces a chopped/modulated RF waveform swinging
~1.4 Vpp at full envelope. Rich in Si5351's harmonic content (square
wave edges) plus any mixing products.

### Stage 2 — RC snubber and buffer (analog board)

- **R1 (50 Ω) + C1 (100 pF)** form a single-pole 32 MHz low-pass
  snubber at the DGFET drain. Not a sharp filter — just enough to
  tame Si5351's sub-nanosecond CMOS edges and prevent broadband
  EMI radiation from the downstream signal path. The output band
  LPF handles regulatory harmonic suppression; this snubber only
  cleans up the local EMI.
- **U1 (LM7171 high-speed op-amp)** buffers the filtered signal
  with a build-time gain hedge:
  - **R_f = 3 kΩ** installed in feedback
  - **R_g to GND** intentionally **unpopulated by default**
  - Default: unity gain (R_g open → `gain = 1 + 3k/∞ = 1`)
  - To get class-C-capable drive: **populate R_g = 1 kΩ** →
    gain = 4 → ~2 Vpp at the PA input
- **R2 (50 Ω)** series output back-match into the coax.

### Stage 3 — Coax interconnect to PA

Single-ended RF leaves the analog board via **J1 (SMA)** and enters
the ss_pa board via **J3 (SMA)**. Short chassis-length run (<30 cm),
RG316 or similar.

### Stage 4 — Input transformer T201 (ss_pa)

**T201** is a **BN61-2402 binocular ferrite** core, vertical mount,
hand-wound:
- Primary: 2 turns (pins 1 = RF in, 2 = GND)
- Secondary: 3-turn bifilar (pins 3 and 5 to the two BS170 gates;
  pin 4 is the center tap, where DRIVER_BIAS is injected)

Phase-splits the single-ended RF input into two equal, opposite-
polarity drives for the push-pull driver stage. DRIVER_BIAS DC is
inserted at the center tap so each BS170 gate sees the same DC bias
voltage plus/minus the AC drive.

### Stage 5 — BS170 PP driver (ss_pa)

**Q2 and Q6** (both BS170) in push-pull configuration. Each FET's
drain feeds one end of T202's bifilar primary. Each gate is driven
from the respective end of T201's bifilar secondary.

- Gates biased by **DRIVER_BIAS** from analog U4 MCP4922 ch B via
  T201 center tap and R17/R18 (220 Ω each)
- Sources connect to GND through R15/R16 (2.2 Ω each, source
  degeneration for stability)
- Drains to T202 primary + L18 center-tap bias feed to +12 V

### Stage 6 — Interstage transformer T202 (ss_pa)

**T202** is also **BN61-2402**, vertical mount, 5 pads:
- Primary (3-pin, bifilar CT): pins 1 and 3 to BS170 drains, pin 2
  is CT (bias feed from +12 V through L18 ferrite choke, RF
  blocked)
- Secondary: 2-pin (5-turn winding, drives IRF510 gates through
  the drain-gate feedback network)

Steps up the voltage from the BS170 drains to the gate drive
required for the IRF510 PP finals.

### Stage 7 — IRF510 push-pull finals (ss_pa)

**Q3 and Q4** (both IRF510 N-channel power MOSFETs) in push-pull:

- Gates: driven from T202 secondary via drain-gate feedback network
  (C7/C8 + R5/R6 + L1/L2 — classic QRP Labs 10 W kit feedback for
  bandwidth flattening and VHF stability), DC-biased by
  PA_Bias_A/B through R7/R8 (47 Ω each) from the fault-shutdown
  switch output
- Drains: feed T204 output transformer and T203 bifilar drain-feed
  choke (which carries DC +13.8 V to each drain via its CT)
- Sources: through R1||R2 and R3||R4 (two 0.22 Ω in parallel per
  FET = 0.11 Ω effective) for both current sensing and thermal
  degeneration. Not bypassed with caps — the ~1.7 dB gain cost
  buys stability against FET mismatch and thermal runaway. Source
  voltage goes back to the Metro ADC as Source_Sense_A/B via J31
  umbilical.

### Stage 8 — Drain feed T203 (ss_pa)

**T203** is an **Amidon T50-43 toroid**, vertical (on-edge) mount,
bifilar hand-wound, 4 pads:
- Winding A: pins 1 (+13.8 V) and 2 (Q4 drain)
- Winding B: pins 3 (+13.8 V) and 4 (Q3 drain)

The two bifilar windings in anti-series present a very high common-
mode impedance (DC supply to the drains) while being transparent to
the differential-mode push-pull RF signal. Classic bifilar drain
feed topology — no DC in the output transformer core.

### Stage 9 — Output transformer T204 (ss_pa)

**T204** is a **Fair-Rite BN43-202 binocular** core, horizontal
mount (kit style), 4 pads:
- Primary (pins 1, 2): drain-to-drain across the IRF510 pair
- Secondary (pins 3, 4): pin 3 = GND, pin 4 = RF output

Impedance ratio 2:3 in turns → (3/2)² = 2.25× step-up in impedance.
50 Ω antenna load reflects back as ~22 Ω drain-to-drain, well
matched to the IRF510 pair at ~10 W output.

### Stage 10 — Coax to Output LPF board

The ss_pa board's RF output leaves via **J1 (SMA)** and enters the
Output LPF board. Maximum level ~22 V peak into 50 Ω (10 W). Use
RG316 or RG400 for the thermal and voltage margin.

### Stage 11 — Band-switched LPF (Output LPF board)

4 banks of 7-pole Chebyshev LPFs selected by **dual relays per
band** (input SPST + output SPST, RelComm RSS-SR042P reed relays).
Dual relays ensure unused filters are fully isolated — no shunt
loading or resonance leakage into the active path. Band select
signals come from analog U17 (PCF8575 I/O expander) via **J2 RJ45**
umbilical.

Band plan (10 m deliberately dropped from Rev D):
- 15 m: Fc ≈ 26 MHz
- 17 m: Fc ≈ 22 MHz
- 20 m: Fc ≈ 18 MHz
- 40 m: Fc ≈ 8.0 MHz (7.3 MHz sits at 0.91·Fc — in-band but
  tolerance margin is tight)

Simulated 20 m LPF (7-pole Chebyshev 0.1 dB ripple, Fc = 18 MHz)
rejects 3rd harmonic by 68 dB and 5th by 84 dB → every harmonic
sits > 27 dB below the FCC −43 dBc floor. Insertion loss 0.1 dB
in-band.

### Stage 12 — Antenna port

Clean, filtered RF leaves the LPF board to a chassis-mount SMA
antenna jack. Up to 10 W output power at 13.8 V supply, 20 m band.
Other bands tested in simulation; actual power varies slightly with
IRF510 behavior at each frequency.

---

## 4. Control architecture

### Microcontroller

**Adafruit Metro ESP32-S3** (ESP32-S3-WROOM-1 module on Metro
Arduino form factor), mounted on analog board via female headers.
Hosts all control firmware; USB connection to PC for programming
and WinKey emulation.

### I²C bus

Single I²C bus physically routed via STEMMA-QT chain from Metro's
on-board jack:
- Metro STEMMA-QT → **MCP4728 (U3) STEMMA IN** (power + bus)
- MCP4728 STEMMA OUT → **Si5351 (U5) STEMMA IN** (chained)
- Si5351's 0.1" header SDA/SCL are wired on-schematic → inject
  the bus onto the PCB traces
- PCB traces reach PCF8575 (U17) and the RJ45 J4 to frontpanel

Device addresses:
- Si5351A: **0x60** (factory default)
- MCP4728: **0x67** (reprogrammed from factory 0x60 on first boot;
  needed because both parts default to 0x60 — reprogram procedure
  uses physical isolation via the STEMMA chain, see
  `Documentation/i2c_bus.md`)
- PCF8575 main-board (U17): **0x20** (A0 open)
- PCF8575 frontpanel: **0x21** (A0 soldered high)
- Metro on-board MAX17048 fuel gauge: **0x36** (unavoidable)
- STEP encoder (Adafruit I²C QT Rotary): **0x37** (A0 soldered)
- FUNC encoder: **0x38** (A1 soldered)

### SPI bus

Metro SPI drives **MCP4922 (U4)** on the analog board, a dual
12-bit DAC:
- **Ch A (VoutA, pin 14) → DRIVER_BIAS** → J31 pin 6 → ss_pa board
  → RC filter (C19, C20) → T201 secondary CT. Sets the BS170 driver
  DC bias point. Firmware-adjustable at TX/RX transitions (slow,
  per-TX setting).
- **Ch B (VoutB, pin 10) → envelope** → Q2 (DGFET) Gate 2 via U11
  TL071CP offset-mute op-amp (V_G2 = V_DAC × 1.62 − 3.13). This is
  the raised-cosine CW envelope DAC. Update rate ~40 kHz (25 µs
  tick) during key transitions. DAC output = 0 drives G2 to −3.1 V,
  cutting off the DGFET (no separate KEY_UP net).

### DAC assignments (full picture)

- **MCP4922 (U4, SPI, 2 channels, on analog):**
  - **Ch A (pin 14): DRIVER_BIAS** → BS170 driver bias (slower, per-TX setting)
  - **Ch B (pin 10): envelope** → DGFET G2 (fast, per-dit shaping)
- **MCP4728 (U3, I²C, 4 channels, on analog):**
  - Ch A: **PA_Bias_A_Raw** → J31 pin 7 → ss_pa U2 (CD74HC4066
    fault switch) ch A input → PA_Bias_A → Q3 (IRF510) gate via
    R8 (47 Ω). Sets Q3 DC quiescent bias; firmware-controlled.
  - Ch B: **PA_Bias_B_Raw** → J31 pin 8 → ss_pa U2 ch B input →
    PA_Bias_B → Q4 (IRF510) gate via R7 (47 Ω). Sets Q4 bias.
  - Ch C, D: unused in current design; reserved for future
    expansion.

### GPIO and discrete control

- **PCF8575 (U17)** provides 16 additional I/O lines on the I²C
  bus. Current assignments:
  - P2-P5: **RLY_10, RLY_15, RLY_17, RLY_20** → J2 pins 1-3, 6
    → Output LPF band-select relays. (RLY_40 provisioned but
    needs J2 pin reassignment.)
  - Other outputs: control relays K1-K4 on analog board for
    T/R switching, bias control, etc.
- **CD14538B (U18)**: hardware heartbeat watchdog. Metro must
  pulse a PCF8575 output (P12) HIGH→LOW→HIGH at ≥ 3 Hz into the
  A-side **negative-going (−TR) trigger input**, or the
  monostable times out, Q_A drops, and K5 (SS_PWR_RLY) opens —
  removing +13.8 V from the ss_pa. Trailing-edge trigger is used
  so that the PCF8575's default-HIGH power-up state looks
  inactive (no false trigger before firmware has configured the
  pin). Same chain protects HV if a tube PA is ever added later.
  RST_A pulled HIGH via R48 (10 kΩ) — no RC on reset.
- **AM26LS32 (U16)**: RS-422 differential receiver for front-
  panel encoder signals (MBL-600 encoder) over the CAT6
  umbilical J4.

### Fault protection chain (analog board, sub-sheet `fault_shutdown.kicad_sch`)

Dedicated hardware chain, independent of firmware, that detects
overcurrent and cuts PA bias within microseconds. The entire chain
lives on the analog board (reference designators in the +200 series:
U201, U202, R-/C-/D- series). ss_pa carries only passive source-sense
networks; the Source_Sense_A/B signals cross the J31 umbilical into
the analog board.

- **U201 (LM393)** — open-collector dual comparator powered from
  +5 V. Both halves are used, one per Source_Sense input.
    - Pin 2 (half-A −in) ← R221 100 kΩ ← Source_Sense_A; pin 2 also
      has R224 = 4.7 MΩ bias pullup to +5 V
    - Pin 6 (half-B −in) ← R222 100 kΩ ← Source_Sense_B; pin 6 also
      has R225 = 4.7 MΩ bias pullup to +5 V
    - Pins 3 and 5 (both + inputs) = V_REF
    - Pins 1 and 7 (outputs) wire-OR'd into FAULT_N_RAW
    - Trip condition: Source_Sense > V_REF on either channel →
      output pulls FAULT_N_RAW low
- **RF π-filter** on each Source_Sense input before the LM393:
  L208/L209 (1 µH series) + C223/C229 (100 nF + 100 pF to GND) on
  channel A, L209 + C224/C228 on channel B.
- **FAULT_N_RAW** has R209 = 100 kΩ pullup to +5 V (defensive;
  defines idle state when switch 3 is open during reset).
- **U202 (CD74HC4066)** quad bilateral switch:
    - Switch 3 couples FAULT_N_RAW ↔ FAULT_N; enabled by
      FAULT_N_OVERRIDE_N (from CD14538B monostable half-B);
      closed in normal operation, open for 1 ms during a reset pulse
    - Switches 1 and 2 are the series-pass bias switches between
      PA_Bias_A/B_Raw (from the DACs) and PA_Bias_A/B (to the
      IRF510 gates); both enabled by FAULT_N
    - **R219 = 2.2 kΩ** (PA_Bias_A to GND) and **R212 = 2.2 kΩ**
      (PA_Bias_B to GND) are the stiff gate pull-downs that collapse
      IRF510 C_iss (~180 pF) in τ ≈ 0.4 µs when the bias switch
      opens on fault — PA conduction cuts well inside the thermal
      damage window
- **FAULT_N** has R46 = 2.2 kΩ pullup to +5 V (dominant pullup) and
  C14 = 0.01 µF + C225 = 100 pF RF/noise bypass to GND. FAULT_N also
  feeds R3 = 100 kΩ + R4 = 200 kΩ divider to produce FAULT_N_CLEAN
  at 3.3 V levels for the Metro's digital input.
- **Source_Sense signal conditioning**: Source_Sense_A/B on ss_pa
  are amplified 10× by U1 MCP6002 (dual RRIO op-amp, +5 V single
  supply from J31 pin 3) before crossing the J31 umbilical as
  `Source_Sense_A_Raw` and `Source_Sense_B_Raw`. On analog, a 2:1
  resistive divider (R65 + R68 = 10 kΩ each for channel A, R66 +
  R67 for channel B) attenuates back to 5× effective gain,
  keeping ADC readings inside the ESP32's 3.3 V input range and
  giving a cleaner trip-reference scale. **Firmware ADC scaling:**
  `I_source = ADC_voltage / 0.55` (A), i.e. 2.3 V ADC reading ≈
  4.2 A per FET.
- **V_REF generator** with operator-adjustable trip range: NODEX
  is divided from GND and −12 V by R41 = 2.7 kΩ and R59 = 15 kΩ.
  V_REF connects to NODEX through R17 = 160 kΩ in series with the
  wiper arm of **RV1 = 10 kΩ Bourns 3296W-103LF** top-adjust
  trimmer; R16 = 100 kΩ provides hysteresis coupling from FAULT_N
  back to V_REF. In the no-fault state V_REF sits positive
  (adjustable **~0.98 V to ~2.40 V** via RV1); in the latched
  state FAULT_N drops to ~0.2 V and the hysteresis path pulls
  V_REF solidly negative (−1.9 V at min-trip pot position, −0.55 V
  at max-trip pot position) so that V_REF < Source_Sense at zero
  current across the full pot range (true latch, not Schmitt
  hysteresis). Operator-adjustable trip current:
  **~1.6 A to ~4.3 A per IRF510** across RV1's travel.
- **Fault reset** via Metro: firmware pulses PCF8575 pin P11
  (FAULT_CLEAR) LOW; the trailing edge triggers CD14538B half-B
  (U18B), which drives FAULT_N_OVERRIDE_N low for 1 ms (R61 = 10 kΩ,
  C19 = 0.1 µF). Switch 3 opens during that 1 ms, releasing FAULT_N
  to +5 V via R46, restoring V_REF positive. If the fault has
  cleared, the chain stays released; if still faulting, it re-latches
  on switch-3 re-close.
- **No LDO on ss_pa** — the +5 V rail for the fault chain is
  generated on analog by U6 (LM2940CT-5.0). ss_pa receives only
  +13.8 V through its dedicated screw terminals (gated upstream by
  the heartbeat relay K5 and the inrush limiter / K6 bypass).

### Operating classes

The design accommodates both class-AB and class-C operation of the
IRF510 PA via firmware-selectable bias and build-time drive
configuration:

- **Class-AB (default, more linear, less efficient):**
  - PA_Bias_A/B set to ~3.8 V by MCP4728 → IRF510s conduct a
    bit above threshold at idle, smooth sinusoidal conduction
    through the full RF cycle
  - U1 at unity gain (R_g unpopulated) → ~500 mVpp drive → gentle
    class-AB
  - Efficiency ~50 %, output ~5 W
- **Class-C (high efficiency, needs CW/constant-envelope only):**
  - PA_Bias_A/B dropped to ~1-2 V by MCP4728 → IRF510s off at
    idle, only strong signal peaks turn them on briefly
  - Populate R_g = 1 kΩ on U1 → gain = 4 → ~2 Vpp drive, enough
    to push gates above threshold during peaks
  - Efficiency ~75-80 %, output ~10 W
  - Harmonic content worse but caught by output LPF

Firmware can switch between modes at run time (just by changing
DAC values); drive level (U1 gain) is a build-time choice.

---

## 5. Boards

### Analog board (`KiCAD/analog/`)

The control + low-level RF generation board. 200 × 150 mm landscape,
A3-centered. Hosts Metro, DACs, Si5351, DGFET keyer, LM7171 buffer,
PCF8575 expander, logic-rail regulators (+12/−12 V via LM2940/LT1054,
+5 V, +3.3 V via MCP1700), and the user-interface support (RS-422
receiver for encoder).

Connectors:
- **J1** (SMA) — RF out to ss_pa
- **J2** (RJ45) — band select (4 bands) to Output LPF
- **J31** (RJ45) — bias + sense + fault + control to ss_pa
- **J35** (RJ45) — all future tube-PA control signals
  consolidated on one umbilical (I_CATHODE_A/B,
  GRID_CTL_A/B, GRID_BLOCK_CRASH). No electrical destination
  today — provisioned so a future tube PA can be added without
  re-fabbing analog.
- **J22** (4-pin screw terminal), **J23/J24** (SMAs) — bench
  access to the tube-control signals for direct probing / scope
  attach; parallel paths to J35 (intentional).
- **J3** (4-pin screw terminal) — external bias trim access
- Various other screw terminals for power in, test points, etc.

Status: schematic complete, 100% footprinted, PCB layout pending.

### ss_pa board (`KiCAD/ss_pa/`)

**This board is essentially a direct schematic copy of the QRP Labs
10 W Linear PA kit** (same RF topology, same transformer core choices
and winding ratios, same drain-gate feedback network). The deliberate
departures from the kit are:
- **DAC-controlled bias:** replaces the kit's mechanical trimmers
  with DAC-driven PA_Bias_A/B (MCP4728 ch A/B on analog) for the
  IRF510 finals, and DRIVER_BIAS (MCP4922 ch B on analog) for the
  BS170 driver. All three bias points are firmware-adjustable.
- **Per-FET source-sense resistors:** R1||R2 and R3||R4
  (0.22 Ω Yageo RSF200JT 2 W × 2 parallel = 0.11 Ω effective) feed
  Source_Sense_A/B back to the Metro ADC via J31 and to the fault
  chain on analog. Source nodes are RF-bypassed on-board by four
  220 nF 0805 X7R caps (C11||C12 at Q3 source, C13||C15 at Q4
  source — same value to parallel ESL without anti-resonance).
- **PCB (not kit's):** laid out from scratch rather than using the
  QRP Labs PCB because the added telemetry + bias-DAC routing
  can't be cleanly bolted onto the stock board without disturbing
  RF layout.

**No LDO, no comparators, no bias switch on ss_pa.** The entire
hardware fault chain (LM393 + CD74HC4066 + V_REF generator) lives
on the analog board — see "Fault protection chain" above. ss_pa
carries only RF stages (BS170 PP driver, IRF510 PP finals, four
hand-wound ferrite transformers T201–T204), the source-sense
networks, the **MCP6002 10× sense pre-amplifier (U1)** that
boosts Source_Sense_A/B before they cross J31 to analog, the
bias feeds, and the J31 umbilical.

RF topology, winding counts, feedback R/L/C values, and
component-reference-designator numbering (T201–T204, etc.) all
mirror the kit so documentation and build knowledge transfer
directly.

Connectors:
- **J3** (SMA) — RF in from analog
- **J1** (SMA) — RF out to Output LPF
- **J2** (2-pin screw terminal) — +13.8 V in, GND
- **J31** (RJ45) — bias, sense, FAULT_N, DRIVER_BIAS to/from analog
- **J31** (RJ45) — bias + sense + fault + control from analog

Status: schematic complete, 100% footprinted, PCB layout pending.
**4-layer PCB stackup planned** (not 2-layer): outer layers for
signal + GND pour; inner layers for solid GND plane (layer 2) and
solid +13.8 V plane (layer 3). Rationale: cleaner RF return
currents under the driver + final chain, lower-impedance power
distribution for the IRF510 pulse currents (~2 A peak each),
better heat spreading through the +13.8 V plane under the drain-
feed region, and reduced EMI radiation (RF signals sandwiched
between GND references).

### Output LPF board (`KiCAD/Output LPF/`)

The output low-pass filter bank. 4 bands (40/20/17/15 m); 10 m
deliberately not covered. Dual-relay switching per band for proper
isolation (one DPDT G6K-2P-Y-T1 relay per band, pole 1 switches
output, pole 2 switches input).

**Relay coil supply:** powered by **SS_PA_Power** from analog J2
pin 8 — i.e. the switched 13.8 V downstream of K5 (heartbeat relay)
and K6 (inrush-bypass relay). This rail is **dead at power-up**
until firmware arms the heartbeat watchdog, which guarantees no
band-select relay can energize before firmware takes control.
Because the G6K coils are nominally 12 V but see ~13.8 V on
SS_PA_Power, a 62 Ω 1 W current-limit resistor **R28** on the LPF
board drops the coil voltage back into spec.

Connectors:
- **RF in** (SMA) from ss_pa
- **RF out** (SMA) to antenna
- **Band select RJ45 J2** from analog J2 (SS_PA_Power on pin 8,
  4 band selects on pins 2-5, T/R control on pin 1, T/R status on
  pins 6-7, shield = GND)

Status: schematic complete, 100% footprinted, PCB layout pending.

### Frontpanel board (`KiCAD/frontpanel/`)

User interface: 16×2 or 20×4 LCD, rotary encoders (STEP + FUNC),
LEDs, pushbuttons, paddle input. Communicates with analog via one
CAT6 cable:
- I²C (local PCF8575 at 0x21, drives LCD and LEDs; QT rotary
  encoders at 0x37, 0x38)
- MBL-600 RS-422 differential pair for one encoder (if used)
- +5 V and GND

Connector:
- **J1** (RJ45) — umbilical from analog J4

Status: schematic in development, 100% footprinted so far.

### Protoshield (`KiCAD/protoshield/`)

Adafruit Proto-Shield (PID 2077) mounted on the Metro ESP32-S3.
Carries signal-conditioning parts for Metro I/O: bypass caps,
series resistors, pull-ups for paddles, encoder interrupt, etc.
Keeps the analog board PCB cleaner by moving per-pin
conditioning to a stackable shield.

Status: schematic in progress, Metro ESP32-S3 custom footprint
still needed before layout.

### Historical / shelved

- **`KiCAD/bias/`** (OPA454 grid bias generator) — for tube PA
- **`KiCAD/power/`** (HV rectifier + filter) — for tube PA

Both retained as drawings in case a future high-power tube-PA
upgrade is attempted. Not currently being fabricated.

---

## 6. Signal naming and interconnects

Cross-board signal map is maintained in **`revD_interconnect.md`**
(this project's authoritative source for every pin-by-pin
interconnect). Updated BEFORE any netlist regen; always consult it
when a board I/O connector changes.

Quick cross-reference of important nets:
- **Carrier RF** — Si5351 output → carried on net names
  "Net-(Q2-G1)" through the DGFET, then Q2 drain → RC → U1 →
  J1 SMA → ss_pa
- **Envelope DAC output** — MCP4922 ch A, Gate 2 of Q2
- **DRIVER_BIAS** — MCP4922 ch B, J31 pin 6, BS170 driver bias
- **PA_Bias_A_Raw / PA_Bias_B_Raw** — MCP4728 ch A/B, J31 pins
  7/8, fault-switch inputs
- **PA_Bias_A / PA_Bias_B** — fault-switch outputs, routed to
  IRF510 gates
- **Source_Sense_A / Source_Sense_B** — IRF510 source voltage,
  J31 pins 1/4, to Metro ADC
- **FAULT_N** — fault latch output, J31 pin 3, to Metro input
- **RLY_10, RLY_15, RLY_17, RLY_20, RLY_40** — band-select from
  PCF8575, J2 pins 1-5 to Output LPF relays
- **I_CATHODE_A, I_CATHODE_B, GRID_CTL_A, GRID_CTL_B,
  GRID_BLOCK_CRASH** — the full set of signals that would drive
  a possible future tube PA. All consolidated on **J35** (new RJ45
  on analog, added 2026-10-19) with no destination today. Previously
  GRID_CTL_A/B lived on J2 as a stop-gap tube-PA provision; moved
  to J35 as part of the 2026-10-19 consolidation so J2 is purely
  band-select. If a tube PA is ever built, plug its control cable
  into J35 (and leave J2 for the LPF). Same signals ALSO appear on
  J22 (4-pin screw terminal) and J23/J24 (SMAs) for bench access
  / scope probing without unplugging anything from J35 (intentional
  parallel paths).

---

## 7. Firmware (planned)

Not yet scaffolded as of 2026-10-19. Will use **ESP-IDF v5.4.4
LTS** (not Arduino-ESP32), C++17, FreeRTOS native tasks pinned
to specific cores for determinism.

Planned modules:
- **main** — startup, config, task spawn
- **keyer_envelope** — raised-cosine envelope generation,
  25 µs tick, pinned to core 1 for timing determinism, writes
  MCP4922 ch A over SPI
- **keyer_winkey** — WinKey protocol emulation over USB-CDC
  (standard CW keyer protocol understood by most logging apps)
- **fault_handler** — reads FAULT_N on GPIO, Source_Sense_A/B
  on ADC, implements bias servo (slowly adjust PA_Bias to hold
  constant Iq), BIST on startup
- **band_select** — reads frontpanel band encoder, drives
  PCF8575 outputs (RLY_10..RLY_40), also programs Si5351 to the
  correct frequency
- **ui** — LCD updates, LED states, button handling, settings
  menu

See `Documentation/cw_envelope_keyer.md` for the envelope design
specifics (raised-cosine shape math, LUT, predistortion, dit
timing, WPM mapping). Note that this doc was originally written
for the MC1496 keyer topology; the envelope generation logic
(firmware, DAC, LUT) is topology-agnostic and still applies to
the DGFET keyer. The MC1496-specific hardware sections (PNP null
injection, reconstruction filter, post-keyer gain) are historical.

---

## 8. Supporting documentation

Other `.md` files that go deeper on specific areas:

- `revD_interconnect.md` — authoritative cross-board signal map
- `front_panel_interface.md` — J4 pinout, PCF8575, MBL-600 wiring
- `i2c_bus.md` — I²C address plan, STEMMA topology, reprogram
- `cw_envelope_keyer.md` — envelope DAC design and firmware
- `ss_pa.md` — ss_pa board specifics
- `control_board_functional_blocks.md` — analog board blocks
- `pcb_fab_checklist.md` — pre-fab gate items
- `build_checklist.md` — rolling phase-by-phase build items
- `ESP-IDF_Setup_Windows.md` — toolchain install notes

Historical / shelved (tube-PA era):
- `grid_bias.md`, `pa_cathode_monitor.md`,
  `2026-06-08-pa-validation.md`,
  `Cathode_Monitor_Schematic.pdf`

---

## 9. Design history (for context)

- **Rev A** (fabricated 2026-07-14): MC1496 balanced-modulator
  keyer + push-pull 6146B tube PA. Boards built; the MC1496
  keyer stage did not work (minimal output, dirty RF, suspected
  balance-trim feedback path). Rev A hardware pointed to a
  topology problem.
- **Rev B** (schematic only): pivoted keyer from MC1496 to DGFET
  (Q2 40673). Tubes still in the design but shelved as the
  primary RF path. Intermediate state.
- **Rev C** (schematic only): dropped the tube PA entirely in
  favor of a solid-state IRF510 PP output stage with the LM7171
  op-amp PP driver chain (U10/U11/U12). Full ngspice simulation
  of this chain revealed that the LM7171's ±12 V rails cap clean
  output power at ~4.5 W — the op-amp was the bottleneck, not
  the IRF510. Pushing harder caused rail clipping, broke the
  push-pull symmetry, and sent VDS flyback above the IRF510 abs
  max. Clear sign the architecture needed to change.
- **Rev D** (current): deleted the LM7171 driver, replaced with a
  single buffer stage on analog, moved the actual driver + final
  work to the ss_pa board following the QRP Labs 10 W kit
  topology (BS170 PP driver → IRF510 PP final). Added firmware-
  controlled DAC bias on both the driver and the finals so the
  operator can experiment with class-AB vs. class-C without
  mechanical trimmers. Spun the band-switched output LPF out to
  its own board. Dropped the "+3.3 V on the umbilical" and
  generated it locally on ss_pa via LDO. Added build-time
  gain hedge on U1 so a single resistor change can push the
  drive level up by 4× if class-C operation is desired.

Current branch is **revD**. There are **no plans to merge revD (or
revB or revC) to master.** Master holds the Rev A state — the
schematic and PCB files that were actually fabricated and are
physically on hand. Merging a later rev to master would wipe out
that fabricated-hardware history, which is still useful as the
reference against which the Rev A boards can be debugged, modified,
or revived. The newer branches are the active design track; master
is the fabrication record. If and when a Rev D board is actually
fabricated, we'd consider either (a) tagging the fab snapshot and
keeping revD as its own long-lived branch, or (b) advancing master
to the fabricated Rev D state — but even then, Rev A would need to
be preserved on a tag or branch of its own first.

---

## 10. Status snapshot (2026-10-19)

**Schematic:**
- Analog: complete, 100% footprinted
- ss_pa: complete, 100% footprinted (5 custom binocular/toroid
  footprints built from datasheet dimensions; marked "verify
  before fab")
- Output LPF: complete, 100% footprinted
- Frontpanel: in development, 100% footprinted so far
- Protoshield: in development, waiting on Metro ESP32-S3
  footprint

**PCB layout:**
- Analog: outline sized to 150 × 200 mm landscape, mounting
  holes placed; component placement + routing pending
- ss_pa: outline not yet started
- Output LPF: outline not yet started
- Frontpanel: outline not yet started
- Protoshield: not started

**Fabrication:**
- Rev A analog board physically exists (fabricated 2026-07-14).
  The MC1496 keyer stage didn't work, so Rev A is not operational,
  but the board is on hand and master still reflects its state.
- No Rev D boards fabricated yet. See §9 above re: no plans to
  merge revD back to master.

**Firmware:**
- ESP-IDF v5.4.4 toolchain installed and verified on both dev
  machines (primary + secondary, 2026-06-12).
- `firmware/` directory not yet scaffolded.

**Simulation:**
- Rev C full chain simulated at 14.2 MHz in ngspice; confirmed
  push-pull cancellation of even harmonics, −70+ dBc rejection
  with the 20 m band LPF, LM7171 power ceiling, and the gain
  recovery available by removing drain-gate feedback.
- Rev D chain not yet simulated end-to-end.

**Open design questions:**
- 40 m band select: J2 is full with 4 bands + GRID_CTL spares.
  To wire RLY_40 to the Output LPF umbilical, either (a)
  reassign one of the GRID_CTL pins (loses future tube-PA
  provision), (b) replace one GND pin (adds load to shield
  return), or (c) add a second small connector. No decision yet.
- Metro ESP32-S3 custom footprint for protoshield.
- Where +13.8 V enters the system physically (PA board, analog
  board, or dedicated power entry) and how it's distributed.

---

## 11. For external review / AI critique

This document is intended to be self-contained enough that a
reviewer (human or AI) can understand the project at a system level
without needing to open the schematics. For deeper review, pair it
with:
- Both netlists: `KiCAD/analog/analog.net`, `KiCAD/ss_pa/ss_pa.net`
- The interconnect spec: `Documentation/revD_interconnect.md`
- The ngspice sim decks: `xmitter_prj/revc_chain_20m*.cir`

Any reviewer should feel free to question architectural
choices — particularly the dual-DAC bias scheme, the no-bypass-cap
source degeneration, the gain-hedge on U1, and the single-coax
drive to the PA input. These were deliberate decisions but each
has a trade-off that could reasonably be made differently.

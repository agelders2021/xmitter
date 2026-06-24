# PA Cathode Current Monitor and Failsafe Chain

Per-tube cathode-current monitoring on the push-pull 6146B PA, with all the
defensive layers between a hot cathode and the MCU's ADC pin.

## Why this matters

The cathode is the only point in the PA where you can measure the **total** tube
current (plate + screen + grid) cleanly. It's the right place to detect:

- **Tube faults** — internal flashover, gas, runaway, end-of-life
- **Operating-point drift** — bias supply shift, screen supply ripple, thermal
- **PA overdrive** — drive level inappropriate for current bias / load
- **Loss of grid bias** — bias supply failure → tubes try to run at zero bias

But "the cathode" is at +1 V nominal during normal operation, sitting one
component (a 10 Ω resistor) away from a 600 V plate supply. If R_C ever opens,
the cathode floats up to plate voltage. Any sense path connected to the cathode
top needs serious protection between it and the ADC.

## System block diagram

```
                                            +600V plate
                                              │
                                             6146B
                                              │
        Cathode pin ──┬── R_C(10Ω) ── GND        ← Level 0 (cathode resistor)
                      │
                      ├── C_BYP(0.01µF) ── GND   ← RF bypass
                      │
                      └─→ DC sense tap
                          │
                          F1 (PTC, 100mA hold)   ← Level 1 (thermal slow-blow)
                          │
                          R_S(10kΩ)              ← Level 2 (current limit)
                          │
                  ┌───────┼─────────────┐
                  │       │             │
                 D1     C_FILT(1nF)    D2        ← Level 3 (clamp + anti-alias)
                  │       │             │
                 GND     GND          +3.3V
                          │
                  ┌───────┴─────────┐
                  │                 │
              U1: Op-amp           U2: Comparator   ← Level 4: buffer +
              buffer (+5V)         (LM393)              Level 5: fast hardware trip
                  │                 │
            (gain = 1)           open-drain ─┬─→ to SR latch / watchdog gate
                  │                          │
                  ▼                          │
            ADC input ───→ MCU ADC ──→ firmware  ← Level 6 (soft trip)
                                       │
                                       └──→ NVS fault log  ← Level 7 (post-mortem)
```

## Layer-by-layer design

### Level 0 — Cathode resistor + RF bypass

┌───────────┬───────────────────────┬──────────────────────────────────────────────────────────────────────────┐
│ Component │ Value                 │ Notes                                                                    │
├───────────┼───────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ R_C       │ 10 Ω, 1 W metal film  │ Sense resistor; carries full cathode current. 1 W = 4× margin at 150 mA  │
│ C_BYP     │ 0.01 µF NP0 ceramic   │ RF bypass to GND. Mount **at the tube socket cathode pin**, short leads  │
│           │                       │ (≤5 mm). Low-ESL package (1206 or smaller).                              │
└───────────┴───────────────────────┴──────────────────────────────────────────────────────────────────────────┘

**Critical layout rule:** the **DC sense tap leaves the R_C top *before* C_BYP**.
RF currents go through C_BYP to ground; DC sense goes elsewhere. This prevents
14 MHz RF from coupling into the sense chain.

Operating point (per tube, full drive):
- I_cathode_avg ≈ 100 mA (= I_plate_avg + I_screen + I_grid_drive ≈ 80 + 15 + 5)
- V_sense_DC ≈ 1.0 V
- ADC operating point: ~30 % of full-scale on a 3.3 V ADC → comfortable headroom

### Level 1 — PTC fuse (resettable thermal)

┌───────────┬─────────────────┬────────────────────────────────────────────────────┐
│ Component │ Value           │ Notes                                              │
├───────────┼─────────────────┼────────────────────────────────────────────────────┤
│ F1        │ Bourns MF-R010  │ Hold 100 mA, trip 200 mA, V_max 60 V, R ~5 Ω init  │
└───────────┴─────────────────┴────────────────────────────────────────────────────┘

Slow-blow thermal protection. Opens within ~1 s at 500 mA sustained, faster at
higher currents. Self-resets when the fault clears. Catches the case where R_C
opens AND clamp diodes are conducting hard — without F1, D1/D2 would burn
through trying to clamp 60 mA of fault current continuously. With F1, the fault
current trips F1 in <1 s and protects everything downstream.

V_max = 60 V means **F1 can't survive a 600 V cathode-open fault on its own** —
the fault voltage exceeds F1's V_max. R_S (Level 2) handles that case by
limiting fault current to a value F1 can handle while the comparator (Level 5)
trips the watchdog gate within microseconds.

### Level 2 — Series current limiter

┌───────────┬──────────────────────────┬─────────────────────┐
│ Component │ Value                    │ Notes               │
├───────────┼──────────────────────────┼─────────────────────┤
│ R_S       │ 10 kΩ, 1/4 W metal film  │ Fault current limit │
└───────────┴──────────────────────────┴─────────────────────┘

If everything above failed and the sense tap saw the full 600 V plate supply,
R_S limits fault current to 600 V / 10 kΩ = **60 mA**. That's:

- Survivable for clamp diodes (BAT54 has 200 mA peak, 30 mA continuous — would be
  damaged eventually but not instantly)
- Below F1's trip current (so F1 trips and opens the path before D1/D2 die)
- Well below R_S's own thermal limit (60 mA × 600 V × duty cycle of 100 % =
  36 W instantaneous, but R_S only sees this during the brief fault window
  before F1 opens; integrated energy is small)

Normal-case impedance of R_S vs. the op-amp's high input impedance: ADC bias
current is microamps, so the 10 kΩ drop is microvolts. No measurement error.

### Level 3 — Schottky clamps + anti-alias filter

┌───────────┬────────────────────┬────────────────────────────────────────────────┐
│ Component │ Value              │ Notes                                          │
├───────────┼────────────────────┼────────────────────────────────────────────────┤
│ D1        │ BAT54 (or 1N5817)  │ Schottky to GND, catches negative excursions   │
│ D2        │ BAT54 (or 1N5817)  │ Schottky to +3.3 V, catches positive excursions│
│ C_FILT    │ 1 nF X7R           │ Anti-alias / RF rejection                      │
└───────────┴────────────────────┴────────────────────────────────────────────────┘

D1 and D2 turn on ~300 mV beyond their rail and shunt overvoltage into the
supply. C_FILT in parallel makes the node a single-pole LPF with R_S:
fc = 1 / (2π × 10 kΩ × 1 nF) ≈ **16 kHz**. Rejects 14 MHz RF and the keying
envelope's harmonics (well above the ~200 Hz envelope content); fast enough
not to slow the comparator trip beyond ~60 µs.

The +3.3 V rail must be **stiff enough to absorb the fault current** transient
without sagging. With F1 + R_S limiting the worst case to 60 mA, the +3.3 V
rail needs an electrolytic bulk cap (~10 µF) near the clamp node to absorb the
energy. The Schottky clamps then conduct for the brief window until F1 trips
(< 1 s).

### Level 4 — Op-amp buffer (ADC isolation)

┌─────────────┬──────────────────────┬───────────────────────────────────────────────────────────────┐
│ Component   │ Value                │ Notes                                                         │
├─────────────┼──────────────────────┼───────────────────────────────────────────────────────────────┤
│ U1          │ OPA1641              │ ±20 V differential input protection, single-supply, FET input │
│ Alternates  │ LMC6041 / LM358      │ All work; OPA1641 has lowest leakage                          │
│ Supply      │ +5 V regulated, GND  │ Same +5 V the ADC uses                                        │
└─────────────┴──────────────────────┴───────────────────────────────────────────────────────────────┘

Configured as **unity-gain buffer** (output tied to inverting input). Provides:

- **Hard limit on ADC voltage:** op-amp output can only swing within its
  supplies. Even if input goes to 600 V briefly, output stays within 0–5 V.
  ADC is physically protected regardless of upstream failures.
- **High input impedance:** doesn't load R_S or affect measurement.
- **Low output impedance:** drives the ADC sample-and-hold cleanly.

OPA1641's built-in **±20 V differential input protection** means it survives
input excursions to ±20 V even if D1/D2 fail. That's an additional defensive
layer at no extra cost.

**Sanity check:** with V_sense_DC at 1.0 V nominal, the op-amp is well within
its CM range (0 V to +3 V with +5 V supply). At fault (input clamped to ~3.3 V
by D2), op-amp is at the edge of CM but still within absolute max.

### Level 5 — Hardware comparator (FAST hardware trip)

┌───────────┬────────────────────────────┬─────────────────────────────────────────────────────────────┐
│ Component │ Value                      │ Notes                                                       │
├───────────┼────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ U2        │ LM393                      │ Dual comparator (one section per tube)                      │
│ V_THR     │ +1.06 to +2.13 V from a    │ Trip threshold = ~150 mA cathode current at the chosen set  │
│           │ trimmer divider on the     │ point. R17 (27 kΩ) → RV1 (10 kΩ 25-turn cermet) →           │
│           │ shared +5 V LM4040 rail    │ R18 (10 kΩ) → GND. ONE divider feeds BOTH comparators       │
│           │                            │ (channels share the same threshold).                        │
│ R_SOURCE  │ 7.5 kΩ (one per channel:   │ Series resistor between OPA1641 OUT and LM393 (+) input.    │
│           │  R20 = ch.B, R22 = ch.A)   │ Sets the hysteresis voltage with R_HYST.                    │
│ R_HYST    │ 470 kΩ (one per channel:   │ Positive feedback LM393 OUT → (+) input. With R_SOURCE =    │
│           │  R21 = ch.B, R23 = ch.A)   │ 7.5 kΩ and a 3.15 V LM393 swing, gives ~50 mV hysteresis.   │
│ R_PULLUP  │ 4.7 kΩ to +3.3 V, one per  │ NOT a shared pull-up — see "Per-tube summing" below for the │
│           │ channel                    │ diode-OR rationale.                                         │
│ C_DEC     │ 100 nF X7R                 │ Local supply bypass at LM393 V+ pin                         │
└───────────┴────────────────────────────┴─────────────────────────────────────────────────────────────┘

Input polarity: OPA1641 buffer output (V_sense) feeds the LM393 **(+)** input
through R_SOURCE. The threshold (from the trimmer divider) feeds the **(−)**
input. When V_sense exceeds the threshold:

- LM393 output transistor turns OFF → the open-collector floats → its
  per-channel R_PULLUP takes the output node to +3.3 V (**fault = HIGH**).
- Hysteresis (R_HYST through R_SOURCE) gives ~50 mV separation between the
  trip-up and trip-down thresholds — no chatter near the set point.
- Either channel going HIGH propagates through the **diode-OR** (see
  "Per-tube summing" below) onto the GRID_BLOCK_CRASH net.
- GRID_BLOCK_CRASH (active HIGH) drives the Q2/Q3 bias-slam MOSFETs on the
  bias sheet, which yank the OPA454 summing junctions to GND → the OPA454
  outputs slam to their negative rail (~−85 V) → both tubes go to deep
  cutoff in <100 µs.
- Reset: power-cycle, or assert a firmware CLEAR line that releases the
  slam (TBD — see Open items).

Total fault response time:
- Op-amp slew + comparator decision + hysteresis settling: < 10 µs
- Diode-OR forward + bias-slam Q gate drive: < 5 µs
- OPA454 slew from operating bias (~−60 V) to negative rail (~−85 V) at
  13 V/µs: < 2 µs
- **Total cathode-to-tubes-cut-off latency: well under 100 µs**

That's fast enough to protect the tubes from internal flashover faults that
would otherwise damage them in milliseconds.

### Level 6 — Firmware soft trip

ADC samples cathode voltage at **1 kHz** per channel using the
**built-in ESP32-S3 ADC** (12-bit, on-chip, ADC1 module). Two analog
input pins on the Metro — one per tube — route off the bias sheet via
hierarchical labels `I_CATHODE_A` / `I_CATHODE_B` and land on a pair
of ESP32 GPIOs on the arduino sheet. No external ADC chip.

**Why built-in instead of ADS1115:**

- **Resolution.** 100 mA full-scale maps to ~3.0 V at the buffer
  output → 80 µA LSB. The soft-trip thresholds (warning at 120 mA,
  hard at 150 mA) sit 250–625 LSB above zero — quantization is
  ignorable.
- **Tube balance trim.** Differential matching between ADC1 channels
  (same SAR core, same Vref) is tight enough to resolve well under
  0.5 mA tube-to-tube difference. With 100-sample averaging at 1 kHz
  the noise floor drops another 10×. The practical balance limit is
  tube thermal drift (~5–10 mA over warm-up), not ADC resolution.
- **Speed.** ESP32-S3 ADC supports kHz-class sampling natively; the
  ADS1115 caps at 860 SPS in continuous mode. The hardware LM393
  comparator (Level 5) handles the fast trip path anyway — the ADC's
  only deadline is the 50 ms warning detection window.
- **Bus simplicity.** One fewer I²C address to manage on a bus that
  already carries Si5351 (0x60), MCP4728 (0x62 after reprogram), and
  the two per-tube MCP4725 bias DACs.
- **Bias DAC quantization sets the balance floor.** MCP4725 step at
  the OPA454 V+ input is ~0.8 mV → ~0.1 mA cathode current step.
  16-bit ADC precision is wasted resolution against a 12-bit DAC
  control signal.

**Cost:** ESP32 ADC INL is documented as noisy near rail ends.
Mitigation is two-point per-tube calibration (zero + a known full-load
shunt) stored in NVS — see "Calibration procedure" below.

┌───────────┬─────────┬────────────────────┬──────────────────────────────────────────────────────────────────┐
│ Threshold │ Voltage │ Cathode current    │ Action                                                           │
├───────────┼─────────┼────────────────────┼──────────────────────────────────────────────────────────────────┤
│ Nominal   │ 1.0 V   │ 100 mA             │ Normal operation, log every 1 s                                  │
│ Warning   │ 1.2 V   │ 120 mA for >50 ms  │ Soft fault: log, alert UI, reduce envelope DAC code by 10 %      │
│ Hard      │ 1.5 V   │ 150 mA for >5 ms   │ Hard fault: drop screen via watchdog GPIO, log timestamp, UI     │
└───────────┴─────────┴────────────────────┴──────────────────────────────────────────────────────────────────┘

The hardware comparator (Level 5) trips at 1.5 V too — both fire on hard
faults; the hardware path is faster, the firmware path provides logging.

Use a **running average** (10-sample / 10 ms window) before applying
thresholds, to avoid false trips from RF transients getting into the sense
chain (despite C_BYP).

### Level 7 — Persistent fault log

NVS storage (ESP32 wear-leveling NVS partition) records each fault event:

```c
struct FaultLog {
    uint32_t timestamp;       // unix seconds
    uint8_t  tube_id;         // 0 or 1
    uint8_t  fault_type;      // 0=warning, 1=hard
    uint16_t i_cathode_mA;    // current at trip
    uint16_t duration_ms;     // how long it persisted
    uint16_t recovered;       // 0=manual reset required, 1=auto-cleared
};
```

Ring buffer of last 32 events. Accessible via serial/web UI for post-mortem
analysis. Cleared by operator command.

## Per-tube wiring + grounding

```
Tube socket cathode pin
   │
   ├── R_C (mounted DIRECTLY at the socket pin) ── GND_RF
   │       │
   │      C_BYP ── GND_RF   (twisted with R_C lead, short)
   │
   └── DC sense wire ──────────→ analog board
                                  (twisted pair with GND_SENSE return)
                                  
   GND_RF and GND_SENSE meet at the analog board's single ground point.
```

Three separate "grounds":
- **GND_RF**: chassis ground at the tube socket area; bypass caps return here
- **GND_SENSE**: analog signal ground at the analog board
- **GND_DIG**: digital ground at the MCU board

All three meet at **one point**: the analog board's star ground. Prevents
ground-loop currents from corrupting the cathode sense measurement.

**Sense wire is a TWISTED PAIR**: DC sense + GND_SENSE return. Twisting kills
common-mode pickup. Optional: shielded cable, with shield grounded ONLY at the
analog board (avoids ground loops).

## Layout rules (binding decisions for this build)

### F1 and R_S stay paired in F1 → R_S order

R_C, C_BYP, **F1**, and **R_S** all mount at the tube socket area.
Only the sense signal *after R_S* routes to the analog board.

The F1 → R_S pairing is **not optional** — either keep both at the
socket, or move both to the analog board. Splitting them with the
cable in the middle creates a fault-mode failure: if F1 opens during a
cathode-open fault, no current flows, R_S drops 0 V, and the cable
sits at full plate voltage (~600 V) for the fault duration. Cable is
rated for low voltage only.

The current ordering (F1 → R_S → cable → clamps) is safe because
clamps D1/D2 actively pull cable voltage to ≤ 3.3 V while current
flows, and when F1 opens the cable is on the *clamp side* of R_S — so
it floats at clamp voltage, not source voltage.

### F1 thermal: chassis muffin fan over 6146 socket area

F1 (Bourns MF-R010) is rated 60 °C ambient. Mounted near the 6146B
socket, it sees envelope heat. A muffin fan in the chassis directed at
the bottom side of the 6146 sockets is required to keep the socket
area below 60 °C during sustained CW operation. Socket-area
temperature is not measurable once HV is live (safety) — designed-in
cooling, not bench-tuned.

### Sense cable: shielded coax, shield grounded at tube end

For this HF transmitter environment, shielded coax is chosen over the
twisted-pair alternative described above. The shield grounds ONLY at
the tube-socket end (the noisier reference) so RF return currents
drain locally instead of flowing through the shield into the analog
board. The PCB end of the shield is left floating. If HF noise shows
up on the analog board after assembly, a 1 nF ceramic from
PCB-end-of-shield to PCB GND adds an HF tie without creating a DC
ground loop.

## Calibration procedure (bring-up)

1. **Zero**: tubes in deep cutoff (key-up). ADC reading is the offset.
   Store as `cathode_offset[tube_id]`.

2. **Gain**: insert a known shunt resistor in series with the cathode return
   to a DMM. Apply moderate drive. Read both DMM (I_cathode in mA) and ADC
   counts. Compute `gain[tube_id] = (ADC_count − offset) / I_cathode_mA`.
   Repeat at 3-4 current levels to verify linearity.

3. **Threshold trim**: drive the tube to known I_cathode = 150 mA. Adjust the
   LM4040 divider trim until the comparator just trips. Verify it un-trips
   when I_cathode drops to 100 mA (50 mV hysteresis).

Store calibration constants in NVS. Re-run periodically (every 100 operating
hours or after any servicing).

## Per-tube → both-tubes summing

Two parallel sense chains, one per tube. Both feed into:

- **Per-tube ADC channels** (`I_CATHODE_A`, `I_CATHODE_B` hierarchical labels)
  tapped at the OPA1641 OUT node — *before* R_SOURCE — for individual tube
  monitoring + balance trim. Routes to ESP32-S3 ADC1 pins on the arduino sheet.
- **Comparator chain**: each tube's LM393 comparator output is HIGH on fault
  (see Level 5 polarity above). The two outputs combine through a **diode-OR**
  to produce a single GRID_BLOCK_CRASH (active HIGH) net.

### Why diode-OR (not the simpler wired-tie)

LM393 is open-collector: it can pull LOW but not drive HIGH (it depends on the
external pull-up to define the HIGH state). With our polarity (V_sense on +,
threshold on −), the OC transistor is OFF on fault — and tying two OC outputs
to a single pull-up gives wired-AND of HIGH, not wired-OR: the combined node
only goes HIGH when *both* tubes fault simultaneously. Useless for our case.

A diode-OR with **per-channel pull-ups** gives true OR:

```
       +3.3V                       +3.3V
         |                           |
        R_PU_A (4.7K)               R_PU_B (4.7K)
         |                           |
         +--- LM393A OC              +--- LM393B OC
              |                           |
              D_OR_A (1N4148, anode→cath) D_OR_B (1N4148, anode→cath)
                       \                 /
                        +-------+-------+
                                |
                              R_PD (100K to GND)   ← defines LOW when no fault
                                |
                                +---→  GRID_BLOCK_CRASH (active HIGH)
                                        │
                                        ▼
                                  Q2/Q3 bias-slam gates on bias sheet
```

Either fault → that channel's OC releases → R_PU takes it HIGH → its diode
forward-biases → common node goes to ~2.7 V → Q2/Q3 turn ON → bias slammed.
No fault → both OCs pulled LOW by their pull-ups → diodes reverse-biased →
R_PD holds the common node at 0 V → Q2/Q3 OFF → bias circuit operates normally.

No inverter required — polarity propagates straight through.

- **Optional sum probe** (future): sum the two cathode voltages via two 10 kΩ
  resistors to a third comparator with threshold at 1.4 V (≡ 280 mA total
  cathode). Catches the case where both tubes drift hot together below the
  per-tube threshold.

## BOM

Per-tube items are marked Qty=1 (multiply ×2 for the pair). Shared items
(divider, diode-OR combiner, LM393 chip) are marked with the actual count.

┌─────────────────┬──────────────────────────────┬──────────┬─────────────────────────────────────────────────┐
│ Ref             │ Part                         │ Qty      │ Notes                                           │
├─────────────────┼──────────────────────────────┼──────────┼─────────────────────────────────────────────────┤
│ R_C             │ 10 Ω 1 % 1 W metal film      │ 1/tube   │ Vishay PR01000101000JR500 or similar            │
│ C_BYP           │ 0.01 µF NP0 ceramic, 100 V   │ 1/tube   │ Mount AT the tube socket                        │
│ F1              │ Bourns MF-R010               │ 1/tube   │ PTC, 100 mA hold                                │
│ R_S             │ 10 kΩ 1 % 1/4 W              │ 1/tube   │ Mounts at the tube socket (see Layout rules)    │
│ D1, D2          │ 1N5817                       │ 2/tube   │ Schottky clamps to GND and +3.3 V               │
│ C_FILT          │ 1 nF X7R 50 V                │ 1/tube   │                                                 │
│ U13, U14        │ OPA1641                      │ 1/tube   │ Voltage-follower buffer (one IC per tube)       │
│ U12             │ LM393                        │ 1        │ Dual comparator — one IC handles both tubes     │
│ U11             │ LM4040DIZ-5.0                │ 0        │ Already in grid_bias BOM; same +5 V_REF rail    │
│                 │                              │          │ powers both subsystems                          │
│ R17             │ 27 kΩ 1 % 1/4 W              │ 1        │ Threshold divider top                           │
│ RV1             │ Bourns 3296W 10 kΩ 25-turn   │ 1        │ Threshold trim pot (shared between channels)    │
│ R18             │ 10 kΩ 1 % 1/4 W              │ 1        │ Threshold divider bottom. Wiper range:          │
│                 │                              │          │ 1.06 V – 2.13 V; nominal set point ~1.5 V       │
│ R_SOURCE        │ 7.5 kΩ 1 % 1/4 W             │ 1/tube   │ R20 (ch.B) and R22 (ch.A). OPA1641 OUT → LM393  │
│                 │                              │          │ (+). Sets hysteresis with R_HYST.               │
│ R_HYST          │ 470 kΩ 1 % 1/4 W             │ 1/tube   │ R21 (ch.B) and R23 (ch.A). LM393 OUT → (+).     │
│                 │                              │          │ ~50 mV hysteresis with 3.15 V LM393 swing.      │
│ R_PULLUP        │ 4.7 kΩ 1 % 1/4 W             │ 1/tube   │ Pull-up to +3.3 V on each LM393 OC output       │
│                 │                              │          │ (NOT shared — see "Per-tube summing").          │
│ D_OR_A, D_OR_B  │ 1N4148 (or 1N5817 since      │ 1/tube   │ Diode-OR combiner. Anode at LM393 OC, cathodes  │
│                 │  already in stock)           │          │ tied at common GRID_BLOCK_CRASH node.           │
│ R_PD            │ 100 kΩ 1 % 1/4 W             │ 1        │ Pull-down at the diode-OR common node, defines  │
│                 │                              │          │ LOW state when no fault.                        │
│ C_DEC           │ 100 nF X7R + 10 µF bulk      │ several  │ Decoupling at each IC (OPA1641, LM393, LM4040). │
└─────────────────┴──────────────────────────────┴──────────┴─────────────────────────────────────────────────┘

## Watchdog gate (grid-bias slam, on the bias sheet)

The fault output from Level 5 / Level 6 needs to **actually do something** to
protect the tubes. The current design uses **grid-bias slam** — yanking the
grid bias from its normal operating point (~−60 V) to deep cutoff (~−85 V)
within a few microseconds.

This is implemented on the `bias.kicad_sch` sheet:

- **Q2, Q3** (2N7000 N-channel MOSFETs, one per tube) sit across the OPA454
  summing junction. Their gates are tied together through R_GATE and fed by
  the `GRID_BLOCK_CRASH` net (active HIGH).
- When `GRID_BLOCK_CRASH` goes HIGH (via the diode-OR above), both MOSFETs
  turn ON simultaneously, pulling the OPA454 inverting inputs to GND through
  R_PADA / R_PADB. The OPA454 outputs slam to their negative rail (~−85 V).
- Both tubes go to deep cutoff in <100 µs (see Level 5 timing budget).

**Why grid bias instead of screen, plate, or filament?**

- **Plate**: hard to switch reliably at 600 V / 250 mA without a relay (slow,
  arcing). The plate supply cap also stores significant energy that must
  dissipate somewhere.
- **Screen**: would work (low current, fast off) but adds a separate
  switching MOSFET and a dedicated path with its own failure modes. The grid
  bias rail is already available, already controlled by the OPA454s, and
  already designed for fast slewing.
- **Grid bias**: re-uses the existing OPA454 bias generator. A single
  2N7000 per tube short-circuits the summing junction; the OPA454 then does
  the heavy lifting (slewing to −85 V at 13 V/µs). Independent of firmware
  — the slam fires purely from the hardware comparator chain.
- **Filament**: takes seconds for cathode to cool. Doesn't protect against
  the immediate fault.

See `Documentation/grid_bias.md` for the OPA454 bias generator topology and
the Q2/Q3 slam-transistor wiring detail.

## Open items

- [x] ~~Choose ADC: built-in ESP32 ADC vs. ADS1115.~~ Decided 2026-06-23:
      **built-in ESP32-S3 ADC1**, 12-bit. Rationale in Level 6 above.
- [x] ~~Decide hardware vs. firmware-only latch.~~ Decided 2026-06-23: **no
      latch chip** — diode-OR + grid-bias slam provides the fast hardware
      path (<100 µs); firmware records the event from the ADC oversampling
      path (Level 6). Slam stays asserted as long as cathode current is
      above threshold; clearing requires the fault to physically subside
      OR a firmware-asserted CLEAR (TBD wiring).
- [ ] Wire the CLEAR path. Either:
      (a) firmware GPIO that pulls the diode-OR common node LOW through a
          weak resistor (overrides R_PD only while asserted), or
      (b) skip the explicit CLEAR — assume any real fault is physical and
          the slam releases on its own when the cathode current drops back
          below threshold (− 50 mV hysteresis).
- [ ] Confirm 1N5817 voltage rating handles the 60 mA fault current
      transient on the clamp side. Datasheet: 1 A continuous, 25 A peak
      surge — comfortably above the 60 mA F1-limited fault current.
- [ ] Add the diode-OR diodes (D_OR_A, D_OR_B) and R_PD (100 kΩ pull-down)
      to bias.kicad_sch.
- [ ] Add `I_CATHODE_A` and `I_CATHODE_B` hierarchical labels on
      bias.kicad_sch and route them to ESP32-S3 ADC1 pins on the arduino
      sheet (D7/ADC1, D8/ADC1 are the picked spares).
- [ ] PCB layout: cathode socket area to analog board distance, twisted-pair
      wire gauge, shielding decision.

## Related docs

- `Documentation/2026-06-08-pa-validation.md` — PA operating point that
  determines I_cathode nominal and limits
- `Documentation/Grid_Bias_Schematic.pdf` — companion subsystem on the same
  analog board. Both subsystems share a **single LM4040DIZ-5.0** producing
  the +5 V reference rail: grid_bias uses it raw (R_G input to OPA454);
  cathode_monitor divides it down to +1.5 V (R_DIV1 / R_TRIM / R_DIV2 above)
  for the LM393 threshold. One chip, two consumers.
- `xmitter_prj/grid_bias.sch` — QUCS-S sim of the bias circuit; supplies are
  V+ = +5 V (V3) and V− = −90 V (V2), LM4040 = 5 V
- `Documentation/cw_envelope_keyer.md` — firmware fail-safe rationale (the
  watchdog gate concept originated here)

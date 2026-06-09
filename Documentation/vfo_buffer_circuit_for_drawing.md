# MC1496 VCA Buffer — Circuit Description for Schematic Drawing

Draw a schematic for the MC1496 VCA (keyed buffer) stage of a 20m CW transmitter.
Use standard schematic conventions. Label all nets and component values.

---

## Supply Rails

| Net   | Voltage |
|-------|---------|
| VDD   | +12V    |
| VEE   | −8.2V   |
| GND   | 0V      |

---

## Components and Connections

### RF Carrier Input Path
- **V_Q1S** — 14.175 MHz sine source, 0.378 V peak, referenced to GND  
  V_Q1S(+) → net _rf_in; V_Q1S(−) → GND
- **CC_CAR** — 10nF coupling capacitor  
  Left pin → _rf_in; Right pin → CAR_P
- **CCAR_N** — 100nF bypass capacitor  
  Top → GND; Bottom → CAR_N

### MC1496 (DIP-14, Gilbert cell)

Pin assignments per datasheet (MC1496 / LM1496):

| Pin # | Datasheet Function | Circuit Net / Connection |
|-------|--------------------|--------------------------|
| 1     | Signal input (+)   | SIG_P → R_SIG_P (10kΩ to GND); also receives R_INJ1 (330kΩ) from DAC_NULL_P |
| 2     | Gain adjust        | Pin 2 end of R_RE (1kΩ between pins 2 and 3)     |
| 3     | Gain adjust        | Pin 3 end of R_RE (1kΩ between pins 2 and 3)     |
| 4     | Signal input (−)   | SIG_N → AGC divider (R_SCALE1 / R_SCALE2); also receives R_INJ2 (330kΩ) from DAC_NULL_N |
| 5     | Bias               | VBIAS → R_BIAS (6.8kΩ to GND) |
| 6     | Output (+)         | OUT_P → R_LOAD_P bottom (3.9kΩ to VDD) |
| 7     | NC                 | — |
| 8     | Carrier input      | CAR_P → CC_CAR right pin (RF input from VFO) |
| 9     | NC                 | — |
| 10    | Carrier input      | CAR_N → CCAR_N (100nF to GND) |
| 11    | NC                 | — |
| 12    | Output (−)         | OUT_N → R_LOAD_N bottom (3.9kΩ to VDD) |
| 13    | NC                 | — |
| 14    | Vee                | VEE rail (−8.2V) |

**No dedicated VCC pin.** Positive supply (+12V) is applied through load resistors R_LOAD_P and R_LOAD_N at the output pins (6 and 12).

*(Pins 7, 9, 11, 13 are NC; use DIP-14 outline)*

### Output Load Resistors (connect VDD to MC1496 outputs)
- **R_LOAD_P** — 3.9kΩ  
  Top → VDD (+12V); Bottom → OUT_P (pin 6)
- **R_LOAD_N** — 3.9kΩ  
  Top → VDD (+12V); Bottom → OUT_N (pin 12)

These are **real hardware resistors**, not simulation stand-ins.  
OUT_P and OUT_N are also the differential output of the subcircuit (feed driver stage).

### Signal Port Bias / AGC Network
- **R_SIG_P** — 10kΩ  
  Top → SIG_P (pin 1); Bottom → GND  
  *(holds signal+ reference at GND)*

- **R_SCALE2** — 5.1kΩ  
  Top → AGC node (SIG_N / pin 4); Bottom → GND

- **R_SCALE1** — 100kΩ  
  Top → AGC node (SIG_N / pin 4); Bottom → V_AGC (+)

- **V_AGC** — 10V DC source (represents TL071 AGC integrator output in simulation)  
  V_AGC(+) → R_SCALE1 bottom; V_AGC(−) → GND  
  *(In hardware this node is driven by TL071 output via the R_SCALE1/R_SCALE2 divider)*

### Digital Carrier Null Network
The MC1496's internal transistors are not perfectly matched, causing residual carrier leakage at key-up even when the signal port differential is nominally zero. Two DAC-driven injection resistors provide digital null under microcontroller control, replacing the mechanical trimmer pot.

- **R_INJ1** — 330kΩ  
  From DAC_NULL_P output → SIG_P (pin 1). Joins the existing R_SIG_P / pin 1 wire at that junction.
- **R_INJ2** — 330kΩ  
  From DAC_NULL_N output → SIG_N (pin 4). Joins the existing AGC network / pin 4 wire at that junction.

**DAC coding:** DAC_NULL_P and DAC_NULL_N are complementary — firmware maintains DAC_A + DAC_B = full_scale and sweeps from center toward null. At midscale on both DACs there is no net differential injection (null starting point). Full-scale swing provides ±16 mV injection at each pin, giving ±33 mV total differential — sufficient to cover the MC1496 worst-case input offset (≤ 5 mV per datasheet). At 12-bit resolution, step size is ~8 µV; no resolution concern.

No series protection resistors (equivalent to the old R_N1/R_N2) are required; the 330 kΩ injection resistors inherently limit injection current to safe levels.

**Auto-null procedure:** At key-down, firmware performs a binary search on the complementary DAC codes to minimize carrier power as measured by the existing RF detector / AGC loop. The null setting is stored in non-volatile memory and refreshed periodically to track thermal drift.

### Bias and Gain-Set
- **R_BIAS** — 6.8kΩ  
  Top → BIAS (pin 5); Bottom → GND  
  *(Per AN531/D formula: R5 = (|VEE| − 0.75V) / I5 − 500Ω = 6.95kΩ → use 6.8kΩ std. Sets I5 ≈ 1mA)*

- **R_RE** — 1kΩ  
  Between pin 2 and pin 3 (NOT shorted to VEE)  
  *(Sets gain Av = R_LOAD / R_RE; sets linear range Vy_peak = I5 × R_RE; may change to 500Ω at bring-up)*

---

## Signal Flow (left to right)

```
V_Q1S ──── CC_CAR ──── CAR_P (pin 8)
                              │
                         MC1496
                              │
            VDD ── R_LOAD_P ── OUT_P (pin 6)  ──► to driver P2
            VDD ── R_LOAD_N ── OUT_N (pin 12) ──► to driver P4

GND ── CCAR_N ── CAR_N (pin 10)

V_AGC ── R_SCALE1 ── SIG_N (pin 4) ── R_SCALE2 ── GND
                          (AGC gain control)

GND ── R_SIG_P ── SIG_P (pin 1)
                          (signal+ reference)

         Digital carrier null network:
         DAC_NULL_P ── R_INJ1 (330kΩ) ── SIG_P (pin 1)
         DAC_NULL_N ── R_INJ2 (330kΩ) ── SIG_N (pin 4)
         (complementary DAC codes; midscale = no injection)

GND ── R_BIAS ── BIAS (pin 5)
pin 2 ── R_RE (1kΩ) ── pin 3   (between gain-adjust pins, NOT to VEE)

VEE (−8.2V) ── pin 14
```

---

## Key Layout Notes for the Drawing

1. **VDD connects ONLY to R_LOAD_P top and R_LOAD_N top** — it does NOT touch the RF carrier input wire (CC_CAR / pin 8 path).
2. The RF carrier path (V_Q1S → CC_CAR → pin 8) and the output load path (VDD → R_LOAD_P → pin 6) share NO nodes. Pin 6 is an output, pin 8 is carrier input — they are completely separate.
3. OUT_P (pin 6) and OUT_N (pin 12) are the differential balanced output feeding the driver push-pull grids.
4. SIG_N (pin 4) is the gain/level control input (AGC), not an RF signal port.
5. CCAR_N bypasses CAR_N (pin 10) to GND — keep lead short in hardware.
6. Pins 2 and 3 are both gain-adjust pins; connect R_RE (1kΩ) BETWEEN pin 2 and pin 3. Do NOT short them together or connect either end to VEE — that eliminates emitter degeneration and destroys the gain and linearity setting (per AN531/D).
7. Vee (pin 14) connects directly to the VEE rail (−8.2V). No dedicated VCC pin exists — +12V enters only through the load resistors.
8. **Digital carrier null:** R_INJ1 (330kΩ) connects DAC_NULL_P to SIG_P (pin 1); R_INJ2 (330kΩ) connects DAC_NULL_N to SIG_N (pin 4). DAC_NULL_P and DAC_NULL_N are complementary 12-bit outputs; firmware sweeps from midscale to minimize carrier leakage. The 330kΩ resistors inherently limit injection current — no separate protection resistors needed. The null point is stored in NVRAM and refreshed on each key-down.

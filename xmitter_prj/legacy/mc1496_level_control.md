# MC1496 Voltage-Controlled Level Control Circuit

## Project Overview

Design and simulate a voltage-controlled amplitude level circuit for a 14 MHz signal using through-hole components only. No surface-mount devices are permitted anywhere in the design.

## Requirements

- **Input signal**: ~0.4V amplitude, 14 MHz sine wave
- **Control voltage**: 0–4V DC from a DAC (e.g., MCP4921 or similar)
- **Output**: Amplitude-adjustable from 0–4V at 14 MHz, controlled by DAC voltage
- **All components must be through-hole (DIP/TO package)**

## Core Components

| Function | Part | Package |
|----------|------|---------|
| Voltage-controlled amplifier | MC1496 or LM1496 | DIP-14 |
| DAC buffer / control scaler | NE5534 or LM6172 | DIP-8 |
| Power supply decoupling | 10µF electrolytic + 100nF ceramic | Through-hole |

## Power Supply

The MC1496 requires dual supply rails. Use **+12V and -8V** (or ±8V if preferred).
- V+ = +12V
- V- = -8V
- All bypass capacitors: 100nF ceramic + 10µF electrolytic at each supply pin

## MC1496 Pin Configuration (DIP-14)

Per ON Semiconductor MC1496 datasheet:

```
Pin 1  - Signal Input (+)
Pin 2  - Gain Adjust  ← R_RE (1kΩ) connects between this pin and pin 3 (NOT shorted to pin 3 or VEE)
Pin 3  - Gain Adjust  ← R_RE (1kΩ) connects between this pin and pin 2 (NOT shorted to pin 2 or VEE)
Pin 4  - Signal Input (-)  ← DC control voltage input
Pin 5  - Bias  ← connect R_BIAS (6.8kΩ) to GND (not V−; see AN531/D)
Pin 6  - Output (+)  ← 3.9kΩ load to V+; RF output
Pin 7  - NC
Pin 8  - Carrier Input (+)  ← 14 MHz signal in via 10nF coupling cap
Pin 9  - NC
Pin 10 - Carrier Input (-)  ← bypass to ground via 100nF
Pin 11 - NC
Pin 12 - Output (-)  ← 3.9kΩ load to V+; RF output (differential)
Pin 13 - NC
Pin 14 - V- (Vee)  ← negative supply rail (-8.2V)
```

No dedicated V+ pin. Positive supply enters only through the output load resistors at pins 6 and 12.

> Note: Earlier versions of this document incorrectly listed pin 6 as carrier input and pin 10 as output — these were swapped. The above matches the datasheet and the KiCad symbol.

## Circuit Description

### Signal Input (Carrier Port — Pins 8/10)
- Feed 14 MHz signal into **Pin 8** through a 10nF DC-blocking capacitor
- **Pin 10** (differential carrier input, other side) bypassed to ground via 100nF capacitor
- Input impedance is approximately 1kΩ; match with a series resistor if needed

### Control Voltage Input (Signal Port — Pins 1/4)
- **Pin 4** receives the scaled DAC control voltage
- **Pin 1** sets the quiescent bias point (held near GND via R_SIG_P 10kΩ)
- A differential DC voltage between pins 1 and 4 controls the output amplitude
- At 0V differential: output is suppressed (carrier-null / zero output)
- At maximum differential: output is at maximum

### Digital Carrier Null
Due to transistor mismatch inside the MC1496, a residual carrier appears at the output even when the signal port differential is nominally zero (key-up). Two DAC-driven injection resistors provide digital null under microcontroller control, replacing a mechanical trimmer pot and enabling automatic re-nulling.

**Implementation:**
- R_INJ1: 330kΩ from DAC_NULL_P → SIG_P (pin 1); joins the existing R_SIG_P / pin 1 junction
- R_INJ2: 330kΩ from DAC_NULL_N → SIG_N (pin 4); joins the existing AGC network / pin 4 junction
- DAC_NULL_P and DAC_NULL_N are complementary 12-bit outputs: firmware maintains DAC_A + DAC_B = full_scale
- Midscale on both DACs = no differential injection (null starting point)
- Full-scale swing: ±16 mV injection at each pin, ±33 mV total differential — covers MC1496 worst-case offset (≤ 5 mV)
- 12-bit resolution: ~8 µV/step — no resolution concern
- No series protection resistors needed; 330kΩ inherently limits current
- Null found by firmware binary search at key-down; stored in NVRAM, refreshed periodically

### DAC Scaling (NE5534 or LM6172)
The DAC produces 0–4V. The MC1496 control port needs a differential voltage in the range of approximately 0–500mV for linear control (it saturates beyond ~1V differential).

Scale the DAC output using a resistor divider or inverting op-amp stage:

```
DAC output (0–4V) → resistor divider (/8) → 0–500mV → MC1496 Pin 4
```

Or use the op-amp in an inverting attenuator configuration:
- Rin = 80kΩ, Rf = 10kΩ → gain = 0.125
- Output: 0–500mV from 0–4V DAC input

Pin 1 bias: set to mid-supply reference (~0V for dual supply) via voltage divider.

### Output (Pins 6/12)
- The MC1496 produces a differential output on pins 6 and 12
- Load resistors: 3.9kΩ from each output pin to V+
- For single-ended output: take from Pin 6 through a blocking capacitor
- For differential output (this design): pins 6 and 12 feed driver push-pull grids directly

### Output Amplitude Scaling
The MC1496 output swing with 3.9kΩ loads on ±8–12V supplies can reach several volts peak-to-peak. Verify output level against requirement (0–4V) and add a resistor attenuator or op-amp buffer stage after the output blocking capacitor if needed.

## Component Values Summary

| Component | Value | Purpose |
|-----------|-------|---------|
| R_LOAD_P, R_LOAD_N | 3.9kΩ ea | MC1496 output load (pins 6, 12 to V+) |
| R_RE | 1kΩ | Gain-set resistor between pins 2 and 3 (NOT shorted to VEE) |
| R_BIAS | 6.8kΩ | Bias pin 5 to GND; sets I5 ≈ 1mA (per AN531/D formula) |
| R_SIG_P | 10kΩ | Pin 1 reference to GND |
| R_SCALE1 | 100kΩ | AGC divider upper leg (DAC/TL071 to pin 4) |
| R_SCALE2 | 5.1kΩ | AGC divider lower leg (pin 4 to GND) |
| R_INJ1 | 330kΩ | Digital null injection: DAC_NULL_P → pin 1 (SIG_P) |
| R_INJ2 | 330kΩ | Digital null injection: DAC_NULL_N → pin 4 (SIG_N) |
| CC_CAR | 10nF | Carrier input coupling (to pin 8) |
| CCAR_N | 100nF | Carrier input bypass (pin 10 to GND) |
| C_supply (×4) | 100nF + 10µF | Power supply decoupling |

## Deliverables Requested

1. **Schematic** (KiCad .kicad_sch or SPICE netlist) of the complete circuit
2. **SPICE simulation** (.asc LTspice or ngspice netlist) showing:
   - Output amplitude vs. control voltage sweep (0–4V DAC, 14 MHz input)
   - Output waveform at min, mid, and max control voltage
   - Frequency response at fixed control voltage
3. **Bill of materials** (CSV) with Mouser/Digikey part numbers for all through-hole components
4. **Notes** on any nonlinearity observed in the control law and suggested correction if needed

## Constraints Reminder

- **No surface-mount components** — all parts must be through-hole (DIP, TO-92, TO-220, axial, radial)
- Target frequency: 14 MHz (20-meter amateur band)
- Single-ended 50Ω RF environment preferred at input and output if practical
- DAC control voltage: 0–4V, high impedance source (buffer before scaling)

## References

- ON Semiconductor MC1496 Datasheet: https://www.onsemi.com/pdf/datasheet/mc1496-d.pdf
- ARRL Handbook, chapter on mixers and modulators (MC1496 application circuits)
- Hayward, Campbell & Larkin, *Experimental Methods in RF Design*, Chapter 5

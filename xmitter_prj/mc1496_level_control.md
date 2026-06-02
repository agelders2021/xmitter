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

```
Pin 1  - Signal Input (+)
Pin 2  - Signal Input Bias (connect 1kΩ to V-)
Pin 3  - (NC or bias)
Pin 4  - Signal Input (-)  ← DC control voltage input
Pin 5  - Gain control / bias
Pin 6  - Carrier Input (+) ← 14 MHz signal in
Pin 7  - V- supply
Pin 8  - Carrier Input (-) ← bypass to ground via 0.1µF
Pin 9  - (NC)
Pin 10 - Output (+)
Pin 11 - (NC)
Pin 12 - Output (-)
Pin 13 - V+ supply
Pin 14 - Gain set resistor (connect 1kΩ to V-)
```

> Note: Verify pin assignments against the ON Semiconductor MC1496 datasheet before layout.
> Datasheet: https://www.onsemi.com/pdf/datasheet/mc1496-d.pdf

## Circuit Description

### Signal Input (Carrier Port — Pins 6/8)
- Feed 14 MHz signal into **Pin 6** through a 0.1µF DC-blocking capacitor
- **Pin 8** (differential carrier input) bypassed to ground via 0.1µF capacitor
- Input impedance is approximately 1kΩ; match with a series resistor if needed

### Control Voltage Input (Signal Port — Pins 1/4)
- **Pin 4** receives the scaled DAC control voltage
- **Pin 1** sets the quiescent bias point
- A differential DC voltage between pins 1 and 4 controls the output amplitude
- At 0V differential: output is suppressed (carrier-null / zero output)
- At maximum differential: output is at maximum

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

### Output (Pins 10/12)
- The MC1496 produces a differential output on pins 10 and 12
- Load resistors: 3.9kΩ from each output pin to V+
- For single-ended output: take from Pin 10 through a 0.1µF blocking capacitor
- For differential output: use a transformer balun (e.g., FT37-43 wound as 1:1 balun)

### Output Amplitude Scaling
The MC1496 output swing with 3.9kΩ loads on ±8–12V supplies can reach several volts peak-to-peak. Verify output level against requirement (0–4V) and add a resistor attenuator or op-amp buffer stage after the output blocking capacitor if needed.

## Component Values Summary

| Component | Value | Purpose |
|-----------|-------|---------|
| R_load (×2) | 3.9kΩ | MC1496 output load (pins 10, 12 to V+) |
| R_gain | 1kΩ | Gain-set resistor (pin 14 to V-) |
| R_bias | 1kΩ | Signal port bias (pin 2 to V-) |
| R_in (DAC scaler) | 80kΩ | Op-amp attenuator input resistor |
| R_f (DAC scaler) | 10kΩ | Op-amp attenuator feedback resistor |
| C_block (×3) | 0.1µF | DC blocking / RF bypass |
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

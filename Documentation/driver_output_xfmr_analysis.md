# Driver Output Transformer — Design Analysis

**Circuit:** Push-pull 6CL6 driver → 4-winding output transformer → push-pull 6146B PA  
**Operating frequency:** 14.2 MHz  
**Date:** 2026-05-24

---

## Current Design State

| Parameter | Value |
|---|---|
| INPUT_L (each primary half) | 6.3 µH |
| OUTPUT_L (each secondary half) | 1.5 µH |
| C_IN (primary plate to ground) | 6.0 pF |
| Coupling (all pairs) | K = 0.95 |
| Turns ratio (primary:secondary) | 2:1 |

### AC Simulation Results (1 V input, 14.2 MHz)

| Probe | Location | Peak | Value @ 14.2 MHz |
|---|---|---|---|
| Pr3 | Driver xfmr primary (differential) | 86.1 V @ 14.62 MHz | 83.7 V |
| Pr4 | Driver xfmr secondary / PA grid drive | 41.5 V @ 14.62 MHz | 40.3 V |
| Pr2 | PA plate / LPF input | 140.4 V @ 14.55 MHz | 127.3 V |
| Pr1 | LPF output / 500 Ω load | 123.2 V @ 14.45 MHz | 118.3 V |

---

## Toroid Buildability

### Core and Turn Counts

Using a **T68-6** iron powder core (AL = 47 nH/t², type 6 yellow/clear, good to ~40 MHz):

| Winding | Inductance | Turns |
|---|---|---|
| Primary half (×2) | 6.3 µH | 12 turns |
| Secondary half (×2) | 1.5 µH | 6 turns |

- Wind primary **bifilar** (12 turns, two wires): gives k ≈ 0.97–0.98 between the two halves — the K=0.95 simulation value is conservative.
- Wind secondary **bifilar** (6 turns) over or interleaved with primary.
- Total: 36 turns on T68; feasible with #28–30 AWG wire.
- Core saturation and loss are not concerns at driver power levels (~100–200 mW).

### The 6 pF Capacitor Problem

6 pF is the critical buildability concern. Typical stray capacitances at the 6CL6 plate node:

| Source | Capacitance |
|---|---|
| Tube socket strays | 2–4 pF |
| Wiring/lead dress | 1–2 pF per inch |
| Transformer interwinding | 1–3 pF |

Any combination of these can easily equal or exceed 6 pF, shifting the resonant peak unpredictably. A 2.5 pF trimmer helps but may not cover the full range of uncertainty.

**The 8 pF design (committed baseline) is more buildable** — parasitics are a smaller fraction of the total capacitance and standard 8 pF NPO/C0G fixed caps are available.

### Coupling Coefficient in Practice

K = 0.95 is realistic for a well-wound toroidal transformer:
- Bifilar primary: k ≈ 0.97–0.99 between the two primary halves
- Primary-to-secondary: k ≈ 0.90–0.96 depending on winding interleave
- Uniform distribution around the toroid improves all coupling coefficients

---

## 6CL6 Driver Linearity

### DC Operating Point

| Component | Value | Effect |
|---|---|---|
| B+ supply | 150 V | Plate supply |
| Grid bias resistor (R4) | 47 kΩ to ground | Self-bias via cathode |
| Cathode resistor (R1/R8) | 100 Ω | ~1.0–1.2 V at ~10–12 mA |
| Quiescent grid bias | ≈ −1.0 to −1.2 V | Class A operating point |

### Linearity Limit

Grid conduction begins just above Vg = 0 V. With a cathode bias of ~1.0–1.2 V, the maximum linear positive grid swing is **~1.0–1.2 V peak**.

- **1 V input (current):** Right at the linear limit. Positive peaks approach grid conduction.
- **> 1.5 V input:** Grid current flows on positive peaks → asymmetric clipping → odd-harmonic distortion in push-pull.
- **For CW:** Mild class AB is acceptable; the LPF suppresses harmonics. Waveform shape at the PA grid is less critical than for SSB.

### Options to Increase Headroom

1. **Larger cathode resistor (150–180 Ω):** Sets quiescent bias more negative (−1.5 to −2 V), allows ~1.5–2 V peak input before grid conduction. Reduces plate current slightly (minor gain reduction).
2. **Fixed negative grid bias supply:** Cleaner; separates bias from signal path. Allows precise control of operating point.
3. **Accept class AB:** For a CW transmitter with a good LPF, the driver running mild class AB is a common and practical choice.

---

## Summary Recommendations

1. **Capacitor:** Stay at 8 pF or use a trimmer (e.g., 2–20 pF range) rather than pushing to 6 pF. Layout discipline (short leads, minimal socket strays) is essential either way.
2. **Toroid:** T68-6 with 12+12 / 6+6 bifilar winding is straightforward to build. K=0.95 is achievable without special techniques.
3. **Drive level:** 1 V input is the practical maximum for clean class A operation. For CW, up to ~1.5 V is usable with mild AB distortion that the LPF will handle.
4. **If more drive voltage is needed:** Increase cathode resistor to ~150 Ω rather than increasing input level.

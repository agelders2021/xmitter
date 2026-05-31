# 20m CW Transmitter — Design Reference

## Overview

Push-pull 6146B beam tetrode PA for 20m CW (14.2 MHz), simulated in QUCS-S/ngspice.
Git repo: `agelders2021/xmitter`. Workspace linked via Windows junction:
`xmitter_prj/` → `C:\Users\AlAnd\QucsWorkspace\xmitter_prj\`

Simulator: ngspice backend in QUCS-S 26.1.1. Tube models from a modified
TubesExtended library (files in `qucs-s-modified-files/`).

---

## File Structure

```
xmitter/
├── xmitter_prj/
│   ├── xmitter.sch                  Top-level simulation schematic
│   ├── PA Subcircuit.sch            Push-pull PA subcircuit
│   └── tank-lpf Subcircuit.sch     5-pole balanced LPF subcircuit
├── tank-lpf.sch                     Standalone tank+LPF test bench
├── PA detail.sch                    Standalone PA test bench
├── ATU.sch                          ATU (work in progress)
├── 5th-order-chebyshev.sch         LPF prototype
└── qucs-s-modified-files/
    ├── Program Files-.../TubesExtended.lib
    ├── Program Files-.../6146_fixed.lib
    └── Program Files-.../6CL6.lib
```

Generated files (`.ngspice`, `.cir`) are excluded from git via `.gitignore`.

---

## Top-Level: xmitter.sch

```
V1 (40V / 14.2MHz) → SUB1 (PA) → SUB2 (tank-lpf) → R1 (300Ω load)
```

| Component | Value | Purpose |
|-----------|-------|---------|
| V1 | 40V AC, 14.2 MHz | Drive source |
| SUB1 | PA Subcircuit | Push-pull 6146B PA |
| SUB2 | tank-lpf Subcircuit | 5-pole balanced LPF |
| R1 | 300 Ω | Load |
| Pr1 | VProbe | LPF output voltage |
| Pr2 | VProbe | PA input voltage |

**Simulations:**
- `.AC`: 10–15 MHz, 200 points (linear)
- `.TR`: 0–100 µs, 10000 steps (effective 1 ns/step), Trapezoidal

**Initial conditions (required for convergence):**
```spice
.IC v(xsub1._net0)=500   ; tube 1 plate
.IC v(xsub1._net7)=500   ; tube 2 plate
.IC v(xsub1._net6)=-52   ; tube 1 grid bias
.IC v(xsub1._net13)=-52  ; tube 2 grid bias
```
The `.uic` flag is used in transient — DC operating point is skipped.

---

## PA Subcircuit (PA Subcircuit.sch)

### Ports
| Port | # | Signal |
|------|---|--------|
| IN_HOT | 1 | Drive input + |
| IN_COLD | 2 | Drive input − |
| OUT_COLD | 3 | RF output − |
| OUT_HOT | 4 | RF output + |

### Power Supplies
| Supply | Value | Purpose |
|--------|-------|---------|
| V5 | 500V | Plate (B+) |
| V1, V3 | 52V | Grid bias (via R4/R8 divider → −52V at grid) |
| V2, V4 | 225V | Screen grid |

### Tube Biasing
| Component | Value | Purpose |
|-----------|-------|---------|
| R4, R8 | 22 kΩ | Grid leak resistors |
| R1, R5 | 10 Ω | Cathode resistors |
| R3, R7 | 1 kΩ | Grid stopper resistors |
| R2, R6 | 100 Ω | Screen feed resistors |
| C3, C4 | 1000 pF | Screen bypass |
| C8, C10 | 0.01 µF | Screen bypass (low-freq) |
| C9, C11 | 100 pF | Screen bypass (HF) |

### Drive Transformer (center-tapped primary)
| Component | Value | Coupling |
|-----------|-------|---------|
| L1, L2 | 6.3 µH each | Primary halves (K1: L1-L2, K=0.9) |
| L3 | 6.3 µH | Secondary (K2: L1-L3, K=0.9; K3: L2-L3, K=0.9) |
| R16 | 0.5 Ω | L3 winding resistance (prevents singular matrix) |

L3 connects directly between IN_HOT and IN_COLD ports.
The center tap of L1/L2 drives each tube's grid through R3/R7.

### Plate Output Transformer
| Component | Value | Coupling |
|-----------|-------|---------|
| L4, L5 | 1.71 µH each | Plate coils (K4: L4-L5, K=0.75) |
| L6 | 0.43 µH | Output winding (K5: L4-L6, K=0.57; K6: L5-L6, K=0.57) |

L6 output appears at OUT_HOT/OUT_COLD ports. DC-isolated from plate supply.

### Parasitic Suppression
| Component | Value | Purpose |
|-----------|-------|---------|
| C6, C7 | 0.24 pF | Neutralization (plate-to-grid) |
| C12, C13 | 30 pF | Anti-parasitic shunt |
| R14, R15 | 47 Ω | Parasitic suppressor resistors |
| L10, L11 | 1 µH | Parasitic suppressor chokes |

### Measurement Probes (in subcircuit)
| Probe | Measures |
|-------|---------|
| Pr1 | Differential output voltage |
| Pr3 | Cathode current (IProbe) |
| Pr6 | Plate-to-plate voltage |
| Pr7 | Cathode voltage |
| Pr8 | Grid voltage |
| Pr9 | Drive input signal |

---

## Tank-LPF Subcircuit (tank-lpf Subcircuit.sch)

5-pole balanced (differential) Chebyshev low-pass filter.
Equivalent to a single-ended 5-pole LPF with 3 series inductors and 2 shunt capacitors.

### Ports
| Port | # | Signal |
|------|---|--------|
| IN_HOT | 1 | Input + (from PA OUT_HOT) |
| IN_COLD | 2 | Input − (from PA OUT_COLD) |
| OUT_HOT | 3 | Output + |
| OUT_COLD | 4 | Output − |

### Filter Components

**Series inductors (one per leg):**
| Components | Value | Position |
|-----------|-------|---------|
| L1, L2 | 2.72 µH | Input |
| L3, L4 | 4.04 µH | Middle |
| L5, L6 | 2.72 µH | Output |

**Shunt capacitors (differential, between legs):**
| Component | Value | Position |
|-----------|-------|---------|
| C3 | 43 pF | After L1/L2 |
| C4 | 43 pF | After L3/L4 |

Note: C1/C2 (390 pF series input caps) were removed — analysis confirmed
they had no measurable effect on filter performance.

---

## Standalone Tank-LPF Test Bench (tank-lpf.sch)

Models the complete output network including PA source impedance.

| Component | Value | Purpose |
|-----------|-------|---------|
| V1 | 1V AC, 14 MHz | Signal source |
| R4 | 6600 Ω | PA equivalent output impedance |
| L9 | 6 µH | Plate coil model |
| C7 | 20 pF | Plate tank capacitor (resonates with L9 at ~14.5 MHz) |
| L10 | 0.43 µH | Output coupling coil |
| K1 | L9-L10, K=0.8 | Tank-to-filter coupling |
| R1 | 300 Ω | Load |

The LPF section (L1–L6, C3, C4) is identical to the subcircuit.
AC sweep: 10–80 MHz, 200 points.

---

## Simulation Results

### Transient (xmitter.sch)
- Drive: 40V peak at 14.2 MHz
- Output power: ~16 W into 300 Ω
- Simulation time: 100 µs (captures steady state after ~5 µs)

### AC Harmonic Analysis (tank-lpf.sch)
Measured at LPF output (Pr1), relative to fundamental:

| Harmonic | Frequency | Level |
|----------|-----------|-------|
| Fundamental | 14.2 MHz | 0 dBc (reference) |
| 2nd | 28.4 MHz | −60 dBc |
| 3rd | 42.6 MHz | −84 dBc |
| 5th | 70.5 MHz | −110 dBc |

FCC Part 97 requires −43 dBc for harmonics below 30 MHz. Passes by large margin.
Note: even harmonics (2nd, 4th) are suppressed by push-pull topology, not the LPF.

---

## Known Limitations

**Output power lower than real-world 6146B (typical 60–100W):**
- Grid barely driven past cutoff: bias = −52V, drive peak = +40V → grid peak = −12V
- Plate-to-output coupling loose: K5/K6 = 0.57
- Increasing drive voltage or reducing grid bias would increase output power

**Balanced output requires balun for coax-fed antennas:**
- The PA and LPF are balanced/differential
- A 1:1 current balun is needed at the LPF output before connecting to coaxial cable

**No explicit plate-to-plate tank capacitor in xmitter.sch:**
- The tank circuit (L9/C7) exists only in the standalone tank-lpf.sch test bench
- The full simulation uses L6 (0.43 µH PA output winding) directly driving the LPF

**Singular matrix warning (benign):**
- Cause: L3 (drive transformer secondary) creates DC short between V1 terminals
- Benign because `.uic` skips DC operating point in transient
- Fixed by R16 (0.5 Ω winding resistance on L3)

---

## Design Areas for Future Work

- Increase drive or reduce bias to get closer to rated output power
- Add explicit plate-to-plate tuning capacitor to xmitter.sch
- Design output balun for coax interface
- ATU design (ATU.sch started but incomplete)
- VFO/buffer stage
- Key shaper / envelope control
- T/R relay and sequencing
- Power supply schematic

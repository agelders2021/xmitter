# 20m CW Transmitter — Output Network Design
## 14.2 MHz, Balanced 500 Ω, PA → LPF → ATU → 300 Ω Twin-Line → Folded Dipole

---

## 1. Signal Chain Overview

```
PA (push-pull 6146B)
  |  500 Ω balanced differential output
  v
Low-Pass Filter  (7-element Chebyshev, 500 Ω, fc = 18 MHz)
  |  harmonic suppression; passes fundamental, kills 2nd/3rd/4th
  v
ATU  (balanced pi-network, Rs = 500 Ω input)
  |  matches 163–566 Ω resistive + reactive loads
  v
300 Ω twin-line
  v
Folded dipole antenna  (~300 Ω balanced, varies ± ~200 Ω reactive off resonance)
```

All stages are **balanced / differential**. There is no RF ground reference in the signal path.  
The PA plate-to-plate load (tank circuit) is designed for **500 Ω differential**.

---

## 2. Coupling Constant — ATU Series Inductors

The ATU uses two series inductors in a balanced pi-network. If they are wound on a
common core (bifilar) with high coupling constant k, the effective differential
inductance is drastically reduced:

```
XL_diff = 2 × ω × L × (1 - k)
```

| k    | Description                  | XL_diff (each L = 1.60 µH) |
|------|------------------------------|----------------------------|
| 0.99 | Tightly coupled, same core   | 2.9 Ω  — **unusable**      |
| 0.90 | Loosely coupled              | 28.5 Ω — inadequate        |
| 0.00 | Separate, non-interleaved    | 285.5 Ω — **required**     |

**The two ATU series inductors must be wound and mounted so that k ≈ 0.**  
Wind them at 90° to each other, or place them at opposite ends of the chassis.

---

## 3. ATU — Balanced Pi-Network

### Design Parameters

| Parameter           | Value                          |
|---------------------|--------------------------------|
| Frequency           | 14.2 MHz                       |
| Rs (input)          | 500 Ω balanced differential    |
| Series inductors    | 1.60 µH each, k = 0            |
| XL each (single)    | 142.8 Ω at 14.2 MHz            |
| XL_diff (both, k=0) | 285.5 Ω                        |
| C1/C2 (input, each) | 8 – 100 pF variable            |
| C3/C4 (output, each)| 8 – 140 pF variable            |
| RL resistive range  | 163 – 566 Ω (3.5× ratio), continuous |
| Max cap. load       | ≈ −286 Ω reactance (inductors resonate it) |
| Max ind. load       | ≈ +160 Ω reactance (output caps cancel it) |

### Why L = 1.60 µH (not 1.40 or 1.42 µH)

Two separate gap conditions must both be satisfied:

**Gap condition 1 — Q2 sign (L-too-small):**  
When XL_diff < Rs/2 = 250 Ω, Q2 goes negative mid-range and no solution exists
for a continuous band of RL values. Minimum L: XL_diff ≥ 250 Ω → L_each ≥ 1.40 µH.

**Gap condition 2 — output capacitor range (L-still-too-small):**  
Even with Q2 > 0 everywhere, the Q2 minimum (Q2_min) occurs at Q1 ≈ Rs/(2×XL_diff).
At this point RL ≈ Rs/2 and a very small Q2 requires an extremely large output cap
reactance. With L_each = 1.42 µH: Q2_min = 0.014, requiring C3 = 1.2 pF — far below
the 8 pF minimum. This creates a **dead zone from 185–419 Ω** (the 300 Ω folded
dipole sits squarely in the middle of this gap).

With L_each = 1.60 µH: Q2_min = 0.133, requiring C3 = 10.4 pF — within the 8–140 pF
range. Coverage is confirmed **continuous from 163–566 Ω**.

### ATU Tuning Guide (purely resistive loads)

Tuning procedure: set C1/C2 for minimum reflected power (dip in reflected), then
adjust C3/C4 for maximum forward power (peak in forward). Iterate once or twice.

| RL (Ω) | C1/C2 (pF ea.) | C3/C4 (pF ea.) | Rm (Ω) |  Q1   |  Q2   |
|--------|----------------|----------------|---------|-------|-------|
|    165 |      83.4      |      93.4      |   112   | 1.861 | 0.688 |
|    175 |      66.4      |      43.8      |   157   | 1.480 | 0.342 |
|    200 |      99.9      |     131.9      |    84   | 2.227 | 1.177 |
|    225 |      50.9      |      17.1      |   219   | 1.135 | 0.172 |
|    250 |      45.8      |      13.0      |   245   | 1.021 | 0.145 |
|    275 |      41.4      |      11.0      |   270   | 0.923 | 0.134 |
|    300 |      37.4      |      10.0      |   295   | 0.835 | 0.134 |
|    325 |      33.8      |       9.8      |   319   | 0.755 | 0.142 |
|    350 |      30.5      |       9.9      |   342   | 0.680 | 0.155 |
|    400 |      24.5      |      10.9      |   385   | 0.546 | 0.195 |
|    450 |      19.0      |      12.4      |   424   | 0.425 | 0.249 |
|    500 |      14.1      |      14.1      |   455   | 0.314 | 0.314 |
|    565 |       8.1      |      16.2      |   484   | 0.181 | 0.409 |

C1/C2 and C3/C4 values are for each individual section (each air-variable gang).
For the balanced topology: C1_top rail = C1_bottom rail = table value.

---

## 4. LPF — Balanced 7-Element Chebyshev

### Design Parameters

| Parameter      | Value                              |
|----------------|------------------------------------|
| Topology       | 7-element Chebyshev low-pass       |
| Ripple         | 0.5 dB                             |
| Zo             | 500 Ω (source and load)            |
| fc (cutoff)    | 18 MHz                             |
| Passband IL    | < 0.01 dB at 14.2 MHz              |

fc = 18 MHz is chosen so that the 2nd harmonic (28.4 MHz) receives > 50 dB
attenuation, exceeding the FCC Part 97 40 dB requirement by a comfortable margin.
(fc = 22 MHz would give only 30 dB at 28.4 MHz — insufficient.)

The push-pull balanced PA provides natural even-harmonic cancellation of roughly
20 dB, so the combined suppression at the antenna is the LPF value plus ~20 dB.

### Harmonic Attenuation

| Frequency            | Attenuation  | Meets FCC 40 dB? |
|----------------------|-------------|------------------|
| 14.2 MHz (fund.)     | 0.003 dB    | passband         |
| 18.0 MHz (cutoff)    | 0.5 dB      | —                |
| 28.4 MHz (2nd harm.) | 47.4 dB     | Yes (+7 dB)      |
| 42.6 MHz (3rd harm.) | 76.5 dB     | Yes              |
| 56.8 MHz (4th harm.) | 95.3 dB     | Yes              |

### Single-Ended Prototype → Scaled Values

The ladder topology is: **C – L – C – L – C – L – C** (shunt-cap first, 7 elements).

Prototype g-values (0.5 dB Chebyshev, n = 7, equal terminations):  
g1 = 1.7372, g2 = 1.2583, g3 = 2.6381, g4 = 1.3444, g5 = 2.6381, g6 = 1.2583, g7 = 1.7372

| Element | g value | Single-ended value (500 Ω, 18 MHz) |
|---------|---------|-------------------------------------|
| C1      | 1.7372  | 30.72 pF                            |
| L1      | 1.2583  | 5563 nH  (5.563 µH)                 |
| C2      | 2.6381  | 46.65 pF                            |
| L2      | 1.3444  | 5944 nH  (5.944 µH)                 |
| C3      | 2.6381  | 46.65 pF                            |
| L3      | 1.2583  | 5563 nH  (5.563 µH)                 |
| C4      | 1.7372  | 30.72 pF                            |

### Balanced Ladder Component Values

For balanced (differential) operation:
- **Series inductors** → split into two halves, one per rail (each = L/2)
- **Shunt capacitors** → remain the full value, connected rail-to-rail (differential)

| Designator    | Type | Value              | Notes                           |
|---------------|------|--------------------|---------------------------------|
| C1            | cap  | 30.72 pF           | rail-to-rail (NP0/C0G)          |
| L1a, L1b      | ind  | 2782 nH each       | 2.782 µH; one per rail          |
| C2            | cap  | 46.65 pF           | rail-to-rail                    |
| L2a, L2b      | ind  | 2972 nH each       | 2.972 µH; one per rail          |
| C3            | cap  | 46.65 pF           | rail-to-rail                    |
| L3a, L3b      | ind  | 2782 nH each       | 2.782 µH; one per rail          |
| C4            | cap  | 30.72 pF           | rail-to-rail                    |

Capacitor tolerance: ±1% or better (NP0/C0G). Voltage rating: 500 V minimum.  
Inductor Q: target > 100 at 14.2 MHz (silver-mica or air-core; avoid iron-powder above 30 MHz).

---

## 5. Master Component Table

### ATU Components

| Ref  | Type     | Value / Range   | Notes                                         |
|------|----------|-----------------|-----------------------------------------------|
| C1   | variable | 8 – 100 pF      | input shunt, hot rail; air variable           |
| C2   | variable | 8 – 100 pF      | input shunt, cold rail; ganged with C1        |
| C3   | variable | 8 – 140 pF      | output shunt, hot rail; air variable          |
| C4   | variable | 8 – 140 pF      | output shunt, cold rail; ganged with C3       |
| L1   | fixed    | 1.60 µH         | series, hot rail; k ≈ 0 with respect to L2   |
| L2   | fixed    | 1.60 µH         | series, cold rail; wound/mounted separately   |

### LPF Components

| Ref       | Type | Value    | Tolerance | Voltage |
|-----------|------|----------|-----------|---------|
| C1 (LPF)  | cap  | 30.72 pF | ±1%       | 500 V   |
| L1a (LPF) | ind  | 2.782 µH | ±2%       | —       |
| L1b (LPF) | ind  | 2.782 µH | ±2%       | —       |
| C2 (LPF)  | cap  | 46.65 pF | ±1%       | 500 V   |
| L2a (LPF) | ind  | 2.972 µH | ±2%       | —       |
| L2b (LPF) | ind  | 2.972 µH | ±2%       | —       |
| C3 (LPF)  | cap  | 46.65 pF | ±1%       | 500 V   |
| L3a (LPF) | ind  | 2.782 µH | ±2%       | —       |
| L3b (LPF) | ind  | 2.782 µH | ±2%       | —       |
| C4 (LPF)  | cap  | 30.72 pF | ±1%       | 500 V   |

---

## 6. Analysis Scripts

| Script                  | Purpose                                          |
|-------------------------|--------------------------------------------------|
| `_atu_lpf_values.py`    | Computes ATU tuning guide + LPF scaled values    |
| `_atu_gap_check.py`     | Diagnoses cap-constraint gap; finds minimum L    |
| `_atu_correct.py`       | Gap condition using Q2<0 discriminant (partial)  |
| `_atu_rs_sweep.py`      | Sweeps Rs and L for best coverage                |
| `_atu_sweep.py`         | Rs=300 Ω sweep of L vs. matching range           |
| `_atu_final.py`         | Rs=500, L=1.1 µH (obsolete — gap present)        |

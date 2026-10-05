# Band LPF Component Values — 20 / 17 / 15 / 10 m

## Design parameters

- **Topology:** 7-element Chebyshev lowpass filter, CLCLCLC arrangement (shunt C at input and output).  3 series inductors (`L1 = L3`, `L2` middle) and 4 shunt capacitors (`C1 = C4`, `C2 = C3`), filter symmetric.
- **Ripple:** 0.1 dB passband ripple (W3NQN QRP-standard).
- **Source / load impedance:** 50 Ω.
- **Cutoff anchoring:** `fc` chosen so that `C1` lands on a readily-sourced NP0 ceramic value.  All other components computed from that choice.

### Prototype coefficients (7-pole Chebyshev, 0.1 dB ripple)

| Element | g value |
|---------|:-------:|
| g1 (C1 shunt) | 1.1811 |
| g2 (L1 series) | 1.4228 |
| g3 (C2 shunt) | 2.0966 |
| g4 (L2 series middle) | 1.5733 |

Symmetric: g5 = g3, g6 = g2, g7 = g1.  Scaling: `C = g / (ωc·R)`, `L = g·R / ωc`.

### Core A_L reference

- **T50-6:** A_L = **4.0 nH/N²** (equivalent to 40 µH per 100 turns²).  OD 12.70 mm, ID 7.70 mm, H 4.83 mm.
- **T68-6:** A_L = **4.7 nH/N²** (equivalent to 47 µH per 100 turns²).  OD 17.53 mm, ID 9.40 mm, H 4.83 mm.

**Unit note:** Amidon / kitsandparts.com catalogs usually list A_L in **µH per 100 turns²** (a convenient but non-SI unit).  To use in the formula `L (nH) = N² × A_L`, divide the catalog number by 10.  The 4.0 and 4.7 values above are in `nH/N²`.

Both tolerance ±10 %; final value must be dip-measured after winding and trimmed by spread/bunch of turns.

### Capacitor sourcing note

NP0 ceramic recommended for all shunt caps — low temperature coefficient, low loss, 50 V / 100 V available.  Values flagged as "non-E12" below need either a direct order for that specific value or a two-cap parallel combination:

- 110 pF = 100 pF ∥ 10 pF
- 200 pF = 100 pF ∥ 100 pF, or 180 pF (−10 %), or 220 pF (+10 %)

---

## 20 m band

**Cutoff:** 17.09 MHz (highest op freq 14.35 MHz)

### Capacitors

| Component | Target | Standard part | Error |
|-----------|:------:|:-------------:|:-----:|
| C1 = C4   | 220 pF | 220 pF (E12)  | 0 %   |
| C2 = C3   | 393 pF | 390 pF (E12)  | −1 %  |

### T50-6 inductors (A_L = 4.0 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 662 nH   | 13 T  | 676 nH   | +2 %  |
| L2        | 733 nH   | 14 T  | 784 nH   | +7 %  |

### T68-6 inductors (A_L = 4.7 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 662 nH   | 12 T  | 677 nH   | +2 %  |
| L2        | 733 nH   | 13 T  | 794 nH   | +8 %  |

---

## 17 m band

**Cutoff:** 20.90 MHz (highest op freq 18.17 MHz)

### Capacitors

| Component | Target | Standard part | Error |
|-----------|:------:|:-------------:|:-----:|
| C1 = C4   | 180 pF | 180 pF (E12)  | 0 %   |
| C2 = C3   | 319 pF | 330 pF (E12)  | +3 %  |

### T50-6 inductors (A_L = 4.0 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 542 nH   | 12 T  | 576 nH   | +6 %  |
| L2        | 599 nH   | 12 T  | 576 nH   | −4 %  |

### T68-6 inductors (A_L = 4.7 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 542 nH   | 11 T  | 569 nH   | +5 %  |
| L2        | 599 nH   | 11 T  | 569 nH   | −5 %  |

---

## 15 m band

**Cutoff:** 25.07 MHz (highest op freq 21.45 MHz)

### Capacitors

| Component | Target | Standard part | Error |
|-----------|:------:|:-------------:|:-----:|
| C1 = C4   | 150 pF | 150 pF (E12)  | 0 %   |
| C2 = C3   | 266 pF | 270 pF (E12)  | +1.5 %|

### T50-6 inductors (A_L = 4.0 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 452 nH   | 11 T  | 484 nH   | +7 %  |
| L2        | 499 nH   | 11 T  | 484 nH   | −3 %  |

### T68-6 inductors (A_L = 4.7 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 452 nH   | 10 T  | 470 nH   | +4 %  |
| L2        | 499 nH   | 10 T  | 470 nH   | −6 %  |

---

## 10 m band

**Cutoff:** 34.19 MHz (highest op freq 29.70 MHz)

### Capacitors

| Component | Target | Standard part | Error |
|-----------|:------:|:-------------:|:-----:|
| C1 = C4   | 111 pF | **110 pF** (non-E12 — direct order or 100 ∥ 10) | −1 % |
| C2 = C3   | 195 pF | **200 pF** (non-E12 — direct order or 100 ∥ 100) | +3 % |

### T50-6 inductors (A_L = 4.0 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 331 nH   | 9 T   | 324 nH   | −2 %  |
| L2        | 366 nH   | 10 T  | 400 nH   | +9 %  |

### T68-6 inductors (A_L = 4.7 nH/N²)

| Component | Target L | Turns | Actual L | Error |
|-----------|:--------:|:-----:|:--------:|:-----:|
| L1 = L3   | 331 nH   | 8 T   | 301 nH   | −9 %  |
| L2        | 366 nH   | 9 T   | 381 nH   | +4 %  |

---

## Reading the inductor tables

- **Target L** is the ideal Chebyshev prototype value scaled for the chosen fc.
- **Turns** is `round(√(L_target / A_L))` — the integer turn count nearest the ideal, with `A_L` in nH/N² (4.0 for T50-6, 4.7 for T68-6).
- **Actual L** = `N² × A_L` nominal, with that integer turn count.
- **Error** is the % offset of actual-vs-target.  Spread or bunch the winding around the core to tune:
  - Positive error (actual > target) → spread turns around the full circumference to shed inductance
  - Negative error (actual < target) → bunch turns tightly to add inductance
  - Range of adjustment: comfortably ±20 %, with care up to ±30 %
- A_L nominal has ±10 % tolerance core-to-core; always **dip-measure after winding** and trim.

## Which core to use

Both T50-6 and T68-6 work for all four bands.  Trade-offs:

- **T50-6** — needs 1-2 more turns than T68-6 for the same inductance.  Smaller footprint (12.7 mm OD vs 17.5 mm OD).
- **T68-6** — fewer turns needed, easier hand-wind, larger window for the wire.  Bigger footprint.  Matches the user's existing stock and prior build pattern.

**For a 4-band bank with visual consistency, pick one core type and stick with it.**  My mild preference remains **T68-6** because it needs fewer turns per inductor, has a wider window for the 22 AWG wire, and matches your recall of winding this way before.

**Wire gauge:** 22 AWG magnet wire fits comfortably at these turn counts on both T50-6 (up to ~15 T) and T68-6 (up to ~20 T).  At QRP power (10-20 W, I_rms ≤ 0.63 A into 50 Ω), either gauge is fine thermally.

## After winding — tune and verify

1. Install the LPF on the board (or on a test fixture).  Measure the actual filter response with a vector network analyzer (NanoVNA, TinySA Ultra, etc.) from 1 MHz past 3 × fc.
2. Verify passband insertion loss < 1 dB and stopband rejection ≥ 40 dB at 2 × band center (checks FCC Part 97.307 (e) margin).
3. If the −3 dB corner is low or high by > 10 %, spread or bunch the inductor windings to re-center.
4. If a cap value is wrong, swap to the next standard value — you can't trim ceramic caps easily.
5. Record the final tuned turn counts in the parts list / BOM for build-to-build repeatability.

## References

- Zverev, A.I., *Handbook of Filter Synthesis*, Wiley, 1967 (Chebyshev prototype g-value tables).
- Wetherhold, Ed (W3NQN), "Hands-On Design: Exact-Component-Value Chebyshev LPFs," *QEX*, Jan/Feb 1999.
- Micrometals / Amidon iron-powder toroid catalogs (A_L values and dimensions — **note the µH/100T² convention**).
- kitsandparts.com toroid calculator (useful sanity-check for turn counts).
- QRP Labs LPF kit assembly manuals (reference values for comparison; QRP Labs uses slightly different ripple / cutoff and often different cap-value anchors).

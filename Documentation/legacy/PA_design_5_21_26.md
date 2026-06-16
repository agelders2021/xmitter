# PA Design Reference — 6146B Push-Pull, 14.2 MHz
**Date:** 2026-05-21  
**Target:** 50–60 W CW output, balanced 500 Ω, Class AB1

---

## 1. Overview

Push-pull pair of 6146B beam tetrodes driving a balanced 500 Ω output chain
(LPF → ATU → 300 Ω twin-line → folded dipole).  
Simulated in QUCS-S / ngspice.

---

## 2. DC Operating Point

| Supply | Value | Notes |
|--------|-------|-------|
| B+ (plate) | 500 V | Center tap of plate tank coil |
| Screen (V2, V4) | 225 V | Via 1 kΩ series resistors R3/R7 |
| Grid bias (V1, V3) | −52 V | Via 22 kΩ grid leak R4/R8 |
| Cathode resistors R1, R5 | 10 Ω | Current sense: 1 mV = 1 mA |
| Idle plate current | 15–25 mA/tube | Confirm from 6146B plate curves |

---

## 3. Plate Tank Circuit

### Topology
Each plate connects through a parasitic suppressor (L10/R14 or L11/R15) to the
tank inductor, which returns to B+. The tank capacitor connects from each plate
directly to chassis.

```
Plate → [L10 ‖ R14] → tank node → L4 → B+
Plate → C12 → chassis
```

### Component Values

| Component | Value | Notes |
|-----------|-------|-------|
| L4, L5 | **1.71 µH each** | Plate coils; air-core, self-supporting |
| k4 (L4–L5) | **0.75** | Coupling between plate coils |
| L_half = L4×(1+k4) | 2.993 µH | Half-circuit equivalent inductance |
| L_pp = 2×L_half | 5.985 µH | Plate-to-plate differential inductance |
| XL_pp at 14.2 MHz | 534 Ω | |
| C12, C13 | **39 pF** | Tank caps (simulation); variable in hardware |
| Cak (6146B) | 8.5 pF | Adds to C12/C13 in resonance |

### Tank Resonance Calculation

The suppressor L10‖R14 is in series with the plate-to-B+ path. At 14.2 MHz:

```
Z_sup = Z_L10 ‖ R14 = 36.8 + j19.4 Ω   (XL10 = 89.2 Ω, R14 = 47 Ω)
Z_series = Z_sup + jωL_half = 36.8 + j286.4 Ω
Resonance condition: ωC_total = Im(1/Z_series) = 3.435 mS
C_total = 38.5 pF  →  C_ext = 38.5 − 8.5 (Cak) = 30 pF  (suppressor in circuit)
```

With the new L6 = 2.5 µH / k = 0.80 output link, the loading effect reduces
effective tank inductance to ~5.26 µH, requiring C12/C13 ≈ **39 pF** in simulation
to maintain 14.2 MHz resonance. The physical variable cap compensates automatically.

### Parasitic Suppression

| Component | Value | Location |
|-----------|-------|----------|
| R14, R15 | 47 Ω | In parallel with L10/L11, plate-to-tank node |
| L10, L11 | 1 µH | Suppressor choke, plate-to-tank node |

At 14.2 MHz: `|Z_sup| ≈ 42 Ω` — passes RF plate current with modest loss.
Provides high impedance to VHF parasitics.

**Air-core construction required** — see Section 6.

---

## 4. Output Coupling (Plate Tank → LPF)

### Why the Original Values Were Wrong

The original link coil L6 = 0.43 µH with k5/k6 = 0.57 delivered a plate-to-plate
load of ~18,700 Ω — far above the 1,640 Ω optimal for 55 W. Maximum extractable
power with those values was approximately 5 W regardless of drive level.

### Correct Values for 50–60 W into 500 Ω

The required effective mutual inductance:

```
M_eff = L_pp / √(R_pp / R_load) = 5.985 µH / √(1642 / 500) = 3.30 µH
M_eff = 2 × k × √(L4 × L6)   (push-pull: both plate coils couple to link)
```

Selected design point: **k5 = k6 = 0.80, L6 = 2.5 µH**

| Parameter | Current | New |
|-----------|---------|-----|
| L6 (link/output winding) | 0.43 µH | **2.5 µH** |
| k5 (L4–L6 coupling) | 0.57 | **0.80** |
| k6 (L5–L6 coupling) | 0.57 | **0.80** |
| L4, L5 (plate coils) | 1.71 µH | **1.71 µH** (unchanged) |
| k4 (L4–L5 coupling) | 0.75 | **0.75** (unchanged) |
| C12, C13 (simulation) | 30 pF | **39 pF** (detuning correction) |

Alternative coupling options (all give M_eff ≈ 3.30 µH):

| k5/k6 | L6 required |
|-------|-------------|
| 0.57 | 4.9 µH |
| 0.70 | 3.3 µH |
| 0.80 | 2.5 µH |
| 0.90 | 2.0 µH |

### Output Power Targets

| Po | R_pp optimal | P_dc (η=63%) | Idc (both tubes) | Ip_peak/tube |
|----|-------------|-------------|-----------------|-------------|
| 50 W | 1806 Ω | 79 W | 159 mA | 249 mA |
| 55 W | 1642 Ω | 87 W | 175 mA | 274 mA |
| 60 W | 1505 Ω | 95 W | 190 mA | 299 mA |

These assume V_knee ≈ 75 V (plate voltage at peak current), Class AB1 efficiency ≈ 63%.

---

## 5. Drive and Bias Requirements

For Class AB1 operation:
- Grid must **not** be driven positive (no grid current)
- Peak grid voltage should approach 0 V at drive peaks
- With bias = −52 V: requires **52 V peak** drive at the grid

The 6CL6 driver stage produces approximately 3 V p-p output (gain ≈ 3×, 0.1 V input).
This is **far short** of the 52 V peak required. Options:

1. **Reduce bias magnitude** — e.g., −15 to −20 V brings the drive requirement
   within reach of a single 6CL6 stage, at the cost of higher idle current
2. **Add a driver amplifier stage** — additional gain between 6CL6 and 6146B grids
3. **Increase 6CL6 drive** — confirm maximum 6CL6 output swing from simulation

Grid coupling: C3, C4 = 1000 pF NP0 (grid coupling caps, existing).  
Grid stoppers: R2, R6 = 100 Ω (existing, unchanged).

---

## 6. Construction Notes — Air-Core Coils Required

**Toroids are not suitable for the plate tank or output link.** Reasons:

| Issue | Detail |
|-------|--------|
| Plate-to-chassis voltage | Up to 925 V peak (500 V DC + 425 V RF) |
| Plate-to-plate RF voltage | 850 V peak — exceeds magnet wire insulation ratings |
| Core losses | ~19 A RF circulating current at Q=12; significant heating in any core material |
| Q degradation | Iron powder Q ≈ 50–150 vs air-core Q ≈ 200–500 at 14.2 MHz |

**Recommended construction:**

| Coil | Wire | Form |
|------|------|------|
| L4/L5 (plate, 1.71 µH each) | 14–16 AWG silver-plated or bare copper | Self-supporting, ~2" dia, ~2" long, ~10–12 turns |
| L6 (link, 2.5 µH) | 14–16 AWG | Separate coil, concentric with or adjacent to L4/L5 |

The plate variable capacitor (C12/C13) replaces the fixed simulation value.
Starting range: 10–75 pF per section (standard transmitting variable).

---

## 7. Neutralization

Cross-coupled neutralization caps C6/C7 = **0.24 pF** (matches 6146B Cga = 0.24 pF).
Connect from each plate to the **opposite grid**, on the grid side of the stopper resistor.
These values are unchanged.

---

## 8. Simulation Files

| File | Purpose |
|------|---------|
| `xmitter_prj/PA Subcircuit.sch` | Current PA schematic |
| `xmitter_prj/netlist.cir` | Regenerated netlist (verify node names before editing IC/NODESET) |
| `xmitter_prj/_pa_values.py` | Tank resonance and output coupling calculations |

**Critical reminder:** QUCS-S renumbers nodes every time the schematic is edited.
Always regenerate the netlist and re-verify node names before updating `.IC` or
`.NODESET` directives.

---

## 9. Pending Schematic Changes

- [ ] Change L6: `0.43uH` → `2.5uH`
- [ ] Change k5, k6: `0.57` → `0.80`
- [ ] Change C12, C13: `30pF` → `39pF` (simulation only)
- [ ] Verify drive level — confirm 6CL6 output swing and decide on bias adjustment
- [ ] Update `.IC` node names after schematic edits

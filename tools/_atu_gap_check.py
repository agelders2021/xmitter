"""Diagnose the ATU cap-constraint gap and find Rs/L combos that avoid it."""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f = 14.2e6
w = 2 * np.pi * f

XC_out_max = 2 / (w * 8e-12)     # 2802 ohm (C3_min = 8 pF)
XC_out_min = 2 / (w * 140e-12)   # 160 ohm  (C3_max = 140 pF)
XC_in_max  = 2 / (w * 8e-12)     # 2802 ohm
XC_in_min  = 2 / (w * 100e-12)   # 224 ohm

def atu_coverage(Rs, L_uH):
    """Return sorted RL values covered; detect gaps."""
    XL = 2 * w * L_uH * 1e-6
    results = []
    for Q1 in np.linspace(Rs/XC_in_max, Rs/XC_in_min, 100000):
        Rm = Rs / (1 + Q1**2)
        Q2 = XL / Rm - Q1
        if Q2 < 0:
            continue
        RL = Rm * (1 + Q2**2)
        XCout = RL / Q2 if Q2 > 1e-6 else 1e9
        if not (XC_out_min <= XCout <= XC_out_max):
            continue
        results.append(RL)
    return sorted(results)

def find_bands(RL_list, gap_threshold=5.0):
    """Split sorted RL list into continuous bands; returns list of (lo, hi) tuples."""
    if not RL_list:
        return []
    bands = []
    start = RL_list[0]
    prev = RL_list[0]
    for RL in RL_list[1:]:
        if RL - prev > gap_threshold:
            bands.append((start, prev))
            start = RL
        prev = RL
    bands.append((start, prev))
    return bands

# ── Q2_min analysis for Rs=500, L=1.42uH ────────────────────────────────────
print("=== Q2_min analysis: where the output cap bottleneck occurs ===\n")
Rs = 500.0
L_uH = 1.42
XL = 2 * w * L_uH * 1e-6
Q1_at_Q2min = Rs / (2 * XL)
Rm_at_Q2min = Rs / (1 + Q1_at_Q2min**2)
Q2_min = XL / Rm_at_Q2min - Q1_at_Q2min
RL_at_Q2min = Rm_at_Q2min * (1 + Q2_min**2)
XCout_needed = RL_at_Q2min / Q2_min if Q2_min > 0 else 1e9
C3_needed_pF = 2 / (w * XCout_needed) * 1e12

print(f"Rs={Rs:.0f} ohm, L={L_uH:.2f} uH, XL_diff={XL:.1f} ohm")
print(f"Q2 minimum occurs at Q1 = {Q1_at_Q2min:.3f}")
print(f"  Q2_min = {Q2_min:.4f}")
print(f"  Rm     = {Rm_at_Q2min:.1f} ohm")
print(f"  RL     = {RL_at_Q2min:.1f} ohm  <- the 'forbidden zone' center")
print(f"  XC_out needed = {XCout_needed:.0f} ohm  (requires C3 = {C3_needed_pF:.2f} pF)")
print(f"  Available max XC_out = {XC_out_max:.0f} ohm (C3_min = 8 pF)")
print(f"  GAP: {'YES - cap too large' if XCout_needed > XC_out_max else 'NO'}\n")

# ── Actual bands for Rs=500, L=1.42 ─────────────────────────────────────────
print("=== Actual tuning bands: Rs=500, L=1.42 uH ===\n")
RL_list = atu_coverage(500, 1.42)
bands = find_bands(RL_list, gap_threshold=2.0)
if len(bands) == 1:
    print(f"  CONTINUOUS: {bands[0][0]:.0f} - {bands[0][1]:.0f} ohm")
else:
    for i, (lo, hi) in enumerate(bands):
        print(f"  Band {i+1}: {lo:.0f} - {hi:.0f} ohm")
    gaps = [(bands[i][1], bands[i+1][0]) for i in range(len(bands)-1)]
    for g in gaps:
        print(f"  GAP:  {g[0]:.0f} - {g[1]:.0f} ohm  <- UNTUNABLE")

# ── Find minimum L for continuous coverage at Rs=500 ─────────────────────────
print("\n=== Minimum L for continuous coverage (Rs=500 ohm) ===\n")
print(f"{'L (uH)':>8}  {'Bands / Coverage'}")
print("-" * 60)
for L_uH in [1.42, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2]:
    RL_list = atu_coverage(500, L_uH)
    bands = find_bands(RL_list, gap_threshold=2.0)
    if len(bands) == 1:
        lo, hi = bands[0]
        print(f"{L_uH:>8.2f}  CONTINUOUS: {lo:.0f} - {hi:.0f} ohm  ({hi/lo:.1f}x)")
    else:
        parts = [f"{b[0]:.0f}-{b[1]:.0f}" for b in bands]
        print(f"{L_uH:>8.2f}  GAP: {' | '.join(parts)}")

# ── Check Rs=300 with L=1.42 ─────────────────────────────────────────────────
print("\n=== Rs=300 ohm alternatives ===\n")
print(f"{'L (uH)':>8}  {'Bands / Coverage'}")
print("-" * 60)
for L_uH in [0.90, 1.00, 1.10, 1.20, 1.42]:
    RL_list = atu_coverage(300, L_uH)
    bands = find_bands(RL_list, gap_threshold=2.0)
    if len(bands) == 1:
        lo, hi = bands[0]
        print(f"{L_uH:>8.2f}  CONTINUOUS: {lo:.0f} - {hi:.0f} ohm  ({hi/lo:.1f}x)")
    else:
        parts = [f"{b[0]:.0f}-{b[1]:.0f}" for b in bands]
        print(f"{L_uH:>8.2f}  GAP: {' | '.join(parts)}")

# ── Optimal Rs for covering 150-450 ohm ─────────────────────────────────────
print("\n=== Best Rs + L for continuous 150-450 ohm coverage ===\n")
print(f"{'Rs':>6}  {'L (uH)':>8}  {'RL_min':>8}  {'RL_max':>8}  {'ratio':>7}  {'150-450 covered?'}")
print("-" * 70)
for Rs in [200, 250, 300, 350, 400, 450, 500]:
    best = None
    best_score = -1
    for L_uH in np.arange(Rs/(4*w)*1e6, Rs/(4*w)*1e6 + 3.0, 0.05):
        RL_list = atu_coverage(Rs, L_uH)
        bands = find_bands(RL_list, gap_threshold=2.0)
        if len(bands) != 1:
            continue  # skip if gap
        lo, hi = bands[0]
        cov = max(0, min(hi, 450) - max(lo, 150)) / 300
        if cov > best_score:
            best_score = cov
            best = (L_uH, lo, hi)
    if best:
        L_uH, lo, hi = best
        print(f"{Rs:>6}  {L_uH:>8.2f}  {lo:>8.0f}  {hi:>8.0f}  {hi/lo:>6.1f}x  {best_score*100:.0f}%")
    else:
        print(f"{Rs:>6}  {'no continuous solution':>30}")

"""Sweep Rs AND L for best ATU coverage — balanced pi-network, 14.2 MHz."""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f = 14.2e6
w = 2 * np.pi * f

# Differential reactance limits (balanced, factor-of-2)
XC_in_min  = 2 / (w * 100e-12)   # 224 ohm  (C1=100pF each)
XC_in_max  = 2 / (w *   8e-12)   # 2802 ohm (C1=8pF each)
XC_out_min = 2 / (w * 140e-12)   # 160 ohm  (C3=140pF each)
XC_out_max = 2 / (w *   8e-12)   # 2802 ohm (C3=8pF each)

def match_range(Rs, L_uH):
    """Return (RL_min, RL_max) achievable for given Rs and L_each."""
    XL = 2 * w * L_uH * 1e-6
    results = []
    for Q1 in np.linspace(Rs/XC_in_max, Rs/XC_in_min, 20000):
        Rm = Rs / (1 + Q1**2)
        Q2 = XL / Rm - Q1
        if Q2 < 0:
            continue
        RL = Rm * (1 + Q2**2)
        XC_out = RL / Q2 if Q2 > 1e-6 else 1e9
        if not (XC_out_min <= XC_out <= XC_out_max):
            continue
        results.append(RL)
    if not results:
        return None, None
    return min(results), max(results)

# For each Rs, find the L that best centers the range on 100-500 ohm target
print("=== Optimal L for each Rs (target: cover 100-500 ohm) ===\n")
print(f"{'Rs':>6}  {'L_each':>8}  {'RL_min':>8}  {'RL_max':>8}  "
      f"{'ratio':>7}  {'covers 100-500?'}")
print("-" * 65)

target_lo, target_hi = 100, 500

for Rs in [75, 100, 150, 200, 250, 300, 400, 500]:
    best_score = -1
    best = None
    for L_uH in np.arange(0.1, 3.0, 0.05):
        lo, hi = match_range(Rs, L_uH)
        if lo is None:
            continue
        # score: fraction of [target_lo, target_hi] covered
        covered_lo = max(lo, target_lo)
        covered_hi = min(hi, target_hi)
        if covered_hi <= covered_lo:
            continue
        score = (covered_hi - covered_lo) / (target_hi - target_lo)
        if score > best_score:
            best_score = score
            best = (L_uH, lo, hi)
    if best is None:
        print(f"{Rs:>6}  {'no sol':>8}")
        continue
    L_uH, lo, hi = best
    ratio = hi / lo if lo > 0 else 0
    covers = f"{best_score*100:.0f}%"
    print(f"{Rs:>5}  {L_uH:>7.2f}u  {lo:>8.0f}  {hi:>8.0f}  "
          f"{ratio:>6.1f}x  {covers}")

# ── show full picture for a few key Rs values ─────────────────────────────────
print("\n=== Matching range vs L for selected Rs values ===\n")
print(f"{'L_each':>8}", end="")
for Rs in [150, 200, 300]:
    print(f"   Rs={Rs}: RL_min  RL_max", end="")
print()
print("-" * 75)

for L_uH in [0.5, 0.7, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.14]:
    print(f"{L_uH:>7.2f}u", end="")
    for Rs in [150, 200, 300]:
        lo, hi = match_range(Rs, L_uH)
        if lo is None:
            print(f"   {'--':>14}  {'--':>6}", end="")
        else:
            print(f"   {lo:>12.0f}  {hi:>6.0f}", end="")
    print()

# ── insight: max ratio achievable vs Rs (best-case L) ─────────────────────────
print("\n=== Maximum RL_max/RL_min ratio achievable vs Rs (any L) ===\n")
print(f"{'Rs':>6}  {'best L':>8}  {'RL_min':>8}  {'RL_max':>8}  {'ratio':>7}")
print("-" * 50)
for Rs in [75, 100, 150, 200, 250, 300, 400, 500]:
    best_ratio = 0
    best = None
    for L_uH in np.arange(0.1, 3.0, 0.05):
        lo, hi = match_range(Rs, L_uH)
        if lo is None or lo < 1:
            continue
        r = hi / lo
        if r > best_ratio:
            best_ratio = r
            best = (L_uH, lo, hi)
    if best:
        print(f"{Rs:>6}  {best[0]:>7.2f}u  {best[1]:>8.0f}  {best[2]:>8.0f}  "
              f"{best_ratio:>6.1f}x")

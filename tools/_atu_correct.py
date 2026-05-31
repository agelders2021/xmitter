"""Corrected ATU analysis — properly checks for gaps in matching range.

A gap exists when Q2 goes negative mid-range, which happens when Rs > 2*XL_diff.
The no-gap condition is: XL_diff >= Rs/2, i.e., L_each >= Rs / (4*omega).
"""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f  = 14.2e6
w  = 2 * np.pi * f

XC_in_min  = 2/(w*100e-12)   # 224 ohm
XC_in_max  = 2/(w*  8e-12)   # 2802 ohm
XC_out_min = 2/(w*140e-12)   # 160 ohm
XC_out_max = 2/(w*  8e-12)   # 2802 ohm

def find_range(Rs, L_uH):
    """Return (RL_min, RL_max, has_gap).  has_gap=True means discontinuous."""
    XL = 2 * w * L_uH * 1e-6
    # Gap condition
    disc = Rs**2 - 4*XL**2
    has_gap = disc > 0

    results = []
    for Q1 in np.linspace(Rs/XC_in_max, Rs/XC_in_min, 50000):
        Rm = Rs / (1 + Q1**2)
        Q2 = XL / Rm - Q1
        if Q2 < 0:
            continue
        RL    = Rm * (1 + Q2**2)
        XCout = RL / Q2 if Q2 > 1e-6 else 1e9
        if not (XC_out_min <= XCout <= XC_out_max):
            continue
        results.append(RL)
    if not results:
        return None, None, has_gap
    return min(results), max(results), has_gap

print("=== Gap condition: requires XL_diff >= Rs/2, i.e. L_each >= Rs/(4*omega) ===\n")
print(f"{'Rs':>5}  {'L_min_nogap':>13}  XL_min")
for Rs in [200, 250, 300, 350, 400, 450, 500]:
    Lmin = Rs / (4*w) * 1e6
    XLmin = Rs / 2
    print(f"{Rs:>5}  {Lmin:>10.3f} uH  {XLmin:.0f} ohm")

print("\n=== Correct continuous matching ranges (no gap) ===\n")
print(f"{'Rs':>5}  {'L_each':>8}  {'RL_min':>8}  {'RL_max':>8}  {'ratio':>7}  gap?")
print("-" * 55)

best_options = []
for Rs in [300, 350, 400, 450, 500]:
    L_critical = Rs / (4*w) * 1e6      # minimum L for no gap
    for L_uH in np.arange(L_critical, L_critical + 1.5, 0.05):
        lo, hi, gap = find_range(Rs, L_uH)
        if lo is None or gap:
            continue
        ratio = hi/lo if lo > 0 else 0
        flag = "GAP" if gap else "ok"
        if abs(L_uH - L_critical) < 0.08 or abs(L_uH - (L_critical + 0.3)) < 0.08:
            print(f"{Rs:>5}  {L_uH:>7.2f}u  {lo:>8.0f}  {hi:>8.0f}  {ratio:>6.1f}x  {flag}")
        best_options.append((Rs, L_uH, lo, hi, ratio))

# Find best option for covering 150-450 ohm (realistic folded dipole range)
print("\n=== Best option for each Rs (maximise coverage of 150-450 ohm) ===\n")
print(f"{'Rs':>5}  {'L_each':>8}  {'RL_min':>8}  {'RL_max':>8}  {'ratio':>7}  {'covers 150-450':>15}")
print("-" * 70)
for Rs in [300, 350, 400, 450, 500]:
    best_score, best = -1, None
    for L_uH in np.arange(Rs/(4*w)*1e6, Rs/(4*w)*1e6 + 2.0, 0.02):
        lo, hi, gap = find_range(Rs, L_uH)
        if lo is None or gap:
            continue
        cov_lo = max(lo, 150)
        cov_hi = min(hi, 450)
        score = max(0, cov_hi - cov_lo) / 300
        if score > best_score:
            best_score, best = score, (L_uH, lo, hi, lo/hi)
    if best:
        L_uH, lo, hi, _ = best
        ratio = hi/lo
        print(f"{Rs:>5}  {L_uH:>7.2f}u  {lo:>8.0f}  {hi:>8.0f}  {ratio:>6.1f}x  "
              f"{best_score*100:>8.0f}%")

# ── head-to-head comparison of top candidates ─────────────────────────────────
print("\n=== Head-to-head: top candidates ===\n")
candidates = [
    (300, 0.90, "Rs=300, L=0.90uH (original plan, adj L)"),
    (400, 1.12, "Rs=400, L=1.12uH (min-gap L for Rs=400)"),
    (500, 1.42, "Rs=500, L=1.42uH (min-gap L for Rs=500)"),
]
print(f"{'Candidate':<40}  {'RL_min':>8}  {'RL_max':>8}  {'ratio':>7}  gap?")
print("-" * 75)
for Rs, L_uH, label in candidates:
    lo, hi, gap = find_range(Rs, L_uH)
    flag = "  ** GAP **" if gap else ""
    if lo:
        print(f"{label:<40}  {lo:>8.0f}  {hi:>8.0f}  {hi/lo:>6.1f}x{flag}")
    else:
        print(f"{label:<40}  {'--':>8}  {'--':>8}{flag}")

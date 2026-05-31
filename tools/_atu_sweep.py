"""Sweep inductor value vs ATU matching range (balanced pi-network, 14.2 MHz)."""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f  = 14.2e6
w  = 2 * np.pi * f
Rs = 300.0

# Differential reactance limits from caps (factor-of-2 for balanced)
XC_in_min  = 2 / (w * 100e-12)   # 224 ohm (C1=100pF)
XC_in_max  = 2 / (w *   8e-12)   # 2802 ohm (C1=8pF)
XC_out_min = 2 / (w * 140e-12)   # 160 ohm (C3=140pF)
XC_out_max = 2 / (w *   8e-12)   # 2802 ohm (C3=8pF)

Q1_lo = Rs / XC_in_max   # 0.107
Q1_hi = Rs / XC_in_min   # 1.339

print(f"Cap constraints: Q1 in [{Q1_lo:.3f}, {Q1_hi:.3f}]")
print(f"  XC_in:  {XC_in_min:.0f} - {XC_in_max:.0f} ohm")
print(f"  XC_out: {XC_out_min:.0f} - {XC_out_max:.0f} ohm")
print(f"  Absolute min RL (cap-limited): {Rs/(1+Q1_hi**2):.0f} ohm\n")

print(f"{'L_each':>8}  {'XL_diff':>8}  {'RL_min':>8}  {'RL_max':>8}  "
      f"{'C1@min':>8}  {'C3@min':>8}  {'C1@max':>8}  {'C3@max':>8}")
print("-" * 80)

for L_uH in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.14]:
    L   = L_uH * 1e-6
    XL  = 2 * w * L   # both inductors, k=0

    results = []
    for Q1 in np.linspace(Q1_lo, Q1_hi, 50000):
        Rm = Rs / (1 + Q1**2)
        Q2 = XL / Rm - Q1
        if Q2 < 0:
            continue
        RL     = Rm * (1 + Q2**2)
        XC_out = RL / Q2 if Q2 > 0 else 1e9
        if not (XC_out_min <= XC_out <= XC_out_max):
            continue
        C1 = 2 / (w * (Rs / Q1)) * 1e12   # pF each
        C3 = 2 / (w * (RL / Q2)) * 1e12 if Q2 > 0 else 8.0
        results.append((RL, C1, C3))

    if not results:
        print(f"{L_uH:>7.2f}u  {XL:>8.1f}  {'--':>8}  {'--':>8}")
        continue

    RL_vals = [r[0] for r in results]
    imin = int(np.argmin(RL_vals))
    imax = int(np.argmax(RL_vals))
    rmin = results[imin]
    rmax = results[imax]
    print(f"{L_uH:>7.2f}u  {XL:>8.1f}  {rmin[0]:>8.0f}  {rmax[0]:>8.0f}  "
          f"{rmin[1]:>7.0f}p  {rmin[2]:>7.0f}p  {rmax[1]:>7.0f}p  {rmax[2]:>7.0f}p")

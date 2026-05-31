"""Compute final ATU design values: Rs=500 ohm, L=1.1 uH each, k=0, f=14.2 MHz."""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f   = 14.2e6
w   = 2 * np.pi * f
Rs  = 500.0
L   = 1.1e-6

XL  = 2 * w * L          # both inductors, k=0, balanced
XL1 = w * L              # single inductor reactance

XC_in_min  = 2/(w*100e-12)   # 224 ohm  (C1/C2 = 100 pF each)
XC_in_max  = 2/(w*  8e-12)   # 2802 ohm (C1/C2 = 8 pF each)
XC_out_min = 2/(w*140e-12)   # 160 ohm  (C3/C4 = 140 pF each)
XC_out_max = 2/(w*  8e-12)   # 2802 ohm (C3/C4 = 8 pF each)

print(f"=== ATU Design: Rs={Rs:.0f} ohm, L={L*1e6:.2f} uH each, k=0, f={f/1e6:.1f} MHz ===\n")
print(f"Single inductor XL      = {XL1:.1f} ohm")
print(f"Differential series XL  = {XL:.1f} ohm  (both inductors, push-pull)")
print(f"XL / Rs ratio           = {XL/Rs:.3f}  (< 1 -> can match below Rs)\n")

print(f"Input caps C1/C2 (8-100 pF each):")
print(f"  XC_diff range: {XC_in_min:.0f} ohm (100 pF) to {XC_in_max:.0f} ohm (8 pF)")
print(f"  Q1 range:      {Rs/XC_in_max:.3f} to {Rs/XC_in_min:.3f}")
print(f"Output caps C3/C4 (8-140 pF each):")
print(f"  XC_diff range: {XC_out_min:.0f} ohm (140 pF) to {XC_out_max:.0f} ohm (8 pF)\n")

# ── full sweep ─────────────────────────────────────────────────────────────────
results = []
for Q1 in np.linspace(Rs/XC_in_max, Rs/XC_in_min, 100000):
    Rm = Rs / (1 + Q1**2)
    Q2 = XL / Rm - Q1
    if Q2 < 0:
        continue
    RL = Rm * (1 + Q2**2)
    XC_out = RL / Q2 if Q2 > 1e-6 else 1e9
    if not (XC_out_min <= XC_out <= XC_out_max):
        continue
    C1 = 2/(w*(Rs/Q1)) * 1e12
    C3 = 2/(w*(RL/Q2)) * 1e12 if Q2 > 1e-6 else 8.0
    results.append((Q1, Rm, Q2, RL, C1, C3))

RL_vals = [r[3] for r in results]
RL_min  = min(RL_vals)
RL_max  = max(RL_vals)
print(f"=== Resistive matching range ===")
print(f"  RL_min = {RL_min:.0f} ohm")
print(f"  RL_max = {RL_max:.0f} ohm")
print(f"  Ratio  = {RL_max/RL_min:.1f}x\n")

# ── reactive range ─────────────────────────────────────────────────────────────
print(f"=== Reactive tuning range (rough) ===")
print(f"  Max capacitive load reactance: ~-{XL:.0f} ohm  (series L resonates it)")
print(f"  Max inductive  load reactance: ~+{XC_out_min:.0f} ohm  (output cap cancels it)\n")

# ── tuning table: target RL -> required C1, Rm, C3 ───────────────────────────
print(f"=== Tuning guide: target RL -> capacitor settings ===")
print(f"  (These are purely resistive load operating points)")
print()
print(f"  {'RL (ohm)':>9}  {'C1/C2 (pF)':>11}  {'C3/C4 (pF)':>11}  "
      f"{'Rm (ohm)':>9}  {'Q1':>6}  {'Q2':>6}  {'Net Q':>7}")
print(f"  {'-'*72}")

targets = [85, 100, 125, 150, 175, 200, 250, 300, 350, 400, 450, 500, 509]
shown = set()
for tgt in targets:
    # find result closest to target
    best = min(results, key=lambda r: abs(r[3]-tgt))
    Q1, Rm, Q2, RL, C1, C3 = best
    # deduplicate
    key = round(RL/10)*10
    if key in shown:
        continue
    shown.add(key)
    net_q = (Q1 + Q2) / 2
    print(f"  {RL:>9.0f}  {C1:>11.1f}  {C3:>11.1f}  "
          f"{Rm:>9.1f}  {Q1:>6.3f}  {Q2:>6.3f}  {net_q:>7.3f}")

# ── coupling constant reminder ─────────────────────────────────────────────────
print(f"\n=== Coupling constant effect on XL_diff ===")
for k, label in [(0.99,"k=0.99 (original)"), (0.90,"k=0.90"), (0.00,"k=0.00 (required)")]:
    xl = 2 * w * L * (1-k)
    print(f"  {label}: XL_diff = {xl:.1f} ohm  ({xl/XL*100:.0f}% of k=0 value)")

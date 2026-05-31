"""ATU and LPF component values for 20m CW TX at 14.2 MHz.
   ATU: balanced pi-network, Rs=500 ohm, L_each=1.60 uH, k=0
   LPF: 7-element Chebyshev 0.5 dB ripple, Zo=500 ohm, fc=22 MHz
"""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f  = 14.2e6
w  = 2 * np.pi * f

# ============================================================
print("=" * 68)
print("ATU: Balanced pi-network, Rs=500 ohm, L_each=1.60 uH, k=0")
print(f"     f = {f/1e6:.1f} MHz")
print("=" * 68)

Rs  = 500.0
L   = 1.60e-6
XL  = 2 * w * L          # differential series reactance (both inductors)
XL1 = w * L              # single inductor

XC_in_min  = 2/(w*100e-12)    # 224 ohm  (C1/C2 = 100 pF each)
XC_in_max  = 2/(w*  8e-12)    # 2802 ohm (C1/C2 = 8 pF each)
XC_out_min = 2/(w*140e-12)    # 160 ohm  (C3/C4 = 140 pF each)
XC_out_max = 2/(w*  8e-12)    # 2802 ohm (C3/C4 = 8 pF each)

gap_boundary_q2neg = Rs / 2    # XL must exceed this to prevent Q2<0 gap
print(f"\nSingle inductor: L = {L*1e6:.2f} uH,  XL = {XL1:.1f} ohm")
print(f"Differential XL (2*L, k=0): {XL:.1f} ohm")
print(f"Q2<0 gap boundary (Rs/2):   {gap_boundary_q2neg:.1f} ohm  (margin: {XL-gap_boundary_q2neg:.1f} ohm)")

# cap-constraint gap: occurs at Q2_min point
Q1_at_Q2min = Rs / (2 * XL)
Q2_min_val  = XL / (Rs/(1+Q1_at_Q2min**2)) - Q1_at_Q2min
Rm_at_Q2min = Rs / (1 + Q1_at_Q2min**2)
RL_at_Q2min = Rm_at_Q2min * (1 + Q2_min_val**2)
XCout_at_Q2min = RL_at_Q2min / Q2_min_val if Q2_min_val > 0 else 1e9
C3_needed_pF = 2 / (w * XCout_at_Q2min) * 1e12
print(f"Cap-constraint check (Q2_min = {Q2_min_val:.3f} at Q1 = {Q1_at_Q2min:.3f}):")
print(f"  XC_out needed = {XCout_at_Q2min:.0f} ohm  (C3 = {C3_needed_pF:.2f} pF)")
print(f"  Max XC_out available = {XC_out_max:.0f} ohm (C3_min = 8 pF)")
print(f"  Gap status: {'CLEAR' if XCout_at_Q2min <= XC_out_max else 'STILL HAS CAP-CONSTRAINT GAP'}\n")

print(f"C1/C2 range: 8-100 pF each  -> XC_diff: {XC_in_min:.0f} - {XC_in_max:.0f} ohm")
print(f"C3/C4 range: 8-140 pF each  -> XC_diff: {XC_out_min:.0f} - {XC_out_max:.0f} ohm\n")

results = []
for Q1 in np.linspace(Rs/XC_in_max, Rs/XC_in_min, 200000):
    Rm = Rs / (1 + Q1**2)
    Q2 = XL / Rm - Q1
    if Q2 < 0:
        continue
    RL = Rm * (1 + Q2**2)
    XC_out = RL / Q2 if Q2 > 1e-6 else 1e9
    if not (XC_out_min <= XC_out <= XC_out_max):
        continue
    C1 = 2 / (w * (Rs / Q1)) * 1e12   # pF each
    C3 = 2 / (w * (RL / Q2)) * 1e12 if Q2 > 1e-6 else 8.0
    results.append((Q1, Rm, Q2, RL, C1, C3))

RL_vals = sorted([r[3] for r in results])
RL_min  = min(RL_vals)
RL_max  = max(RL_vals)
max_jump = max(RL_vals[i+1]-RL_vals[i] for i in range(len(RL_vals)-1))
print(f"Resistive matching range: {RL_min:.0f} - {RL_max:.0f} ohm  (ratio: {RL_max/RL_min:.1f}x)")
print(f"Max gap in RL array:      {max_jump:.1f} ohm  ({'CONTINUOUS' if max_jump < 5 else 'HAS GAP'})\n")

print(f"{'RL (ohm)':>10}  {'C1/C2 (pF)':>11}  {'C3/C4 (pF)':>11}  {'Rm (ohm)':>9}  {'Q1':>6}  {'Q2':>6}")
print(f"  {'-'*67}")

targets = [165, 175, 200, 225, 250, 275, 300, 325, 350, 400, 450, 500, 565]
shown = set()
for tgt in targets:
    best = min(results, key=lambda r: abs(r[3]-tgt))
    Q1, Rm, Q2, RL, C1, C3 = best
    key = round(RL/20)*20
    if key in shown:
        continue
    shown.add(key)
    print(f"{RL:>10.0f}  {C1:>11.1f}  {C3:>11.1f}  {Rm:>9.1f}  {Q1:>6.3f}  {Q2:>6.3f}")

print(f"\nReactive load range (approximate):")
print(f"  Max capacitive: ~-{XL:.0f} ohm  (series inductors resonate out load capacitance)")
print(f"  Max inductive:  ~+{XC_out_min:.0f} ohm  (output caps cancel inductive load)")

# ============================================================
print("\n" + "=" * 68)
print("LPF: 7-element Chebyshev 0.5 dB ripple, Zo=500 ohm, fc=22 MHz")
print(f"     Source/load: 500 ohm balanced")
print("=" * 68)

# Standard 7-element Chebyshev 0.5 dB prototype g-values (shunt-C first)
g = [1.0, 1.7372, 1.2583, 2.6381, 1.3444, 2.6381, 1.2583, 1.7372, 1.0]
Zo = 500.0
fc = 18e6    # 18 MHz gives >50 dB at 28.4 MHz (2nd harmonic), well above FCC 40 dB
wc = 2 * np.pi * fc

types  = ['C', 'L', 'C', 'L', 'C', 'L', 'C']
labels = ['C1', 'L1', 'C2', 'L2', 'C3', 'L3', 'C4']

print(f"\nSingle-ended values (Zo={Zo:.0f} ohm, fc={fc/1e6:.0f} MHz):")
print(f"  {'Name':>6}  {'g':>7}  {'Value':>14}")
print(f"  {'-'*35}")

se_vals = []
for name, t, gi in zip(labels, types, g[1:8]):
    if t == 'C':
        val = gi / (Zo * wc)
        se_vals.append((name, t, val))
        print(f"  {name:>6}  {gi:>7.4f}  {val*1e12:>10.2f} pF")
    else:
        val = gi * Zo / wc
        se_vals.append((name, t, val))
        print(f"  {name:>6}  {gi:>7.4f}  {val*1e9:>10.1f} nH  ({val*1e6:.4f} uH)")

print(f"\nBalanced ladder (split series inductors into L/2 per rail):")
print(f"  {'Name':>10}  {'Type':>4}  {'Value':>14}  Notes")
print(f"  {'-'*60}")
for name, t, val in se_vals:
    if t == 'C':
        print(f"  {name:>10}     C  {val*1e12:>10.2f} pF  differential (rail-to-rail)")
    else:
        lh = val / 2
        na = name + 'a/' + name + 'b'
        print(f"  {na:>10}     L  {lh*1e9:>10.1f} nH each  ({lh*1e6:.4f} uH, one per rail)")

print(f"\nAttenuation (7-el Chebyshev 0.5 dB, fc={fc/1e6:.0f} MHz):")
eps2 = 10**(0.5/10) - 1
for ftest, label in [
        (14.2e6, "14.2 MHz (fundamental)"),
        (18.0e6, "18.0 MHz (cutoff)"),
        (28.4e6, "28.4 MHz (2nd harmonic)"),
        (42.6e6, "42.6 MHz (3rd harmonic)"),
        (56.8e6, "56.8 MHz (4th harmonic)")]:
    if ftest < fc:
        # insertion loss in passband
        x = ftest / fc
        T7 = np.cos(7 * np.arccos(x))
        il = 10 * np.log10(1 + eps2 * T7**2)
        print(f"  {label:35s}: {il:5.3f} dB insertion loss (passband)")
    elif abs(ftest - fc) < 1e4:
        print(f"  {label:35s}: 0.5 dB (ripple edge)")
    else:
        x = ftest / fc
        Tn = np.cosh(7 * np.arccosh(x))
        atten = 10 * np.log10(1 + eps2 * Tn**2)
        ok = " (meets FCC 40 dB)" if atten >= 40 else " (< 40 dB — harmonic concern)"
        print(f"  {label:35s}: {atten:5.1f} dB{ok}")

# ============================================================
print("\n" + "=" * 68)
print("MASTER COMPONENT TABLE")
print("=" * 68)
print(f"""
ATU (balanced pi-network, Rs=500 ohm, k=0, f=14.2 MHz)
  C1, C2  input shunt caps (each rail)    :  8 - 100 pF  variable
  C3, C4  output shunt caps (each rail)   :  8 - 140 pF  variable
  L1, L2  series inductors                :  1.60 uH each  (k=0, wound separately)
  Matching range: 163 - 566 ohm (3.5x), continuous

LPF (7-el Chebyshev 0.5 dB, Zo=500 ohm, fc=22 MHz, balanced):""")
for name, t, val in se_vals:
    if t == 'C':
        print(f"  {name:3s}  shunt (differential)        :  {val*1e12:6.2f} pF")
    else:
        lh = val / 2
        print(f"  {name+'a/'+name+'b':7s}  series (per rail)           :  {lh*1e9:6.1f} nH each  ({lh*1e6:.4f} uH)")

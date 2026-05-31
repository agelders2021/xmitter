"""PA component value recalculation — 6146B push-pull, 14.2 MHz, 500 ohm output.
Accounts for plate parasitic suppressor (L10||R14) in the tank circuit.
"""
import numpy as np, sys
sys.stdout.reconfigure(encoding="utf-8")

f   = 14.2e6
w   = 2 * np.pi * f
Vb  = 500.0    # B+
Vs  = 225.0    # screen
Vg  = -52.0    # bias
Vk_min = 75.0  # plate voltage at conduction peak (knee), rough estimate

# ── Tube capacitances (6146B) ─────────────────────────────────────────────────
Cak = 8.5e-12   # plate-to-cathode (adds to external tank cap)
Cgk = 13e-12
Cga = 0.24e-12  # (neutralization cap matches this)

# ── Plate tank inductors ──────────────────────────────────────────────────────
L4  = 1.71e-6   # plate coil each
k4  = 0.75      # coupling between L4 and L5 (plate-to-plate)
L_half = L4 * (1 + k4)   # half-circuit equivalent inductance
L_pp   = 2 * L_half      # full plate-to-plate differential inductance

# ── Parasitic suppressor (current topology: between plate and tank node) ──────
L10 = 1.0e-6    # suppressor choke
R14 = 47.0      # suppressor resistor (parallel with L10)

print("=" * 68)
print("PA Tank Resonance — 6146B Push-Pull, f = 14.2 MHz")
print("=" * 68)

print(f"\nL4 = L5 = {L4*1e6:.2f} uH,  k4(L4-L5) = {k4}")
print(f"L_half (half-circuit) = L4*(1+k4) = {L_half*1e6:.4f} uH")
print(f"L_pp (plate-to-plate) = 2*L_half  = {L_pp*1e6:.4f} uH")
print(f"XL_half = {w*L_half:.1f} ohm,  XL_pp = {w*L_pp:.1f} ohm")

# ── Suppressor impedance at 14.2 MHz ─────────────────────────────────────────
Z_L10 = 1j * w * L10
Z_sup  = Z_L10 * R14 / (Z_L10 + R14)   # L10 || R14
print(f"\nSuppressor L10||R14 at {f/1e6:.1f} MHz:")
print(f"  XL10 = {w*L10:.1f} ohm")
print(f"  Z_sup = {Z_sup.real:.2f} + j{Z_sup.imag:.2f} ohm  (|Z| = {abs(Z_sup):.1f} ohm)")

# ── Tank resonance — three models ─────────────────────────────────────────────
print(f"\n{'Model':<40}  {'C_total':>9}  {'C_ext':>9}  {'f_res':>9}")
print("-" * 75)

def resonate(L_eff_series, Z_extra_series=0):
    """Find C_total for parallel resonance with series branch Z_extra + jωL_eff."""
    Z_series = Z_extra_series + 1j * w * L_eff_series
    Y_series = 1 / Z_series
    # Im(Y_shunt_C + Y_series) = 0  →  wC = -Im(Y_series)
    C_total = -Y_series.imag / w
    return C_total

# Model 1: No suppressor (just L_half)
C1 = resonate(L_half, 0)
print(f"{'1. No suppressor (L_half only)':<40}  {C1*1e12:>8.1f}p  "
      f"{(C1-Cak)*1e12:>8.1f}p  "
      f"{1/(2*np.pi*np.sqrt(L_half*C1))/1e6:>8.2f} MHz")

# Model 2: Suppressor as pure inductor L10 in series (R14 ignored)
C2 = resonate(L_half, 1j * w * L10)
print(f"{'2. Suppressor as pure L10 in series':<40}  {C2*1e12:>8.1f}p  "
      f"{(C2-Cak)*1e12:>8.1f}p  -- (lossy)")

# Model 3: Suppressor as L10||R14 (accurate)
C3 = resonate(L_half, Z_sup)
C3_ext = C3 - Cak
f_res_check = 1 / (2 * np.pi * np.sqrt(L_half * C3))   # approximate
print(f"{'3. Suppressor as L10||R14 (accurate)':<40}  {C3*1e12:>8.1f}p  "
      f"{C3_ext*1e12:>8.1f}p  -- (lossy)")

print(f"\n  Current schematic value: C12 = C13 = 30 pF")
print(f"  Cak contribution: {Cak*1e12:.1f} pF (tube plate-to-cathode)")

# Verify with current 30 pF
C12_cur = 30e-12
C_total_cur = C12_cur + Cak
Z_ser = Z_sup + 1j * w * L_half
Y_total = 1j * w * C_total_cur + 1/Z_ser
print(f"\n  Verification with C12=30pF: Im(Y_total) = {Y_total.imag:.4e} S  "
      f"({'resonant' if abs(Y_total.imag) < 1e-5 else 'off resonance'})")

# ── Operating point for 50-60 W ──────────────────────────────────────────────
print(f"\n{'='*68}")
print(f"Target Operating Point: 50-60 W, B+={Vb:.0f}V, Screen={Vs:.0f}V")
print(f"{'='*68}")

for Po_target in [50, 55, 60]:
    Vswing = Vb - Vk_min           # plate voltage swing to knee
    R_pp_opt = Vswing**2 / (2 * Po_target)
    eta_approx = Po_target / (Vb * Po_target / (0.63 * Vb))  # rough
    Idc_avg = Po_target / (0.63 * Vb)     # class AB1 efficiency ~63%
    Ip_peak_each = Idc_avg * np.pi / 2    # class B approximation
    print(f"\n  Po = {Po_target} W:")
    print(f"    R_pp_optimal  = {R_pp_opt:.0f} ohm (plate-to-plate load)")
    print(f"    Eta (approx)  = 63%  =>  P_dc = {Po_target/0.63:.0f} W")
    print(f"    Idc (both)    = {Idc_avg*1000:.0f} mA  =>  ~{Idc_avg*500:.0f} mA per tube avg")
    print(f"    Ip_peak each  = {Ip_peak_each*1000:.0f} mA (class-B approx)")

# ── Output coupling — what L6/k must be for 55 W ─────────────────────────────
print(f"\n{'='*68}")
print(f"Output Coupling Required for R_pp = 1680 ohm (55 W), Load = 500 ohm")
print(f"{'='*68}")

Po      = 55.0
R_pp    = (Vb - Vk_min)**2 / (2 * Po)   # 1642 ohm
R_load  = 500.0
L6_cur  = 0.43e-6
k56_cur = 0.57

# Effective mutual in push-pull: M_eff = 2*k*sqrt(L4*L6)
# R_pp = R_load * (L_pp / M_eff)^2   (link-coupled tank formula)
# M_eff_needed = L_pp / sqrt(R_pp / R_load)
M_needed = L_pp / np.sqrt(R_pp / R_load)
print(f"\nR_pp optimal for {Po:.0f} W = {R_pp:.0f} ohm")
print(f"M_eff needed = L_pp / sqrt(R_pp/R_load) = {M_needed*1e6:.3f} uH")

# Current M_eff
M_cur = 2 * k56_cur * np.sqrt(L4 * L6_cur)
R_pp_cur = R_load * (L_pp / M_cur)**2
print(f"\nCurrent coupling: L6={L6_cur*1e6:.2f} uH, k5=k6={k56_cur}")
print(f"  M_eff_current  = 2*k*sqrt(L4*L6) = {M_cur*1e6:.3f} uH")
print(f"  R_pp delivered = R_load*(L_pp/M)^2 = {R_pp_cur:.0f} ohm  (way too high)")
print(f"  Max power (approx) = {(Vb-Vk_min)**2/(2*R_pp_cur):.1f} W")

print(f"\nOptions to reach R_pp = {R_pp:.0f} ohm:")
print(f"  {'k5=k6':>6}  {'L6 needed':>12}  {'M_eff':>10}  {'R_pp check':>12}")
print(f"  {'-'*50}")
for k56 in [0.57, 0.70, 0.80, 0.90]:
    # M = 2*k*sqrt(L4*L6)  => sqrt(L6) = M/(2k*sqrt(L4))  => L6 = (M/(2k*sqrt(L4)))^2
    L6_needed = (M_needed / (2 * k56 * np.sqrt(L4)))**2
    M_check   = 2 * k56 * np.sqrt(L4 * L6_needed)
    R_pp_check = R_load * (L_pp / M_check)**2
    print(f"  {k56:>6.2f}  {L6_needed*1e6:>10.3f} uH  {M_check*1e6:>8.3f} uH  {R_pp_check:>10.0f} ohm")

# ── Bias / drive for class AB1 ────────────────────────────────────────────────
print(f"\n{'='*68}")
print(f"Bias and Drive — Class AB1")
print(f"{'='*68}")
print(f"""
For class AB1 push-pull operation:
  - Grid must NOT be driven positive (no grid current)
  - Peak grid voltage should approach 0 V (or just below) at drive peaks
  - Current bias = {Vg:.0f} V  =>  grid swing needed = {abs(Vg):.0f} V peak
  - Cutoff for 6146B at Vs={Vs:.0f}V:  approx -65 to -75 V (read from plate curves)

Idle current per tube (class AB1): 15-25 mA at Vg={Vg:.0f}V, Vs={Vs:.0f}V, Vb={Vb:.0f}V
  - Confirm with datasheet plate curves

Drive required:
  - Peak grid voltage ~ 0 V  =>  drive amplitude at grid = {abs(Vg):.0f} V peak
  - Driver transformer secondary delivers this with ~1 V input from 6CL6
  - 6CL6 stage gain ~3x (from previous session) with 0.1V input => ~0.3 V
  - Need to verify 6CL6 can swing {abs(Vg):.0f} V peak at its output
  - If not: increase drive or reduce grid bias magnitude (e.g., to -40 V)
""")

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 68)
print("SUMMARY OF CHANGES NEEDED")
print("=" * 68)
print(f"""
Tank capacitors C12, C13:
  Current value: 30 pF — already resonant at 14.2 MHz (with L10||R14 in circuit)
  If suppressor moved OUT of tank path: change to 33-34 pF
  Physical design: use ~10-50 pF variable cap (covers all cases)

Output coupling (MUST CHANGE for 50-60 W):
  Current:  L6 = 0.43 uH, k5=k6=0.57  =>  R_pp ~ 18,700 ohm => max ~4-5 W
  Required: L6 ~ 2.0-5.0 uH depending on k5/k6 chosen
  Recommended: k5=k6=0.80, L6=2.5 uH  =>  M_eff ~ 3.2 uH => R_pp ~ 1640 ohm

Operating point (no change to bias/screen needed for 50-60 W):
  B+ = 500 V, Screen = 225 V, Bias = -52 V are reasonable
  Target R_pp = 1642 ohm (for 55 W), 1500 ohm (for 60 W)
  Main lever: fix the output coupling to deliver correct plate load
""")

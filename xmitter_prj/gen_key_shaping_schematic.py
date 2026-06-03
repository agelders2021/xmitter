"""
gen_key_shaping_schematic.py
Generate a signal-flow schematic PDF of the CW key-shaping chain:
  MCP4921 DAC  →  2-pole RC LPF  →  TL072 non-inverting amp (×3)  →  MC1496 modulating port
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path(r'C:\Users\AlAnd\Git Backed Projects\xmitter\Documentation\key_shaping_chain.pdf')

# ── figure ────────────────────────────────────────────────────────────────────
FW, FH = 13.0, 8.0
fig, ax = plt.subplots(figsize=(FW, FH))
ax.set_xlim(0, FW)
ax.set_ylim(0, FH)
ax.set_aspect('equal')
ax.axis('off')
fig.patch.set_facecolor('white')

# ── primitives ────────────────────────────────────────────────────────────────
def W(x1, y1, x2, y2, c='k', lw=1.5):
    ax.plot([x1, x2], [y1, y2], '-', c=c, lw=lw, solid_capstyle='round')

def DOT(x, y):
    ax.add_patch(plt.Circle((x, y), .075, color='k', zorder=6))

def GND(x, y):
    """Ground symbol pointing down from (x, y)."""
    for i, hw in enumerate([.21, .14, .07]):
        ax.plot([x - hw, x + hw], [y - i * .13, y - i * .13], 'k-', lw=1.5)

def zigzag_h(x1, x2, y, n=8, amp=.09):
    mg = .12 * (x2 - x1)
    xs = np.linspace(x1 + mg, x2 - mg, n + 1)
    ys = ([y] +
          [y + amp * (1 if i % 2 == 0 else -1) for i in range(n - 1)] +
          [y])
    ax.plot([x1, x1 + mg], [y, y], 'k-', lw=1.5)
    ax.plot([x2 - mg, x2], [y, y], 'k-', lw=1.5)
    ax.plot(xs, ys, 'k-', lw=1.5)

def zigzag_v(x, y1, y2, n=8, amp=.09):
    """y1 = bottom connection, y2 = top connection."""
    mg = .12 * (y2 - y1)
    ys = np.linspace(y1 + mg, y2 - mg, n + 1)
    xs = ([x] +
          [x + amp * (1 if i % 2 == 0 else -1) for i in range(n - 1)] +
          [x])
    ax.plot([x, x], [y1, y1 + mg], 'k-', lw=1.5)
    ax.plot([x, x], [y2 - mg, y2], 'k-', lw=1.5)
    ax.plot(xs, ys, 'k-', lw=1.5)

def RH(x1, x2, y, lbl='', side='above'):
    zigzag_h(x1, x2, y)
    if lbl:
        xc, off = (x1 + x2) / 2, .09 + .13
        va = 'bottom' if side == 'above' else 'top'
        ax.text(xc, y + (off if side == 'above' else -off), lbl,
                ha='center', va=va, fontsize=8)

def RV(x, y1, y2, lbl='', side='right'):
    zigzag_v(x, y1, y2)
    if lbl:
        yc, off = (y1 + y2) / 2, .09 + .14
        ha = 'left' if side == 'right' else 'right'
        ax.text(x + (off if side == 'right' else -off), yc, lbl,
                ha=ha, va='center', fontsize=8)

def POT(x1, x2, y, lbl='', side='below'):
    """Horizontal trim-pot: zigzag body with wiper arrow."""
    RH(x1, x2, y, lbl, side)
    xc = (x1 + x2) / 2
    ax.annotate('', xy=(xc - .27, y + .31), xytext=(xc + .27, y - .27),
                arrowprops=dict(arrowstyle='->', color='k', lw=1.2, mutation_scale=11))

def CAP(x, ytop, ybot, lbl='', side='right'):
    """Vertical capacitor from ybot to ytop at x."""
    yc = (ytop + ybot) / 2
    pw, gap = .28, .10
    W(x, ytop, x, yc + gap)
    ax.plot([x - pw, x + pw], [yc + gap, yc + gap], 'k-', lw=2.8)
    ax.plot([x - pw, x + pw], [yc - gap, yc - gap], 'k-', lw=2.8)
    W(x, yc - gap, x, ybot)
    if lbl:
        off = pw + .13
        ha = 'left' if side == 'right' else 'right'
        ax.text(x + (off if side == 'right' else -off), yc, lbl,
                ha=ha, va='center', fontsize=8)

def OA(xl, xr, yb, yt):
    """Draw op-amp triangle; return (y_plus, y_minus, y_out)."""
    ym = (yb + yt) / 2
    rng = yt - yb
    yp = yt - rng / 3.0
    yn = yb + rng / 3.0
    ax.add_patch(plt.Polygon([[xl, yt], [xl, yb], [xr, ym]],
                             fill=False, edgecolor='k', lw=1.8, zorder=3))
    ax.text(xl + .22, yp + .05, '+', ha='left', va='bottom', fontsize=13, fontweight='bold')
    ax.text(xl + .22, yn - .05, '−', ha='left', va='top', fontsize=13, fontweight='bold')
    ax.text(xl * .30 + xr * .70, ym + .24, 'TL072',
            ha='center', va='bottom', fontsize=9, style='italic')
    ax.plot([xl - .30, xl], [yp, yp], 'k-', lw=1.5)   # + lead
    ax.plot([xl - .30, xl], [yn, yn], 'k-', lw=1.5)   # − lead
    ax.plot([xr, xr + .30], [ym, ym], 'k-', lw=1.5)   # output lead
    return yp, yn, ym

# ── op-amp (everything keys off these) ───────────────────────────────────────
OAx1, OAx2 = 8.1, 9.6
OAyb, OAyt = 3.9, 5.5      # height = 1.6"
yp, yn, yo = OA(OAx1, OAx2, OAyb, OAyt)
# yp = 5.5 - 1.6/3 = 4.967   ← SY
# yn = 3.9 + 1.6/3 = 4.433
# yo = (5.5+3.9)/2 = 4.700
SY  = yp          # main signal-path y (= + input y)
PP  = OAx1 - .30  # + pin left x  = 7.80
NP  = OAx1 - .30  # − pin left x  = 7.80

# power-supply stubs (dashed, inside triangle pointing out)
VX = (OAx1 + OAx2) / 2 - .20    # 8.55
ax.plot([VX, VX], [OAyt - .10, OAyt + .50], 'k--', lw=1.0)
ax.text(VX, OAyt + .57, '+12 V',  ha='center', va='bottom', fontsize=8, color='#555')
ax.plot([VX, VX], [OAyb + .10, OAyb - .50], 'k--', lw=1.0)
ax.text(VX, OAyb - .57, '−8.2 V', ha='center', va='top',  fontsize=8, color='#555')

# ── input terminal ────────────────────────────────────────────────────────────
TX = .65
ax.add_patch(plt.Circle((TX, SY), .14, fill=False, edgecolor='k', lw=1.8))
ax.text(TX, SY + .28, 'MCP4921 VOUT', ha='center', va='bottom', fontsize=8.5, fontweight='bold')
ax.text(TX, SY - .28, '0 – 3.3 V',   ha='center', va='top',    fontsize=8,   color='#555')
W(TX + .14, SY, 1.2, SY)

# ── LPF: R1 + C1 ─────────────────────────────────────────────────────────────
RH(1.2, 2.6, SY, 'R1    1 kΩ')
W(2.6, SY, 3.2, SY)

C1X = 3.2
DOT(C1X, SY)
CAP(C1X, SY, 3.15, 'C1   22 nF')
GND(C1X, 3.15)
W(C1X, SY, 3.7, SY)

# ── LPF: R2 + C2 ─────────────────────────────────────────────────────────────
RH(3.7, 5.2, SY, 'R2    1 kΩ')
W(5.2, SY, 5.85, SY)

C2X = 5.85
DOT(C2X, SY)
CAP(C2X, SY, 3.15, 'C2   22 nF')
GND(C2X, 3.15)

# wire from C2 node to + input pin
W(C2X, SY, PP, SY)

# ── output wire and terminal ──────────────────────────────────────────────────
GRN = 'darkgreen'
OUT_TERM = 11.7
W(OAx2 + .30, yo, OUT_TERM, yo, c=GRN, lw=1.8)
ax.plot(OUT_TERM, yo, 'o', ms=9, mec=GRN, mfc='white', mew=1.8, zorder=5)
ax.text(OUT_TERM, yo + .25, 'AGC OUT', ha='center', va='bottom',
        fontsize=9.5, fontweight='bold', color=GRN)
ax.text(OUT_TERM, yo + .04, '0 – 10 V', ha='center', va='bottom',
        fontsize=8.5, color=GRN)
ax.text(OUT_TERM, yo - .22, '→ MC1496 modulating port', ha='center', va='top',
        fontsize=8, color='#444')

# feedback tap on output wire
FBx = 10.4
DOT(FBx, yo)

# ── feedback network ──────────────────────────────────────────────────────────
FBy = 2.05    # horizontal Rf / trim line y

W(FBx, yo, FBx, FBy)              # output-tap wire down to Rf right end

W(NP, yn, NP, FBy)                # − input pin wire down to Rf/Rg junction
DOT(NP, FBy)

# Rf  20 kΩ
RFe = NP + 1.75                   # 7.80 + 1.75 = 9.55
RH(NP, RFe, FBy, 'Rf    20 kΩ', 'below')

# short wire to trim pot
W(RFe, FBy, RFe + .12, FBy)

# Trim pot  2 kΩ
POT(RFe + .12, FBx, FBy, 'TRIM   2 kΩ', 'below')

# Rg  10 kΩ  (− input to GND)
RV(NP, .95, FBy, 'Rg   10 kΩ', 'right')
W(NP, .95, NP, .80)
GND(NP, .80)

# ── section bracket labels ────────────────────────────────────────────────────
BRY = SY + .82   # bracket y = 5.787

# LPF bracket
BCOLOR_LPF = 'steelblue'
ax.plot([.70, 6.50], [BRY, BRY], '-', c=BCOLOR_LPF, lw=.9)
ax.plot([.70, .70],  [BRY - .12, BRY], '-', c=BCOLOR_LPF, lw=.9)
ax.plot([6.50, 6.50], [BRY - .12, BRY], '-', c=BCOLOR_LPF, lw=.9)
ax.text(3.60, BRY + .07, '2-POLE RC  RECONSTRUCTION LPF',
        ha='center', va='bottom', fontsize=9.5, color=BCOLOR_LPF, fontweight='bold')

# Gain stage bracket
BCOLOR_AMP = '#8B4513'
ax.plot([7.60, 11.50], [BRY, BRY], '-', c=BCOLOR_AMP, lw=.9)
ax.plot([7.60, 7.60],  [BRY - .12, BRY], '-', c=BCOLOR_AMP, lw=.9)
ax.plot([11.50, 11.50], [BRY - .12, BRY], '-', c=BCOLOR_AMP, lw=.9)
ax.text(9.55, BRY + .07, 'NON-INVERTING GAIN STAGE  (×3)',
        ha='center', va='bottom', fontsize=9.5, color=BCOLOR_AMP, fontweight='bold')

# ── title ─────────────────────────────────────────────────────────────────────
ax.text(FW / 2, FH - .18,
        '20 m CW TX  —  Key Shaping Chain:  MCP4921 DAC → LPF → Op-Amp → MC1496',
        ha='center', va='top', fontsize=11.5, fontweight='bold')

# ── design notes ──────────────────────────────────────────────────────────────
notes = (
    'R1 = R2 = 1 kΩ,  C1 = C2 = 22 nF   →   each pole fc ≈ 7.2 kHz,  '
    'cascaded −3 dB ≈ 4.5 kHz\n'
    'Rg = 10 kΩ,  Rf = 20 kΩ   →   gain = 3.0,  VOUT(max) = 3.3 × 3.0 = 9.9 V\n'
    'Adjust TRIM to calibrate VOUT(max) = 10.0 V exactly for full MC1496 AGC range.\n'
    'Op-amp supply: use rig +12 V / −8.2 V rails (already present).'
)
ax.text(.40, .85, notes, ha='left', va='top', fontsize=7.5,
        family='monospace', color='#333',
        bbox=dict(boxstyle='round,pad=.40', facecolor='#f8f8f8',
                  edgecolor='#bbb', lw=.8))

# ── save ──────────────────────────────────────────────────────────────────────
fig.savefig(str(OUT), format='pdf', bbox_inches='tight')
print('Saved:', OUT)

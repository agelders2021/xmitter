#!/usr/bin/env python3
"""
MC1496 VCA Buffer — Signal-Flow Schematic (PDF)
Draws MC1496 as a labelled block; component values in blue, net names in green.
Run: python gen_buffer_schematic.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUTPUT = r"C:\Users\AlAnd\Git Backed Projects\xmitter\Documentation\mc1496_buffer_signal_flow.pdf"

# ── canvas ─────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(17, 10))
ax.set_xlim(0, 17)
ax.set_ylim(0, 10)
ax.set_aspect("equal")
ax.axis("off")
fig.patch.set_facecolor("white")

# ── palette ────────────────────────────────────────────────────────────
BLK  = "#111111"
CARR = "#004aad"   # carrier path (blue)
SIG  = "#8b1a1a"   # AGC / signal path (dark red)
OUTP = "#1a6b1a"   # output path (dark green)
BIAS = "#7a5c00"   # bias / supply (olive)
VDD_ = "#cc0000"
VEE_ = "#0000cc"
CVAL = "#1a5faa"   # component-value label
CNET = "#1a8c1a"   # net-name label
LW   = 1.6

# ── primitives ─────────────────────────────────────────────────────────

def W(x1, y1, x2, y2, c=BLK, lw=LW):
    ax.plot([x1, x2], [y1, y2], color=c, lw=lw,
            solid_capstyle="round", solid_joinstyle="round", zorder=3)

def DOT(x, y):
    ax.plot(x, y, "o", ms=4.5, mfc=BLK, mec=BLK, zorder=7)

def GND(x, y, s=0.14):
    W(x, y, x, y - s * 0.6)
    for i, f in enumerate([1.0, 0.65, 0.35]):
        yy = y - s * 0.6 - i * s * 0.55
        W(x - s * f, yy, x + s * f, yy)

def VDD_PWR(x, y, label="+12 V"):
    ax.annotate("", xy=(x, y + 0.32), xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=VDD_, lw=2.1))
    ax.text(x, y + 0.38, label, ha="center", va="bottom",
            fontsize=7.5, color=VDD_, fontweight="bold", zorder=6)

def VEE_PWR(x, y, label="−8.2 V"):
    ax.annotate("", xy=(x, y - 0.32), xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=VEE_, lw=2.1))
    ax.text(x, y - 0.38, label, ha="center", va="top",
            fontsize=7.5, color=VEE_, fontweight="bold", zorder=6)

def NETLBL(x, y, txt, angle=0):
    ax.text(x, y, txt, ha="center", va="center", fontsize=7.5,
            color=CNET, fontstyle="italic", rotation=angle, zorder=6,
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))

# Resistor helpers — BW=body-width, BH=body-height, LD=lead-length
BW, BH, LD = 0.44, 0.22, 0.15
VBW, VBH   = 0.22, 0.40

def RH(cx, cy, name="", val="", c=BLK):
    """Horizontal resistor centred at (cx, cy). Returns (left_x, right_x)."""
    rect = plt.Rectangle((cx - BW/2, cy - BH/2), BW, BH,
                          fc="white", ec=c, lw=1.3, zorder=5)
    ax.add_patch(rect)
    W(cx - BW/2 - LD, cy, cx - BW/2, cy, c, 1.3)
    W(cx + BW/2, cy, cx + BW/2 + LD, cy, c, 1.3)
    if name: ax.text(cx, cy + BH/2 + 0.05, name, ha="center", va="bottom",
                     fontsize=6.5, color=c, zorder=6)
    if val:  ax.text(cx, cy - BH/2 - 0.05, val, ha="center", va="top",
                     fontsize=6.5, color=CVAL, zorder=6)
    return cx - BW/2 - LD, cx + BW/2 + LD   # left_x, right_x

def RV(cx, cy, name="", val="", c=BLK):
    """Vertical resistor centred at (cx, cy). Returns (bot_y, top_y)."""
    rect = plt.Rectangle((cx - VBW/2, cy - VBH/2), VBW, VBH,
                          fc="white", ec=c, lw=1.3, zorder=5)
    ax.add_patch(rect)
    W(cx, cy - VBH/2 - LD, cx, cy - VBH/2, c, 1.3)
    W(cx, cy + VBH/2, cx, cy + VBH/2 + LD, c, 1.3)
    if name: ax.text(cx + VBW/2 + 0.07, cy + 0.12, name, ha="left",
                     va="center", fontsize=6.5, color=c, zorder=6)
    if val:  ax.text(cx - VBW/2 - 0.07, cy - 0.12, val, ha="right",
                     va="center", fontsize=6.5, color=CVAL, zorder=6)
    return cy - VBH/2 - LD, cy + VBH/2 + LD   # bot_y, top_y

def CAP_H(cx, cy, name="", val=""):
    """Horizontal capacitor."""
    G, PH = 0.07, 0.24
    W(cx - 0.38, cy, cx - G, cy, BLK, 1.6)
    W(cx + G, cy, cx + 0.38, cy, BLK, 1.6)
    W(cx - G, cy - PH/2, cx - G, cy + PH/2, BLK, 2.8)
    W(cx + G, cy - PH/2, cx + G, cy + PH/2, BLK, 2.8)
    if name: ax.text(cx, cy + PH/2 + 0.1, name, ha="center", va="bottom",
                     fontsize=6.5, color=BLK, zorder=6)
    if val:  ax.text(cx, cy - PH/2 - 0.1, val, ha="center", va="top",
                     fontsize=6.5, color=CVAL, zorder=6)
    return cx - 0.38, cx + 0.38

def CAP_V(cx, cy, name="", val=""):
    """Vertical capacitor."""
    G, PW = 0.07, 0.24
    W(cx, cy - 0.34, cx, cy - G, BLK, 1.6)
    W(cx, cy + G, cx, cy + 0.34, BLK, 1.6)
    W(cx - PW/2, cy - G, cx + PW/2, cy - G, BLK, 2.8)
    W(cx - PW/2, cy + G, cx + PW/2, cy + G, BLK, 2.8)
    if name: ax.text(cx + PW/2 + 0.1, cy, name, ha="left",
                     va="center", fontsize=6.5, color=BLK, zorder=6)
    if val:  ax.text(cx - PW/2 - 0.1, cy, val, ha="right",
                     va="center", fontsize=6.5, color=CVAL, zorder=6)
    return cy - 0.34, cy + 0.34

def AC_SRC(cx, cy, name="", val=""):
    circ = plt.Circle((cx, cy), 0.30, fc="white", ec=CARR, lw=1.8, zorder=5)
    ax.add_patch(circ)
    t = np.linspace(-np.pi, np.pi, 60)
    ax.plot(cx + 0.16*t/np.pi, cy + 0.13*np.sin(t), c=CARR, lw=1.2, zorder=6)
    if name: ax.text(cx, cy - 0.46, name, ha="center", va="top",
                     fontsize=7.5, color=CARR, fontweight="bold", zorder=6)
    if val:  ax.text(cx, cy - 0.68, val, ha="center", va="top",
                     fontsize=6.5, color=CARR, zorder=6)

def DC_SRC(cx, cy, name="", val=""):
    circ = plt.Circle((cx, cy), 0.30, fc="white", ec=SIG, lw=1.8, zorder=5)
    ax.add_patch(circ)
    ax.plot([cx - 0.14, cx + 0.14], [cy + 0.09, cy + 0.09], c=SIG, lw=2.2, zorder=6)
    ax.plot([cx - 0.08, cx + 0.08], [cy - 0.09, cy - 0.09], c=SIG, lw=1.3, zorder=6)
    if name: ax.text(cx, cy - 0.46, name, ha="center", va="top",
                     fontsize=7.5, color=SIG, fontweight="bold", zorder=6)
    if val:  ax.text(cx, cy - 0.68, val, ha="center", va="top",
                     fontsize=6.5, color=SIG, zorder=6)

# ══════════════════════════════════════════════════════════════════
# IC BLOCK
# ══════════════════════════════════════════════════════════════════
IC_CX, IC_CY = 8.5, 4.9
IC_W,  IC_H  = 3.0, 5.4
IL = IC_CX - IC_W/2   # 7.0
IR = IC_CX + IC_W/2   # 10.0
IT = IC_CY + IC_H/2   # 7.6
IB = IC_CY - IC_H/2   # 2.2
STUB = 0.42            # pin stub outside IC

ic_body = plt.Rectangle((IL, IB), IC_W, IC_H,
                         fc="#fffde7", ec=BLK, lw=2.6, zorder=2)
ax.add_patch(ic_body)

ax.text(IC_CX, IC_CY + 1.05, "MC1496", ha="center", va="center",
        fontsize=14, fontweight="bold", color=BLK, zorder=5)
ax.text(IC_CX, IC_CY + 0.52, "Gilbert Cell VCA", ha="center", va="center",
        fontsize=9, color="#444", zorder=5)
ax.text(IC_CX, IC_CY + 0.05, "Balanced Modulator", ha="center", va="center",
        fontsize=8, color="#666", zorder=5)
ax.text(IC_CX, IC_CY - 0.55, "✕", ha="center", va="center",
        fontsize=36, color="#cccc88", alpha=0.6, zorder=3)

# dashed divider separating signal port (top) from carrier port (middle)
ax.plot([IL, IR], [IC_CY + 0.35, IC_CY + 0.35],
        c="#cccc99", lw=0.9, ls="--", zorder=3)

# ── pin Y coordinates ──────────────────────────────────────────────
SIG_P_Y   = IT - 0.70   # 6.90
SIG_N_Y   = IT - 1.35   # 6.25
CAR_P_Y   = IC_CY + 0.15  # 5.05  (just above dashed divider line)
CAR_N_Y   = IC_CY - 0.55  # 4.35
VCC_Y     = IC_CY - 1.50  # 3.40
BIAS_Y    = IB + 0.52      # 2.72

OUT_P_Y   = (SIG_P_Y + SIG_N_Y) / 2   # 6.575
OUT_N_Y   = (CAR_P_Y + CAR_N_Y) / 2   # 4.700
VEE_Y     = VCC_Y                      # 3.40
GAIN_RE_Y = BIAS_Y                     # 2.72

# ── pin stubs + IC-side labels ─────────────────────────────────────
def LEFT_PIN(y, lbl, c):
    W(IL, y, IL - STUB, y, c)
    ax.text(IL + 0.1, y, lbl, ha="left", va="center",
            fontsize=7, color=c, zorder=5)
    return IL - STUB          # external attach x

def RIGHT_PIN(y, lbl, c):
    W(IR, y, IR + STUB, y, c)
    ax.text(IR - 0.1, y, lbl, ha="right", va="center",
            fontsize=7, color=c, zorder=5)
    return IR + STUB          # external attach x

L_SIG_P  = LEFT_PIN(SIG_P_Y,  "SIG_P ①", SIG)
L_SIG_N  = LEFT_PIN(SIG_N_Y,  "SIG_N ②", SIG)
L_CAR_P  = LEFT_PIN(CAR_P_Y,  "CAR_P ③", CARR)
L_CAR_N  = LEFT_PIN(CAR_N_Y,  "CAR_N ④", CARR)
L_VCC    = LEFT_PIN(VCC_Y,    "VCC ⑦",   VDD_)
L_BIAS   = LEFT_PIN(BIAS_Y,   "BIAS ⑨",  BIAS)

R_OUT_P  = RIGHT_PIN(OUT_P_Y,   "⑤ OUT_P", OUTP)
R_OUT_N  = RIGHT_PIN(OUT_N_Y,   "⑥ OUT_N", OUTP)
R_VEE    = RIGHT_PIN(VEE_Y,     "⑧ VEE",   VEE_)
R_GAIN   = RIGHT_PIN(GAIN_RE_Y, "⑩ GAIN_RE", BIAS)

# ══════════════════════════════════════════════════════════════════
# CARRIER INPUT PATH  (blue)
# V_Q1S → CC_CAR → car_p  ;  car_n → CCAR_N → GND
# ══════════════════════════════════════════════════════════════════
# V_Q1S source centred between CAR_P and CAR_N
VS_Y = (CAR_P_Y + CAR_N_Y) / 2   # 4.70
VS_X = 1.5
AC_SRC(VS_X, VS_Y, "V_Q1S", "0.378 V / 14.175 MHz")
W(VS_X, VS_Y - 0.30, VS_X, VS_Y - 0.62, CARR)
GND(VS_X, VS_Y - 0.62)

# output wire from source → CC_CAR
CC_X = 3.10
W(VS_X + 0.30, VS_Y, CC_X - 0.38, VS_Y, CARR)
CAP_H(CC_X, VS_Y, "CC_CAR", "10 nF")

# after cap, jog up to CAR_P level (push JOG_X right so it clears NODE_X)
CC_RIGHT = CC_X + 0.38
JOG_X = CC_RIGHT + 0.65   # 4.13 — well right of NODE_X (~3.72)
W(CC_RIGHT, VS_Y, JOG_X, VS_Y, CARR)
W(JOG_X, VS_Y, JOG_X, CAR_P_Y, CARR)
W(JOG_X, CAR_P_Y, L_CAR_P, CAR_P_Y, CARR)
NETLBL((JOG_X + L_CAR_P)/2, CAR_P_Y + 0.19, "car_p")

# CAR_N: stub exits IC left → wire left → CCAR_N bypass cap → GND
CN_X = 4.55   # right of JOG_X to avoid visual clutter
W(L_CAR_N, CAR_N_Y, CN_X, CAR_N_Y, CARR)
W(CN_X, CAR_N_Y, CN_X, CAR_N_Y - 0.45, CARR)
CAP_V(CN_X, CAR_N_Y - 0.75, "CCAR_N", "100 nF")
W(CN_X, CAR_N_Y - 1.09, CN_X, CAR_N_Y - 1.35, CARR)
GND(CN_X, CAR_N_Y - 1.35)
NETLBL((L_CAR_N + CN_X)/2, CAR_N_Y + 0.19, "car_n")

# ══════════════════════════════════════════════════════════════════
# AGC / SIGNAL CONTROL  (dark red)
# V_AGC → R_SCALE1 → node → R_SCALE2 → GND
#               node → SIG_N (IC left pin)
# SIG_P → R_SIG_P → GND
# ══════════════════════════════════════════════════════════════════
# V_AGC: placed at same y as SIG_N for a clean horizontal run
VAGC_X = 1.5
VAGC_Y = SIG_N_Y   # 6.25
DC_SRC(VAGC_X, VAGC_Y, "V_AGC", "0–10 V DC")
W(VAGC_X, VAGC_Y - 0.30, VAGC_X, VAGC_Y - 0.62, SIG)
GND(VAGC_X, VAGC_Y - 0.62)

# R_SCALE1 horizontal
RS1_X = 3.05
W(VAGC_X + 0.30, VAGC_Y, RS1_X - BW/2 - LD, VAGC_Y, SIG)
RH(RS1_X, VAGC_Y, "R_SCALE1", "100 kΩ", SIG)

# junction node
NODE_X = RS1_X + BW/2 + LD + 0.30   # ~3.94
W(RS1_X + BW/2 + LD, VAGC_Y, NODE_X, VAGC_Y, SIG)
DOT(NODE_X, VAGC_Y)

# R_SCALE2 vertical (down to GND)
RS2_CY = VAGC_Y - 0.65   # centre
W(NODE_X, VAGC_Y, NODE_X, RS2_CY + VBH/2 + LD, SIG)
RV(NODE_X, RS2_CY, "R_SCALE2", "5.1 kΩ", SIG)
W(NODE_X, RS2_CY - VBH/2 - LD, NODE_X, RS2_CY - 0.70, SIG)
GND(NODE_X, RS2_CY - 0.70)

# sig_n wire: from junction → right → IC SIG_N pin
W(NODE_X, VAGC_Y, L_SIG_N, VAGC_Y, SIG)
# If VAGC_Y == SIG_N_Y, this is already at the right height; direct to IC:
# (they are equal by design)
NETLBL((NODE_X + L_SIG_N)/2, VAGC_Y + 0.20, "sig_n")

# R_SIG_P: SIG_P pin → left stub exit (L_SIG_P) → short wire left → R_SIG_P → GND
# Place R_SIG_P above the IC (between SIG_P_Y and the top of the figure)
# Route: from L_SIG_P at y=SIG_P_Y, go UP to y=SIG_P_Y+0.65, then R_SIG_P vertical
RSP_CX = L_SIG_P   # same x as SIG_P stub end = IL - STUB = 6.58
RSP_CY = SIG_P_Y + 0.65
W(L_SIG_P, SIG_P_Y, RSP_CX, RSP_CY - VBH/2 - LD, SIG)
RV(RSP_CX, RSP_CY, "R_SIG_P", "10 kΩ", SIG)
# Single-bar supply indicator for GND (avoids downward GND symbol pointing into IC area)
GND_BAR_Y = RSP_CY + VBH/2 + LD + 0.28
W(RSP_CX, RSP_CY + VBH/2 + LD, RSP_CX, GND_BAR_Y, SIG)
W(RSP_CX - 0.20, GND_BAR_Y, RSP_CX + 0.20, GND_BAR_Y, SIG, 2.2)
ax.text(RSP_CX + 0.25, GND_BAR_Y, "GND", ha="left", va="center",
        fontsize=7.5, color=SIG, fontweight="bold", zorder=6)
NETLBL(RSP_CX + 0.55, SIG_P_Y + 0.10, "sig_p")

# ══════════════════════════════════════════════════════════════════
# OUTPUT PATH  (dark green)
# OUT_P → R_LOAD_P → VDD rail
# OUT_N → R_LOAD_N → VDD rail
# ══════════════════════════════════════════════════════════════════
RL_X     = 12.40   # centre of load resistors
VDD_RAIL = 13.60   # x of VDD vertical rail
VDD_TOP  = 8.20    # y of VDD rail top

# OUT_P
W(R_OUT_P, OUT_P_Y, RL_X - BW/2 - LD, OUT_P_Y, OUTP)
RH(RL_X, OUT_P_Y, "R_LOAD_P", "3.9 kΩ", OUTP)
W(RL_X + BW/2 + LD, OUT_P_Y, VDD_RAIL, OUT_P_Y, OUTP)
W(VDD_RAIL, OUT_P_Y, VDD_RAIL, VDD_TOP, OUTP)
DOT(VDD_RAIL, OUT_P_Y)

# OUT_N
W(R_OUT_N, OUT_N_Y, RL_X - BW/2 - LD, OUT_N_Y, OUTP)
RH(RL_X, OUT_N_Y, "R_LOAD_N", "3.9 kΩ", OUTP)
W(RL_X + BW/2 + LD, OUT_N_Y, VDD_RAIL, OUT_N_Y, OUTP)
DOT(VDD_RAIL, OUT_N_Y)

# VDD power arrow on rail
VDD_PWR(VDD_RAIL, VDD_TOP, "+12 V  (VDD)")

# net labels
NETLBL((R_OUT_P + RL_X)/2, OUT_P_Y + 0.19, "out_p")
NETLBL((R_OUT_N + RL_X)/2, OUT_N_Y - 0.19, "out_n")

# ══════════════════════════════════════════════════════════════════
# VCC / VEE SUPPLY CONNECTIONS AT IC PINS
# ══════════════════════════════════════════════════════════════════
# VCC left pin: wire left then arrow up (VDD)
VCC_TIE_X = L_VCC - 0.45
W(L_VCC, VCC_Y, VCC_TIE_X, VCC_Y, VDD_)
VDD_PWR(VCC_TIE_X, VCC_Y, "VDD")

# VEE right pin: wire right then arrow down (VEE)
VEE_TIE_X = R_VEE + 0.45
W(R_VEE, VEE_Y, VEE_TIE_X, VEE_Y, VEE_)
VEE_PWR(VEE_TIE_X, VEE_Y, "VEE  −8.2 V")

# ══════════════════════════════════════════════════════════════════
# BIAS NETWORK  (olive)
# BIAS pin → R_BIAS → VEE
# GAIN_RE pin → R_RE → VEE
# ══════════════════════════════════════════════════════════════════
# R_BIAS: to the left of IC
RBIAS_X = 5.20
W(L_BIAS, BIAS_Y, RBIAS_X + BW/2 + LD, BIAS_Y, BIAS)
RH(RBIAS_X, BIAS_Y, "R_BIAS", "1 kΩ", BIAS)
W(RBIAS_X - BW/2 - LD, BIAS_Y, RBIAS_X - 0.75, BIAS_Y, BIAS)
W(RBIAS_X - 0.75, BIAS_Y, RBIAS_X - 0.75, BIAS_Y - 0.60, BIAS)
VEE_PWR(RBIAS_X - 0.75, BIAS_Y - 0.60, "VEE")
NETLBL((L_BIAS + RBIAS_X)/2, BIAS_Y + 0.19, "vbias")

# R_RE: to the right of IC
RRE_X = 11.50
W(R_GAIN, GAIN_RE_Y, RRE_X - BW/2 - LD, GAIN_RE_Y, BIAS)
RH(RRE_X, GAIN_RE_Y, "R_RE", "1 kΩ", BIAS)
W(RRE_X + BW/2 + LD, GAIN_RE_Y, RRE_X + 0.75, GAIN_RE_Y, BIAS)
W(RRE_X + 0.75, GAIN_RE_Y, RRE_X + 0.75, GAIN_RE_Y - 0.60, BIAS)
VEE_PWR(RRE_X + 0.75, GAIN_RE_Y - 0.60, "VEE")
NETLBL((R_GAIN + RRE_X)/2, GAIN_RE_Y + 0.19, "vgain")

# ══════════════════════════════════════════════════════════════════
# TITLE + LEGEND + NOTES
# ══════════════════════════════════════════════════════════════════
ax.text(8.5, 9.80, "MC1496 Gilbert-Cell VCA Buffer  —  Signal Flow",
        ha="center", va="top", fontsize=13, fontweight="bold", color=BLK)
ax.text(8.5, 9.45,
        "14.175 MHz  20m CW TX  |  VDD = +12 V   VEE = −8.2 V  "
        "|  V_AGC = 0 V → carrier null (key-up)   V_AGC = 10 V → max gain",
        ha="center", va="top", fontsize=8, color="#444")

# colour legend
legend_x, legend_y = 0.25, 9.40
for label, clr in [
    ("Carrier RF path (14.175 MHz)", CARR),
    ("AGC control path", SIG),
    ("Output path", OUTP),
    ("Bias / supply network", BIAS),
]:
    ax.plot([legend_x, legend_x + 0.35], [legend_y, legend_y], c=clr, lw=2.0)
    ax.text(legend_x + 0.45, legend_y, label, ha="left", va="center",
            fontsize=7, color=clr)
    legend_y -= 0.28

# Notes box (bottom-left)
notes = (
    "Circuit notes:\n"
    "• V_Q1S: J310 source-follower output into 14.175 MHz carrier port\n"
    "• AGC divider: R_SCALE1 (100 kΩ) + R_SCALE2 (5.1 kΩ) → 4.85 %\n"
    "   V_AGC = 10 V  →  485 mV at SIG_N  (within MC1496 500 mV linear range)\n"
    "• Simulated output: ~3.6 Vpp each side at max gain with 3.9 kΩ loads\n"
    "• Hardware: replace R_LOAD_P/N with 100 µH RFC + FT37-43 bifilar T1 (1:1)\n"
    "• VEE = −8.2 V from 1N4738A zener regulated off grid-bias rail"
)
ax.text(0.20, 2.15, notes, ha="left", va="top", fontsize=7, color="#333",
        fontfamily="monospace",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f7f7f7", ec="#999", alpha=0.95, zorder=5))

# ── save ───────────────────────────────────────────────────────────
plt.tight_layout(pad=0.2)
fig.savefig(OUTPUT, format="pdf", bbox_inches="tight", dpi=150)
print(f"Saved: {OUTPUT}")

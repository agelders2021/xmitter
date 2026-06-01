"""
Q2 Stage schematic — 20 m leveled keyed buffer
Draws the full Q2 VGA + tank + T1 + leveling loop circuit using schemdraw.
Outputs Documentation/Q2-stage-schematic.pdf
"""

import schemdraw
import schemdraw.elements as elm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import matplotlib.lines as mlines
import numpy as np

# ── page layout ──────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 17))
ax = fig.add_subplot(111)
ax.set_aspect("equal")
ax.axis("off")
fig.patch.set_facecolor("white")

# ── helper draw functions ────────────────────────────────────────────────────
def wire(x0, y0, x1, y1, lw=1.2):
    ax.plot([x0, x1], [y0, y1], "k-", lw=lw)

def dot(x, y, r=0.07):
    ax.add_patch(plt.Circle((x, y), r, color="k"))

def label(x, y, txt, ha="center", va="center", fs=7.5, color="k", style="normal"):
    ax.text(x, y, txt, ha=ha, va=va, fontsize=fs, color=color, style=style,
            fontfamily="monospace")

def net_label(x, y, txt, side="right", fs=6.5):
    ha = "left" if side == "right" else "right"
    dx = 0.12 if side == "right" else -0.12
    ax.text(x + dx, y, txt, ha=ha, va="center", fontsize=fs,
            color="#0055aa", fontfamily="monospace", style="italic")

def box_comp(cx, cy, w, h, txt, val, color="#ddeeFF"):
    rect = mpatches.FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                                   boxstyle="round,pad=0.05",
                                   facecolor=color, edgecolor="k", lw=1.0)
    ax.add_patch(rect)
    label(cx, cy + 0.10, txt, fs=7.5)
    label(cx, cy - 0.13, val, fs=6.5, color="#333333")

def resistor(x0, y0, x1, y1, ref, val, label_side="right"):
    """Horizontal or vertical resistor as zigzag."""
    horiz = abs(y1 - y0) < 0.01
    if horiz:
        cx, cy = (x0 + x1) / 2, y0
        segs = 6
        w = abs(x1 - x0)
        zw = w * 0.7
        zh = 0.18
        xs = np.linspace(cx - zw/2, cx + zw/2, segs + 1)
        ys = [cy + (zh if i % 2 == 0 else -zh) for i in range(segs + 1)]
        ax.plot([x0, xs[0]], [y0, cy], "k-", lw=1.2)
        ax.plot(xs, ys, "k-", lw=1.2)
        ax.plot([xs[-1], x1], [cy, y0], "k-", lw=1.2)
        if label_side == "top":
            label(cx, cy + 0.35, ref, fs=7)
            label(cx, cy + 0.20, val, fs=6.5, color="#333333")
        else:
            label(cx, cy - 0.35, ref, fs=7)
            label(cx, cy - 0.20, val, fs=6.5, color="#333333")
    else:
        cy_m = (y0 + y1) / 2
        h = abs(y1 - y0)
        zh = h * 0.7
        zw = 0.18
        ys = np.linspace(cy_m - zh/2, cy_m + zh/2, 7)
        xs = [x0 + (zw if i % 2 == 0 else -zw) for i in range(7)]
        ax.plot([x0, x0], [y0, ys[0]], "k-", lw=1.2)
        ax.plot(xs, ys, "k-", lw=1.2)
        ax.plot([x0, x0], [ys[-1], y1], "k-", lw=1.2)
        if label_side == "right":
            label(x0 + 0.55, cy_m, f"{ref}\n{val}", fs=6.5)
        else:
            label(x0 - 0.55, cy_m, f"{ref}\n{val}", fs=6.5)

def capacitor(x0, y0, x1, y1, ref, val, label_side="right"):
    """Horizontal or vertical capacitor."""
    horiz = abs(y1 - y0) < 0.01
    if horiz:
        cx = (x0 + x1) / 2
        gap = 0.13
        ax.plot([x0, cx - gap], [y0, y0], "k-", lw=1.2)
        ax.plot([cx + gap, x1], [y0, y0], "k-", lw=1.2)
        ax.plot([cx - gap, cx - gap], [y0 - 0.22, y0 + 0.22], "k-", lw=2.0)
        ax.plot([cx + gap, cx + gap], [y0 - 0.22, y0 + 0.22], "k-", lw=2.0)
        label(cx, y0 + 0.40, ref, fs=7)
        label(cx, y0 + 0.25, val, fs=6.5, color="#333333")
    else:
        cy = (y0 + y1) / 2
        gap = 0.13
        ax.plot([x0, x0], [y0, cy - gap], "k-", lw=1.2)
        ax.plot([x0, x0], [cy + gap, y1], "k-", lw=1.2)
        ax.plot([x0 - 0.22, x0 + 0.22], [cy - gap, cy - gap], "k-", lw=2.0)
        ax.plot([x0 - 0.22, x0 + 0.22], [cy + gap, cy + gap], "k-", lw=2.0)
        if label_side == "right":
            label(x0 + 0.55, cy, f"{ref}  {val}", fs=6.5)
        else:
            label(x0 - 0.55, cy, f"{ref}  {val}", fs=6.5)

def inductor(x0, y0, x1, y1, ref, val, label_side="right", n_bumps=5):
    """Vertical inductor as series of arcs."""
    cy_m = (y0 + y1) / 2
    total_h = abs(y1 - y0)
    bump_h = total_h / n_bumps
    r = bump_h / 2
    xs, ys = [], []
    for i in range(n_bumps):
        cy_b = min(y0, y1) + r + i * bump_h
        theta = np.linspace(np.pi, 0, 30)
        xs.extend(x0 + r * np.cos(theta))
        ys.extend(cy_b + r * np.sin(theta))
    ax.plot(xs, ys, "k-", lw=1.5)
    if label_side == "right":
        label(x0 + 0.65, cy_m, f"{ref}\n{val}", fs=6.5)
    else:
        label(x0 - 0.65, cy_m, f"{ref}\n{val}", fs=6.5)

def gnd(x, y):
    for i, w in enumerate([0.30, 0.20, 0.10]):
        ax.plot([x - w, x + w], [y - i*0.12, y - i*0.12], "k-", lw=1.2)

def vdd(x, y, label_txt="+12V VDD"):
    ax.annotate("", xy=(x, y), xytext=(x, y - 0.35),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2))
    label(x, y + 0.18, label_txt, fs=7, color="#880000")

def diode(x0, y0, x1, y1, ref, val):
    """Vertical diode, anode at y0, cathode at y1 (y1 > y0)."""
    cy = (y0 + y1) / 2
    r = 0.18
    ax.plot([x0, x0], [y0, cy - r], "k-", lw=1.2)
    ax.plot([x0, x0], [cy + r, y1], "k-", lw=1.2)
    tri = plt.Polygon([[x0, cy - r], [x0 - r, cy + r], [x0 + r, cy + r]],
                      closed=True, facecolor="k", edgecolor="k")
    ax.add_patch(tri)
    ax.plot([x0 - r, x0 + r], [cy + r, cy + r], "k-", lw=1.5)
    label(x0 + 0.55, cy, f"{ref}\n{val}", fs=6.5)

def opamp(cx, cy, w=1.4, h=1.0, ref="A1", label_txt="TL071"):
    tri = plt.Polygon([[cx - w/2, cy + h/2],
                       [cx - w/2, cy - h/2],
                       [cx + w/2, cy]],
                      closed=True, facecolor="#ffffcc", edgecolor="k", lw=1.2)
    ax.add_patch(tri)
    label(cx - 0.12, cy, label_txt, fs=7)
    label(cx - w/2 + 0.18, cy + h/4, "-", fs=9)
    label(cx - w/2 + 0.18, cy - h/4, "+", fs=9)
    label(cx - w/2 - 0.05, cy + h/4, "p2", fs=6)
    label(cx - w/2 - 0.05, cy - h/4, "p3", fs=6)
    label(cx + w/2 + 0.05, cy, "p6", fs=6, ha="left")
    label(cx, cy + h/2 + 0.18, f"{ref}", fs=7)

# ──────────────────────────────────────────────────────────────────────────────
#  Coordinates (all in "drawing units"; 1 unit ≈ 1 cm on the page)
# ──────────────────────────────────────────────────────────────────────────────

# ── 1.  Input coupling (left side) ───────────────────────────────────────────
#  Q1S at (1.5, 12)
Q1S_x, Q1S_y = 1.5, 12.0
# CC2 horizontal from Q1S to Q2G1
CC2_x = 2.5
Q2G1_x = 3.5
label(Q1S_x - 0.3, Q1S_y + 0.18, "Q1S", fs=7.5, color="#0055aa", ha="right")
wire(Q1S_x, Q1S_y, CC2_x - 0.2, Q1S_y)
capacitor(CC2_x - 0.3, Q1S_y, CC2_x + 0.3, Q1S_y, "CC2", "10n NP0")
wire(CC2_x + 0.3, Q1S_y, Q2G1_x, Q1S_y)

# RG1 from Q2G1 down to GND
RG1_top = Q1S_y
RG1_bot = Q1S_y - 1.6
wire(Q2G1_x, RG1_top, Q2G1_x, RG1_top - 0.2)
resistor(Q2G1_x, RG1_top - 0.2, Q2G1_x, RG1_bot + 0.2, "RG1", "100k")
wire(Q2G1_x, RG1_bot + 0.2, Q2G1_x, RG1_bot)
gnd(Q2G1_x, RG1_bot)
net_label(Q2G1_x + 0.15, Q1S_y - 0.15, "Q2G1", "right")

# ── 2.  Q2 BF961 (drawn as a rectangle with labeled pins) ────────────────────
Q2_cx, Q2_cy = 5.5, 12.0
Q2_w, Q2_h = 1.6, 2.0
box_comp(Q2_cx, Q2_cy, Q2_w, Q2_h,
         "Q2  BF961", "(or 40673 / 3N211)", color="#ddeedd")
# Pin leads
G1_y = Q2_cy + 0.5
G2_y = Q2_cy - 0.5
D_y = Q2_cy + 0.5
S_y = Q2_cy - 0.5
G1_px = Q2_cx - Q2_w/2   # left side
G2_px = Q2_cx - Q2_w/2
D_px  = Q2_cx + Q2_w/2   # right side
S_px  = Q2_cx + Q2_w/2

# G1 wire from Q2G1 junction to Q2 box
wire(Q2G1_x, Q1S_y, G1_px, G1_y)
label(G1_px - 0.15, G1_y, "G1", fs=6.5, ha="right")

# G2 wire — will connect to A1OUT network (drawn later)
wire(G2_px, G2_y, G2_px - 0.5, G2_y)
label(G2_px - 0.15, G2_y, "G2", fs=6.5, ha="right")
G2_net_x = G2_px - 0.5
net_label(G2_net_x - 0.15, G2_y - 0.15, "Q2G2", "left")

# D wire upward to tank
D_net_x = D_px
D_net_y = D_y
wire(D_px, D_y, D_net_x + 0.4, D_net_y)
TANK_x = D_net_x + 0.4
TANK_y = D_net_y
label(D_px + 0.15, D_y, "D", fs=6.5, ha="left")

# S wire down to RS2
S_net_x = S_px
S_net_y = S_y
wire(S_px, S_y, S_net_x + 0.4, S_net_y)
Q2S_x = S_net_x + 0.4
Q2S_y = S_net_y
label(S_px + 0.15, S_y, "S", fs=6.5, ha="left")
net_label(Q2S_x + 0.1, Q2S_y - 0.2, "Q2S", "right")

# ── 3.  RS2 + CS1 (Q2 source bias) ──────────────────────────────────────────
RS2_x = Q2S_x + 0.7
RS2_top = Q2S_y
RS2_bot = Q2S_y - 1.2

wire(Q2S_x, Q2S_y, RS2_x, Q2S_y)
wire(RS2_x, RS2_top, RS2_x, RS2_top - 0.1)
resistor(RS2_x, RS2_top - 0.1, RS2_x, RS2_bot + 0.1, "RS2", "270Ω")
wire(RS2_x, RS2_bot + 0.1, RS2_x, RS2_bot)
gnd(RS2_x, RS2_bot)

# CS1 bypass
CS1_x = RS2_x + 0.9
wire(Q2S_x, Q2S_y, Q2S_x, Q2S_y - 0.1)  # short stub
# connect at Q2S_y level to CS1
wire(Q2S_x + 0.0, Q2S_y, CS1_x, Q2S_y)
dot(Q2S_x + 0.0, Q2S_y)
wire(CS1_x, Q2S_y, CS1_x, Q2S_y - 0.1)
capacitor(CS1_x, Q2S_y - 0.1, CS1_x, Q2S_y - 0.9, "CS1", "10n NP0", "right")
gnd(CS1_x, Q2S_y - 0.9)

# ── 4.  Tank circuit: L1 (primary) + C1a + C1b + bypass caps ─────────────────
# L1 goes from TANK up to VDD. Place L1 to the right of Q2 drain
L1_x = TANK_x + 1.1
L1_bot_y = TANK_y        # = drain level ≈ 12.0
L1_top_y = TANK_y + 3.0  # VDD node

wire(TANK_x, TANK_y, L1_x, TANK_y)
dot(L1_x, TANK_y)  # TANK junction

# L1 inductor upward
inductor(L1_x, L1_bot_y, L1_x, L1_top_y, "L1", "22t T50-6\n1.9µH", "right")

# T1 secondary annotation (drawn over L1)
ax.annotate("T1 secondary\n10+10t CT\n(wound over L1\n same core)",
            xy=(L1_x + 0.3, (L1_bot_y + L1_top_y)/2),
            xytext=(L1_x + 2.2, (L1_bot_y + L1_top_y)/2),
            fontsize=6.5, va="center",
            arrowprops=dict(arrowstyle="->", color="#555555", lw=0.8),
            color="#555555")

# T1 coupling mark (dashed line beside L1)
ax.plot([L1_x - 0.45, L1_x - 0.45],
        [L1_bot_y + 0.3, L1_top_y - 0.3], "k--", lw=0.8, alpha=0.6)
label(L1_x - 0.52, (L1_bot_y + L1_top_y)/2, "T1", fs=7, ha="right")

# VDD at top of L1
vdd(L1_x, L1_top_y, "+12V VDD")

# VDD bypass cap CVDD1 (10n) at cold end
CVDD1_x = L1_x + 0.8
wire(L1_x, L1_top_y, CVDD1_x, L1_top_y)
dot(L1_x, L1_top_y)
wire(CVDD1_x, L1_top_y, CVDD1_x, L1_top_y - 0.2)
capacitor(CVDD1_x, L1_top_y - 0.2, CVDD1_x, L1_top_y - 1.0, "CVDD1", "10n", "right")
gnd(CVDD1_x, L1_top_y - 1.0)

# VDD bulk cap CVDD2 (10µ) next to it
CVDD2_x = CVDD1_x + 0.9
wire(L1_x, L1_top_y, CVDD2_x, L1_top_y)
wire(CVDD2_x, L1_top_y, CVDD2_x, L1_top_y - 0.2)
capacitor(CVDD2_x, L1_top_y - 0.2, CVDD2_x, L1_top_y - 1.0, "CVDD2", "10µ elec", "right")
gnd(CVDD2_x, L1_top_y - 1.0)

# C1a (47p) — from TANK to GND
C1a_x = L1_x + 0.0
C1a_top = TANK_y
C1a_bot = TANK_y - 1.5
wire(L1_x, TANK_y, C1a_x, C1a_top)
wire(C1a_x, C1a_top, C1a_x, C1a_top - 0.1)
capacitor(C1a_x, C1a_top - 0.1, C1a_x, C1a_bot + 0.1, "C1a", "47p NP0", "left")
wire(C1a_x, C1a_bot + 0.1, C1a_x, C1a_bot)
gnd(C1a_x, C1a_bot)
net_label(C1a_x + 0.12, C1a_top, "TANK / Q2D", "right")

# C1b trimmer (20p) adjacent
C1b_x = C1a_x - 1.0
wire(L1_x, TANK_y, C1b_x, TANK_y)
dot(L1_x, TANK_y)
wire(C1b_x, TANK_y, C1b_x, TANK_y - 0.1)
capacitor(C1b_x, TANK_y - 0.1, C1b_x, TANK_y - 1.0, "C1b", "20p trimmer", "left")
gnd(C1b_x, TANK_y - 1.0)

# ── 5.  T1 secondary leads ────────────────────────────────────────────────────
# T1A from upper secondary tap, T1B from lower, T1CT center
T1A_x = L1_x - 0.45   # dashed winding marks
T1A_y = L1_bot_y + 2.2
T1B_y = L1_bot_y + 0.8
T1CT_y = (T1A_y + T1B_y) / 2

# Extend wires rightward off the winding symbol for T1A, CT, T1B
T1_out_x = L1_x + 1.8   # rightward output column (push-pull feeds)

wire(L1_x, T1A_y, T1_out_x, T1A_y)
wire(L1_x, T1CT_y, T1_out_x, T1CT_y)
wire(L1_x, T1B_y, T1_out_x, T1B_y)

net_label(T1_out_x + 0.1, T1A_y, "T1A", "right")
net_label(T1_out_x + 0.1, T1CT_y, "T1CT", "right")
net_label(T1_out_x + 0.1, T1B_y, "T1B", "right")

# Mark center-tap junction
dot(T1_out_x, T1CT_y)

# Grid stoppers — small resistors off T1A and T1B
RGS_x_end = T1_out_x + 2.0
resistor(T1_out_x, T1A_y, T1_out_x + 0.9, T1A_y, "RGS_A", "100Ω", "top")
resistor(T1_out_x, T1B_y, T1_out_x + 0.9, T1B_y, "RGS_B", "100Ω", "top")

# Arrow connectors to 6146B grids
ax.annotate("→ 6146B\n  grid 1",
            xy=(T1_out_x + 0.9, T1A_y),
            xytext=(T1_out_x + 1.4, T1A_y + 0.3),
            fontsize=7, va="center", color="#440000",
            arrowprops=dict(arrowstyle="->", color="#440000", lw=0.8))
ax.annotate("→ 6146B\n  grid 2",
            xy=(T1_out_x + 0.9, T1B_y),
            xytext=(T1_out_x + 1.4, T1B_y - 0.3),
            fontsize=7, va="center", color="#440000",
            arrowprops=dict(arrowstyle="->", color="#440000", lw=0.8))

# T1CT bias scheme box (self-bias option)
T1CT_bias_x = T1_out_x + 0.4
T1CT_bias_gnd = T1CT_y - 1.0
wire(T1_out_x, T1CT_y, T1CT_bias_x, T1CT_y)
# R_GL
wire(T1CT_bias_x, T1CT_y, T1CT_bias_x, T1CT_y - 0.15)
resistor(T1CT_bias_x, T1CT_y - 0.15, T1CT_bias_x, T1CT_bias_gnd + 0.35, "R_GL", "22k", "right")
wire(T1CT_bias_x, T1CT_bias_gnd + 0.35, T1CT_bias_x, T1CT_bias_gnd + 0.15)
# C_GL parallel
CGL_x = T1CT_bias_x + 0.7
wire(T1CT_bias_x, T1CT_y, CGL_x, T1CT_y)
dot(T1CT_bias_x, T1CT_y)
wire(CGL_x, T1CT_y, CGL_x, T1CT_y - 0.15)
capacitor(CGL_x, T1CT_y - 0.15, CGL_x, T1CT_bias_gnd + 0.35, "C_GL", "10n", "right")
wire(CGL_x, T1CT_bias_gnd + 0.35, CGL_x, T1CT_bias_gnd + 0.15)
# Common GND bar
ax.plot([T1CT_bias_x, CGL_x], [T1CT_bias_gnd + 0.15, T1CT_bias_gnd + 0.15], "k-", lw=1.2)
gnd((T1CT_bias_x + CGL_x)/2, T1CT_bias_gnd + 0.15)
label(T1CT_bias_x - 0.3, T1CT_bias_gnd - 0.35,
      "Grid-leak self-bias\n(alt: neg supply to T1CT)", fs=6, style="italic", ha="left")

# ── 6.  Leveling-loop detector ────────────────────────────────────────────────
# Sample T1A through C_DET_IN (1000p), diode D1 to V_DET
DET_x0 = T1_out_x + 0.0
DET_y  = T1A_y
CDET_x = DET_x0 + 0.5
VDET_x = CDET_x + 1.2
VDET_y = DET_y - 2.5

wire(T1_out_x, DET_y, CDET_x - 0.3, DET_y)
dot(T1_out_x, DET_y)
capacitor(CDET_x - 0.3, DET_y, CDET_x + 0.3, DET_y, "CDET_IN", "1000p NP0")
wire(CDET_x + 0.3, DET_y, VDET_x, DET_y)
wire(VDET_x, DET_y, VDET_x, DET_y - 0.6)
diode(VDET_x, DET_y - 0.6, VDET_x, VDET_y + 0.4, "D1", "1N5711")
wire(VDET_x, VDET_y + 0.4, VDET_x, VDET_y)
net_label(VDET_x + 0.1, VDET_y, "V_DET", "right")

# R_BIAS (330k) from VDD to V_DET
RBIAS_x = VDET_x + 1.0
wire(VDET_x, VDET_y, RBIAS_x, VDET_y)
dot(VDET_x, VDET_y)
wire(RBIAS_x, VDET_y, RBIAS_x, VDET_y + 0.2)
resistor(RBIAS_x, VDET_y + 0.2, RBIAS_x, VDET_y + 1.5, "R_BIAS", "330k", "right")
vdd(RBIAS_x, VDET_y + 1.5)

# C_DET_OUT (10n film) from V_DET to GND
CDOUT_x = RBIAS_x + 1.0
wire(VDET_x, VDET_y, CDOUT_x, VDET_y)
wire(CDOUT_x, VDET_y, CDOUT_x, VDET_y - 0.1)
capacitor(CDOUT_x, VDET_y - 0.1, CDOUT_x, VDET_y - 0.9, "CDET_OUT", "10n film", "right")
gnd(CDOUT_x, VDET_y - 0.9)

# ── 7.  TL071 integrator (A1) ─────────────────────────────────────────────────
OA_cx, OA_cy = CDOUT_x + 2.5, VDET_y - 0.0
opamp(OA_cx, OA_cy, 1.6, 1.0, "A1", "TL071")

# R_INT from V_DET to pin 2 (inverting)
RINT_x_start = VDET_x
RINT_y = OA_cy + 0.25   # pin 2 y
wire(VDET_x, VDET_y, VDET_x, RINT_y)
dot(VDET_x, VDET_y)
resistor(VDET_x, RINT_y, OA_cx - 0.8, RINT_y, "R_INT", "100k", "top")
wire(OA_cx - 0.8, RINT_y, OA_cx - 0.8 + 0.0, RINT_y)

# Feedback: C_INT (1µ) + R_FB (470k) from pin 6 to pin 2
A1_out_x = OA_cx + 0.8
A1_in2_x = OA_cx - 0.8
A1_in2_y = OA_cy + 0.25
A1_out_y = OA_cy
# Run feedback above the opamp
FB_top_y = OA_cy + 1.2
wire(A1_out_x, A1_out_y, A1_out_x, FB_top_y)
wire(A1_out_x, FB_top_y, A1_in2_x, FB_top_y)
# split into C_INT and R_FB parallel branches
mid_fb_x = (A1_out_x + A1_in2_x) / 2
# C_INT
CINT_x = mid_fb_x + 0.5
capacitor(A1_in2_x, FB_top_y, CINT_x, FB_top_y, "C_INT", "1µ film")
wire(CINT_x, FB_top_y, A1_out_x, FB_top_y)
# R_FB
RFB_x_mid = mid_fb_x - 0.5
resistor(A1_in2_x, FB_top_y + 0.55, A1_out_x, FB_top_y + 0.55, "R_FB", "470k", "top")
wire(A1_in2_x, FB_top_y, A1_in2_x, FB_top_y + 0.55)
wire(A1_out_x, FB_top_y, A1_out_x, FB_top_y + 0.55)

wire(A1_in2_x, FB_top_y, A1_in2_x, A1_in2_y)

# V_CMD at pin 3 (non-inverting)
VCMD_y = OA_cy - 0.25
wire(OA_cx - 0.8, VCMD_y, OA_cx - 1.4, VCMD_y)
net_label(OA_cx - 1.5, VCMD_y, "V_CMD", "left")
label(OA_cx - 1.7, VCMD_y - 0.2, "(MCP4725 DAC)", fs=6, style="italic", ha="right")

# VDD (pin 7) and GND (pin 4) of A1
wire(OA_cx - 0.0, OA_cy + 0.5 + 0.0, OA_cx, OA_cy + 0.5 + 0.4)
vdd(OA_cx, OA_cy + 0.5 + 0.4, "+12V")
wire(OA_cx - 0.0, OA_cy - 0.5, OA_cx, OA_cy - 0.5 - 0.25)
gnd(OA_cx, OA_cy - 0.5 - 0.25)
label(OA_cx + 0.12, OA_cy + 0.5 + 0.1, "p7", fs=6, ha="left")
label(OA_cx + 0.12, OA_cy - 0.5 - 0.08, "p4", fs=6, ha="left")

# A1OUT wire from pin 6
net_label(A1_out_x + 0.12, A1_out_y, "A1OUT", "right")

# ── 8.  RG2 + CG2 — AGC path to Q2 G2 ───────────────────────────────────────
# A1OUT -> RG2 -> Q2G2
RG2_y = G2_y  # = Q2_cy - 0.5 = 11.5
RG2_x_right = G2_net_x   # left side of RG2, at Q2G2 net

# We need to run A1OUT down and then left to G2 level
A1OUT_junction_x = A1_out_x
A1OUT_junction_y = RG2_y

wire(A1_out_x, A1_out_y, A1_out_x, A1OUT_junction_y)
resistor(A1_out_x, RG2_y, RG2_x_right, RG2_y, "RG2", "10k", "top")
wire(RG2_x_right, RG2_y, G2_net_x, G2_y)
dot(G2_net_x, G2_y)

# CG2 bypass from Q2G2 to GND
CG2_x = G2_net_x - 0.6
wire(G2_net_x, G2_y, CG2_x, G2_y)
wire(CG2_x, G2_y, CG2_x, G2_y - 0.2)
capacitor(CG2_x, G2_y - 0.2, CG2_x, G2_y - 1.0, "CG2", "10n NP0", "left")
gnd(CG2_x, G2_y - 1.0)

# ── 9.  Keying circuit (bottom-left) ─────────────────────────────────────────
KEY_x = OA_cx - 1.4
KEY_y = OA_cy - 1.8

ax.add_patch(mpatches.FancyBboxPatch((KEY_x - 1.2, KEY_y - 0.7), 2.4, 1.4,
             boxstyle="round,pad=0.1",
             facecolor="#fff0e0", edgecolor="#aa6600", lw=1.0))
label(KEY_x, KEY_y + 0.4, "Keying", fs=7.5, color="#aa6600")
label(KEY_x, KEY_y + 0.1, "R_KEY 4.7k  →  V_CMD_RAW", fs=6.5)
label(KEY_x, KEY_y - 0.15, "C_KEY 1µ  →  GND", fs=6.5)
label(KEY_x, KEY_y - 0.40, "~5 ms RC envelope on V_CMD", fs=6, style="italic", color="#666666")
wire(KEY_x, KEY_y + 0.7, KEY_x, VCMD_y)

# ── 10.  Cascode J310 substitute note ────────────────────────────────────────
NOTE_x, NOTE_y = 0.3, 7.0
ax.add_patch(mpatches.FancyBboxPatch((NOTE_x, NOTE_y - 1.5), 6.0, 1.7,
             boxstyle="round,pad=0.1",
             facecolor="#f8f8f8", edgecolor="#888888", lw=0.8))
label(NOTE_x + 3.0, NOTE_y + 0.0, "Cascode J310 substitute (if BF961/40673 unavailable):", fs=7.5, ha="center")
label(NOTE_x + 3.0, NOTE_y - 0.4,
      "Q2a (lower, common-source): G=Q2G1, D=Q2a_D, S→RS2a(270Ω)→GND+CS2a(10n)",
      fs=6.5, ha="center")
label(NOTE_x + 3.0, NOTE_y - 0.8,
      "Q2b (upper, common-gate):  G=V_AGC, D=TANK, S=Q2a_D",
      fs=6.5, ha="center")
label(NOTE_x + 3.0, NOTE_y - 1.2,
      "V_AGC via R_VB(10k) from A1OUT; C_VB(10n) from V_AGC to Q2a_D (RF bypass)",
      fs=6.5, ha="center")

# ── 11.  Title block ─────────────────────────────────────────────────────────
ax.add_patch(mpatches.FancyBboxPatch((0.1, 0.1), 21.8, 1.2,
             boxstyle="square,pad=0.0",
             facecolor="#e8e8e8", edgecolor="k", lw=1.0))
label(11.0, 0.95, "Q2 VGA STAGE — 20 m Leveled Keyed Buffer", fs=12, color="#000000")
label(11.0, 0.55,
      "BF961 (or 40673/3N211) dual-gate MOSFET  ·  T50-6 tank + T1 interstage  ·  TL071 leveling loop",
      fs=8, color="#333333")
label(11.0, 0.25,
      "Companion to: 20m-leveled-keyed-buffer.md  /  Q2-stage-schematic-entry.md",
      fs=7, color="#555555", style="italic")

# ── axis limits ──────────────────────────────────────────────────────────────
ax.set_xlim(-0.5, 22.5)
ax.set_ylim(-0.5, 17.5)

plt.tight_layout(pad=0.3)
out_path = r"C:\Users\AlAnd\Git Backed Projects\xmitter\Documentation\Q2-stage-schematic.pdf"
plt.savefig(out_path, format="pdf", dpi=200, bbox_inches="tight")
print(f"Saved: {out_path}")

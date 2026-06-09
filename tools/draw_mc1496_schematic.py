"""Draw the MC1496 VCA buffer schematic using matplotlib primitives.
Returns a matplotlib Figure suitable for embedding in a PDF."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


# ── Drawing helpers ────────────────────────────────────────────────────────────

LW   = 0.9   # normal wire width
LWH  = 1.4   # heavy line width (IC border, component bodies)
FC   = 'white'
EC   = 'black'
FS   = 7.0   # default font size

def _wire(ax, pts, lw=LW):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color='black', lw=lw, solid_capstyle='round', solid_joinstyle='round')

def _dot(ax, x, y, r=0.05):
    ax.add_patch(patches.Circle((x, y), r, color='black', zorder=5))

def _txt(ax, x, y, s, ha='center', va='center', size=FS, bold=False, color='black', italic=False):
    weight = 'bold' if bold else 'normal'
    style  = 'italic' if italic else 'normal'
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, fontweight=weight,
            fontstyle=style, color=color, zorder=6)

def resistor_h(ax, x1, y, x2, lbl='', la=True):
    """Horizontal zigzag resistor from (x1,y) to (x2,y)."""
    cx, bw = (x1+x2)/2, min(0.55, abs(x2-x1)*0.65)
    _wire(ax, [(x1,y),(cx-bw/2,y)])
    _wire(ax, [(cx+bw/2,y),(x2,y)])
    n = 8
    xs = np.linspace(cx-bw/2, cx+bw/2, n+1)
    ys = [y + (0.10 if i%2==1 else (-0.10 if i%2==0 and i not in (0,n) else y)) for i in range(n+1)]
    ys[0] = ys[-1] = y
    ax.plot(xs, ys, color='black', lw=LW, solid_capstyle='round', solid_joinstyle='round')
    if lbl:
        ax.text(cx, y+(0.22 if la else -0.22), lbl, ha='center',
                va='bottom' if la else 'top', fontsize=6.0)

def resistor_v(ax, x, y1, y2, lbl='', lr=True):
    """Vertical zigzag resistor from (x,y1) to (x,y2)."""
    cy, bh = (y1+y2)/2, min(0.55, abs(y2-y1)*0.65)
    _wire(ax, [(x,y1),(x,cy+bh/2)])
    _wire(ax, [(x,cy-bh/2),(x,y2)])
    n = 8
    ys = np.linspace(cy-bh/2, cy+bh/2, n+1)
    xs = [x + (0.10 if i%2==1 else (-0.10 if i%2==0 and i not in (0,n) else 0)) for i in range(n+1)]
    xs[0] = xs[-1] = x
    ax.plot(xs, ys, color='black', lw=LW, solid_capstyle='round', solid_joinstyle='round')
    if lbl:
        off = 0.28 if lr else -0.28
        ax.text(x+off, cy, lbl, ha='left' if lr else 'right', va='center', fontsize=6.0)

def cap_h(ax, x1, y, x2, lbl='', la=True):
    """Horizontal capacitor."""
    cx, pg, ph = (x1+x2)/2, 0.08, 0.22
    _wire(ax, [(x1,y),(cx-pg/2-0.01,y)])
    _wire(ax, [(cx+pg/2+0.01,y),(x2,y)])
    ax.plot([cx-pg/2,cx-pg/2],[y-ph/2,y+ph/2], color='black', lw=LWH)
    ax.plot([cx+pg/2,cx+pg/2],[y-ph/2,y+ph/2], color='black', lw=LWH)
    if lbl:
        ax.text(cx, y+(0.24 if la else -0.24), lbl, ha='center',
                va='bottom' if la else 'top', fontsize=6.0)

def cap_v(ax, x, y1, y2, lbl='', lr=True):
    """Vertical capacitor."""
    cy, pg, pw = (y1+y2)/2, 0.08, 0.22
    _wire(ax, [(x,y1),(x,cy+pg/2+0.01)])
    _wire(ax, [(x,cy-pg/2-0.01),(x,y2)])
    ax.plot([x-pw/2,x+pw/2],[cy+pg/2,cy+pg/2], color='black', lw=LWH)
    ax.plot([x-pw/2,x+pw/2],[cy-pg/2,cy-pg/2], color='black', lw=LWH)
    if lbl:
        off = 0.28 if lr else -0.28
        ax.text(x+off, cy, lbl, ha='left' if lr else 'right', va='center', fontsize=6.0)

def pot_v(ax, x, ytop, ybot, lbl=''):
    """Vertical potentiometer. Returns wiper point (x,y)."""
    cy, bh, bw = (ytop+ybot)/2, min(0.80, abs(ytop-ybot)*0.6), 0.22
    _wire(ax, [(x,ytop),(x,cy+bh/2)])
    _wire(ax, [(x,cy-bh/2),(x,ybot)])
    ax.add_patch(patches.Rectangle((x-bw/2, cy-bh/2), bw, bh,
                                    ec='black', fc='white', lw=LW, zorder=3))
    # Wiper arrow pointing right into body
    wy = cy
    ax.annotate('', xy=(x+bw/2-0.02, wy), xytext=(x+bw/2+0.35, wy),
                arrowprops=dict(arrowstyle='->', color='black', lw=LW))
    _wire(ax, [(x+bw/2+0.35, wy),(x+bw/2+0.55, wy)])
    if lbl:
        ax.text(x-bw/2-0.08, cy, lbl, ha='right', va='center', fontsize=6.0)
    return (x+bw/2+0.55, wy)

def gnd(ax, x, y):
    _wire(ax, [(x,y),(x,y+0.12)])
    ax.plot([x-0.18,x+0.18],[y,y],   color='black', lw=LWH)
    ax.plot([x-0.12,x+0.12],[y-0.08,y-0.08], color='black', lw=LW+0.3)
    ax.plot([x-0.06,x+0.06],[y-0.16,y-0.16], color='black', lw=LW)

def vdd(ax, x, y, lbl='+12V'):
    _wire(ax, [(x,y),(x,y-0.12)])
    ax.plot([x-0.18,x+0.18],[y,y], color='black', lw=LWH)
    _txt(ax, x, y+0.16, lbl, size=6.5, bold=True)

def vee_sym(ax, x, y, lbl='VEE\n−8.2V'):
    _wire(ax, [(x,y),(x,y+0.12)])
    ax.plot([x-0.18,x+0.18],[y,y], color='black', lw=LWH)
    _txt(ax, x, y-0.08, lbl, size=6.0, bold=True, va='top')

def ac_source(ax, x, y, lbl=''):
    r = 0.32
    ax.add_patch(patches.Circle((x,y), r, ec='black', fc='white', lw=LW, zorder=3))
    t = np.linspace(0, 2*np.pi, 60)
    ax.plot(x+0.18*np.cos(t), y+0.13*np.sin(t), color='black', lw=0.7)
    if lbl:
        _txt(ax, x, y-r-0.14, lbl, size=6.0, va='top')

def dc_source_v(ax, x, ybot, ytop, lbl=''):
    """Vertical DC voltage source: + at top."""
    r = 0.28
    cy = (ybot+ytop)/2
    _wire(ax, [(x,ybot),(x,cy-r)])
    _wire(ax, [(x,cy+r),(x,ytop)])
    ax.add_patch(patches.Circle((x,cy), r, ec='black', fc='white', lw=LW, zorder=3))
    _txt(ax, x, cy+0.07, '+', size=8, bold=True)
    _txt(ax, x, cy-0.10, '−', size=10)
    if lbl:
        _txt(ax, x+r+0.08, cy, lbl, ha='left', size=6.0)


# ── Main schematic function ────────────────────────────────────────────────────

def make_schematic():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)

    # ── IC geometry ───────────────────────────────────────────────────────────
    IC_LX, IC_RX = 6.5, 9.5
    IC_TY, IC_BY = 9.5, 2.0
    STUB = 0.5
    PS = (IC_TY - IC_BY) / 6   # pin spacing = 1.25

    def py(pin):
        if 1 <= pin <= 7:
            return IC_TY - (pin-1)*PS
        return IC_TY - (14-pin)*PS   # pins 8–14

    # IC rectangle
    ax.add_patch(patches.FancyBboxPatch((IC_LX, IC_BY), IC_RX-IC_LX, IC_TY-IC_BY,
                                         boxstyle='square,pad=0', ec='black', fc='#F4F6FF', lw=LWH))
    _txt(ax, (IC_LX+IC_RX)/2, (IC_TY+IC_BY)/2+0.18, 'MC1496', size=12, bold=True, color='#1A1A7A')
    _txt(ax, (IC_LX+IC_RX)/2, (IC_TY+IC_BY)/2-0.22, 'DIP-14', size=8.5, color='#444444')
    # Pin-1 notch
    ax.add_patch(patches.Arc((IC_LX, IC_TY), 0.28, 0.28, theta1=0, theta2=180,
                              color='black', lw=LW))

    # Pin stubs and internal labels
    left_names  = {1:'SIG_P', 2:'G.ADJ', 3:'G.ADJ', 4:'SIG_N',
                   5:'BIAS',  6:'OUT_P', 7:'NC'}
    right_names = {14:'VEE',   13:'NC',   12:'OUT_N', 11:'NC',
                   10:'CAR_N', 9:'NC',    8:'CAR_P'}
    for p, name in left_names.items():
        y = py(p)
        _wire(ax, [(IC_LX-STUB, y),(IC_LX, y)], lw=0.8)
        _txt(ax, IC_LX-STUB-0.06, y, str(p), ha='right', size=6, color='#555')
        _txt(ax, IC_LX+0.10, y, name, ha='left', size=6.5)
    for p, name in right_names.items():
        y = py(p)
        _wire(ax, [(IC_RX, y),(IC_RX+STUB, y)], lw=0.8)
        _txt(ax, IC_RX+STUB+0.06, y, str(p), ha='left', size=6, color='#555')
        _txt(ax, IC_RX-0.10, y, name, ha='right', size=6.5)

    lx = IC_LX - STUB   # left  stub endpoint x = 6.0
    rx = IC_RX + STUB   # right stub endpoint x = 10.0

    # ── PIN 1 (SIG_P, y=9.5) — R_SIG_P to GND; R_INJ1 from DAC_NULL_P ────────
    p1y = py(1)   # 9.5
    _wire(ax, [(lx, p1y),(5.5, p1y)])
    _dot(ax, 5.5, p1y)
    resistor_h(ax, 5.5, p1y, 4.6, lbl='R_SIG_P\n10kΩ', la=True)
    _wire(ax, [(4.6, p1y),(4.3, p1y),(4.3, p1y-0.18)])
    gnd(ax, 4.3, p1y-0.18)

    # ── PINS 2 & 3 (G.ADJ, y=8.25 / 7.0) — R_RE between pins 2 and 3 ─────
    p2y, p3y = py(2), py(3)   # 8.25, 7.0
    re_x = 5.5
    _wire(ax, [(lx, p2y),(re_x, p2y)])
    _wire(ax, [(lx, p3y),(re_x, p3y)])
    resistor_v(ax, re_x, p2y, p3y, lbl='R_RE\n1kΩ', lr=False)
    _dot(ax, re_x, p2y); _dot(ax, re_x, p3y)

    # ── PIN 4 (SIG_N, y=5.75) — R_SCALE2 down, R_SCALE1 left, null branch ───
    p4y = py(4)   # 5.75
    _wire(ax, [(lx, p4y),(5.5, p4y)])
    _dot(ax, 5.5, p4y)

    # R_SCALE2 down to GND
    resistor_v(ax, 5.5, p4y, p4y-1.0, lbl='R_SCALE2\n5.1kΩ', lr=True)
    gnd(ax, 5.5, p4y-1.0)

    # R_SCALE1 left: junction at 3.8, then to V_AGC
    _wire(ax, [(5.5, p4y),(3.8, p4y)])
    _dot(ax, 3.8, p4y)
    resistor_h(ax, 3.8, p4y, 2.6, lbl='R_SCALE1  100kΩ', la=True)
    # V_AGC DC source (vertical, + at top connecting to R_SCALE1 left end)
    _wire(ax, [(2.6, p4y),(2.1, p4y),(2.1, p4y-0.0)])  # horizontal to source top
    dc_source_v(ax, 2.1, p4y-0.9, p4y, lbl='V_AGC 10V\n(TL071 sim)')
    gnd(ax, 2.1, p4y-0.9)

    # ── PIN 5 (BIAS, y=4.5) — R_BIAS to GND ─────────────────────────────────
    p5y = py(5)   # 4.5
    _wire(ax, [(lx, p5y),(5.5, p5y)])
    resistor_h(ax, 5.5, p5y, 4.5, lbl='R_BIAS 6.8kΩ', la=True)
    _wire(ax, [(4.5, p5y),(4.1, p5y),(4.1, p5y-0.35)])
    gnd(ax, 4.1, p5y-0.35)

    # ── PIN 6 (OUT_P, y=3.25) — R_LOAD_P to VDD; output label ───────────────
    p6y = py(6)   # 3.25
    _wire(ax, [(lx, p6y),(5.2, p6y)])
    _dot(ax, 5.2, p6y)
    _txt(ax, 5.1, p6y+0.12, '→ Driver P2', ha='right', size=7,
         bold=True, color='#006600')
    # R_LOAD_P vertical at x=4.8 up to VDD
    _wire(ax, [(5.2, p6y),(4.8, p6y)])
    resistor_v(ax, 4.8, p6y, p6y+1.5, lbl='R_LOAD_P\n3.9kΩ', lr=False)
    vdd(ax, 4.8, p6y+1.5)

    # ── PIN 7 (NC) — already labelled via left_names ─────────────────────────

    # ── DIGITAL NULL NETWORK — R_INJ1 (pin 1) and R_INJ2 (pin 4) ─────────────
    # R_INJ1: DAC_NULL_P → pin 1 (SIG_P) at p1y
    resistor_h(ax, 3.0, p1y, 5.5, lbl='R_INJ1\n330kΩ', la=False)
    _dot(ax, 5.5, p1y)
    _wire(ax, [(2.5, p1y),(3.0, p1y)])
    _txt(ax, 2.4, p1y, 'DAC_NULL_P', ha='right', size=6.5, bold=True, color='#004488')

    # R_INJ2: DAC_NULL_N → pin 4 (SIG_N) at p4y
    resistor_h(ax, 1.8, p4y, 3.8, lbl='R_INJ2\n330kΩ', la=False)
    _dot(ax, 3.8, p4y)
    _wire(ax, [(1.3, p4y),(1.8, p4y)])
    _txt(ax, 1.2, p4y, 'DAC_NULL_N', ha='right', size=6.5, bold=True, color='#004488')

    # ── RIGHT SIDE ────────────────────────────────────────────────────────────

    # PIN 14 (VEE, y=9.5)
    p14y = py(14)   # 9.5
    _wire(ax, [(rx, p14y),(rx+0.35, p14y)])
    vee_sym(ax, rx+0.35, p14y)

    # PINS 13, 11, 9 (NC) — no connections

    # PIN 12 (OUT_N, y=7.0) — R_LOAD_N to VDD; output label ──────────────────
    p12y = py(12)   # 7.0
    _wire(ax, [(rx, p12y),(10.8, p12y)])
    _dot(ax, 10.8, p12y)
    _txt(ax, 10.9, p12y+0.12, 'Driver P4 →', ha='left', size=7,
         bold=True, color='#006600')
    # R_LOAD_N vertical at x=11.2 up to VDD
    _wire(ax, [(10.8, p12y),(11.2, p12y)])
    resistor_v(ax, 11.2, p12y, p12y+1.5, lbl='R_LOAD_N\n3.9kΩ', lr=True)
    vdd(ax, 11.2, p12y+1.5)

    # PIN 10 (CAR_N, y=4.5) — CCAR_N then GND ────────────────────────────────
    p10y = py(10)   # 4.5
    cap_h(ax, rx, p10y, rx+1.0, lbl='CCAR_N\n100nF', la=True)
    _wire(ax, [(rx+1.0, p10y),(rx+1.15, p10y),(rx+1.15, p10y-0.2)])
    gnd(ax, rx+1.15, p10y-0.2)

    # PIN 8 (CAR_P, y=2.0) — CC_CAR then AC source (VFO) ────────────────────
    p8y = py(8)   # 2.0
    cap_h(ax, rx, p8y, rx+1.0, lbl='CC_CAR\n10nF', la=True)
    _wire(ax, [(rx+1.0, p8y),(rx+1.4, p8y)])
    ac_source(ax, rx+1.75, p8y, lbl='V_Q1S\n14.175 MHz\n0.378 V pk')
    _wire(ax, [(rx+1.75, p8y-0.32),(rx+1.75, p8y-0.55)])
    gnd(ax, rx+1.75, p8y-0.55)

    # ── Title & annotations ───────────────────────────────────────────────────
    _txt(ax, 8, 10.72, 'MC1496 VCA Buffer — 20m CW Transmitter',
         size=13, bold=True, color='#1A1A7A')
    _txt(ax, 8, 10.38, 'Keyed buffer / amplitude control stage  ·  Pinout per ON Semiconductor MC1496 datasheet',
         size=8.5, color='#444444')

    ax.add_patch(patches.FancyBboxPatch((1.2, 0.15), 13.6, 0.52,
                                         boxstyle='round,pad=0.08',
                                         ec='#CC8800', fc='#FFF8E0', lw=0.8))
    _txt(ax, 8, 0.41,
         '⚠  Pin numbers corrected from earlier docs: '
         'OUT_P = pin 6, OUT_N = pin 12   |   CAR_P = pin 8, CAR_N = pin 10   |   '
         'VEE = pin 14   |   No dedicated VCC pin — +12 V through load resistors only   |   '
         'Digital null DAC: R_INJ1/R_INJ2 (330kΩ) replace mechanical null pot',
         size=6.5, color='#7A4000')

    # Supply legend
    lx2, ly = 12.5, 10.2
    _txt(ax, lx2, ly,      'VDD (+12V): enters via R_LOAD_P / R_LOAD_N only',        ha='left', size=6.5, color='#CC0000')
    _txt(ax, lx2, ly-0.28, 'VEE (−8.2V): pin 14 only',                               ha='left', size=6.5, color='#0000CC')
    _txt(ax, lx2, ly-0.56, 'GND: R_BIAS (pin 5), signal refs, cap bypasses',         ha='left', size=6.5)
    _txt(ax, lx2, ly-0.84, 'V_AGC: sim stand-in for TL071 AGC integrator',           ha='left', size=6.5, color='#555')
    _txt(ax, lx2, ly-1.12, 'Digital null: DAC_NULL_P/N → R_INJ1/2 (330kΩ) → pins 1/4', ha='left', size=6.5, color='#004488')

    fig.tight_layout(pad=0.2)
    return fig


if __name__ == '__main__':
    import os
    fig = make_schematic()
    out = os.path.join(os.path.dirname(__file__), '..', 'Documentation',
                       'MC1496_VCA_Buffer_Schematic.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print(f'PNG saved: {os.path.abspath(out)}')
    plt.show()

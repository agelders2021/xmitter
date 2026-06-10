"""Draw the per-tube cathode current monitor + failsafe chain schematic.

Single channel shown (one tube). Replicate for the second tube; comparator
outputs OR'd into the watchdog gate.

Signal flow, left to right:
  6146B cathode -> R_C + C_BYP (at socket) -> sense tap -> F1 PTC -> R_S
    -> clamp + anti-alias network -> OPA1641 buffer -> ADC
                                                    -> LM393 comparator -> SR latch -> watchdog
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches


LW = 0.9
LWH = 1.4
FS = 7.5


def _wire(ax, pts, lw=LW):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color='black', lw=lw,
            solid_capstyle='round', solid_joinstyle='round')


def _dot(ax, x, y, r=0.06):
    ax.add_patch(patches.Circle((x, y), r, color='black', zorder=5))


def _txt(ax, x, y, s, ha='center', va='center', size=FS, bold=False,
         color='black', italic=False):
    weight = 'bold' if bold else 'normal'
    style = 'italic' if italic else 'normal'
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, fontweight=weight,
            fontstyle=style, color=color, zorder=6)


def _resistor_h(ax, x, y, w=0.9, label_above='', label_below=''):
    half = w / 2
    ax.add_patch(patches.Rectangle((x - half, y - 0.13), w, 0.26,
                                   fill=True, facecolor='white',
                                   edgecolor='black', lw=LWH, zorder=4))
    if label_above:
        _txt(ax, x, y + 0.30, label_above, va='bottom', size=FS - 0.5)
    if label_below:
        _txt(ax, x, y - 0.30, label_below, va='top', size=FS - 1,
             italic=True, color='#555555')


def _resistor_v(ax, x, y, h=0.9, label_right='', label_left=''):
    half = h / 2
    ax.add_patch(patches.Rectangle((x - 0.13, y - half), 0.26, h,
                                   fill=True, facecolor='white',
                                   edgecolor='black', lw=LWH, zorder=4))
    if label_right:
        _txt(ax, x + 0.30, y, label_right, ha='left', size=FS - 0.5)
    if label_left:
        _txt(ax, x - 0.30, y, label_left, ha='right', size=FS - 1,
             italic=True, color='#555555')


def _cap_v(ax, x, y, label_right=''):
    """Vertical cap (two horizontal plates) centered at (x, y)."""
    plate_w = 0.22
    gap = 0.06
    _wire(ax, [(x - plate_w, y + gap), (x + plate_w, y + gap)], lw=LWH + 0.2)
    _wire(ax, [(x - plate_w, y - gap), (x + plate_w, y - gap)], lw=LWH + 0.2)
    if label_right:
        _txt(ax, x + 0.32, y, label_right, ha='left', size=FS - 0.5)


def _diode(ax, x, y, dir='up', label_right=''):
    """Schottky diode, vertical, with arrow pointing 'up' or 'down'.
    'up' = anode at bottom, cathode at top (conducts up).
    """
    s = 0.22  # triangle size
    if dir == 'up':
        # Triangle (anode) pointing UP
        tri = [(x - s, y - s), (x + s, y - s), (x, y + s * 0.4)]
        # Cathode bar above
        bar_y = y + s * 0.4
    else:
        tri = [(x - s, y + s), (x + s, y + s), (x, y - s * 0.4)]
        bar_y = y - s * 0.4

    ax.add_patch(patches.Polygon(tri, closed=True, fill=True,
                                 facecolor='white', edgecolor='black',
                                 lw=LWH, zorder=4))
    _wire(ax, [(x - s, bar_y), (x + s, bar_y)], lw=LWH + 0.2)
    # Schottky "S" hooks on the cathode bar
    hook_len = 0.06
    if dir == 'up':
        _wire(ax, [(x - s, bar_y), (x - s - hook_len, bar_y + hook_len)], lw=LWH)
        _wire(ax, [(x + s, bar_y), (x + s + hook_len, bar_y - hook_len)], lw=LWH)
    else:
        _wire(ax, [(x - s, bar_y), (x - s - hook_len, bar_y - hook_len)], lw=LWH)
        _wire(ax, [(x + s, bar_y), (x + s + hook_len, bar_y + hook_len)], lw=LWH)

    if label_right:
        _txt(ax, x + 0.40, y, label_right, ha='left', size=FS - 0.5)


def _ptc(ax, x, y, label_above=''):
    """PTC fuse symbol -- rectangle with diagonal slash and 't' marker."""
    w, h = 1.0, 0.36
    ax.add_patch(patches.Rectangle((x - w / 2, y - h / 2), w, h,
                                   fill=True, facecolor='white',
                                   edgecolor='black', lw=LWH, zorder=4))
    # Diagonal slash for PTC
    _wire(ax, [(x - w / 2 + 0.10, y - h / 2 + 0.06),
               (x + w / 2 - 0.10, y + h / 2 - 0.06)], lw=LWH)
    _txt(ax, x, y - h / 2 - 0.18, 't', size=FS - 1, italic=True)
    if label_above:
        _txt(ax, x, y + 0.36, label_above, va='bottom', size=FS - 0.5)


def _gnd(ax, x, y, size=0.18):
    _wire(ax, [(x, y), (x, y - size)])
    _wire(ax, [(x - size, y - size), (x + size, y - size)], lw=LWH)
    _wire(ax, [(x - size * 0.6, y - size - 0.10),
               (x + size * 0.6, y - size - 0.10)])
    _wire(ax, [(x - size * 0.25, y - size - 0.20),
               (x + size * 0.25, y - size - 0.20)])


def _supply(ax, x, y, label, up=True):
    dy = 0.22 if up else -0.22
    _wire(ax, [(x, y), (x, y + dy)])
    _wire(ax, [(x - 0.16, y + dy), (x + 0.16, y + dy)], lw=LWH)
    _txt(ax, x, y + dy + (0.20 if up else -0.20), label,
         va='bottom' if up else 'top', bold=True, size=FS - 0.5)


def _opamp(ax, cx, cy, w=1.4, h=1.2, label=''):
    tri = [(cx - w / 2, cy - h / 2),
           (cx - w / 2, cy + h / 2),
           (cx + w / 2, cy)]
    ax.add_patch(patches.Polygon(tri, closed=True, fill=True,
                                 facecolor='white', edgecolor='black',
                                 lw=LWH, zorder=4))
    pin_inv = (cx - w / 2, cy + h / 4)
    pin_non = (cx - w / 2, cy - h / 4)
    pin_out = (cx + w / 2, cy)
    pin_vp = (cx - w / 4, cy + h / 2 + 0.04)
    pin_vn = (cx - w / 4, cy - h / 2 - 0.04)

    _txt(ax, pin_inv[0] + 0.14, pin_inv[1], '-', ha='left', bold=True,
         size=FS + 1)
    _txt(ax, pin_non[0] + 0.14, pin_non[1], '+', ha='left', bold=True,
         size=FS + 1)
    if label:
        _txt(ax, cx + w / 2 - 0.45, cy - 0.4, label, size=FS - 1,
             italic=True, color='#444444')
    return {'inv': pin_inv, 'non': pin_non, 'out': pin_out,
            'v_pos': pin_vp, 'v_neg': pin_vn}


def _tube_cath_pin(ax, x, y):
    """Symbol for the 6146B cathode pin connection."""
    ax.add_patch(patches.Circle((x, y), 0.10, fill=False,
                                edgecolor='black', lw=LWH, zorder=5))
    _txt(ax, x, y + 0.35, '6146B', ha='center', bold=True, size=FS - 0.5)
    _txt(ax, x, y + 0.15, 'cathode', ha='center', size=FS - 1,
         italic=True, color='#555555')


def _block(ax, x, y, w, h, label, sublabel=''):
    """Generic block (used for ADC, latch, etc.)."""
    ax.add_patch(patches.Rectangle((x - w / 2, y - h / 2), w, h,
                                   fill=True, facecolor='#f0f0ff',
                                   edgecolor='black', lw=LWH, zorder=4))
    _txt(ax, x, y + 0.10, label, bold=True, size=FS)
    if sublabel:
        _txt(ax, x, y - 0.15, sublabel, size=FS - 1, italic=True,
             color='#555555')


def make_schematic():
    fig, ax = plt.subplots(figsize=(15, 9.5))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 11)
    ax.set_aspect('equal')
    ax.axis('off')

    # Title
    _txt(ax, 9, 10.5,
         'Per-Tube Cathode Current Monitor + Failsafe Chain',
         size=12, bold=True)
    _txt(ax, 9, 10.1,
         'Seven defensive layers from cathode (+1 V nominal, may see 600 V on fault) to MCU ADC. '
         'Replicate one channel per tube; comparator outputs OR-ed to watchdog gate.',
         size=8, italic=True, color='#555555')

    # ── Tube cathode area ────────────────────────────────────────────────
    cath_x, cath_y = 1.2, 7.0
    _tube_cath_pin(ax, cath_x, cath_y)
    # Wire down from cathode pin
    _wire(ax, [(cath_x, cath_y - 0.10), (cath_x, 5.8)])

    # R_C 10 ohm to GND
    rc_y = 5.0
    _resistor_v(ax, cath_x, rc_y, h=0.7, label_right='R_C = 10 Ω',
                label_left='1 W')
    _wire(ax, [(cath_x, 5.35), (cath_x, 5.8)])
    _wire(ax, [(cath_x, 4.65), (cath_x, 4.30)])
    _gnd(ax, cath_x, 4.30)

    # C_BYP 0.01 uF (small, to GND, at the tube socket)
    cbyp_x = cath_x + 1.2
    _wire(ax, [(cath_x, 5.8), (cbyp_x, 5.8)])
    _dot(ax, cath_x, 5.8)
    _cap_v(ax, cbyp_x, 5.50, label_right='C_BYP = 0.01 µF')
    _wire(ax, [(cbyp_x, 5.8), (cbyp_x, 5.56)])
    _wire(ax, [(cbyp_x, 5.44), (cbyp_x, 5.10)])
    _gnd(ax, cbyp_x, 5.10)
    _txt(ax, cbyp_x, 5.10 - 0.50, '(at tube socket)',
         size=FS - 1, italic=True, color='#cc4400')

    # Sense tap label
    _txt(ax, cath_x + 0.05, 6.10, 'DC sense tap', ha='left',
         size=FS - 1, italic=True, color='#0066aa')
    _txt(ax, cath_x + 0.05, 6.32, '(BEFORE C_BYP)', ha='left',
         size=FS - 1.5, italic=True, color='#0066aa')

    # ── Level 0/1 boundary annotation ────────────────────────────────────
    _txt(ax, 1.2, 8.4, 'L0: socket-side', size=FS - 0.5, bold=True,
         color='#888800')

    # ── Sense wire run to analog board ───────────────────────────────────
    # From tap point at (cath_x, 5.8) up and over to F1 area
    _wire(ax, [(cath_x, 5.8), (cath_x, 7.5)])
    _wire(ax, [(cath_x, 7.5), (3.5, 7.5)])
    _txt(ax, 2.4, 7.65, 'twisted pair to analog board',
         size=FS - 1, italic=True, color='#666666')

    # ── Level 1: PTC fuse F1 ─────────────────────────────────────────────
    _ptc(ax, 4.0, 7.5, label_above='F1: Bourns MF-R010\n(PTC, 100 mA hold)')
    _wire(ax, [(3.5, 7.5), (3.5, 7.5)])

    # ── Level 2: R_S series limiter ─────────────────────────────────────
    rs_x = 5.6
    _wire(ax, [(4.5, 7.5), (rs_x - 0.45, 7.5)])
    _resistor_h(ax, rs_x, 7.5, w=0.9,
                label_above='R_S = 10 kΩ',
                label_below='current limit')

    # ── Level 3: clamp diodes + anti-alias cap ──────────────────────────
    # Junction node
    jx = 7.2
    _wire(ax, [(rs_x + 0.45, 7.5), (jx, 7.5)])
    _dot(ax, jx, 7.5)

    # D1: cathode at junction, anode at GND (so reverse biased normally;
    # forward when junction goes NEGATIVE below GND)
    _wire(ax, [(jx, 7.5), (jx, 7.15)])
    _diode(ax, jx, 6.85, dir='up', label_right='D1 BAT54')
    _wire(ax, [(jx, 6.55), (jx, 6.20)])
    _gnd(ax, jx, 6.20)

    # C_FILT (anti-alias)
    cf_x = jx + 0.9
    _wire(ax, [(jx, 7.5), (cf_x, 7.5)])
    _cap_v(ax, cf_x, 7.10, label_right='C_FILT\n1 nF')
    _wire(ax, [(cf_x, 7.5), (cf_x, 7.16)])
    _wire(ax, [(cf_x, 7.04), (cf_x, 6.70)])
    _gnd(ax, cf_x, 6.70)

    # D2: cathode at +3.3V, anode at junction (reverse biased normally;
    # forward when junction goes ABOVE +3.3V)
    d2_x = jx + 1.8
    _wire(ax, [(jx, 7.5), (d2_x, 7.5)])
    _diode(ax, d2_x, 7.85, dir='up', label_right='D2 BAT54')
    _wire(ax, [(d2_x, 7.5), (d2_x, 7.55)])
    _wire(ax, [(d2_x, 8.15), (d2_x, 8.45)])
    _supply(ax, d2_x, 8.45, '+3.3 V', up=True)

    # ── Level 4: OPA1641 buffer ──────────────────────────────────────────
    # Op-amp at (11.0, 7.5). Pin layout per _opamp():
    #   (-) input at TOP-LEFT  = (10.3, 7.8)
    #   (+) input at BOT-LEFT  = (10.3, 7.2)
    #   output    at RIGHT     = (11.7, 7.5)
    op_cx, op_cy = 11.0, 7.5
    ports = _opamp(ax, op_cx, op_cy, w=1.4, h=1.2, label='OPA1641')

    # Signal enters (+) at y = 7.2. Drop down BEFORE reaching the triangle
    # so the wire visually terminates ON the (+) pin, not on the triangle edge.
    drop_x = d2_x + 0.6
    _wire(ax, [(d2_x, 7.5), (drop_x, 7.5)])           # horizontal at y=7.5
    _wire(ax, [(drop_x, 7.5), (drop_x, 7.2)])         # vertical drop to (+) y
    _wire(ax, [(drop_x, 7.2), ports['non']])          # horizontal into (+) pin

    # Unity-gain buffer: output ── right ── up over the top ── left ── down to (-)
    fb_x_right = ports['out'][0] + 0.5    # 12.2 -- output branch x
    fb_y_top   = op_cy + 1.1               # 8.6 -- well above triangle top (8.1)
    fb_x_left  = ports['inv'][0] - 0.3    # 10.0 -- approach to (-) from the LEFT
    _wire(ax, [ports['out'], (fb_x_right, ports['out'][1])])  # out → right
    _wire(ax, [(fb_x_right, ports['out'][1]), (fb_x_right, fb_y_top)])  # up
    _wire(ax, [(fb_x_right, fb_y_top), (fb_x_left, fb_y_top)])  # across
    _wire(ax, [(fb_x_left, fb_y_top), (fb_x_left, ports['inv'][1])])  # down
    _wire(ax, [(fb_x_left, ports['inv'][1]), ports['inv']])  # right into (-)
    _dot(ax, fb_x_right, ports['out'][1])   # junction dot at output branch

    # Op-amp supplies
    _wire(ax, [ports['v_pos'], (ports['v_pos'][0], ports['v_pos'][1] + 0.4)])
    _supply(ax, ports['v_pos'][0], ports['v_pos'][1] + 0.4, '+5 V', up=True)
    _wire(ax, [ports['v_neg'], (ports['v_neg'][0], ports['v_neg'][1] - 0.4)])
    _gnd(ax, ports['v_neg'][0], ports['v_neg'][1] - 0.4)

    # ── Output of buffer fans out: ADC (right) and comparator (down) ─────
    # Add another dot a bit further right to mark the fan-out point
    fanout_x = fb_x_right + 0.5    # 12.7
    _wire(ax, [(fb_x_right, ports['out'][1]), (fanout_x, ports['out'][1])])
    _dot(ax, fanout_x, ports['out'][1])

    # ADC tap goes right
    adc_x = fanout_x + 0.5
    _wire(ax, [(fanout_x, ports['out'][1]), (adc_x, ports['out'][1])])
    _txt(ax, adc_x + 0.1, ports['out'][1], '→ ADC',
         ha='left', size=FS - 0.5, bold=True, color='#006600')
    _txt(ax, adc_x + 0.1, ports['out'][1] - 0.30, '(MCU, 12-bit)',
         ha='left', size=FS - 1, italic=True, color='#006600')

    # ── Level 5: LM393 comparator ────────────────────────────────────────
    # Placed BELOW the op-amp output area for a clean down-then-right routing.
    # Pin layout same as op-amp via _opamp():
    #   (-) input at TOP-LEFT, (+) input at BOT-LEFT
    comp_cx, comp_cy = 14.0, 5.0
    comp_ports = _opamp(ax, comp_cx, comp_cy, w=1.4, h=1.2, label='LM393')
    # (+) input at (13.3, 4.7), (-) at (13.3, 5.3), output at (14.7, 5.0)

    # Signal from buffer fan-out drops down then approaches (+) input at y=4.7
    _wire(ax, [(fanout_x, ports['out'][1]), (fanout_x, 4.7)])  # straight down
    _wire(ax, [(fanout_x, 4.7), comp_ports['non']])  # horizontal into (+) pin

    # V_REF block on (-) input -- enter horizontally at the (-) input's y
    vref_x = comp_ports['inv'][0] - 1.2
    _wire(ax, [comp_ports['inv'], (vref_x, comp_ports['inv'][1])])
    ax.add_patch(patches.Rectangle((vref_x - 1.0, comp_ports['inv'][1] - 0.25),
                                   1.0, 0.5, fill=True, facecolor='#fff8e8',
                                   edgecolor='black', lw=LWH, zorder=4))
    _txt(ax, vref_x - 0.5, comp_ports['inv'][1] + 0.05, 'V_REF',
         size=FS - 0.5, bold=True, color='#0066aa')
    _txt(ax, vref_x - 0.5, comp_ports['inv'][1] - 0.13, '+1.5 V',
         size=FS - 1, italic=True, color='#0066aa')

    # Hysteresis: R_HYST from output back to (+) input
    # Route: output → right → up (above triangle) → left → down to (+) input
    h_x_right = comp_ports['out'][0] + 0.4    # 15.1
    h_y_top   = comp_cy + 1.1                  # 6.1 (well above triangle top 5.6)
    h_x_left  = comp_ports['non'][0] - 0.4    # 12.9 (approach (+) from left)
    _wire(ax, [comp_ports['out'], (h_x_right, comp_ports['out'][1])])  # right
    _wire(ax, [(h_x_right, comp_ports['out'][1]), (h_x_right, h_y_top)])  # up
    # R_HYST horizontal across the top of the comparator
    hyst_center_x = (h_x_left + h_x_right) / 2
    _resistor_h(ax, hyst_center_x, h_y_top, w=1.0,
                label_above='R_HYST = 470 kΩ',
                label_below='hysteresis (~50 mV)')
    _wire(ax, [(h_x_right, h_y_top), (hyst_center_x + 0.5, h_y_top)])
    _wire(ax, [(h_x_left, h_y_top), (hyst_center_x - 0.5, h_y_top)])
    _wire(ax, [(h_x_left, h_y_top), (h_x_left, comp_ports['non'][1])])  # down
    _wire(ax, [(h_x_left, comp_ports['non'][1]), comp_ports['non']])  # right into (+)
    _dot(ax, h_x_right, comp_ports['out'][1])  # branch point at comparator output
    # Also dot at (+) input where hysteresis joins signal path
    _dot(ax, comp_ports['non'][0], comp_ports['non'][1])

    # Comparator V+ supply -- route LEFT first to clear R_HYST overhead,
    # then UP to a clean supply marker well outside R_HYST's footprint.
    v_pos_pin = comp_ports['v_pos']
    vp_x = comp_ports['non'][0] - 1.0  # 12.3 -- left of R_HYST (which starts at 13.5)
    _wire(ax, [v_pos_pin, (vp_x, v_pos_pin[1])])              # left
    _wire(ax, [(vp_x, v_pos_pin[1]), (vp_x, v_pos_pin[1] + 0.4)])  # up
    _supply(ax, vp_x, v_pos_pin[1] + 0.4, '+5 V', up=True)

    # Comparator V- supply (to GND) -- straight down, no conflict
    _wire(ax, [comp_ports['v_neg'],
               (comp_ports['v_neg'][0], comp_ports['v_neg'][1] - 0.4)])
    _gnd(ax, comp_ports['v_neg'][0], comp_ports['v_neg'][1] - 0.4)

    # R_PULL on comparator output (LM393 is open-collector). By convention,
    # +3.3 V rail goes at the top of the schematic; R_PULL pulls UP from the
    # output node. Place the pull-up branch to the RIGHT of the hysteresis
    # loop so the layout is clean.
    pu_x = h_x_right + 0.7    # 15.8 -- clear of the hysteresis loop column
    # Branch wire from output dot at (h_x_right, output_y) to the pull-up node
    _wire(ax, [(h_x_right, comp_ports['out'][1]),
               (pu_x, comp_ports['out'][1])])
    _dot(ax, pu_x, comp_ports['out'][1])

    # R_PULL vertical, body above the output node
    pu_y_center = comp_ports['out'][1] + 0.6   # 5.6
    _resistor_v(ax, pu_x, pu_y_center, h=0.6, label_right='R_PULL = 4.7 kΩ')
    _wire(ax, [(pu_x, comp_ports['out'][1]),
               (pu_x, pu_y_center - 0.30)])      # output → R_PULL bottom
    _wire(ax, [(pu_x, pu_y_center + 0.30),
               (pu_x, pu_y_center + 0.55)])      # R_PULL top → supply
    _supply(ax, pu_x, pu_y_center + 0.55, '+3.3 V', up=True)

    # Output signal to watchdog: continues right from the pull-up dot
    _wire(ax, [(pu_x, comp_ports['out'][1]),
               (pu_x + 1.4, comp_ports['out'][1])])
    _txt(ax, pu_x + 1.5, comp_ports['out'][1], '→ CT_FAULT_N',
         ha='left', size=FS - 0.5, bold=True, color='#cc0000')
    _txt(ax, pu_x + 1.5, comp_ports['out'][1] - 0.30, '(to watchdog gate)',
         ha='left', size=FS - 1, italic=True, color='#cc0000')

    # ── Level labels ─────────────────────────────────────────────────────
    level_label_y = 8.7
    _txt(ax, 4.0, level_label_y, 'L1: PTC', size=FS - 0.5, bold=True,
         color='#888800')
    _txt(ax, 5.6, level_label_y, 'L2: limit', size=FS - 0.5, bold=True,
         color='#888800')
    _txt(ax, 8.0, level_label_y, 'L3: clamp + LPF', size=FS - 0.5, bold=True,
         color='#888800')
    _txt(ax, 11.0, level_label_y, 'L4: buffer', size=FS - 0.5, bold=True,
         color='#888800')
    _txt(ax, 14.0, level_label_y, 'L5: HW trip', size=FS - 0.5, bold=True,
         color='#888800')

    # ── Notes box at the bottom ──────────────────────────────────────────
    ax.add_patch(patches.FancyBboxPatch(
        (0.5, 0.4), 17.0, 2.2,
        boxstyle='round,pad=0.05', fill=True, facecolor='#fafafa',
        edgecolor='#888888', lw=LW, zorder=3))

    notes = [
        ('Operating point (per tube at full drive):',
         'I_cathode ≈ 100 mA  →  V_sense ≈ 1.0 V at ADC input  →  ~30% ADC range'),
        ('Trip threshold:',
         'V_REF = 1.5 V on LM393 (-) corresponds to 150 mA cathode current; 50 mV hysteresis from R_HYST.'),
        ('Total fault response (cathode overcurrent → tubes off):',
         '< 100 µs total -- op-amp slew (~1 µs) + comparator (~3 µs) + SR latch + screen-voltage gate discharge'),
        ('Critical layout rule:',
         'DC sense tap leaves R_C top BEFORE C_BYP. Sense wire is twisted pair (signal + analog GND return).'),
        ('Three separate grounds, one star point:',
         'GND_RF (at tube socket, bypass returns) | GND_SENSE (analog board signal GND) | '
         'GND_DIG (MCU board). All meet at the analog board single-point ground only.'),
    ]
    for i, (head, body) in enumerate(notes):
        y = 2.30 - i * 0.40
        _txt(ax, 0.85, y, head, ha='left', bold=True, size=FS - 0.5,
             color='#222244')
        _txt(ax, 5.6, y, body, ha='left', size=FS - 0.5, italic=True,
             color='#444444')

    fig.tight_layout()
    return fig


if __name__ == '__main__':
    fig = make_schematic()
    fig.savefig('cathode_monitor_preview.png', dpi=150, bbox_inches='tight')
    print('Wrote cathode_monitor_preview.png')

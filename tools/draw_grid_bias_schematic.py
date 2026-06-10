"""Draw the per-tube grid bias control schematic using matplotlib primitives.

Two design variants:
  make_schematic_opa454()    -- OPA454 HV op-amp version
  make_schematic_discrete()  -- LV op-amp + discrete HV PNP level-shifter

Both produce the same transfer function:
  V_out = V_DAC * (1 + R_F/R_G) - V_REF * R_F/R_G
        = V_DAC * 18 - 85    (with R_F=170k, R_G=10k, V_REF=+5V)

Range:
  V_DAC = 0       -> V_out = -85 V  (IDLE / PA off)
  V_DAC = 1.94 V  -> V_out = -50 V  (OPERATE)
  V_DAC = 3.3 V   -> V_out = -25.6 V (firmware-bounded; never command)

The OPA454 version uses the part directly with V+ = +5 V, V- = -90 V
(95 V total supply, comfortably under the 100 V operating max).

The discrete version puts a low-voltage op-amp inside the feedback loop
with a high-voltage PNP transistor (MPSA92, V_CEO = 300 V) as the HV
output stage. No supply-voltage constraint on the op-amp itself.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches


LW = 0.9
LWH = 1.4
FS = 7.5


# ── Common helpers ───────────────────────────────────────────────────────────

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
    ax.add_patch(patches.Rectangle((x - half, y - 0.16), w, 0.32,
                                   fill=True, facecolor='white',
                                   edgecolor='black', lw=LWH, zorder=4))
    if label_above:
        _txt(ax, x, y + 0.35, label_above, va='bottom')
    if label_below:
        _txt(ax, x, y - 0.35, label_below, va='top', size=FS - 0.5,
             italic=True, color='#555555')
    return x - half, x + half


def _resistor_v(ax, x, y, h=0.9, label_right='', label_left=''):
    half = h / 2
    ax.add_patch(patches.Rectangle((x - 0.16, y - half), 0.32, h,
                                   fill=True, facecolor='white',
                                   edgecolor='black', lw=LWH, zorder=4))
    if label_right:
        _txt(ax, x + 0.35, y, label_right, ha='left')
    if label_left:
        _txt(ax, x - 0.35, y, label_left, ha='right', size=FS - 0.5,
             italic=True, color='#555555')
    return y - half, y + half


def _gnd(ax, x, y, size=0.18):
    _wire(ax, [(x, y), (x, y - size)])
    _wire(ax, [(x - size, y - size), (x + size, y - size)], lw=LWH)
    _wire(ax, [(x - size * 0.6, y - size - 0.10),
               (x + size * 0.6, y - size - 0.10)])
    _wire(ax, [(x - size * 0.25, y - size - 0.20),
               (x + size * 0.25, y - size - 0.20)])


def _supply(ax, x, y, label, up=True):
    dy = 0.25 if up else -0.25
    _wire(ax, [(x, y), (x, y + dy)])
    _wire(ax, [(x - 0.18, y + dy), (x + 0.18, y + dy)], lw=LWH)
    _txt(ax, x, y + dy + 0.18 * (1 if up else -1.6), label,
         va='bottom' if up else 'top', bold=True)


def _opamp(ax, cx, cy, w=1.6, h=1.4, label=''):
    tri = [(cx - w / 2, cy - h / 2),
           (cx - w / 2, cy + h / 2),
           (cx + w / 2, cy)]
    ax.add_patch(patches.Polygon(tri, closed=True, fill=True,
                                 facecolor='white', edgecolor='black',
                                 lw=LWH, zorder=4))
    pin_inv = (cx - w / 2, cy + h / 4)
    pin_non = (cx - w / 2, cy - h / 4)
    pin_out = (cx + w / 2, cy)
    pin_vp = (cx - w / 4, cy + h / 2 + 0.05)
    pin_vn = (cx - w / 4, cy - h / 2 - 0.05)

    _txt(ax, pin_inv[0] + 0.18, pin_inv[1], '−', ha='left', bold=True,
         size=FS + 1)
    _txt(ax, pin_non[0] + 0.18, pin_non[1], '+', ha='left', bold=True,
         size=FS + 1)
    if label:
        _txt(ax, cx + w / 2 - 0.6, cy - 0.5, label, size=FS - 0.5,
             italic=True, color='#444444')

    return {'inv': pin_inv, 'non': pin_non, 'out': pin_out,
            'v_pos': pin_vp, 'v_neg': pin_vn}


def _pnp(ax, cx, cy, r=0.32, label=''):
    """Draw a PNP transistor symbol with circle body.
    Base on left; emitter top-right (arrow IN toward base); collector
    bottom-right. Returns dict with external pin coordinates.
    """
    # Body circle
    ax.add_patch(patches.Circle((cx, cy), r, fill=True, facecolor='white',
                                edgecolor='black', lw=LWH, zorder=4))
    # Base line (vertical inside the circle)
    base_x = cx - r * 0.55
    _wire(ax, [(base_x, cy - r * 0.65), (base_x, cy + r * 0.65)], lw=LWH + 0.4)
    # Lead from base out to the left
    _wire(ax, [(base_x, cy), (cx - r - 0.3, cy)])
    # Emitter (upper-right slant, with arrow toward base for PNP)
    em_inner = (base_x, cy + r * 0.35)
    em_outer = (cx + r * 0.6, cy + r * 0.9)
    _wire(ax, [em_inner, em_outer])
    # Arrow head on emitter — pointing IN toward the base (PNP)
    # Place arrow about 1/3 from the base end
    ax_arrow = base_x + (em_outer[0] - em_inner[0]) * 0.35
    ay_arrow = (cy + r * 0.35) + (em_outer[1] - em_inner[1]) * 0.35
    dx = em_inner[0] - em_outer[0]
    dy = em_inner[1] - em_outer[1]
    # Simple arrow head
    ax.add_patch(patches.FancyArrow(
        ax_arrow, ay_arrow, dx * 0.18, dy * 0.18,
        width=0.02, head_width=0.10, head_length=0.10,
        length_includes_head=True, facecolor='black', edgecolor='black',
        zorder=5))
    # Lead from emitter outer point upward
    _wire(ax, [em_outer, (em_outer[0], em_outer[1] + 0.25)])
    # Collector (lower-right slant)
    coll_inner = (base_x, cy - r * 0.35)
    coll_outer = (cx + r * 0.6, cy - r * 0.9)
    _wire(ax, [coll_inner, coll_outer])
    _wire(ax, [coll_outer, (coll_outer[0], coll_outer[1] - 0.25)])

    if label:
        _txt(ax, cx, cy - r - 0.55, label, italic=True,
             color='#444444', size=FS - 0.5)

    return {
        'B': (cx - r - 0.3, cy),
        'E': (em_outer[0], em_outer[1] + 0.25),
        'C': (coll_outer[0], coll_outer[1] - 0.25),
    }


def _dac_block(ax, x, y):
    """DAC (MCP4725) block. Returns the output port coordinate."""
    w, h = 1.6, 1.8
    ax.add_patch(patches.Rectangle((x - w / 2, y - h / 2),
                                   w, h, fill=True,
                                   facecolor='#f0f0ff', edgecolor='black',
                                   lw=LWH, zorder=4))
    _txt(ax, x, y + 0.55, 'MCP4725', bold=True, size=FS + 0.5)
    _txt(ax, x, y + 0.20, '12-bit DAC', size=FS - 0.5,
         italic=True, color='#555555')
    _txt(ax, x, y - 0.20, 'I²C addr 0x60', size=FS - 1,
         italic=True, color='#555555')
    _txt(ax, x, y - 0.55, '0 → 3.3 V out', size=FS - 0.5,
         italic=True, color='#555555')
    _txt(ax, x - w / 2 - 0.05, y + 0.55, 'SDA', ha='right', size=FS - 1)
    _txt(ax, x - w / 2 - 0.05, y + 0.20, 'SCL', ha='right', size=FS - 1)
    _txt(ax, x - w / 2 - 0.05, y - 0.20, '+3.3 V', ha='right', size=FS - 1)
    _txt(ax, x - w / 2 - 0.05, y - 0.55, 'GND', ha='right', size=FS - 1)
    _txt(ax, x + w / 2 + 0.05, y, 'V_OUT', ha='left', size=FS - 1)
    return (x + w / 2, y)


def _ref_block(ax, x, y, label='LM4040-5.0'):
    """LM4040 +5V reference block."""
    w, h = 1.6, 1.4
    ax.add_patch(patches.Rectangle((x - w / 2, y - h / 2),
                                   w, h, fill=True,
                                   facecolor='#fff8e8', edgecolor='black',
                                   lw=LWH, zorder=4))
    _txt(ax, x, y + 0.35, label, bold=True, size=FS + 0.5)
    _txt(ax, x, y, '+5 V', size=FS, bold=True)
    _txt(ax, x, y - 0.35, 'precision ref', size=FS - 0.5,
         italic=True, color='#555555')
    return (x + w / 2, y)


def _grid_pin(ax, x, y):
    """Draw the 6146B grid pin marker at (x, y), with labels."""
    ax.add_patch(patches.Circle((x, y), 0.10, fill=False,
                                edgecolor='black', lw=LWH, zorder=5))
    _txt(ax, x + 0.2, y + 0.30, '6146B', ha='left', bold=True, size=FS)
    _txt(ax, x + 0.2, y, 'control', ha='left', size=FS - 0.5,
         color='#555555')
    _txt(ax, x + 0.2, y - 0.30, 'grid (G1)', ha='left',
         size=FS - 0.5, color='#555555')


# ── Design A: OPA454 ─────────────────────────────────────────────────────────

def make_schematic_opa454():
    """OPA454 version: V+ = +5V, V− = −90V (95V total, within spec).
    R_F = 170k, R_G = 10k, V_REF = +5V LM4040.
    Output range: V_DAC = 0 → V_out = −85 V; V_DAC = 1.94 V → −50 V.
    """
    fig, ax = plt.subplots(figsize=(13.5, 8.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')

    # Title
    _txt(ax, 8, 9.5,
         'Design A — Per-Tube 6146B Grid Bias with OPA454 HV Op-Amp',
         size=12, bold=True)
    _txt(ax, 8, 9.05,
         'V+ = +12 V, V− = −85 V (97 V total, within OPA454 100 V operating max). '
         'V_out = −85 V (IDLE) → −50 V (OPERATE).',
         size=8.5, italic=True, color='#555555')

    # DAC block (left)
    dac_out = _dac_block(ax, 1.5, 6.0)

    # LM4040 +5V reference block (lower-left)
    ref_out = _ref_block(ax, 1.5, 2.5)

    # Op-amp (center)
    op_cx, op_cy = 8.0, 5.5
    ports = _opamp(ax, op_cx, op_cy, w=2.0, h=1.8, label='OPA454')

    # ── R_pad on (+) input from DAC ─────────────────────────────────────
    # Placed at the (+) input's y so the wire enters straight horizontally.
    # DAC vertical at x=2.7 (separated from the LM4040 vertical at x=3.3 so
    # they don't visually merge into one continuous wire).
    rpad_x = 4.5
    rpad_y = ports['non'][1]  # 5.05
    _wire(ax, [dac_out,
               (2.7, dac_out[1]),       # right past the DAC block
               (2.7, rpad_y),            # down to R_pad's y
               (rpad_x - 0.5, rpad_y)])  # right to R_pad's left side
    _resistor_h(ax, rpad_x, rpad_y, w=0.9,
                label_above='R_pad = 1 kΩ', label_below='1%')
    rpad_right = rpad_x + 0.45
    _wire(ax, [(rpad_right, rpad_y), ports['non']])

    # ── R_G from (−) input to V_REF ─────────────────────────────────────
    # At the (-) input's y. LM4040 vertical routed at x=3.3 -- clearly
    # separated from the DAC vertical at x=2.7.
    rg_x = 4.5
    rg_y = ports['inv'][1]  # 5.95
    _wire(ax, [ports['inv'], (rg_x + 0.5, rg_y)])
    _resistor_h(ax, rg_x, rg_y, w=0.9,
                label_above='R_G = 10 kΩ', label_below='1%')
    rg_left = rg_x - 0.45
    # R_G left side -> over to x=3.3, then DOWN to LM4040 y, then LEFT to ref
    _wire(ax, [(rg_left, rg_y),
               (3.3, rg_y),
               (3.3, ref_out[1]),
               ref_out])
    _dot(ax, ports['inv'][0], rg_y)  # node where R_F joins

    # ── R_F: feedback from output to (−) ────────────────────────────────
    rf_x = op_cx
    rf_y = 7.6
    _wire(ax, [ports['inv'], (ports['inv'][0], rf_y)])
    _resistor_h(ax, rf_x, rf_y, w=1.0,
                label_above='R_F = 170 kΩ', label_below='1%')
    rf_left = rf_x - 0.5
    rf_right = rf_x + 0.5
    _wire(ax, [(rf_left, rf_y), (ports['inv'][0], rf_y)])
    # From R_F right, down to opamp output node
    _wire(ax, [(rf_right, rf_y),
               (ports['out'][0] + 0.7, rf_y),
               (ports['out'][0] + 0.7, ports['out'][1]),
               ports['out']])
    _dot(ax, ports['out'][0] + 0.7, ports['out'][1])

    # ── Power rails on opamp ────────────────────────────────────────────
    # +12V rail: route OUT to the right past R_F so it's clearly visible
    _wire(ax, [ports['v_pos'],
               (ports['v_pos'][0], 6.75),
               (10.5, 6.75),
               (10.5, 8.3)])
    _supply(ax, 10.5, 8.3, '+12 V', up=True)

    # −85V rail straight down
    _wire(ax, [ports['v_neg'], (ports['v_neg'][0], ports['v_neg'][1] - 0.6)])
    _supply(ax, ports['v_neg'][0], ports['v_neg'][1] - 0.6,
            '−85 V', up=False)

    # ── R_GL to grid ────────────────────────────────────────────────────
    rgl_x = 12.5
    rgl_y = 5.5
    _wire(ax, [(ports['out'][0] + 0.7, ports['out'][1]),
               (rgl_x - 0.5, rgl_y)])
    _resistor_h(ax, rgl_x, rgl_y, w=0.9,
                label_above='R_GL = 22 kΩ',
                label_below='(in PA subcircuit)')
    rgl_right = rgl_x + 0.45
    _wire(ax, [(rgl_right, rgl_y), (14.6, rgl_y)])
    _grid_pin(ax, 14.7, rgl_y)

    # ── Transfer function annotation ────────────────────────────────────
    _txt(ax, 12.5, 4.2,
         'V_out = V_DAC × 18 − 85', size=FS, bold=True, color='#2244AA')
    _txt(ax, 12.5, 3.85,
         '  V_DAC = 0      →  V_out = −85 V (IDLE)',
         size=FS - 0.5, italic=True, color='#2244AA')
    _txt(ax, 12.5, 3.55,
         '  V_DAC = 1.94 V →  V_out = −50 V (OPERATE)',
         size=FS - 0.5, italic=True, color='#2244AA')

    # ── Notes ───────────────────────────────────────────────────────────
    ax.add_patch(patches.FancyBboxPatch(
        (3.0, 0.4), 10.5, 1.0,
        boxstyle='round,pad=0.05', fill=True, facecolor='#fafafa',
        edgecolor='#888888', lw=LW, zorder=3))
    _txt(ax, 8.25, 1.20,
         '−85 V rail: small isolated DC-DC + voltage doubler (e.g., '
         'Murata NMA0509 → ±9 V → 10× doubler stages),',
         size=FS - 1, italic=True, color='#444444')
    _txt(ax, 8.25, 0.95,
         'regulated to −85 V via a TL431 shunt or 86 V zener. '
         '~5 mA total for both PA channels.',
         size=FS - 1, italic=True, color='#444444')
    _txt(ax, 8.25, 0.70,
         '+5 V rail: same +5 V supply as the LM4040 reference and DAC '
         'logic; 100 nF + 10 µF decoupling at each OPA454 supply pin.',
         size=FS - 1, italic=True, color='#444444')
    _txt(ax, 8.25, 0.45,
         'Replicate this channel for the second tube (separate I²C address; '
         'shared rails OK).',
         size=FS - 1, italic=True, color='#444444')

    fig.tight_layout()
    return fig


# ── Design B: Discrete PNP level-shifter ─────────────────────────────────────

def make_schematic_discrete():
    """Discrete version: low-voltage op-amp drives a high-V PNP transistor
    (MPSA92, V_CEO = 300 V) as the HV output stage. Op-amp itself runs on
    ±5 V or +5 V single-supply.
    """
    fig, ax = plt.subplots(figsize=(13.5, 8.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')

    # Title
    _txt(ax, 8, 9.5,
         'Design B — Per-Tube 6146B Grid Bias with Discrete HV PNP Level-Shifter',
         size=12, bold=True)
    _txt(ax, 8, 9.05,
         'LM358 low-voltage op-amp + MPSA92 PNP (V_CEO = 300 V). '
         'Same transfer function as Design A. No op-amp voltage limit.',
         size=8.5, italic=True, color='#555555')

    # DAC and reference blocks
    dac_out = _dac_block(ax, 1.5, 6.0)
    ref_out = _ref_block(ax, 1.5, 2.5)

    # LV op-amp (LM358) — center-left
    op_cx, op_cy = 6.5, 5.5
    ports = _opamp(ax, op_cx, op_cy, w=1.8, h=1.6, label='LM358')

    # ── R_pad on (+) input from DAC ────────────────────────────────────
    # At (+) input's y for straight-horizontal entry.
    # DAC vertical at x=2.7 (separated from LM4040 vertical at x=3.1).
    rpad_x = 4.0
    rpad_y = ports['non'][1]  # 5.1
    _wire(ax, [dac_out,
               (2.7, dac_out[1]),
               (2.7, rpad_y),
               (rpad_x - 0.5, rpad_y)])
    _resistor_h(ax, rpad_x, rpad_y, w=0.9,
                label_above='R_pad = 1 kΩ')
    rpad_right = rpad_x + 0.45
    _wire(ax, [(rpad_right, rpad_y), ports['non']])

    # ── R_G from (−) input to V_REF ────────────────────────────────────
    # At (-) input's y. LM4040 vertical at x=3.1, clearly separated.
    rg_x = 4.0
    rg_y = ports['inv'][1]  # 5.9
    _wire(ax, [ports['inv'], (rg_x + 0.5, rg_y)])
    _resistor_h(ax, rg_x, rg_y, w=0.9,
                label_above='R_G = 10 kΩ')
    rg_left = rg_x - 0.45
    _wire(ax, [(rg_left, rg_y),
               (3.1, rg_y),
               (3.1, ref_out[1]),
               ref_out])
    _dot(ax, ports['inv'][0], rg_y)

    # ── R_BASE: from LM358 output to PNP base ───────────────────────────
    rb_x = 9.0
    rb_y = op_cy  # 5.5
    _wire(ax, [ports['out'], (rb_x - 0.5, rb_y)])
    _resistor_h(ax, rb_x, rb_y, w=0.9,
                label_above='R_B = 10 kΩ',
                label_below='current-limit base')
    rb_right = rb_x + 0.45

    # ── PNP transistor (MPSA92) ─────────────────────────────────────────
    pnp_cx, pnp_cy = 11.5, 5.5
    pnp = _pnp(ax, pnp_cx, pnp_cy, r=0.4, label='MPSA92 (V_CEO = 300V)')
    # Connect R_BASE right side to PNP base
    _wire(ax, [(rb_right, rb_y), pnp['B']])

    # ── R_E from PNP emitter to +5V ─────────────────────────────────────
    # PNP emitter pin is at (pnp_cx + 0.24, pnp_cy + 0.36 + 0.25) = (11.74, 6.11)
    re_x = pnp['E'][0]
    re_y = pnp['E'][1] + 0.6
    _resistor_v(ax, re_x, re_y, h=0.9,
                label_right='R_E = 10 kΩ',
                label_left='')
    _wire(ax, [pnp['E'], (re_x, re_y - 0.45)])
    _wire(ax, [(re_x, re_y + 0.45), (re_x, re_y + 0.85)])
    _supply(ax, re_x, re_y + 0.85, '+5 V', up=True)

    # ── R_LOAD from PNP collector to −90V ───────────────────────────────
    # Collector pin is at (pnp_cx + 0.24, pnp_cy - 0.36 - 0.25) = (11.74, 4.89)
    rl_x = pnp['C'][0]
    rl_y = pnp['C'][1] - 0.7
    _wire(ax, [pnp['C'], (rl_x, rl_y + 0.45)])
    _resistor_v(ax, rl_x, rl_y, h=0.9,
                label_right='R_L = 100 kΩ',
                label_left='')
    _wire(ax, [(rl_x, rl_y - 0.45), (rl_x, rl_y - 0.85)])
    _supply(ax, rl_x, rl_y - 0.85, '−85 V', up=False)

    # ── Output node at the actual collector pin ────────────────────────
    # Output wire goes RIGHT from the collector pin to R_GL.
    out_node_x = pnp['C'][0]
    out_node_y = pnp['C'][1]  # actual collector pin, not floating above
    _dot(ax, out_node_x, out_node_y)

    # R_GL to grid
    rgl_x = 14.0
    rgl_y = out_node_y
    _wire(ax, [(out_node_x, out_node_y), (rgl_x - 0.45, rgl_y)])
    _resistor_h(ax, rgl_x, rgl_y, w=0.7, label_above='R_GL = 22 kΩ')
    _wire(ax, [(rgl_x + 0.35, rgl_y), (14.95, rgl_y)])
    _grid_pin(ax, 15.05, rgl_y)

    # ── R_F: feedback from output back to op-amp (−) ───────────────────
    # Tap the output wire at x=13.0 (well clear of PNP body at x≈11.5
    # and R_E vertical at x=11.74), go UP past R_E's top (y≈7.16), across
    # at y=8.0 to R_F, then LEFT and DOWN into the (−) input.
    fb_tap_x = 13.0
    _dot(ax, fb_tap_x, out_node_y)
    _wire(ax, [(fb_tap_x, out_node_y), (fb_tap_x, 8.0)])
    rf_x = 9.0
    rf_y = 8.0
    _resistor_h(ax, rf_x, rf_y, w=1.0,
                label_above='R_F = 170 kΩ', label_below='1%')
    _wire(ax, [(rf_x + 0.5, rf_y), (fb_tap_x, rf_y)])
    _wire(ax, [(rf_x - 0.5, rf_y),
               (ports['inv'][0], rf_y),
               ports['inv']])

    # ── LM358 power rails ───────────────────────────────────────────────
    _wire(ax, [ports['v_pos'], (ports['v_pos'][0], ports['v_pos'][1] + 0.6)])
    _supply(ax, ports['v_pos'][0], ports['v_pos'][1] + 0.6,
            '+5 V', up=True)
    # LM358 is single-supply capable; V- to GND
    _wire(ax, [ports['v_neg'], (ports['v_neg'][0], ports['v_neg'][1] - 0.45)])
    _gnd(ax, ports['v_neg'][0], ports['v_neg'][1] - 0.45)

    # ── Transfer function annotation ────────────────────────────────────
    _txt(ax, 8.0, 1.65,
         'V_out = V_DAC × 18 − 85   '
         '(V_DAC = 0 → −85 V IDLE;  '
         'V_DAC = 1.94 V → −50 V OPERATE)',
         size=FS, bold=True, color='#2244AA')

    # Notes
    ax.add_patch(patches.FancyBboxPatch(
        (1.5, 0.15), 13.0, 1.2,
        boxstyle='round,pad=0.05', fill=True, facecolor='#fafafa',
        edgecolor='#888888', lw=LW, zorder=3))
    _txt(ax, 8.0, 1.15,
         'PNP collector V_CE ranges: V_E ≈ +4.4 V (V_BE drop), V_C ranges '
         '−85 to −50 V → V_CE_max ≈ 89 V, well within MPSA92\'s 300 V '
         'V_CEO rating.',
         size=FS - 1, italic=True, color='#444444')
    _txt(ax, 8.0, 0.85,
         'Max collector current: (V_out − V_L) / R_L = (−50 − (−85)) / 100 k = '
         '0.35 mA. Max P_diss = V_CE × I_C ≈ 31 mW. Anything in TO-92 works.',
         size=FS - 1, italic=True, color='#444444')
    _txt(ax, 8.0, 0.55,
         'Op-amp output swing only needs ±0.7 V to drive the PNP base around '
         'its operating point. LM358, TL072, OP07 all work; LM358 chosen '
         'for cost and single-supply.',
         size=FS - 1, italic=True, color='#444444')
    _txt(ax, 8.0, 0.25,
         'Shares the −85 V and +5 V rails with Design A. Replicate '
         'channel-per-tube.',
         size=FS - 1, italic=True, color='#444444')

    fig.tight_layout()
    return fig


# Backwards-compat alias for the original entry point
def make_schematic():
    return make_schematic_opa454()


if __name__ == '__main__':
    for tag, fn in [('opa454', make_schematic_opa454),
                    ('discrete', make_schematic_discrete)]:
        fig = fn()
        fig.savefig(f'grid_bias_{tag}_preview.png', dpi=150,
                    bbox_inches='tight')
        print(f'Wrote grid_bias_{tag}_preview.png')

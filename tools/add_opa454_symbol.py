"""Add an xmitter:OPA454 symbol to KiCAD/xmitter.kicad_sym.

Custom symbol for the TI OPA454 high-voltage op-amp (100 V op-max, ±50 V
supplies). Used in the grid_bias subsystem (one per tube, ×2 total).

Multi-unit layout — same pattern as the existing TL072 in this library:
  Unit A (1_1): Op-amp triangle with the three signal pins — IN-, IN+, OUT.
  Unit B (2_1): Power + enable + status block with V+, V-, ED, EDCOMM,
                STATFLG. Must be placed on every schematic that uses the
                OPA454 (one Unit B per Unit A).

Pin map (per SBOS391B datasheet, SOIC-8 / DIP-8 same):
  1 = EDCOMM    Enable-input reference (tie to V- or GND)
  2 = -IN       Inverting input
  3 = +IN       Non-inverting input
  4 = V-        Negative supply
  5 = STATFLG   Status flag (open-drain output; asserts on thermal /
                current-limit / over-temp; can be left NC)
  6 = OUT       Output
  7 = V+        Positive supply
  8 = ED        Enable drive (drive HIGH to enable; tie to V+ for always-on)

Footprint: Package_DIP:DIP-8_W7.62mm. The OPA454 only ships in SOIC-8
(and HSOIC PowerPAD), but Al's chips are mounted on SOIC->DIP adapters
that drop into DIP-8 sockets, same as the TL072 in this project.

Idempotent: re-running replaces an existing xmitter:OPA454 in the
library with the newly-built version. Other symbols are untouched.

Files are read/written as bytes to preserve line endings exactly, and
explicitly written without BOM. (PowerShell Set-Content -Encoding UTF8
would add a BOM that KiCad 10 silently treats as empty.)
"""

import sys

sys.stdout.reconfigure(encoding='utf-8')

SYMBOL_NAME = 'OPA454'
FOOTPRINT   = 'Package_DIP:DIP-8_W7.62mm'
DATASHEET   = 'https://www.ti.com/lit/ds/symlink/opa454.pdf'
KEYWORDS    = 'op-amp single HV high-voltage 100V OPA454'
DESCRIPTION = 'High-voltage op-amp, 100 V supply, current-limit + thermal status flag, DIP-8 carrier'
MFR         = 'Texas Instruments'
MPN         = 'OPA454AIDA'

# ---------------------------------------------------------------- properties

PROPS_HIDDEN = [
    ('Footprint',      FOOTPRINT),
    ('Datasheet',      DATASHEET),
    ('ki_keywords',    KEYWORDS),
    ('ki_description', DESCRIPTION),
    ('Manufacturer',   MFR),
    ('MPN',            MPN),
]

# --------------------------------------------------------- unit-A: triangle
# Triangle 15.24 x 15.24 mm body. Three signal pins only — V+/V- live on
# Unit B with the rest of the power/enable network.
#
# Triangle vertices: (-7.62, -7.62) -> (-7.62, 7.62) -> (7.62, 0).

UNIT_A_TRIANGLE = [(-7.62, -7.62), (-7.62, 7.62), (7.62, 0), (-7.62, -7.62)]

UNIT_A_PINS = [
    # (type, name, number, x, y, angle)
    ('input',  'IN-', '2', -10.16,  3.81,   0),
    ('input',  'IN+', '3', -10.16, -3.81,   0),
    ('output', 'OUT', '6',  10.16,  0,    180),
]

# -------------------------------------- unit-B: power + enable + status block
# Rectangle 15.24 mm wide x 22.86 mm tall. Holds the five "support" pins:
# power (V+/V- on top/bottom stubs), enable (ED/EDCOMM on the left side),
# and the open-drain status flag (STATFLG on the right). One Unit B placed
# per OPA454 — wire ED -> V+ rail, EDCOMM -> V- rail, STATFLG -> NC for
# the typical always-on grid_bias channel.
# All pin tips on the 1.27 mm grid.

UNIT_B_RECT = (-7.62, 11.43, 7.62, -11.43)   # (start_x, start_y, end_x, end_y)

UNIT_B_PINS = [
    # Top: V+
    ('power_in', 'V+',      '7',  0,  13.97, 270),
    # Bottom: V-
    ('power_in', 'V-',      '4',  0, -13.97,  90),
    # Left side: ED (enable drive), EDCOMM (enable reference)
    ('input',    'ED',      '8', -10.16,  3.81,   0),
    ('input',    'EDCOMM',  '1', -10.16, -3.81,   0),
    # Right side: STATFLG (open-drain status flag)
    ('open_collector', 'STATFLG', '5',  10.16,  0, 180),
]

# Reference / Value text positions — sit just outside the triangle body.
# (For Unit B the labels land inside the taller rectangle; user can drag
# after placement.)
REF_Y   =  8.89
VALUE_Y = -8.89


def pin_block(ptype, name, number, x, y, angle, indent):
    inner = indent + '  '
    return (
        f'{indent}(pin {ptype} line (at {x:g} {y:g} {angle}) (length 2.54)\n'
        f'{inner}(name "{name}" (effects (font (size 1.27 1.27))))\n'
        f'{inner}(number "{number}" (effects (font (size 1.27 1.27))))\n'
        f'{indent})\n'
    )


def build_symbol():
    """Return the full (symbol "OPA454" ...) block, with 2-space indent
    matching the rest of xmitter.kicad_sym."""

    out = []
    a = out.append

    a('(symbol "OPA454"\n')
    a('    (pin_names (offset 0.254))\n')
    a('    (exclude_from_sim no)\n')
    a('    (in_bom yes)\n')
    a('    (on_board yes)\n')

    # Reference + Value above/below the triangle body
    a('    (property "Reference" "U"\n')
    a(f'      (at 0 {REF_Y:g} 0)\n')
    a('      (effects (font (size 1.27 1.27)))\n')
    a('    )\n')
    a(f'    (property "Value" "{SYMBOL_NAME}"\n')
    a(f'      (at 0 {VALUE_Y:g} 0)\n')
    a('      (effects (font (size 1.27 1.27)))\n')
    a('    )\n')

    for prop_name, prop_val in PROPS_HIDDEN:
        a(f'    (property "{prop_name}" "{prop_val}"\n')
        a('      (at 0 0 0)\n')
        a('      (effects (font (size 1.27 1.27)) (hide yes))\n')
        a('    )\n')

    # Unit 1 — op-amp triangle (graphics + 5 pins in a single sub-symbol).
    # KiCad sub-symbol naming is NAME_{unit}_{body_style}: this is unit 1,
    # body_style 1 (standard view; no DeMorgan variant for an op-amp).
    pts = ' '.join(f'(xy {x:g} {y:g})' for x, y in UNIT_A_TRIANGLE)
    a('    (symbol "OPA454_1_1"\n')
    a('      (polyline\n')
    a(f'        (pts {pts})\n')
    a('        (stroke (width 0.254) (type default))\n')
    a('        (fill (type background))\n')
    a('      )\n')
    for (ptype, name, num, x, y, ang) in UNIT_A_PINS:
        a(pin_block(ptype, name, num, x, y, ang, '      '))
    a('    )\n')

    # Unit 2 — enable + status block. Naming NAME_{unit}_{body_style}: unit 2,
    # body_style 1. This is what makes Unit B placeable as a separate
    # selectable unit in the KiCad symbol-placement dialog.
    sx, sy, ex, ey = UNIT_B_RECT
    a('    (symbol "OPA454_2_1"\n')
    a('      (rectangle\n')
    a(f'        (start {sx:g} {sy:g})\n')
    a(f'        (end {ex:g} {ey:g})\n')
    a('        (stroke (width 0) (type default))\n')
    a('        (fill (type background))\n')
    a('      )\n')
    for (ptype, name, num, x, y, ang) in UNIT_B_PINS:
        a(pin_block(ptype, name, num, x, y, ang, '      '))
    a('    )\n')

    a('  )')
    return ''.join(out)


def end_of_sexp(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError('unbalanced parens')


def read_normalized(path):
    with open(path, 'rb') as f:
        raw = f.read()
    assert raw[:3] != b'\xef\xbb\xbf', f'unexpected BOM in {path}'
    crlf = b'\r\n' in raw
    text = raw.decode('utf-8').replace('\r\n', '\n')
    return text, crlf


def write_with_eol(path, text, crlf):
    data = text.encode('utf-8')
    if crlf:
        data = data.replace(b'\n', b'\r\n')
    with open(path, 'wb') as f:
        f.write(data)


sym_path = 'KiCAD/xmitter.kicad_sym'
sym, sym_crlf = read_normalized(sym_path)
print(f'{sym_path}: line endings = {"CRLF" if sym_crlf else "LF"}')

block = build_symbol()
print(f'Built OPA454 block: {len(block)} chars')

# Idempotent insert / replace
existing = sym.find(f'(symbol "{SYMBOL_NAME}"')
if existing >= 0:
    end = end_of_sexp(sym, existing)
    print(f'  OPA454 exists ({end - existing} chars); replacing')
    # Preserve the indent that prefixed the old (symbol "OPA454" — should be "  "
    line_start = sym.rfind('\n', 0, existing) + 1
    indent = sym[line_start:existing]
    # build_symbol() already emits with "  " indent — strip our leading "(symbol"
    # and re-prefix with the file's actual indent (should be identical).
    assert indent == '  ', f'unexpected indent before existing symbol: {indent!r}'
    sym_new = sym[:existing] + block + sym[end:]
else:
    print('  OPA454 not present; appending before library close')
    lib_open  = sym.find('(kicad_symbol_lib')
    lib_close = end_of_sexp(sym, lib_open)
    # Insert before the library's closing ')'. Match the 2-space indent
    # the existing symbols use, and add a trailing newline.
    insertion = '  ' + block + '\n'
    sym_new = sym[:lib_close - 1] + insertion + sym[lib_close - 1:]

write_with_eol(sym_path, sym_new, sym_crlf)
print(f'  wrote {sym_path}  ({len(sym_new)} chars)')

print()
print(f'OPA454 symbol: 2 units, 8 pins total')
print(f'  Unit A (op-amp triangle):    3 pins -- IN-(2), IN+(3), OUT(6)')
print(f'  Unit B (power+enable+status): 5 pins -- V+(7), V-(4), ED(8), EDCOMM(1), STATFLG(5)')
print(f'  Footprint: {FOOTPRINT}')
print(f'  MPN:       {MPN}')

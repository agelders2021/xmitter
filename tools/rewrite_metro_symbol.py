"""One-shot: rewrite the xmitter:Metro_ESP32S3 symbol with a configurable
pin list. Updates both:
  - KiCAD/xmitter.kicad_sym       (the live library)
  - KiCAD/arduino.kicad_sch       (the cached lib_symbols block)

Pin list is defined in LEFT_PINS / RIGHT_PINS below — edit those to add
or remove pins. Body width is fixed at 25.4 mm; body height grows to fit
the longest column.

Idempotent: re-running replaces the existing symbol with the configured
one. Wires on the arduino sheet are NOT touched (deleted on the first
pass — wires the user has added since are preserved). A CS_DAC
hierarchical label is added on first run only.

Files are read/written as bytes to preserve line endings exactly, and
explicitly written without BOM. (PowerShell Set-Content -Encoding UTF8
would add a BOM that KiCad 10 silently treats as empty.)
"""

import re
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')

# ----------------------------------------------------------------- pin list
# Each entry: (pin_type, display_name, pin_number_string)
# Pin number string MUST match the footprint pad number when one is chosen.
# pin_type ∈ {power_in, power_out, input, output, bidirectional, passive,
#             open_collector, open_emitter, no_connect, free, unspecified}

LEFT_PINS = [
    # power
    ('power_in',      'GND',          'GND_L'),
    ('power_out',     '5V',           '5V'),
    ('power_out',     '3V3',          '3V3_L'),
    # control
    ('passive',       'AREF',         'AREF'),
    ('input',         'RESET',        'RESET'),
    # UART
    ('input',         'D0/RX',        'D0'),
    ('output',        'D1/TX',        'D1'),
    # FREQ encoder (firmware uses D2/D3 for quadrature - I2C goes off-board via STEMMA QT to Si5351)
    ('input',         'D2/FREQ_A',    'D2'),
    ('input',         'D3/FREQ_B',    'D3'),
    # keyer
    ('input',         'D4/DIT',       'D4'),
    # spare digital
    ('passive',       'D7',           'D7'),
    ('passive',       'D8',           'D8'),
    ('passive',       'D9',           'D9'),
]

RIGHT_PINS = [
    # keyer + LED
    ('input',         'D5/DAH',       'D5'),
    ('output',        'D6/TX_LED',    'D6'),
    # SPI to MCP4921
    ('output',        'D10/CS_DAC',   'D10'),
    ('output',        'D11/MOSI',     'D11'),
    ('output',        'D13/SCK',      'D13'),
    # spares
    ('passive',       'D12',          'D12'),
    ('passive',       'A0',           'A0'),
    ('passive',       'A1',           'A1'),
    ('passive',       'A2',           'A2'),
    ('passive',       'A3',           'A3'),
    ('passive',       'A4',           'A4'),
    ('passive',       'A5',           'A5'),
]

# ---------------------------------------------------------- geometry config
BODY_HALF_WIDTH = 12.7        # 25.4 mm total
PIN_PITCH       = 2.54
PIN_LENGTH      = 2.54
PIN_X_LEFT      = -(BODY_HALF_WIDTH + PIN_LENGTH)  # -15.24
PIN_X_RIGHT     =  (BODY_HALF_WIDTH + PIN_LENGTH)  # +15.24

n_left  = len(LEFT_PINS)
n_right = len(RIGHT_PINS)
n_max   = max(n_left, n_right)

# Center pin column vertically. y positions: (n_max-1)/2 above and below 0.
def y_positions(n):
    return [((n - 1) / 2 - i) * PIN_PITCH for i in range(n)]

ys_left  = y_positions(n_left)
ys_right = y_positions(n_right)

# Body height: extend one pitch beyond the outermost pin on each side
y_max_pin = (n_max - 1) / 2 * PIN_PITCH
BODY_HALF_HEIGHT = y_max_pin + PIN_PITCH / 2 + 0.635   # ~1/4 pitch margin
# Round to grid (0.635)
BODY_HALF_HEIGHT = round(BODY_HALF_HEIGHT / 0.635) * 0.635

REF_Y   = BODY_HALF_HEIGHT + 1.27
VALUE_Y = -(BODY_HALF_HEIGHT + 1.27)

# ---------------------------------------------------------- symbol builder

def pin_block(ptype, name, number, x, y, angle, base_indent):
    """Render one (pin ...) s-expression. base_indent is the leading
    whitespace for each line (the indent of the (pin ...) opener)."""
    inner = base_indent + '\t'
    return (
        f'{base_indent}(pin {ptype} line\n'
        f'{inner}(at {x:g} {y:g} {angle})\n'
        f'{inner}(length {PIN_LENGTH:g})\n'
        f'{inner}(name "{name}"\n'
        f'{inner}\t(effects (font (size 1.27 1.27)))\n'
        f'{inner})\n'
        f'{inner}(number "{number}"\n'
        f'{inner}\t(effects (font (size 1.27 1.27)))\n'
        f'{inner})\n'
        f'{base_indent})\n'
    )

def build_symbol(name_in_sym):
    """Render the full (symbol ...) block.

    All inner lines use a placeholder TAB indent. The caller re-indents
    by substituting each '\\t' with the appropriate per-file indent unit
    (2 spaces for kicad_sym, tab for kicad_sch)."""
    parts = []
    p = parts.append
    p(f'(symbol "{name_in_sym}"\n')
    p('\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)\n')
    p('\t\t(exclude_from_sim no)\n')
    p('\t\t(in_bom yes)\n')
    p('\t\t(on_board yes)\n')
    p(f'\t\t(property "Reference" "U"\n\t\t\t(at 0 {REF_Y:g} 0)\n'
      '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
    p(f'\t\t(property "Value" "Metro_ESP32S3"\n\t\t\t(at 0 {VALUE_Y:g} 0)\n'
      '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
    for prop_name, prop_val in [
        ('Footprint', ''),
        ('Datasheet', 'https://learn.adafruit.com/adafruit-metro-esp32-s3'),
        ('ki_keywords', 'ESP32-S3 Metro Arduino Adafruit'),
        ('ki_description', 'Adafruit Metro ESP32-S3 (xmitter project compact symbol)'),
        ('Manufacturer', 'Adafruit Industries'),
        ('MPN', 'Adafruit #5500'),
    ]:
        p(f'\t\t(property "{prop_name}" "{prop_val}"\n\t\t\t(at 0 0 0)\n'
          '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n')

    # Body rectangle as subunit _0_1
    p('\t\t(symbol "Metro_ESP32S3_0_1"\n')
    p(f'\t\t\t(rectangle\n\t\t\t\t(start -{BODY_HALF_WIDTH:g} {BODY_HALF_HEIGHT:g})\n'
      f'\t\t\t\t(end {BODY_HALF_WIDTH:g} -{BODY_HALF_HEIGHT:g})\n'
      '\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n'
      '\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')

    # Pins as subunit _1_1
    p('\t\t(symbol "Metro_ESP32S3_1_1"\n')
    for (ptype, pname, pnum), y in zip(LEFT_PINS, ys_left):
        p(pin_block(ptype, pname, pnum, PIN_X_LEFT, y, 0, '\t\t\t'))
    for (ptype, pname, pnum), y in zip(RIGHT_PINS, ys_right):
        p(pin_block(ptype, pname, pnum, PIN_X_RIGHT, y, 180, '\t\t\t'))
    p('\t\t)\n')
    p('\t)')

    return ''.join(parts)

# ---------------------------------------------------------- file I/O helpers

def end_of_sexp(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(': depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0: return i + 1
    raise ValueError('unbalanced')

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

def reindent(template, file_indent_unit, base_indent):
    """Replace each '\t' in template (other than the very first line) with
    file_indent_unit, then prepend base_indent to each line after the first."""
    lines = template.split('\n')
    out = [lines[0]]
    for ln in lines[1:]:
        out.append(base_indent + ln.replace('\t', file_indent_unit))
    return '\n'.join(out)

# ------------------------------- 1. xmitter.kicad_sym (live library)
sym, sym_crlf = read_normalized('KiCAD/xmitter.kicad_sym')
print(f'xmitter.kicad_sym: line endings = {"CRLF" if sym_crlf else "LF"}')

m_idx = sym.find('"Metro_ESP32S3"')
back = sym.rfind('(symbol ', 0, m_idx)
metro_end = end_of_sexp(sym, back)
print(f'  old Metro symbol: {metro_end - back} chars')

line_start = sym.rfind('\n', 0, back) + 1
indent = sym[line_start:back]   # "  " (2 spaces)

template_sym = build_symbol('Metro_ESP32S3')
# kicad_sym uses 2-space indent units; the template uses '\t' as one indent level
new_metro_sym = reindent(template_sym, '  ', indent)
print(f'  new Metro symbol: {len(new_metro_sym)} chars')

sym_new = sym[:back] + new_metro_sym + sym[metro_end:]
write_with_eol('KiCAD/xmitter.kicad_sym', sym_new, sym_crlf)
print(f'  wrote KiCAD/xmitter.kicad_sym  ({len(sym_new)} chars)')

# ------------------------------- 2. arduino.kicad_sch (cached lib_symbols)
sch, sch_crlf = read_normalized('KiCAD/arduino.kicad_sch')
print(f'\narduino.kicad_sch: line endings = {"CRLF" if sch_crlf else "LF"}')

m_idx2 = sch.find('"xmitter:Metro_ESP32S3"')
back2 = sch.rfind('(symbol ', 0, m_idx2)
metro_end2 = end_of_sexp(sch, back2)
print(f'  old cached Metro: {metro_end2 - back2} chars')

line_start2 = sch.rfind('\n', 0, back2) + 1
indent2 = sch[line_start2:back2]   # '\t\t'

template_sch = build_symbol('xmitter:Metro_ESP32S3')
# kicad_sch uses tab indent unit (each '\t' in template -> one tab)
new_metro_sch = reindent(template_sch, '\t', indent2)
print(f'  new cached Metro: {len(new_metro_sch)} chars')

sch_new = sch[:back2] + new_metro_sch + sch[metro_end2:]

# ------------------------------- 3. (Wires preserved.)
# Earlier versions of this script unconditionally deleted ALL wires on the
# arduino sheet — that was correct only for the very first conversion. Now
# the user has live wiring that must NOT be touched. So we don't touch wires.

# ------------------------------- 4. CS_DAC hierarchical label (idempotent)
if '"CS_DAC"' in sch_new:
    print('  CS_DAC label already present, skipping add')
else:
    cs_dac_uuid = str(uuid.uuid4())
    new_label = (
        '\t(hierarchical_label "CS_DAC"\n'
        '\t\t(shape output)\n'
        '\t\t(at 111.76 95.25 0)\n'
        '\t\t(effects\n'
        '\t\t\t(font\n'
        '\t\t\t\t(size 1.27 1.27)\n'
        '\t\t\t)\n'
        '\t\t\t(justify left)\n'
        '\t\t)\n'
        f'\t\t(uuid "{cs_dac_uuid}")\n'
        '\t)\n'
    )
    ins_marker = sch_new.find('\t(symbol\n\t\t(lib_id ')
    if ins_marker < 0:
        raise RuntimeError('could not find insertion point for CS_DAC label')
    ins_line = sch_new.rfind('\n', 0, ins_marker) + 1
    sch_new = sch_new[:ins_line] + new_label + sch_new[ins_line:]
    print('  added CS_DAC hierarchical label')

write_with_eol('KiCAD/arduino.kicad_sch', sch_new, sch_crlf)
print(f'  wrote KiCAD/arduino.kicad_sch  ({len(sch_new)} chars)')

print(f'\nSymbol summary: {n_left} pins LEFT, {n_right} pins RIGHT, total {n_left+n_right}')
print(f'Body: {BODY_HALF_WIDTH*2:g} mm wide × {BODY_HALF_HEIGHT*2:g} mm tall')

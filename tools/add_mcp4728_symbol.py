"""Add an xmitter:MCP4728 symbol to KiCAD/xmitter.kicad_sym.

Custom symbol for the Adafruit MCP4728 breakout (4-channel 12-bit I2C
DAC). The breakout exposes 10 pins on a 0.1" through-hole header plus
STEMMA QT JST connectors that duplicate VIN/GND/SDA/SCL. The symbol
covers only the 0.1" header pins; the schematic shows the chip as a
through-hole module, not a bare IC.

Idempotent: re-running replaces an existing xmitter:MCP4728 in the
library with the newly-built version. Other symbols are untouched.

Files are read/written as bytes to preserve line endings exactly, and
explicitly written without BOM. (PowerShell Set-Content -Encoding UTF8
would add a BOM that KiCad 10 silently treats as empty.)
"""

import sys

sys.stdout.reconfigure(encoding='utf-8')

# ----------------------------------------------------------------- pin list
# Each entry: (pin_type, display_name, pin_number_string)
# Pin numbers 1-10 match the breakout's 0.1" header pin order.

LEFT_PINS = [
    ('power_in',       'VIN',   '1'),
    ('power_in',       'GND',   '2'),
    ('input',          'SCL',   '3'),
    ('bidirectional',  'SDA',   '4'),
    ('input',          'LDAC',  '5'),
    ('open_collector', 'RDY',   '6'),
]

RIGHT_PINS = [
    ('output', 'VA', '7'),
    ('output', 'VB', '8'),
    ('output', 'VC', '9'),
    ('output', 'VD', '10'),
]

# ---------------------------------------------------------- geometry config
BODY_HALF_WIDTH  = 7.62        # 15.24 mm total — short labels, modest width
PIN_PITCH        = 2.54
PIN_LENGTH       = 2.54
PIN_X_LEFT       = -(BODY_HALF_WIDTH + PIN_LENGTH)
PIN_X_RIGHT      =  (BODY_HALF_WIDTH + PIN_LENGTH)

n_max = max(len(LEFT_PINS), len(RIGHT_PINS))


def y_positions(n):
    return [((n - 1) / 2 - i) * PIN_PITCH for i in range(n)]


ys_left  = y_positions(len(LEFT_PINS))
ys_right = y_positions(len(RIGHT_PINS))

y_max_pin = (n_max - 1) / 2 * PIN_PITCH
BODY_HALF_HEIGHT = round((y_max_pin + 1.27) / 0.635) * 0.635

REF_Y   = BODY_HALF_HEIGHT + 1.27
VALUE_Y = -(BODY_HALF_HEIGHT + 1.27)


def pin_block(ptype, name, number, x, y, angle, base_indent):
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
    parts = []
    p = parts.append
    p(f'(symbol "{name_in_sym}"\n')
    p('\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)\n')
    p('\t\t(exclude_from_sim no)\n')
    p('\t\t(in_bom yes)\n')
    p('\t\t(on_board yes)\n')
    p(f'\t\t(property "Reference" "U"\n\t\t\t(at 0 {REF_Y:g} 0)\n'
      '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
    p(f'\t\t(property "Value" "MCP4728"\n\t\t\t(at 0 {VALUE_Y:g} 0)\n'
      '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
    for prop_name, prop_val in [
        ('Footprint', ''),
        ('Datasheet', 'https://learn.adafruit.com/adafruit-mcp4728-i2c-quad-dac'),
        ('ki_keywords', 'MCP4728 I2C DAC Adafruit quad'),
        ('ki_description', 'Adafruit MCP4728 4-channel 12-bit I2C DAC breakout (xmitter project symbol)'),
        ('Manufacturer', 'Adafruit Industries'),
        ('MPN', 'Adafruit 4470'),
    ]:
        p(f'\t\t(property "{prop_name}" "{prop_val}"\n\t\t\t(at 0 0 0)\n'
          '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n')

    p('\t\t(symbol "MCP4728_0_1"\n')
    p(f'\t\t\t(rectangle\n\t\t\t\t(start -{BODY_HALF_WIDTH:g} {BODY_HALF_HEIGHT:g})\n'
      f'\t\t\t\t(end {BODY_HALF_WIDTH:g} -{BODY_HALF_HEIGHT:g})\n'
      '\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n'
      '\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')

    p('\t\t(symbol "MCP4728_1_1"\n')
    for (ptype, pname, pnum), y in zip(LEFT_PINS, ys_left):
        p(pin_block(ptype, pname, pnum, PIN_X_LEFT, y, 0, '\t\t\t'))
    for (ptype, pname, pnum), y in zip(RIGHT_PINS, ys_right):
        p(pin_block(ptype, pname, pnum, PIN_X_RIGHT, y, 180, '\t\t\t'))
    p('\t\t)\n')
    p('\t)')

    return ''.join(parts)


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
    lines = template.split('\n')
    out = [lines[0]]
    for ln in lines[1:]:
        out.append(base_indent + ln.replace('\t', file_indent_unit))
    return '\n'.join(out)


sym, sym_crlf = read_normalized('KiCAD/xmitter.kicad_sym')
print(f'xmitter.kicad_sym: line endings = {"CRLF" if sym_crlf else "LF"}')

template = build_symbol('MCP4728')

# If the symbol already exists in the library, replace it. Otherwise insert
# before the library's closing paren.
existing = sym.find('(symbol "MCP4728"')
if existing >= 0:
    end = end_of_sexp(sym, existing)
    print(f'  MCP4728 exists ({end - existing} chars); replacing')
    line_start = sym.rfind('\n', 0, existing) + 1
    indent = sym[line_start:existing]
    new_sym = reindent(template, '  ', indent)
    sym_new = sym[:existing] + new_sym + sym[end:]
else:
    print('  MCP4728 not present; appending')
    # Find the library's closing paren — last ')' in the file (modulo trailing whitespace)
    # Library top-level: '(kicad_symbol_lib ... )' — find its matching close
    lib_open = sym.find('(kicad_symbol_lib')
    lib_close = end_of_sexp(sym, lib_open)
    # Insert before the closing paren, at indent of "  " (2 spaces — matches
    # the existing symbol blocks in this file)
    new_sym = reindent(template, '  ', '  ')
    insertion = '  ' + new_sym + '\n'
    sym_new = sym[:lib_close - 1] + insertion + sym[lib_close - 1:]

write_with_eol('KiCAD/xmitter.kicad_sym', sym_new, sym_crlf)
print(f'  wrote KiCAD/xmitter.kicad_sym  ({len(sym_new)} chars)')
print(f'\nMCP4728 symbol: {len(LEFT_PINS)} pins LEFT, {len(RIGHT_PINS)} pins RIGHT')
print(f'Body: {BODY_HALF_WIDTH*2:g} mm wide × {BODY_HALF_HEIGHT*2:g} mm tall')

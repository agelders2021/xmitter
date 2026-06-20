"""Extract every IC's pin-by-pin connectivity on buffer_keyer.kicad_sch.

For each chip pin, report: what is wired/labeled/power-port-connected
to it. Floating pins (no wire, no label, no NC) get a warning. Used to
find missing interconnections after manual schematic edits.
"""
import re
import math
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')


def eos(s, start):
    d = 0
    i = start
    while i < len(s):
        if s[i] == '(':
            d += 1
        elif s[i] == ')':
            d -= 1
            if d == 0:
                return i + 1
        i += 1
    raise ValueError('unbalanced')


with open('KiCAD/buffer_keyer.kicad_sch', 'r', encoding='utf-8') as f:
    sch = f.read()

ls = sch.find('(lib_symbols')
ls_end = eos(sch, ls)
lib_block = sch[ls:ls_end]
inst = sch[ls_end:]

# Pin defs per cached library symbol.
lib_pins = defaultdict(list)
i = 0
while True:
    m = re.search(r'\(symbol "([^"]+)"\n', lib_block[i:])
    if not m:
        break
    sym_name = m.group(1)
    sym_start = i + m.start()
    sym_end = eos(lib_block, sym_start)
    sym_body = lib_block[sym_start:sym_end]
    for pm in re.finditer(
        r'\(pin\s+(\w+)\s+\w+\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\)\s*\(length\s+([\d.]+)\)\s*\(name\s+"([^"]*)"[\s\S]*?\(number\s+"([^"]*)"',
        sym_body
    ):
        ptype, lx, ly, lang, plen, pname, pnum = pm.groups()
        lib_pins[sym_name].append((pnum, pname, ptype, float(lx), float(ly), int(lang), float(plen)))
    i = sym_end

# Symbol instances.
instances = []
i = 0
while True:
    m = re.search(
        r'\(symbol\s*\(lib_id "([^"]+)"\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\)([^(]*)',
        inst[i:]
    )
    if not m:
        break
    libid = m.group(1)
    ix, iy, iang = float(m.group(2)), float(m.group(3)), int(m.group(4))
    mirror_chunk = m.group(5)
    mirror = None
    mm = re.search(r'\(mirror\s+(\w+)\)', mirror_chunk)
    if mm:
        mirror = mm.group(1)
    sym_start = i + m.start()
    sym_end = eos(inst, sym_start)
    sym_body = inst[sym_start:sym_end]
    rm = re.search(r'\(property "Reference" "([^"]+)"', sym_body)
    vm = re.search(r'\(property "Value" "([^"]+)"', sym_body)
    ref = rm.group(1) if rm else '?'
    val = vm.group(1) if vm else '?'
    if not ref.startswith('#'):
        instances.append((ref, val, libid, ix, iy, iang, mirror))
    i = sym_end


def transform(lx, ly, ix, iy, iang, mirror):
    if mirror == 'x':
        lx = -lx
    if mirror == 'y':
        ly = -ly
    rad = math.radians(iang)
    rx = lx * math.cos(rad) - ly * math.sin(rad)
    ry = lx * math.sin(rad) + ly * math.cos(rad)
    gx = ix + rx
    gy = iy - ry  # KiCad y-flip from symbol-editor coords to schematic coords
    return (round(gx, 2), round(gy, 2))


chip_pins = {}
for ref, val, libid, ix, iy, iang, mirror in instances:
    if libid.startswith('power:'):
        continue
    if libid not in lib_pins:
        continue
    pins = []
    for pnum, pname, ptype, lx, ly, lang, plen in lib_pins[libid]:
        gx, gy = transform(lx, ly, ix, iy, iang, mirror)
        pins.append((pnum, pname, ptype, gx, gy))
    chip_pins[ref] = (val, libid, pins)

wires = []
for m in re.finditer(
    r'\(wire\s*\(pts\s*\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)\s*\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)\s*\)',
    inst
):
    x1, y1, x2, y2 = map(float, m.groups())
    wires.append((round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)))

hier_labels = []
for m in re.finditer(
    r'\(hierarchical_label\s+"([^"]+)"\s*\(shape\s+(\w+)\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)',
    inst
):
    hier_labels.append((m.group(1), m.group(2),
                        round(float(m.group(3)), 2), round(float(m.group(4)), 2)))

local_labels = []
for m in re.finditer(
    r'\(label\s+"([^"]+)"\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)',
    inst
):
    local_labels.append((m.group(1), round(float(m.group(2)), 2),
                         round(float(m.group(3)), 2)))

power_ports = []
for m in re.finditer(
    r'\(symbol\s*\(lib_id "(power:[^"]+)"\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\)[\s\S]{0,500}?\(property "Value" "([^"]+)"',
    inst
):
    val = m.group(5)
    x, y = float(m.group(2)), float(m.group(3))
    power_ports.append((val, round(x, 2), round(y, 2)))

ncs = []
for m in re.finditer(r'\(no_connect\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)', inst):
    ncs.append((round(float(m.group(1)), 2), round(float(m.group(2)), 2)))

print(f'Wires: {len(wires)}  Hier labels: {len(hier_labels)}  '
      f'Local labels: {len(local_labels)}  Power ports: {len(power_ports)}  '
      f'NCs: {len(ncs)}')
print(f'Chips with known pin definitions: {len(chip_pins)}')

# Union-Find: every endpoint with the same global coord is electrically joined.
parent = {}


def find(p):
    while parent[p] != p:
        parent[p] = parent[parent[p]]
        p = parent[p]
    return p


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb


def add_pt(p):
    if p not in parent:
        parent[p] = p


for x1, y1, x2, y2 in wires:
    add_pt((x1, y1)); add_pt((x2, y2)); union((x1, y1), (x2, y2))
for ref, (val, libid, pins) in chip_pins.items():
    for pnum, pname, ptype, gx, gy in pins:
        add_pt((gx, gy))
for nm, sh, x, y in hier_labels:
    add_pt((x, y))
for nm, x, y in local_labels:
    add_pt((x, y))
for nm, x, y in power_ports:
    add_pt((x, y))
for x, y in ncs:
    add_pt((x, y))

net_members = defaultdict(list)
for ref, (val, libid, pins) in chip_pins.items():
    for pnum, pname, ptype, gx, gy in pins:
        if (gx, gy) in parent:
            net_members[find((gx, gy))].append(('PIN', f'{ref}.{pnum}({pname})'))
for nm, sh, x, y in hier_labels:
    if (x, y) in parent:
        net_members[find((x, y))].append(('HIER', nm))
for nm, x, y in local_labels:
    if (x, y) in parent:
        net_members[find((x, y))].append(('LABEL', nm))
for nm, x, y in power_ports:
    if (x, y) in parent:
        net_members[find((x, y))].append(('PWR', nm))
for x, y in ncs:
    if (x, y) in parent:
        net_members[find((x, y))].append(('NC', '-'))

CHIPS_OF_INTEREST = ('MC1496', 'MCP4921', 'MCP4728', 'LM7171', 'OPA454', 'TL07')

print('\n========== Per-chip pin connectivity ==========')
for ref in sorted(chip_pins):
    val, libid, pins = chip_pins[ref]
    if not any(s in libid for s in CHIPS_OF_INTEREST):
        continue
    print(f'\n{ref} ({val}):')
    for pnum, pname, ptype, gx, gy in sorted(pins,
            key=lambda x: int(x[0]) if x[0].isdigit() else 99):
        nid = find((gx, gy)) if (gx, gy) in parent else None
        members = net_members.get(nid, []) if nid else []
        others = [f'{kind}:{name}' for kind, name in members
                  if not (kind == 'PIN' and name.startswith(f'{ref}.{pnum}('))]
        tag = '⚠ FLOATING' if not others else '→ ' + ', '.join(others[:8])
        more = '  ...' if len(others) > 8 else ''
        print(f'  pin {pnum:>2} {pname:<14} ({ptype:<14})  {tag}{more}')

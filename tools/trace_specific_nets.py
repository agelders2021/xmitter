"""Trace specific pin connections for LM7171 feedback resistors and
null-injection resistors. Used for deep-dive verification of buffer_keyer."""
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


with open('KiCAD/buffer_keyer.kicad_sch', 'r', encoding='utf-8') as f:
    sch = f.read()

ls = sch.find('(lib_symbols')
ls_end = eos(sch, ls)
lib_block = sch[ls:ls_end]
inst_blk = sch[ls_end:]

lib_pins = defaultdict(list)
i = 0
while True:
    m = re.search(r'\(symbol "([^"]+)"\n', lib_block[i:])
    if not m:
        break
    sym_name = m.group(1)
    sym_start = i + m.start()
    sym_end = eos(lib_block, sym_start)
    body = lib_block[sym_start:sym_end]
    for pm in re.finditer(
        r'\(pin\s+(\w+)\s+\w+\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\)\s*\(length\s+([\d.]+)\)\s*\(name\s+"([^"]*)"[\s\S]*?\(number\s+"([^"]*)"',
        body
    ):
        ptype, lx, ly, lang, plen, pname, pnum = pm.groups()
        lib_pins[sym_name].append((pnum, pname, ptype, float(lx), float(ly)))
    i = sym_end

instances = []
i = 0
while True:
    m = re.search(
        r'\(symbol\s*\(lib_id "([^"]+)"\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\)([^(]*)',
        inst_blk[i:]
    )
    if not m:
        break
    libid = m.group(1)
    ix, iy, iang = float(m.group(2)), float(m.group(3)), int(m.group(4))
    mirror_m = re.search(r'\(mirror\s+(\w+)\)', m.group(5))
    mirror = mirror_m.group(1) if mirror_m else None
    sym_start = i + m.start()
    sym_end = eos(inst_blk, sym_start)
    body = inst_blk[sym_start:sym_end]
    rm = re.search(r'\(property "Reference" "([^"]+)"', body)
    vm = re.search(r'\(property "Value" "([^"]+)"', body)
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
    return (round(ix + rx, 2), round(iy - ry, 2))


pin_pos = {}
for ref, val, libid, ix, iy, iang, mirror in instances:
    if libid not in lib_pins:
        continue
    for pnum, pname, ptype, lx, ly in lib_pins[libid]:
        pin_pos[(ref, pnum)] = (*transform(lx, ly, ix, iy, iang, mirror), pname)

wires = []
for m in re.finditer(
    r'\(wire\s*\(pts\s*\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)\s*\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)',
    inst_blk
):
    wires.append((round(float(m.group(1)), 2), round(float(m.group(2)), 2),
                  round(float(m.group(3)), 2), round(float(m.group(4)), 2)))

hier = [(m.group(1), round(float(m.group(2)), 2), round(float(m.group(3)), 2))
        for m in re.finditer(
            r'\(hierarchical_label\s+"([^"]+)"\s*\(shape\s+\w+\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)',
            inst_blk
        )]
pwr = []
for m in re.finditer(
    r'\(symbol\s*\(lib_id "(power:[^"]+)"\)\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\d+\)([\s\S]{0,800}?)\(property "Value" "([^"]+)"',
    inst_blk
):
    val_str = m.group(5)
    x, y = float(m.group(2)), float(m.group(3))
    pwr.append((val_str, round(x, 2), round(y, 2)))

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


def add(p):
    if p not in parent:
        parent[p] = p


for x1, y1, x2, y2 in wires:
    add((x1, y1)); add((x2, y2)); union((x1, y1), (x2, y2))
for (ref, pn), (gx, gy, _) in pin_pos.items():
    add((gx, gy))
for nm, x, y in hier:
    add((x, y))
for nm, x, y in pwr:
    add((x, y))

members = defaultdict(list)
for (ref, pn), (gx, gy, pn_name) in pin_pos.items():
    if (gx, gy) in parent:
        members[find((gx, gy))].append(f'{ref}.{pn}({pn_name})')
for nm, x, y in hier:
    if (x, y) in parent:
        members[find((x, y))].append(f'HIER:{nm}')
for nm, x, y in pwr:
    if (x, y) in parent:
        members[find((x, y))].append(f'PWR:{nm}')

targets = [
    ('RF_OP', '1'), ('RF_OP', '2'),
    ('RG_OP', '1'), ('RG_OP', '2'),
    ('RF_OP1', '1'), ('RF_OP1', '2'),
    ('RG_OP1', '1'), ('RG_OP1', '2'),
    ('R14', '1'), ('R14', '2'),
    ('R15', '1'), ('R15', '2'),
    ('R_INJ1', '1'), ('R_INJ1', '2'),
    ('R_INJ2', '1'), ('R_INJ2', '2'),
    ('C_IN', '1'), ('C_IN', '2'),
    ('C_IN1', '1'), ('C_IN1', '2'),
    ('C_OP_OUT', '1'), ('C_OP_OUT', '2'),
    ('C_OP_OUT1', '1'), ('C_OP_OUT1', '2'),
]

print('Specific pin nets:')
for ref, pn in targets:
    key = (ref, pn)
    if key not in pin_pos:
        print(f'  {ref}.{pn}: NOT FOUND')
        continue
    gx, gy, pn_name = pin_pos[key]
    nid = find((gx, gy)) if (gx, gy) in parent else None
    nlist = members.get(nid, [])
    others = [n for n in nlist if not n.startswith(f'{ref}.{pn}(')]
    if not others:
        print(f'  {ref}.{pn} at ({gx},{gy}): FLOATING')
    else:
        print(f'  {ref}.{pn} at ({gx},{gy}): {", ".join(others)}')

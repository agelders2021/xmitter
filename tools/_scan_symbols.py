"""One-off: extract every symbol placement from a KiCad 10 sch file.
Prints refdes, lib_id, value, position, rotation, and property list.
"""
import re, sys, pathlib

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding='utf-8')

# Simple s-expr symbol block detector: walk with a paren counter starting at "(symbol"
i = 0
symbols = []
while True:
    idx = text.find('\n\t(symbol\n', i)
    if idx < 0:
        break
    # find end by paren balance
    depth = 0
    j = idx
    while j < len(text):
        c = text[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                j += 1
                break
        j += 1
    block = text[idx:j]
    i = j
    lib = re.search(r'\(lib_id "([^"]+)"\)', block)
    at  = re.search(r'\(at ([\d\.\-]+) ([\d\.\-]+)(?: ([\d\.\-]+))?\)', block)
    ref = re.search(r'\(property "Reference" "([^"]+)"', block)
    val = re.search(r'\(property "Value" "([^"]+)"', block)
    ft  = re.search(r'\(property "Footprint" "([^"]+)"', block)
    if not ref:
        continue
    symbols.append({
        'ref': ref.group(1),
        'lib': lib.group(1) if lib else '?',
        'val': val.group(1) if val else '',
        'x':   at.group(1) if at else '?',
        'y':   at.group(2) if at else '?',
        'rot': at.group(3) if at and at.group(3) else '0',
        'ft':  ft.group(1) if ft else '',
    })

# Sort by refdes prefix + numeric suffix
def refkey(r):
    m = re.match(r'([A-Za-z]+)(\d+)', r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)

symbols.sort(key=lambda s: refkey(s['ref']))

# Print by category
prefixes = sorted(set(refkey(s['ref'])[0] for s in symbols))
for p in prefixes:
    print(f'=== {p} ===')
    for s in symbols:
        if refkey(s['ref'])[0] == p:
            print(f"  {s['ref']:6} {s['lib']:35} val={s['val']:25} pos=({s['x']:>7},{s['y']:>7}) rot={s['rot']:>3}")

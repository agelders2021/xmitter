"""Generate a bin-sort inventory of R / C / Q components across all
xmitter KiCad schematics.

Walks the analog root + sub-sheets, the bias board, and the front-panel
board.  Aggregates by (component-type, value), then proposes a bin
allocation that fits in 24 or fewer physical storage bins.

Outputs:
  Documentation/component_inventory.csv   -- full detail, one row per
                                             unique (type, value)
  Documentation/component_bins.csv        -- 24-bin allocation, one row
                                             per bin with contents
"""
import re
import sys
import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent

SHEETS = [
    ('analog',       'KiCAD/analog/analog.kicad_sch'),
    ('arduino',      'KiCAD/analog/arduino.kicad_sch'),
    ('vfo_buffer',   'KiCAD/analog/buffer_keyer.kicad_sch'),
    ('vfo',          'KiCAD/analog/vfo.kicad_sch'),
    ('interface',    'KiCAD/analog/interface.kicad_sch'),
    ('bias',         'KiCAD/bias/bias.kicad_sch'),
    ('front_panel',  'KiCAD/frontpanel/frontpanel.kicad_sch'),
]

TYPE_MAP = {
    'Device:R':                 ('R', 'axial'),
    'Device:R_US':              ('R', 'axial'),
    'Device:R_Small':           ('R', 'axial'),
    'Device:R_Potentiometer':   ('R', 'pot'),
    'Device:R_Potentiometer_US':('R', 'pot'),
    'Device:C':                 ('C', 'ceramic'),
    'Device:C_Small':           ('C', 'ceramic'),
    'Device:C_Polarized':       ('C', 'electrolytic'),
    'Device:C_Polarized_Small': ('C', 'electrolytic'),
    'Transistor_FET:2N7000':    ('Q', '2N7000'),
    'xmitter:J310':             ('Q', 'J310'),
}

# lib_id patterns that identify PLUG-IN MODULES (Adafruit breakouts, panel
# modules, connectors) rather than raw ICs on the board.  Exclude these
# from the "IC" bin category; they aren't stored loose in parts drawers.
IC_EXCLUDE_PATTERNS = [
    r'Adafruit_',                # any Adafruit breakout
    r'^xmitter:MCP472[58]$',     # xmitter:MCP4725, xmitter:MCP4728 -- both are breakout symbols
    r'^xmitter:Metro_',          # Metro ESP32-S3 carrier
    r'^xmitter:LCD_',            # WH2004A LCD module
    r'^xmitter:Encoder_',        # MBL-600 / other encoder modules
    r'^xmitter:Si5351',          # Si5351A STEMMA breakout
    r'^Connector:',              # 8P8C, headers, etc. -- get their own bin already if needed
    r'^Device:',                 # covered above under R/C
    r'^Transistor_',             # covered above under Q
    r'Breakout',                 # anything else with Breakout in the name
    r'Module',                   # anything else with Module in the name
]
IC_EXCLUDE_RE = re.compile('|'.join(IC_EXCLUDE_PATTERNS), re.IGNORECASE)


def collect_symbols(path):
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    in_lib = False
    depth = 0
    start = 0
    for i, ln in enumerate(lines):
        if '(lib_symbols' in ln and not in_lib:
            in_lib = True
            depth = ln.count('(') - ln.count(')')
            continue
        if in_lib:
            depth += ln.count('(') - ln.count(')')
            if depth <= 0:
                in_lib = False
                start = i + 1
                break
    i = start
    while i < len(lines):
        ln = lines[i]
        if re.match(r'^\t\(symbol', ln):
            s = i
            d = ln.count('(') - ln.count(')')
            j = i + 1
            while j < len(lines) and d > 0:
                d += lines[j].count('(') - lines[j].count(')')
                j += 1
            blk = '\n'.join(lines[s:j])
            ref = re.search(r'property\s+"Reference"\s+"([^"]+)"', blk)
            val = re.search(r'property\s+"Value"\s+"([^"]*)"', blk)
            lib = re.search(r'lib_id\s+"([^"]+)"', blk)
            if ref and not ref.group(1).startswith('#'):
                yield dict(
                    ref=ref.group(1),
                    val=val.group(1) if val else '',
                    lib=lib.group(1) if lib else '',
                )
            i = j
        else:
            i += 1


def normalize_r_ohms(v):
    """Parse resistor value to ohms, or None if unparseable."""
    v = v.strip().rstrip('ohm').strip()
    # 4K7 style
    m = re.match(r'^(\d+)([KMk])(\d+)$', v)
    if m:
        base = float(m.group(1))
        mult = {'K': 1e3, 'k': 1e3, 'M': 1e6}[m.group(2)]
        frac = float('0.' + m.group(3))
        return (base + frac) * mult
    # 100R style
    m = re.match(r'^(\d+(?:\.\d+)?)\s*R?$', v)
    if m:
        return float(m.group(1))
    # 4.7K, 100K, 1M style
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([KMk])$', v)
    if m:
        mult = {'K': 1e3, 'k': 1e3, 'M': 1e6}[m.group(2)]
        return float(m.group(1)) * mult
    return None


def normalize_c_farads(v):
    v = v.strip().replace('µ', 'u').replace('μ', 'u')
    m = re.match(r'^([\d.]+)\s*(pF|nF|uF|F)?$', v, re.I)
    if not m:
        return None
    n = float(m.group(1))
    suffix = (m.group(2) or 'F').upper()
    return n * {'PF': 1e-12, 'NF': 1e-9, 'UF': 1e-6, 'F': 1.0}[suffix]


def fmt_ohms(ohms):
    if ohms is None: return '?'
    if ohms >= 1e6:  return f'{ohms/1e6:g}M'
    if ohms >= 1e3:  return f'{ohms/1e3:g}k'
    return f'{ohms:g}R'


def fmt_farads(f):
    if f is None: return '?'
    if f >= 1e-3: return f'{f/1e-3:g}mF'
    if f >= 1e-6: return f'{f/1e-6:g}uF'
    if f >= 1e-9: return f'{f/1e-9:g}nF'
    return f'{f/1e-12:g}pF'


def main():
    per_key = defaultdict(lambda: defaultdict(list))  # (cat,subcat,val) -> {sheet: [refs]}

    for sheet_name, sheet_path in SHEETS:
        full = ROOT / sheet_path
        if not full.exists():
            sys.stderr.write(f'WARN: {full} not found\n')
            continue
        for sym in collect_symbols(full):
            ref, val, lib = sym['ref'], sym['val'], sym['lib']
            prefix = re.match(r'^([A-Z]+)', ref)
            prefix = prefix.group(1) if prefix else ''
            if lib in TYPE_MAP:
                cat, subcat = TYPE_MAP[lib]
            elif prefix == 'R':
                cat, subcat = 'R', 'axial'
            elif prefix == 'C':
                cat, subcat = 'C', 'ceramic'
            elif prefix == 'Q':
                cat, subcat = 'Q', val or lib.split(':', 1)[-1]
            elif prefix == 'U':
                # Filter out breakouts / modules -- they don't go in parts bins
                if IC_EXCLUDE_RE.search(lib):
                    continue
                cat, subcat = 'U', 'IC'
            else:
                continue
            # Normalize equivalent notations before grouping
            if cat == 'R':
                nv = normalize_r_ohms(val)
                key_val = fmt_ohms(nv) if nv is not None else val
            elif cat == 'C':
                nf = normalize_c_farads(val)
                key_val = fmt_farads(nf) if nf is not None else val
            else:
                key_val = val
            per_key[(cat, subcat, key_val)][sheet_name].append(ref)

    # Build detail rows
    detail = []
    for (cat, subcat, val), sheet_refs in per_key.items():
        total = sum(len(v) for v in sheet_refs.values())
        if cat == 'R':
            sk = normalize_r_ohms(val) or 0
        elif cat == 'C':
            sk = normalize_c_farads(val) or 0
        else:
            sk = 0
        sheets_str = '; '.join(
            f'{s}: {",".join(sorted(sheet_refs[s]))}'
            for s in sorted(sheet_refs.keys())
        )
        detail.append(dict(
            category=cat, subcategory=subcat, value=val,
            qty=total, sort_key=sk, sheets=sheets_str,
        ))

    cat_order = {'R': 0, 'C': 1, 'Q': 2, 'U': 3}
    detail.sort(key=lambda r: (cat_order.get(r['category'], 9),
                               r['subcategory'], r['sort_key'], r['value']))

    # Write full-detail CSV
    detail_out = ROOT / 'Documentation' / 'component_inventory.csv'
    with open(detail_out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Category', 'Subcategory', 'Value', 'Qty', 'Sheet:Refs'])
        for r in detail:
            w.writerow([r['category'], r['subcategory'], r['value'],
                        r['qty'], r['sheets']])

    # -------------------------------------------------------------------
    # 24-bin allocation.  Strategy:
    #   - Any value with qty >= HIGH_COUNT gets a dedicated bin
    #   - Rest of R grouped by decade ranges
    #   - Rest of C grouped by decade + type (ceramic vs electrolytic)
    #   - Each transistor type gets its own bin
    # -------------------------------------------------------------------
    HIGH_COUNT = 8   # anything with 8+ pcs gets a dedicated bin

    # Group by category
    r_axial = [d for d in detail if d['category'] == 'R' and d['subcategory'] == 'axial']
    r_pot   = [d for d in detail if d['category'] == 'R' and d['subcategory'] == 'pot']
    c_cer   = [d for d in detail if d['category'] == 'C' and d['subcategory'] == 'ceramic']
    c_elec  = [d for d in detail if d['category'] == 'C' and d['subcategory'] == 'electrolytic']
    q_all   = [d for d in detail if d['category'] == 'Q']
    u_all   = [d for d in detail if d['category'] == 'U']

    bins = []

    def add_bin(label, contents):
        qty = sum(c['qty'] for c in contents)
        details = ', '.join(f'{c["value"]}x{c["qty"]}' for c in contents)
        bins.append(dict(label=label, qty=qty, details=details,
                         member_count=len(contents)))

    # --- Resistors: value-range bins with dedicated 10k slot -------------
    R_BUCKETS = [
        ('R  < 100 ohm',              0,          100),
        ('R  100 - 999 ohm',          100,        1000),
        ('R  1 k - 3.3 kohm',         1000,       3300),
        ('R  3.3 k - 10 kohm (excl 10k)', 3300,   10000),
        ('R  10 kohm (dedicated)',    10000,      10000.001),
        ('R  10.1 k - 100 kohm',      10000.001,  100000),
        ('R  > 100 kohm',             100000,     1e9),
    ]
    for label, lo, hi in R_BUCKETS:
        members = [d for d in r_axial
                   if d['sort_key'] is not None and lo <= d['sort_key'] < hi]
        if members:
            add_bin(label, members)
    if r_pot:
        add_bin('R  potentiometer (trim)', r_pot)

    # --- Capacitors: ceramics by decade, electrolytics split by decade --
    C_BUCKETS = [
        ('C  ceramic  <= 1 nF (pF range)',        0,           1e-9),
        ('C  ceramic  1 nF - 100 nF (excl 100n)', 1e-9,        100e-9),
        ('C  ceramic  100 nF (0.1 uF, dedicated)', 100e-9,     100e-9 + 1e-15),
        ('C  ceramic  > 100 nF (0.33 uF - 1 uF)', 100e-9 + 1e-15,  10e-6),
    ]
    for label, lo, hi in C_BUCKETS:
        members = [d for d in c_cer
                   if d['sort_key'] is not None and lo <= d['sort_key'] < hi]
        if members:
            add_bin(label, members)
    E_BUCKETS = [
        ('C  electrolytic  <= 1 uF',          0,          1e-6 + 1e-15),
        ('C  electrolytic  >= 10 uF (dedicated + up)', 9.999e-6, 1),
    ]
    for label, lo, hi in E_BUCKETS:
        members = [d for d in c_elec
                   if d['sort_key'] is not None and lo <= d['sort_key'] < hi]
        if members:
            add_bin(label, members)

    # --- Transistors + FETs: single bin (bagged with labels) ------------
    if q_all:
        add_bin('Q  transistors + FETs (bagged)', sorted(q_all, key=lambda x: x['value']))

    # --- Op-amps + comparators: single bin (bagged, all DIP-8) ---------
    OPAMP_PARTS = {'OPA454', 'OPA1641', 'LM7171xIN', 'LM7171', 'LM393'}
    opamps = [u for u in u_all if u['value'] in OPAMP_PARTS]
    other_ics = [u for u in u_all if u['value'] not in OPAMP_PARTS]
    if opamps:
        add_bin('U  op-amps + LM393 comparator (bagged)',
                sorted(opamps, key=lambda x: x['value']))

    # --- Remaining ICs: one bin each -----------------------------------
    for u in sorted(other_ics, key=lambda x: x['value']):
        add_bin(f'U  {u["value"]}', [u])

    # Number bins
    for i, b in enumerate(bins, start=1):
        b['bin'] = i

    # Write bin CSV
    bin_out = ROOT / 'Documentation' / 'component_bins.csv'
    with open(bin_out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Bin', 'Label', 'Total Qty', 'Unique Values', 'Contents'])
        for b in bins:
            w.writerow([b['bin'], b['label'], b['qty'],
                        b['member_count'], b['details']])

    # Console output
    sys.stdout.write(f'\n== Full detail ({len(detail)} unique parts) ==\n')
    sys.stdout.write(f'{"Cat":<3} {"Value":<10} {"Qty":>4}  Sheet:Refs\n')
    sys.stdout.write('-' * 100 + '\n')
    for r in detail:
        sys.stdout.write(f'{r["category"]:<3} {r["value"]:<10} {r["qty"]:>4}  {r["sheets"]}\n')

    sys.stdout.write(f'\n== Bin allocation ({len(bins)} bins, target <=24) ==\n')
    sys.stdout.write(f'{"Bin":>3}  {"Qty":>4}  {"#val":>4}  Label / Contents\n')
    sys.stdout.write('-' * 100 + '\n')
    for b in bins:
        sys.stdout.write(f'{b["bin"]:>3}  {b["qty"]:>4}  {b["member_count"]:>4}  {b["label"]}\n')
        sys.stdout.write(f'{"":>3}                      -> {b["details"]}\n')
    sys.stdout.write(f'\nBin count: {len(bins)} of 24 max\n')

    sys.stdout.write(f'\nCSVs written:\n')
    sys.stdout.write(f'  {detail_out}\n')
    sys.stdout.write(f'  {bin_out}\n')


if __name__ == '__main__':
    main()

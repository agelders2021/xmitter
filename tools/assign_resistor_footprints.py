"""Assign the project-standard axial-THT footprint to Device:R / Device:R_US.

Walks through .kicad_sch files passed on the command line, finds each
Device:R or Device:R_US symbol with an empty Footprint property, and
assigns the DIN0207 horizontal axial footprint that 100% of populated
resistors on this project use.

Skips Device:R_Potentiometer_US (needs a 3-pin trimmer footprint).

Re-runnable; only fills empty footprints (never overwrites).

CRITICAL: writes with utf-8 (no BOM). KiCad 10 silently treats a
BOM-prefixed file as empty — never let PowerShell Set-Content rewrite
these files.
"""

import re
import sys
from pathlib import Path


RESISTOR_LIB_IDS = ('Device:R', 'Device:R_US')
STANDARD_FOOTPRINT = (
    'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
)


def _find_block_end(text, paren_start):
    depth = 0
    i = paren_start
    n = len(text)
    while i < n:
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


_SYMBOL_BLOCK_RE = re.compile(r'\(symbol\r?\n', re.MULTILINE)
_LIB_ID_RE = re.compile(r'\(lib_id "([^"]+)"')
_REFERENCE_RE = re.compile(r'\(property "Reference" "([^"]+)"')
_VALUE_RE = re.compile(r'\(property "Value" "([^"]+)"')
_FOOTPRINT_EMPTY_RE = re.compile(r'(\(property "Footprint" )""')


def update_file(path):
    raw = Path(path).read_bytes()
    text = raw.decode('utf-8')
    out_parts = []
    last_end = 0
    changed = []
    skipped_already_set = []

    for m in _SYMBOL_BLOCK_RE.finditer(text):
        block_start = m.start()
        block_end = _find_block_end(text, block_start)
        if block_end is None:
            out_parts.append(text[last_end:])
            last_end = len(text)
            break

        out_parts.append(text[last_end:block_start])
        block = text[block_start:block_end]
        last_end = block_end

        lib_match = _LIB_ID_RE.search(block)
        if not (lib_match and lib_match.group(1) in RESISTOR_LIB_IDS):
            out_parts.append(block)
            continue

        ref_match = _REFERENCE_RE.search(block)
        val_match = _VALUE_RE.search(block)
        ref = ref_match.group(1) if ref_match else '?'
        val = val_match.group(1) if val_match else '?'

        if not _FOOTPRINT_EMPTY_RE.search(block):
            out_parts.append(block)
            skipped_already_set.append(f'{ref}={val}')
            continue

        new_block = _FOOTPRINT_EMPTY_RE.sub(
            lambda m: m.group(1) + f'"{STANDARD_FOOTPRINT}"',
            block,
            count=1,
        )
        out_parts.append(new_block)
        changed.append(f'{ref}={val}')

    out_parts.append(text[last_end:])
    new_text = ''.join(out_parts)

    if new_text != text:
        Path(path).write_bytes(new_text.encode('utf-8'))

    return changed, skipped_already_set


def main(argv):
    if len(argv) < 2:
        print('Usage: assign_resistor_footprints.py <file.kicad_sch> [...]')
        return 1

    for path in argv[1:]:
        print(f'\n== {path} ==')
        changed, already = update_file(path)
        if changed:
            print(f'  Updated {len(changed)} -> DIN0207:')
            for line in changed:
                print(f'    {line}')
        if already:
            print(f'  Skipped (footprint already set): {", ".join(already)}')
        if not (changed or already):
            print('  No resistor symbols found.')

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

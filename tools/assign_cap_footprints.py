"""Assign capacitor THT footprints to KiCad schematic instances by value.

Walks through .kicad_sch files passed on the command line, finds each
Device:C / Device:C_Polarized symbol with an empty Footprint property,
and assigns a footprint based on the Value field. Caps whose value is
not in the mapping (or already have a footprint assigned) are left
untouched.

Re-runnable; only fills empty footprints (does not overwrite existing
assignments).

Footprint choices match the parts already on the order (Mouser invoice
90968303, dated 2026-06-19):
  100nF / 0.1uF  -> KEMET C410 series, radial MLCC, 5.08 mm pitch
  10uF           -> Panasonic ECA-1EM100, radial electrolytic, 2 mm pitch
  680nF / 0.68uF -> WIMA MKP4, polypropylene film, 10 mm pitch
  10nF / 0.01uF  -> Vishay D103K Y5P ceramic disc, 5.08 mm pitch
  220pF          -> Knowles CD17 silver mica, 5.08 mm pitch

CRITICAL: writes with newline='' (no LF->CRLF translation) and utf-8
(no BOM). KiCad 10 silently treats a BOM-prefixed file as empty -- never
let PowerShell Set-Content rewrite these files.
"""

import re
import sys
from pathlib import Path


VALUE_TO_FOOTPRINT = {
    # 100 nF X7R, KEMET C410C104M5R5TA, P5.08 mm
    '100nF':   'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    '0.1uF':   'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',

    # 10 uF aluminum electrolytic, Panasonic ECA-1EM100, P2.0 mm
    '10uF':    'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm',

    # 0.68 uF polypropylene film, WIMA MKP4D036804F00JSSD, P10 mm
    '680nF':   'Capacitor_THT:C_Rect_L13.0mm_W6.0mm_P10.00mm_FKS3_FKP3_MKS4',
    '0.68uF':  'Capacitor_THT:C_Rect_L13.0mm_W6.0mm_P10.00mm_FKS3_FKP3_MKS4',

    # 10 nF Y5P ceramic disc, Vishay D103K43Y5PH63L2R, P5.08 mm
    # Intended for C_BYP at the tube cathodes (pa sheet, not yet drawn),
    # and acceptable for any other 10 nF non-RF bypass on the analog board.
    '10nF':    'Capacitor_THT:C_Disc_D6.0mm_W2.5mm_P5.00mm',
    '0.01uF':  'Capacitor_THT:C_Disc_D6.0mm_W2.5mm_P5.00mm',

    # 220 pF silver mica, Knowles CD17FD221JO3F, P5.08 mm
    '220pF':   'Capacitor_THT:C_Rect_L7.0mm_W4.5mm_P5.00mm',

    # User-stock ceramic disc caps. Body diameter given; leads on 5.08 mm
    # pitch (bend in/out slightly to fit standard holes).
    '390pF':   'Capacitor_THT:C_Disc_D6.0mm_W2.5mm_P5.00mm',   # 1/4" body
    '330pF':   'Capacitor_THT:C_Disc_D6.0mm_W2.5mm_P5.00mm',   # 1/4" body
    '33pF':    'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',   # 3/16" body
}

CAP_LIB_IDS = ('Device:C', 'Device:C_Polarized')


def _find_block_end(text, paren_start):
    """Given text and an index pointing to '(', return index just past the matching ')'."""
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
_VALUE_RE = re.compile(r'\(property "Value" "([^"]+)"')
_REFERENCE_RE = re.compile(r'\(property "Reference" "([^"]+)"')
_FOOTPRINT_EMPTY_RE = re.compile(r'(\(property "Footprint" )""')


def update_file(path):
    raw = Path(path).read_bytes()
    text = raw.decode('utf-8')
    out_parts = []
    last_end = 0
    changed = []
    skipped_no_match = []
    skipped_already_set = []

    for m in _SYMBOL_BLOCK_RE.finditer(text):
        block_start = m.start()
        paren_pos = block_start  # the '(' is at m.start() ('(symbol\n')
        block_end = _find_block_end(text, paren_pos)
        if block_end is None:
            out_parts.append(text[last_end:])
            last_end = len(text)
            break

        out_parts.append(text[last_end:block_start])
        block = text[block_start:block_end]
        last_end = block_end

        lib_match = _LIB_ID_RE.search(block)
        if not (lib_match and lib_match.group(1) in CAP_LIB_IDS):
            out_parts.append(block)
            continue

        ref_match = _REFERENCE_RE.search(block)
        val_match = _VALUE_RE.search(block)
        ref = ref_match.group(1) if ref_match else '?'
        val = val_match.group(1) if val_match else '?'

        footprint = VALUE_TO_FOOTPRINT.get(val)
        if footprint is None:
            out_parts.append(block)
            skipped_no_match.append(f'{ref}={val}')
            continue

        if not _FOOTPRINT_EMPTY_RE.search(block):
            # already has a non-empty footprint -- leave alone
            out_parts.append(block)
            skipped_already_set.append(f'{ref}={val}')
            continue

        new_block = _FOOTPRINT_EMPTY_RE.sub(
            lambda m: m.group(1) + f'"{footprint}"',
            block,
            count=1,
        )
        out_parts.append(new_block)
        changed.append(f'{ref}={val} -> {footprint.split(":")[-1]}')

    out_parts.append(text[last_end:])
    new_text = ''.join(out_parts)

    if new_text != text:
        # write back preserving LF line endings, utf-8 without BOM
        Path(path).write_bytes(new_text.encode('utf-8'))

    return changed, skipped_no_match, skipped_already_set


def main(argv):
    if len(argv) < 2:
        print('Usage: assign_cap_footprints.py <file.kicad_sch> [...]')
        return 1

    for path in argv[1:]:
        print(f'\n== {path} ==')
        changed, no_match, already = update_file(path)
        if changed:
            print(f'  Updated {len(changed)}:')
            for line in changed:
                print(f'    {line}')
        if no_match:
            print(f'  Skipped (value not in order): {", ".join(no_match)}')
        if already:
            print(f'  Skipped (footprint already set): {", ".join(already)}')
        if not (changed or no_match or already):
            print('  No cap symbols found.')

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

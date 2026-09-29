"""Assign Phoenix MKDS-1,5 screw-terminal footprints by pin count.

Walks through .kicad_sch files passed on the command line, finds each
Connector:Screw_Terminal_01xNN symbol with an empty Footprint property,
and assigns the matching Phoenix MKDS-1,5 P5.00mm horizontal footprint.

Re-runnable; only fills empty footprints (never overwrites).

Same pattern already in use on the protoshield board.

CRITICAL: writes with utf-8 (no BOM). KiCad 10 silently treats a
BOM-prefixed file as empty — never let PowerShell Set-Content rewrite
these files.
"""

import re
import sys
from pathlib import Path


def _fp_for(pins):
    """MKDS-1,5 horizontal footprint for a given pin count."""
    return (
        f'TerminalBlock_Phoenix:'
        f'TerminalBlock_Phoenix_MKDS-1,5-{pins}_1x{pins:02d}_P5.00mm_Horizontal'
    )


CONNECTOR_LIB_PATTERN = re.compile(r'^Connector:Screw_Terminal_01x(\d+)$')


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
        if not lib_match:
            out_parts.append(block)
            continue

        pin_match = CONNECTOR_LIB_PATTERN.match(lib_match.group(1))
        if not pin_match:
            out_parts.append(block)
            continue

        pins = int(pin_match.group(1))
        ref_match = _REFERENCE_RE.search(block)
        ref = ref_match.group(1) if ref_match else '?'

        if not _FOOTPRINT_EMPTY_RE.search(block):
            out_parts.append(block)
            skipped_already_set.append(f'{ref} ({pins}p)')
            continue

        footprint = _fp_for(pins)
        new_block = _FOOTPRINT_EMPTY_RE.sub(
            lambda m: m.group(1) + f'"{footprint}"',
            block,
            count=1,
        )
        out_parts.append(new_block)
        changed.append(f'{ref} ({pins}p) -> MKDS-1,5-{pins}')

    out_parts.append(text[last_end:])
    new_text = ''.join(out_parts)

    if new_text != text:
        Path(path).write_bytes(new_text.encode('utf-8'))

    return changed, skipped_already_set


def main(argv):
    if len(argv) < 2:
        print('Usage: assign_connector_footprints.py <file.kicad_sch> [...]')
        return 1

    for path in argv[1:]:
        print(f'\n== {path} ==')
        changed, already = update_file(path)
        if changed:
            print(f'  Updated {len(changed)}:')
            for line in changed:
                print(f'    {line}')
        if already:
            print(f'  Skipped (footprint already set): {", ".join(already)}')
        if not (changed or already):
            print('  No screw-terminal symbols found.')

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

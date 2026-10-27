"""Assign THT footprints to KiCad schematic instances for parts whose
footprint is a function of lib_id alone (resistors, screw terminals,
pin headers, LT1054, etc.).

Walks each .kicad_sch passed on the command line, finds symbols with
an empty Footprint property matching entries in LIB_ID_TO_FOOTPRINT,
and assigns the mapped footprint. Re-runnable; only fills empty
footprints (does not overwrite existing assignments).

Mirrors the safe-write discipline in assign_cap_footprints.py:
UTF-8 without BOM, no CRLF translation, so KiCad 10 does not treat
the file as empty.
"""

import re
import sys
from pathlib import Path


LIB_ID_TO_FOOTPRINT = {
    # 1/4W axial resistors on 400 mil pitch -- universal convention
    # across every populated resistor in this project.
    'Device:R_US':
        'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    'Device:R':
        'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',

    # Phoenix Contact MKDS-1.5 screw terminal family, P5.00 mm.
    'Connector:Screw_Terminal_01x02':
        'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
    'Connector:Screw_Terminal_01x03':
        'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal',
    'Connector:Screw_Terminal_01x04':
        'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4_1x04_P5.00mm_Horizontal',
    'Connector:Screw_Terminal_01x05':
        'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-5_1x05_P5.00mm_Horizontal',

    # 2.54 mm pin headers -- match the convention used by test points
    # and other 1x_n connectors already populated on these boards.
    'Connector:Conn_01x05_Pin':
        'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical',

    # LT1054 switched-cap converter in DIP-8 THT -- same package used
    # on the analog power sub-sheet.
    'Regulator_SwitchedCapacitor:LT1054':
        'Package_DIP:DIP-8_W7.62mm',
}


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
_VALUE_RE = re.compile(r'\(property "Value" "([^"]+)"')
_REFERENCE_RE = re.compile(r'\(property "Reference" "([^"]+)"')
_FOOTPRINT_EMPTY_RE = re.compile(r'(\(property "Footprint" )""')


def update_file(path):
    raw = Path(path).read_bytes()
    text = raw.decode('utf-8')
    out_parts = []
    last_end = 0
    changed = []
    skipped_already_set = []

    # Skip the (lib_symbols ...) section so we don't touch embedded
    # library definitions -- only symbol instances get a footprint.
    lib_section_start = text.find('(lib_symbols')
    lib_section_end = None
    if lib_section_start >= 0:
        lib_section_end = _find_block_end(text, lib_section_start)

    for m in _SYMBOL_BLOCK_RE.finditer(text):
        block_start = m.start()
        # Inside the lib_symbols block? skip.
        if (lib_section_start is not None and lib_section_end is not None
                and lib_section_start <= block_start < lib_section_end):
            continue
        paren_pos = block_start
        block_end = _find_block_end(text, paren_pos)
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
        lib_id = lib_match.group(1)
        footprint = LIB_ID_TO_FOOTPRINT.get(lib_id)
        if footprint is None:
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
            lambda m: m.group(1) + f'"{footprint}"',
            block,
            count=1,
        )
        out_parts.append(new_block)
        changed.append(f'{ref}={val} -> {footprint.split(":")[-1]}')

    out_parts.append(text[last_end:])
    new_text = ''.join(out_parts)

    if new_text != text:
        Path(path).write_bytes(new_text.encode('utf-8'))

    return changed, skipped_already_set


def main(argv):
    if len(argv) < 2:
        print('Usage: assign_misc_footprints.py <file.kicad_sch> [...]')
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
            print('  No matching symbols found.')

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

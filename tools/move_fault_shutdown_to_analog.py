"""Move KiCAD/ss_pa/fault_shutdown.kicad_sch into KiCAD/analog/ as a new
sub-sheet, renaming all component refs by adding +200 so they do not
collide with analog's existing refs.

What this script does:
  1. Reads ss_pa/fault_shutdown.kicad_sch
  2. Renames every component reference (U, C, R, D, L, J, TP, #PWR) by
     adding 200 to the numeric suffix:
       U1  -> U201   LM393
       U2  -> U202   CD74HC4066
       U3  -> U203   LM2936-5.0 LDO (user plans to delete later)
       D1  -> D201   1N4148
       D3  -> D203   BAT85
       Cn  -> C2nn
       Rn  -> R2nn
       Ln  -> L2nn
       J5  -> J205   V_REF test point
       J31 -> J231   RJ45 umbilical (user plans to delete / rewire later)
       TPn -> TP2nn  Test points
       #PWRnnn -> #PWR(2nn+200)
  3. Replaces (project "ss_pa" with (project "analog" in every
     symbol instance block.
  4. Replaces the hierarchy UUIDs so the moved sheet attaches to the
     analog project root instead of the ss_pa project root.
  5. Writes the renamed file to analog/fault_shutdown.kicad_sch.
  6. Appends a new (sheet ...) block to analog/analog.kicad_sch so
     analog's hierarchy shows the moved sub-sheet.

Does NOT:
  - Modify ss_pa/ in any way. ss_pa still has its own fault_shutdown
    sheet referenced in ss_pa.kicad_sch. Both projects can coexist
    while the user edits.
  - Rewire anything. All global labels, hierarchical pins, and signal
    nets keep their original names so the user can wire them up to
    analog's existing signals during the editing phase.

Writes UTF-8 without BOM, no LF->CRLF translation, per project
convention for KiCad files.
"""

import re
import uuid
from pathlib import Path


REPO = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter")
SRC = REPO / "KiCAD" / "ss_pa" / "fault_shutdown.kicad_sch"
DST = REPO / "KiCAD" / "analog" / "fault_shutdown.kicad_sch"
ANALOG_ROOT_SCH = REPO / "KiCAD" / "analog" / "analog.kicad_sch"

# UUIDs
SS_PA_ROOT_UUID = "7b9fe991-54d6-43c4-a637-0ed9ee982c42"
FAULT_SHEET_UUID = "7e6e5903-d9c4-4499-a3fb-6a30c021fada"
ANALOG_ROOT_UUID = "d3de40b8-856b-4fbd-829c-f45ffcd55742"


def shift_number(text, prefix_pattern, offset=200, pad_to=None):
    """Shift the numeric suffix of refs matching the prefix pattern by `offset`.
    Applies in both `(property "Reference" "XN"` and `(reference "XN")` contexts.
    """
    def _shift(n):
        return f'{n + offset:0{pad_to}d}' if pad_to else str(n + offset)

    # In property blocks: (property "Reference" "XN"
    text = re.sub(
        rf'(property "Reference" "{prefix_pattern})(\d+)(")',
        lambda m: f'{m.group(1)}{_shift(int(m.group(2)))}{m.group(3)}',
        text,
    )
    # In instance blocks: (reference "XN")
    text = re.sub(
        rf'(\(reference "{prefix_pattern})(\d+)(")',
        lambda m: f'{m.group(1)}{_shift(int(m.group(2)))}{m.group(3)}',
        text,
    )
    return text


def main():
    print(f'Reading {SRC}...')
    text = SRC.read_bytes().decode('utf-8')
    original_length = len(text)

    # Fresh UUID for where fault_shutdown is instantiated under analog
    new_sheet_uuid = str(uuid.uuid4())
    print(f'New sheet instance UUID (in analog): {new_sheet_uuid}')

    # Rename single-letter component refs: U, C, R, D, L, J  (one at a time
    # so overlapping prefixes like "TP" vs "P" don't collide — not an issue
    # here but good practice).
    for prefix in ('U', 'C', 'R', 'D', 'L', 'J'):
        text = shift_number(text, prefix, offset=200)

    # Rename TP (test point) refs
    text = shift_number(text, 'TP', offset=200)

    # Rename #PWR refs (3-digit zero-padded)
    # #PWRnnn -> #PWR(nnn+200), still 3-digit
    text = shift_number(text, r'\#PWR', offset=200, pad_to=3)

    # Replace project name in symbol instance blocks
    text = text.replace('(project "ss_pa"', '(project "analog"')

    # Replace hierarchy UUIDs so this sheet attaches to analog, not ss_pa
    text = text.replace(SS_PA_ROOT_UUID, ANALOG_ROOT_UUID)
    text = text.replace(FAULT_SHEET_UUID, new_sheet_uuid)

    # Write the renamed sheet to analog/
    print(f'Writing {DST}...')
    DST.write_bytes(text.encode('utf-8'))
    print(f'  Original size: {original_length} bytes')
    print(f'  New size:      {len(text)} bytes')

    # Add a new (sheet ...) entry to analog.kicad_sch so analog's root
    # hierarchy includes the moved sheet.
    print(f'Updating {ANALOG_ROOT_SCH}...')
    root_text = ANALOG_ROOT_SCH.read_bytes().decode('utf-8')

    # Place the new sheet at (10, 170) with size 50x25 so it does not
    # collide with the existing analog sub-sheet layout. User can drag
    # it into position in KiCad.
    new_sheet_block = f'''	(sheet
		(at 10 170)
		(size 50 25)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(fields_autoplaced yes)
		(stroke
			(width 0.1524)
			(type solid)
		)
		(fill
			(color 0 0 0 0)
		)
		(uuid "{new_sheet_uuid}")
		(property "Sheetname" "Fault_Shutdown"
			(at 10 169.2884 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left bottom)
			)
		)
		(property "Sheetfile" "fault_shutdown.kicad_sch"
			(at 10 195.7146 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify left top)
			)
		)
		(instances
			(project "analog"
				(path "/{ANALOG_ROOT_UUID}"
					(page "11")
				)
			)
		)
	)
'''

    # Insert before the (sheet_instances ...) block
    marker = '\t(sheet_instances'
    if marker not in root_text:
        raise SystemExit('Could not find (sheet_instances in analog.kicad_sch')
    root_text = root_text.replace(marker, new_sheet_block + marker, 1)

    ANALOG_ROOT_SCH.write_bytes(root_text.encode('utf-8'))
    print('Added Fault_Shutdown sheet reference to analog.kicad_sch at (10, 170), page 11')

    print('')
    print('DONE.')
    print('')
    print('Next steps for user:')
    print('  1. Open analog.kicad_pro in KiCad; verify Fault_Shutdown sheet opens.')
    print('  2. Drag the new sheet block into the desired position on the root sheet.')
    print('  3. Delete U203 (LM2936 LDO) and its +5V dependents — ss_pa no longer needs it.')
    print('  4. Rewire J231 nets to analog\'s existing J31 (umbilical) connections.')
    print('  5. Delete J231 placeholder once rewired.')
    print('  6. Delete the Fault_Shutdown sheet reference from ss_pa.kicad_sch and')
    print('     delete ss_pa/fault_shutdown.kicad_sch when confirmed working.')


if __name__ == '__main__':
    main()

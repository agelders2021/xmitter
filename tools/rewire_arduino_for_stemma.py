"""Rewire arduino.kicad_sch for STEMMA-QT I2C distribution.

Changes:
 - Remove SDA, SCL, 3V3 hierarchical labels (their roles move to VFO sheet
   since Si5351 breakout is now the I2C / 3V3 distribution point on the PCB)
 - Add a +3.3V power port at the Metro's 3V3 pin position (same place
   the 3V3 hier label was) so the Metro 3V3 pin has a destination and
   ERC stays clean
 - Add a text note explaining the STEMMA QT routing

Preserves CRLF / no BOM.
"""
import re
import sys
import uuid

sys.stdout.reconfigure(encoding='utf-8')

with open('KiCAD/arduino.kicad_sch', 'rb') as f:
    raw = f.read()
assert raw[:3] != b'\xef\xbb\xbf'
crlf = b'\r\n' in raw
sch = raw.decode('utf-8').replace('\r\n', '\n')


def eos(s, start):
    d = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            d += 1
        elif s[i] == ')':
            d -= 1
            if d == 0:
                return i + 1


# Remove three named hier labels (SDA, SCL, 3V3) — find each (hierarchical_label "X" ...)
# block and excise it including its leading whitespace and trailing newline.
removed = []
for name in ('SDA', 'SCL', '3V3'):
    while True:
        m = re.search(rf'\t\(hierarchical_label "{name}"\s', sch)
        if not m:
            break
        start = m.start()
        end = eos(sch, start)
        # Strip the trailing newline if there is one
        if end < len(sch) and sch[end] == '\n':
            end += 1
        sch = sch[:start] + sch[end:]
        removed.append(name)
print(f'Removed hier labels: {removed}')

# Add a +3.3V power port at (86.36, 63.5) — same place where the 3V3 label was.
# This connects the Metro's 3V3 pin (which sits at global 88.9, 63.5) to the
# global +3.3V net via the existing 2.54 mm horizontal offset.
# Power port lib_symbol must be cached. Check if power:+3.3V is already cached.
lib_start = sch.find('(lib_symbols')
lib_end = eos(sch, lib_start)
lib_block = sch[lib_start:lib_end]
has_3v3_lib = '"power:+3.3V"' in lib_block
print(f'+3.3V symbol cached in lib_symbols: {has_3v3_lib}')

# Add the lib_symbol cache for power:+3.3V if not present — model after +5V cache.
if not has_3v3_lib:
    # Find +5V cached block as a template
    m_5v = re.search(r'\t\t\(symbol "power:\+5V"', lib_block)
    if m_5v:
        five_start_in_lib = m_5v.start()
        five_end_in_lib = eos(lib_block, five_start_in_lib)
        five_template = lib_block[five_start_in_lib:five_end_in_lib]
        # Duplicate, retargeting names to +3.3V (and the value text)
        three_template = (five_template
                          .replace('"power:+5V"', '"power:+3.3V"')
                          .replace('"+5V_0_1"', '"+3.3V_0_1"')
                          .replace('"+5V_1_1"', '"+3.3V_1_1"')
                          .replace('"+5V"\n', '"+3.3V"\n'))
        # Insert before the lib_symbols closing paren
        insertion_point = lib_end - 1   # just before the final ')'
        # The newline pattern in the file: lib block ends with '\n\t)'
        sch = sch[:insertion_point] + three_template + '\n' + sch[insertion_point:]
        print('Added power:+3.3V to lib_symbols cache')

# Now add the +3.3V power port symbol INSTANCE at (86.36, 63.5)
# Use a similar instance format to the existing +5V port. Find existing +5V
# instance for the template.
plus5v_inst_pattern = re.compile(
    r'\t\(symbol\s*\(lib_id "power:\+5V"\)\s*\(at\s+[\d.]+\s+[\d.]+\s+\d+\)[\s\S]+?\n\t\)\n'
)
m5 = plus5v_inst_pattern.search(sch)
if m5:
    template = m5.group()
    # Generate new UUIDs for the new instance
    new_uuids = [str(uuid.uuid4()) for _ in range(3)]
    # Retarget: lib_id, position, ref designator number, uuids, value
    new_inst = template
    new_inst = new_inst.replace('"power:+5V"', '"power:+3.3V"', 1)
    # Replace position: find the (at ...) — set to our target
    new_inst = re.sub(
        r'\(at\s+[\d.]+\s+[\d.]+\s+\d+\)',
        '(at 86.36 63.5 0)',
        new_inst, count=1
    )
    # Replace UUIDs
    uuid_pat = re.compile(r'"[0-9a-f-]{36}"')
    for u in new_uuids:
        new_inst = uuid_pat.sub(f'"{u}"', new_inst, count=1)
    # Replace value '+5V' inside (property "Value" "+5V" with +3.3V
    new_inst = new_inst.replace('"Value" "+5V"', '"Value" "+3.3V"', 1)
    # Change the Reference designator number to next unused PWR number
    existing_pwr = re.findall(r'\(property "Reference" "(#PWR\d+)"', sch)
    nums = [int(re.search(r'\d+', x).group()) for x in existing_pwr]
    next_num = (max(nums) if nums else 0) + 1
    next_ref = f'#PWR{next_num:03d}'
    new_inst = re.sub(r'\(property "Reference" "#PWR\d+"', f'(property "Reference" "{next_ref}"', new_inst, count=1)

    # Insert before the first existing power-port instance (keeps the file tidy)
    insert_at = m5.start()
    sch = sch[:insert_at] + new_inst + sch[insert_at:]
    print(f'Added +3.3V power port at (86.36, 63.5), ref={next_ref}')

# Add a text note explaining the STEMMA QT route
note_uuid = str(uuid.uuid4())
note_block = (
    '\t(text "I2C bus and +3.3V routed off-board via STEMMA QT cable\\n'
    'from Metro JST-SH port to Si5351 breakout (VFO sheet).\\n'
    'Si5351 breakout 0.1\\" header distributes SDA/SCL/+3V3/GND\\n'
    'to other I2C devices via PCB traces."\n'
    '\t\t(exclude_from_sim no)\n'
    '\t\t(at 60.96 110.49 0)\n'
    '\t\t(effects\n'
    '\t\t\t(font\n'
    '\t\t\t\t(size 1.27 1.27)\n'
    '\t\t\t)\n'
    '\t\t\t(justify left)\n'
    '\t\t)\n'
    f'\t\t(uuid "{note_uuid}")\n'
    '\t)\n'
)
# Insert before the first power port instance
m5_after = plus5v_inst_pattern.search(sch)
if m5_after:
    insert_at = m5_after.start()
    sch = sch[:insert_at] + note_block + sch[insert_at:]
    print('Added STEMMA QT text note')

# Write back
out = sch.encode('utf-8')
if crlf:
    out = out.replace(b'\n', b'\r\n')
with open('KiCAD/arduino.kicad_sch', 'wb') as f:
    f.write(out)
print(f'\nWrote KiCAD/arduino.kicad_sch ({len(out)} bytes)')

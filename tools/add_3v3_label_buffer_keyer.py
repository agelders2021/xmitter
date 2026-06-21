"""Add a 3V3 hierarchical label (input direction) to buffer_keyer.kicad_sch
alongside the existing SDA/SCL inputs. The user's plan: VFO sheet sources
SDA/SCL/3V3 from the Si5351 breakout (received via STEMMA cable from Metro);
these flow to buffer_keyer via hierarchical labels routed on the root sheet.

Note: a +3.3V power port already exists at U8 VIN. The new 3V3 hier label
is added at a separate position alongside the other I2C input labels.
The user will need to draw a wire on buffer_keyer connecting the 3V3 hier
label to the +3.3V net (or to U8 VIN directly).
"""
import uuid
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('KiCAD/buffer_keyer.kicad_sch', 'rb') as f:
    raw = f.read()
crlf = b'\r\n' in raw
sch = raw.decode('utf-8').replace('\r\n', '\n')

# Insert a 3V3 hier label at (48.26, 134.62, 180) — one grid above SCL,
# matching the same input-pattern x-coordinate as SDA/SCL/LDAC_4728.
new_uuid = str(uuid.uuid4())
new_label = (
    '\t(hierarchical_label "3V3"\n'
    '\t\t(shape input)\n'
    '\t\t(at 48.26 134.62 180)\n'
    '\t\t(effects\n'
    '\t\t\t(font\n'
    '\t\t\t\t(size 1.27 1.27)\n'
    '\t\t\t)\n'
    '\t\t\t(justify right)\n'
    '\t\t)\n'
    f'\t\t(uuid "{new_uuid}")\n'
    '\t)\n'
)

# Insert before first existing hierarchical_label
idx = sch.find('\t(hierarchical_label "')
sch = sch[:idx] + new_label + sch[idx:]
print('Added 3V3 hier label (input) at (48.26, 134.62)')

out = sch.encode('utf-8')
if crlf:
    out = out.replace(b'\n', b'\r\n')
with open('KiCAD/buffer_keyer.kicad_sch', 'wb') as f:
    f.write(out)
print(f'Wrote KiCAD/buffer_keyer.kicad_sch ({len(out)} bytes)')

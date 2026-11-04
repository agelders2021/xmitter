"""
Build xmitter.pretty/Metro_ESP32-S3.kicad_mod from the KiCad stock
`Module:Arduino_UNO_R3` footprint.

What this does:
  1. Copies the stock footprint verbatim (geometry, silkscreen outline,
     courtyard, fab layer, all 32 drill positions).
  2. Renames the footprint identifier to Metro_ESP32-S3.
  3. Rewrites the default Value text to Metro_ESP32-S3 so the silkscreen
     reads correctly out of the box.
  4. Replaces the numeric pad numbers 1-32 with mnemonic names that match
     the existing `xmitter:Metro_ESP32S3` schematic symbol pin numbers
     (A0-A5, D0-D13, SDA, SCL, RESET, 5V, 3V3_L, GND_L, AREF, VIN, NC).
     Multiple pads can share a pad number — KiCad treats same-numbered
     pads as internally connected.  We use that for GND_L (3 pads) and
     3V3_L (2 pads: IOREF + 3V3).
  5. Adds a small silkscreen annotation next to each labeled pin with
     the Metro silk label + ESP32-S3 GPIO number, so the PCB silkscreen
     is self-documenting.

Output: KiCAD/xmitter.pretty/Metro_ESP32-S3.kicad_mod
"""
import re
import uuid
from pathlib import Path

STOCK = Path(r"D:\Program Files\KiCad\10.0\share\kicad\footprints\Module.pretty\Arduino_UNO_R3.kicad_mod")
OUT   = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\xmitter.pretty\Metro_ESP32-S3.kicad_mod")


# ── Pad remap ──────────────────────────────────────────────────────────────
# Keyed by stock pad number (as a string).  Value is the new pad number.
# Values that repeat (GND_L, 3V3_L) correspond to physically separate pads
# that are ganged in the footprint — pads with the same number are
# treated as electrically connected by KiCad.
PAD_MAP = {
    # Bottom row, POWER header (pins 1-8)
    "1":  "NC",
    "2":  "3V3_L",   # IOREF — tied to 3.3 V on Metro ESP32-S3
    "3":  "RESET",
    "4":  "3V3_L",   # 3V3 — ganged with IOREF
    "5":  "5V",
    "6":  "GND_L",
    "7":  "GND_L",   # ganged
    "8":  "VIN",
    # Bottom row, ANALOG IN header (pins 9-14)
    "9":  "A0",
    "10": "A1",
    "11": "A2",
    "12": "A3",
    "13": "A4",
    "14": "A5",
    # Top row, DIGITAL 0-7 (pins 15-22)
    "15": "D0",
    "16": "D1",
    "17": "D2",
    "18": "D3",
    "19": "D4",
    "20": "D5",
    "21": "D6",
    "22": "D7",
    # Top row, DIGITAL 8-13+ (pins 23-32)
    "23": "D8",
    "24": "D9",
    "25": "D10",
    "26": "D11",
    "27": "D12",
    "28": "D13",
    "29": "GND_L",   # ganged
    "30": "AREF",
    "31": "SDA",
    "32": "SCL",
}


# ── GPIO annotation text per Metro silkscreen label ────────────────────────
# Rendered on F.SilkS next to each pin as a small "GPIOxx" tag so the board
# is self-documenting without pulling out the pinout PDF.
GPIO_OF = {
    "A0":  "GPIO14",
    "A1":  "GPIO15",
    "A2":  "GPIO16",
    "A3":  "GPIO17",
    "A4":  "GPIO18",
    "A5":  "GPIO1",
    "D0":  "GPIO41",
    "D1":  "GPIO40",
    "D2":  "GPIO2",
    "D3":  "GPIO3",   # strapping
    "D4":  "GPIO4",
    "D5":  "GPIO5",
    "D6":  "GPIO6",
    "D7":  "GPIO7",
    "D8":  "GPIO8",
    "D9":  "GPIO9",
    "D10": "GPIO10",
    "D11": "GPIO11",
    "D12": "GPIO12",
    "D13": "GPIO13",
    "SDA": "GPIO47",
    "SCL": "GPIO48",
}


# ── Parse pad geometry from stock so we can place silk annotations ─────────

def parse_pads(text: str) -> dict:
    """Return {stock_pad_num: (x, y)}."""
    pads = {}
    for m in re.finditer(
        r'\(pad "([^"]+)"\s+\S+\s+\S+\s+\(at ([\-\d\.]+)\s+([\-\d\.]+)',
        text,
    ):
        pads[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return pads


def build_silk_label(label: str, gpio: str, x: float, y: float) -> str:
    """Return an fp_text user block near pad (x, y) with a silk label
    like 'D13 GPIO13', rotated 90° so adjacent 2.54 mm-spaced pins don't
    collide.  Text is centered on (x, txt_y) and reads bottom-to-top.
    Labels sit inboard of their pad row (into the PCB) so they don't fall
    off the board edge."""
    # Stock footprint: bottom row at y=0, top row at y=48.26.  Labels
    # need to clear the 1.6 mm pad + leave a small gap before the text
    # starts.  At 0.8 mm font height, "D13 GPIO13" is ~7 mm long after
    # rotation; center the text ~6 mm inboard so one end stops 2 mm
    # short of the pad and the other end lives well clear of the
    # opposite row.
    if y < 24:                 # bottom row (POWER + ANALOG IN)
        txt_y = y + 6.0        # label extends inboard (into PCB)
    else:                      # top row (DIGITAL headers)
        txt_y = y - 6.0
    text = f"{label} {gpio}" if gpio else label
    uid = uuid.uuid4()
    return f'''\t(fp_text user "{text}"
		(at {x:.3f} {txt_y:.3f} 90)
		(layer "F.SilkS")
		(uuid "{uid}")
		(effects
			(font
				(size 0.8 0.8)
				(thickness 0.12)
			)
		)
	)
'''


# ── Main transform ─────────────────────────────────────────────────────────

def main():
    stock = STOCK.read_text(encoding="utf-8")
    pads_xy = parse_pads(stock)

    out = stock

    # 1. Footprint identifier line
    out = re.sub(
        r'^\(footprint "Arduino_UNO_R3"',
        '(footprint "Metro_ESP32-S3"',
        out,
    )
    # 2. descr line — link to Adafruit's PDF
    out = re.sub(
        r'\(descr "[^"]*"\)',
        '(descr "Adafruit Metro ESP32-S3, Arduino Uno R3 pattern. '
        'Pinout: Documentation/Metro_ESP32-S3/Metro_ESP32-S3_Pinout.pdf")',
        out,
        count=1,
    )
    # 3. tags
    out = re.sub(
        r'\(tags "[^"]*"\)',
        '(tags "Adafruit Metro ESP32-S3 ESP32-S3 Arduino Uno R3 shield")',
        out,
        count=1,
    )
    # 4. Default Value text
    out = re.sub(
        r'\(property "Value" "Arduino_UNO_R3"',
        '(property "Value" "Metro_ESP32-S3"',
        out,
        count=1,
    )

    # 5. Pad number remap.  Match on the exact (pad "N" ... form with a word
    # boundary so pad "1" doesn't accidentally match pad "10".
    for stock_num, new_num in PAD_MAP.items():
        out = re.sub(
            r'(\(pad ")' + re.escape(stock_num) + r'("\s+)',
            r'\g<1>' + new_num + r'\g<2>',
            out,
        )

    # 6. Insert GPIO silkscreen annotations.  We append them just before the
    # closing ) of the footprint.
    silk_blocks = []
    for stock_num, (x, y) in sorted(pads_xy.items(), key=lambda t: int(t[0])):
        label = PAD_MAP[stock_num]
        if label in ("NC", "3V3_L", "RESET", "5V", "GND_L", "VIN", "AREF"):
            # Power / control pins — label without GPIO tag (they aren't
            # directly a GPIO)
            silk_blocks.append(build_silk_label(label, "", x, y))
        else:
            silk_blocks.append(
                build_silk_label(label, GPIO_OF.get(label, ""), x, y)
            )

    # Insert before the final closing paren of the footprint
    # (the file ends with ')' on its own line).
    out = out.rstrip()
    if not out.endswith(")"):
        raise RuntimeError("Unexpected end of stock footprint file")
    out = out[:-1] + "\n" + "".join(silk_blocks) + ")\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    size = OUT.stat().st_size
    print(f"Wrote {OUT} ({size} bytes)")

    # Verify by counting pad instances per new pad number
    from collections import Counter
    cnt = Counter()
    for m in re.finditer(r'\(pad "([^"]+)"', out):
        cnt[m.group(1)] += 1
    print("\nPad counts by mnemonic (sanity check):")
    for name in sorted(cnt):
        gang = " (ganged)" if cnt[name] > 1 else ""
        print(f"  {name:<8s} × {cnt[name]}{gang}")


if __name__ == "__main__":
    main()

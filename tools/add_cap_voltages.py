"""
Pass over every .kicad_sch (and matching .net) in the active boards and:

1. Append voltage rating to every capacitor whose Value doesn't already carry
   one. Rule (by footprint family):
       CP_* (electrolytic)               -> 35V
       C_0805_* / C_0603_* (SMT ceramic) -> 50V
       C_Disc_* (THT ceramic)            -> 50V
       C_Rect_* / C_Axial_* (film)       -> 100V
   Existing voltage marks ("200V C0G", "100V", "25V", ...) are preserved
   untouched.

2. Fill empty Footprint fields for a hand-maintained list of refs (see
   FOOTPRINT_FIXES).

Only top-level symbol instances in schematics are touched (lib_symbols
block is skipped). Netlist (.net) files have their matching (value ...)
tokens updated too so both stay in sync.

Re-runnable. No existing voltage-rated caps are modified.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD")

BOARDS = [
    ROOT / "analog",
    ROOT / "ss_pa",
    ROOT / "Output LPF",
]

# Empty-footprint fills identified by gen_board_boms.py.
# Keyed by (sheet filename, refdes) -> footprint string.
FOOTPRINT_FIXES = {
    # analog
    ("Tube_PA.sch.kicad_sch",  "R82"): "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    ("arduino.kicad_sch",      "C63"): "Capacitor_THT:C_Rect_L7.2mm_W4.5mm_P5.00mm",
    ("arduino.kicad_sch",      "C64"): "Capacitor_THT:C_Rect_L7.2mm_W4.5mm_P5.00mm",
    ("dac.kicad_sch",          "R47"): "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    ("power.kicad_sch",        "C65"): "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
    # ss_pa fault_shutdown sub-sheet (R19/R20 reported missing footprint)
    ("fault_shutdown.kicad_sch", "R19"): "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    ("fault_shutdown.kicad_sch", "R20"): "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
}


def voltage_for_footprint(fp: str) -> str | None:
    if not fp:
        return None
    # Electrolytic
    if fp.startswith("Capacitor_THT:CP_") or "CP_Radial" in fp or "CP_Axial" in fp:
        return "35V"
    # SMT ceramic
    if re.search(r"C_0\d{3}_\d{4}Metric", fp):
        return "50V"
    # THT ceramic disc
    if "C_Disc" in fp:
        return "50V"
    # Film / axial
    if "C_Rect" in fp or "C_Axial" in fp:
        return "100V"
    return None


def has_voltage_spec(value: str) -> bool:
    # Matches "25V", "25 V", "25Vdc", etc. Also treat any explicit dielectric
    # marker as already-handled.
    if re.search(r"\b\d+(?:\.\d+)?\s*V(?:\b|dc|DC)", value):
        return True
    return False


# ------- schematic (.kicad_sch) pass -------

_INSTANCE_RE = re.compile(r"\(symbol\s*\n\s*\(lib_id\s+\"[^\"]+\"\)", re.M)


def walk_top_symbol_instances(text: str):
    """Yield (start, end) spans of each top-level schematic symbol instance."""
    for m in _INSTANCE_RE.finditer(text):
        start = m.start()
        # From start, find the matching close paren
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    yield start, i + 1
                    break
            i += 1


_PROP_RE_TEMPLATE = r'(\(property\s+"{name}"\s+")([^"]*)(")'


def get_property(block: str, name: str) -> tuple[int, int, str] | None:
    pat = re.compile(_PROP_RE_TEMPLATE.format(name=re.escape(name)))
    m = pat.search(block)
    if not m:
        return None
    return m.start(2), m.end(2), m.group(2)


def set_property(block: str, name: str, new_val: str) -> str:
    pat = re.compile(_PROP_RE_TEMPLATE.format(name=re.escape(name)))
    return pat.sub(lambda m: m.group(1) + new_val + m.group(3), block, count=1)


def process_schematic(path: Path) -> tuple[int, int, list[str]]:
    """Returns (caps_updated, footprints_set, changes_log)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    orig_text = text
    caps_updated = 0
    fps_set = 0
    log: list[str] = []
    # Walk from the end so string indices stay valid as we replace
    spans = list(walk_top_symbol_instances(text))
    for start, end in reversed(spans):
        block = text[start:end]
        ref_info = get_property(block, "Reference")
        if not ref_info:
            continue
        _, _, ref = ref_info
        if ref.startswith("#"):
            continue
        val_info = get_property(block, "Value")
        fp_info = get_property(block, "Footprint")
        if not val_info or not fp_info:
            continue
        value = val_info[2]
        footprint = fp_info[2]

        new_block = block
        changed = False

        # Fix empty footprint if we have a rule for it
        if not footprint:
            key = (path.name, ref)
            if key in FOOTPRINT_FIXES:
                new_fp = FOOTPRINT_FIXES[key]
                new_block = set_property(new_block, "Footprint", new_fp)
                footprint = new_fp
                fps_set += 1
                log.append(f"  [{path.name}] {ref}: set footprint -> {new_fp}")
                changed = True

        # Add voltage to caps
        if re.match(r"^C\d", ref) and not has_voltage_spec(value):
            v = voltage_for_footprint(footprint)
            if v:
                new_value = f"{value} {v}"
                new_block = set_property(new_block, "Value", new_value)
                caps_updated += 1
                log.append(f"  [{path.name}] {ref}: {value!r} -> {new_value!r}")
                changed = True

        if changed:
            text = text[:start] + new_block + text[end:]

    if text != orig_text:
        path.write_text(text, encoding="utf-8", newline="\n")
    return caps_updated, fps_set, log


# ------- netlist (.net) pass -------

_NET_COMP_RE = re.compile(r"\(comp\s*\n\s*\(ref\s+\"([^\"]+)\"\)")


def process_netlist(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    orig_text = text
    updates = 0
    # Collect (start, end) spans of every cap comp block, then apply edits in reverse.
    spans = []
    for m in _NET_COMP_RE.finditer(text):
        ref = m.group(1)
        if not re.match(r"^C\d", ref):
            continue
        start = m.start()
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    spans.append((start, i + 1))
                    break
            i += 1
    for start, end in reversed(spans):
        block = text[start:end]
        val_m = re.search(r'\(value\s+"([^"]+)"\)', block)
        fp_m = re.search(r'\(footprint\s+"([^"]*)"\)', block)
        if not (val_m and fp_m):
            continue
        value = val_m.group(1)
        footprint = fp_m.group(1)
        if has_voltage_spec(value):
            continue
        v = voltage_for_footprint(footprint)
        if not v:
            continue
        new_value = f"{value} {v}"
        new_block = re.sub(
            r'(\(value\s+")([^"]+)(")',
            lambda m, nv=new_value: m.group(1) + nv + m.group(3),
            block,
            count=1,
        )
        text = text[:start] + new_block + text[end:]
        updates += 1
    if text != orig_text:
        path.write_text(text, encoding="utf-8", newline="\n")
    return updates


def main() -> None:
    total_caps = 0
    total_fps = 0
    for board in BOARDS:
        print(f"=== {board.name} ===")
        for sch in sorted(board.glob("*.kicad_sch")):
            c, f, log = process_schematic(sch)
            if c or f:
                for line in log:
                    print(line)
                total_caps += c
                total_fps += f
        for net in sorted(board.glob("*.net")):
            n = process_netlist(net)
            if n:
                print(f"  [{net.name}] updated {n} cap values in netlist")
    print()
    print(f"Caps with voltage added: {total_caps}")
    print(f"Empty footprints filled: {total_fps}")


if __name__ == "__main__":
    main()

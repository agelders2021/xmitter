"""
Generate per-board BOM spreadsheets for analog, frontpanel, and ss_pa.

For each board:
- Reads the .net file
- Excludes DNP components
- Groups components by Value within refdes-prefix category
- Categories: Resistors (R*), Capacitors (C*), Connectors (J*),
  ICs (U*), Inductors (L*), Transistors (Q*), Diodes (D*),
  Relays (K*), Transformers (T*), Test Points (TP*), Other
- Flags source-sense resistors on ss_pa (R1-R4, 0.22R, 1W)
- Separately tracks components missing footprints

Outputs:
- tools/_bom_<board>.xlsx — per-board BOM
- tools/_missing_footprints.xlsx — all boards combined
"""
from __future__ import annotations
import re
from pathlib import Path
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

BOARDS = [
    ("analog",     r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\analog\analog.net"),
    ("frontpanel", r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\frontpanel\frontpanel.net"),
    ("ss_pa",      r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\ss_pa\ss_pa.net"),
]

OUT_DIR = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\tools")

# Known special-attention components (board, refdes-pattern, note)
SPECIAL_NOTES = [
    ("ss_pa", r"^R[1234]$",
     "Source-sense resistor — needs 1 W rating (dissipates during RF peaks)"),
]

# Categories in priority order — first match wins per component
CATEGORIES = [
    ("Test points", lambda r, v, d: r.startswith("TP")),
    ("Resistor networks RP-RT", lambda r, v, d: r.startswith("RP") or r.startswith("RT")),
    ("Pots-trimmers RV", lambda r, v, d: r.startswith("RV")),
    ("Resistors",   lambda r, v, d: r.startswith("R") and not r.startswith("RP") and not r.startswith("RT") and not r.startswith("RV")),
    ("Capacitors filter CF", lambda r, v, d: r.startswith("CF")),
    ("Capacitors polarized", lambda r, v, d: r.startswith("CP") or (r.startswith("C") and "Polarized" in d)),
    ("Capacitors",  lambda r, v, d: r.startswith("C")),
    ("Inductors",   lambda r, v, d: r.startswith("L") and not r.startswith("LED")),
    ("Transformers", lambda r, v, d: r.startswith("T")),
    ("Diodes",      lambda r, v, d: r.startswith("D")),
    ("Transistors", lambda r, v, d: r.startswith("Q")),
    ("Relays",      lambda r, v, d: r.startswith("K")),
    ("ICs",         lambda r, v, d: r.startswith("U")),
    ("Connectors",  lambda r, v, d: r.startswith("J")),
    ("Mounting Mechanical", lambda r, v, d: r.startswith("H") or r.startswith("M") or r.startswith("FID")),
]


def parse_netlist(path: str):
    """Return list of {ref, value, footprint, description, dnp} dicts."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    components = []
    for m in re.finditer(r'\(comp\s*\n\s*\(ref\s+"([^"]+)"\)', text):
        ref = m.group(1)
        start = m.start()
        # Find matching close paren
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    block = text[start:i+1]
                    val = re.search(r'\(value\s+"([^"]+)"\)', block)
                    fp = re.search(r'\(footprint\s+"([^"]+)"\)', block)
                    desc = re.search(r'\(description\s+"([^"]*)"\)', block)
                    # DNP info is NOT in .net - need to search raw .kicad_sch
                    # For now, check for "DNP" field or set to False
                    dnp = False
                    # Sheetpath (sheet name)
                    sheetpath = re.search(r'\(names\s+"([^"]+)"\)', block)
                    components.append({
                        "ref": ref,
                        "value": val.group(1) if val else "?",
                        "footprint": fp.group(1) if fp else "",
                        "description": desc.group(1) if desc else "",
                        "sheet": sheetpath.group(1) if sheetpath else "/",
                        "dnp": dnp,
                    })
                    break
            i += 1
    return components


def get_dnp_refs(sch_file: Path) -> set:
    """Scan a .kicad_sch file for component instances with (dnp yes)."""
    text = sch_file.read_text(encoding="utf-8", errors="replace")
    dnp_refs = set()
    # Each top-level (symbol block has (dnp ...) and (property "Reference" "...")
    for m in re.finditer(r'\n\t\(symbol\s*\n', text):
        start = m.start()
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    block = text[start:i+1]
                    if re.search(r'\(dnp\s+yes\)', block):
                        ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
                        if ref_m:
                            dnp_refs.add(ref_m.group(1))
                    break
            i += 1
    return dnp_refs


def collect_dnp_refs(board_name: str) -> set:
    """Collect DNP refs across all sheets in a board's directory."""
    board_dir = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD") / board_name
    all_dnp = set()
    for sch in board_dir.glob("*.kicad_sch"):
        all_dnp |= get_dnp_refs(sch)
    return all_dnp


def refs_in_sheet(sch_file: Path) -> set:
    """Return refs that appear in a given sheet (not in lib_symbols)."""
    text = sch_file.read_text(encoding="utf-8", errors="replace")
    refs = set()
    for m in re.finditer(r'\n\t\(symbol\s*\n', text):
        start = m.start()
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    block = text[start:i+1]
                    ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
                    if ref_m and not ref_m.group(1).startswith("#"):
                        refs.add(ref_m.group(1))
                    break
            i += 1
    return refs


def ref_to_sheet(board_name: str) -> dict:
    """Build ref -> sheet-stem mapping."""
    board_dir = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD") / board_name
    mapping = {}
    for sch in board_dir.glob("*.kicad_sch"):
        for ref in refs_in_sheet(sch):
            mapping.setdefault(ref, sch.stem)
    return mapping


def categorize(ref: str, value: str, desc: str) -> str:
    for cat_name, test in CATEGORIES:
        if test(ref, value, desc):
            return cat_name
    return "Other"


def apply_special_note(board: str, ref: str) -> str:
    for b, pat, note in SPECIAL_NOTES:
        if b == board and re.match(pat, ref):
            return note
    return ""


def ref_num(ref: str) -> int:
    m = re.search(r"(\d+)$", ref)
    return int(m.group(1)) if m else 0


def write_board_bom(board: str, components: list, dnp_refs: set, sheet_map: dict):
    """Write BOM xlsx for a single board. Returns rows missing footprint."""
    wb = Workbook()
    missing_fp = []
    first = True

    # Bucket each component into exactly ONE category (first match wins)
    by_cat = {cat_name: [] for cat_name, _ in CATEGORIES}
    by_cat["Other"] = []
    for c in components:
        if c["ref"] in dnp_refs or c["ref"].startswith("#"):
            continue
        matched = False
        for cat_name, test in CATEGORIES:
            if test(c["ref"], c["value"], c["description"]):
                by_cat[cat_name].append(c)
                matched = True
                break
        if not matched:
            by_cat["Other"].append(c)

    for cat_name, _ in CATEGORIES + [("Other", None)]:
        cat_comps = by_cat.get(cat_name, [])
        if not cat_comps:
            continue
        ws = wb.create_sheet(title=cat_name[:30]) if not first else wb.active
        if first:
            ws.title = cat_name[:30]
            first = False

        # Group by value
        grouped = defaultdict(list)
        for c in cat_comps:
            grouped[c["value"]].append(c)

        # Headers
        headers = ["Value", "Qty", "References", "Footprint", "Sheet(s)", "Notes"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="DDDDDD")
            cell.alignment = Alignment(horizontal="center")

        # Rows (sorted by value)
        for value in sorted(grouped.keys()):
            comps = sorted(grouped[value], key=lambda c: (c["ref"][:2], ref_num(c["ref"])))
            refs = ", ".join(c["ref"] for c in comps)
            fps = sorted(set(c["footprint"] for c in comps))
            fp_display = fps[0] if len(fps) == 1 else "(mixed: " + " | ".join(fps) + ")"
            sheets = sorted(set(sheet_map.get(c["ref"], "?") for c in comps))
            sheet_display = ", ".join(sheets)
            notes = sorted(set(filter(None, (apply_special_note(board, c["ref"]) for c in comps))))
            note_display = "; ".join(notes)
            qty = len(comps)
            ws.append([value, qty, refs, fp_display, sheet_display, note_display])

            # Flag missing footprints
            for c in comps:
                if not c["footprint"]:
                    missing_fp.append({
                        "board": board,
                        "sheet": sheet_map.get(c["ref"], "?"),
                        "ref": c["ref"],
                        "value": c["value"],
                        "category": cat_name,
                        "description": c["description"][:80],
                    })

        # Column widths
        for col, width in zip("ABCDEF", (18, 6, 40, 50, 25, 50)):
            ws.column_dimensions[col].width = width

    out = OUT_DIR / f"_bom_{board}.xlsx"
    wb.save(out)
    return missing_fp, out


def write_missing_footprints(all_missing: list):
    wb = Workbook()
    ws = wb.active
    ws.title = "Missing footprints"
    headers = ["Board", "Sheet", "Ref", "Value", "Category", "Description"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    # Sort by board then sheet then ref
    for item in sorted(all_missing, key=lambda x: (x["board"], x["sheet"], x["ref"])):
        ws.append([item["board"], item["sheet"], item["ref"], item["value"],
                   item["category"], item["description"]])
    for col, width in zip("ABCDEF", (12, 20, 10, 20, 25, 60)):
        ws.column_dimensions[col].width = width
    out = OUT_DIR / "_missing_footprints.xlsx"
    wb.save(out)
    return out


def main():
    all_missing = []
    for board, netfile in BOARDS:
        if not Path(netfile).exists():
            print(f"[SKIP] {board}: {netfile} not found")
            continue
        comps = parse_netlist(netfile)
        dnp = collect_dnp_refs(board)
        sheet_map = ref_to_sheet(board)
        print(f"\n=== {board} ===")
        print(f"  components in netlist: {len(comps)}")
        print(f"  DNP refs (excluded): {sorted(dnp)}")
        missing, out = write_board_bom(board, comps, dnp, sheet_map)
        print(f"  wrote {out.name}")
        if missing:
            print(f"  missing footprints: {len(missing)}")
        all_missing.extend(missing)

    out = write_missing_footprints(all_missing)
    print(f"\nMissing-footprints spreadsheet: {out.name} ({len(all_missing)} items)")


if __name__ == "__main__":
    main()

"""
Consolidate the raw per-board BOMs + total BOM + cart diff into two clean
deliverables under Documentation/:

  Documentation/Parts_List_RevD.xlsx        (summary + per-board tabs)
  Documentation/Cart_Diff_2026-11-03.xlsx   (Add / Remove_Overstock / Matched)

Assumes gen_board_boms.py and gen_cart_diff.py have already been run and
the tools/_bom_*.xlsx + tools/_cart_diff.xlsx files exist.
"""
from pathlib import Path
from datetime import date

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment

TOOLS = Path(__file__).resolve().parent
DOCS  = Path(__file__).resolve().parent.parent / "Documentation"

HEADER_FILL = PatternFill("solid", fgColor="DDDDDD")
TITLE_FILL  = PatternFill("solid", fgColor="4F81BD")


def copy_sheets(src_wb, dst_wb, prefix=""):
    for sn in src_wb.sheetnames:
        src = src_wb[sn]
        dst_name = (prefix + " " + sn) if prefix else sn
        dst_name = dst_name[:31]
        dst = dst_wb.create_sheet(title=dst_name)
        for row in src.iter_rows(values_only=False):
            for cell in row:
                new_cell = dst.cell(row=cell.row, column=cell.column, value=cell.value)
                if cell.has_style:
                    new_cell.font = cell.font.copy()
                    new_cell.fill = cell.fill.copy()
                    new_cell.alignment = cell.alignment.copy()
        for col_letter, dim in src.column_dimensions.items():
            dst.column_dimensions[col_letter].width = dim.width


def build_parts_list():
    """Combine tools/_bom_total.xlsx (as Summary) + per-board files."""
    out = DOCS / "Parts_List_RevD.xlsx"
    DOCS.mkdir(exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)

    # Title / cover sheet
    cover = wb.create_sheet("Overview")
    cover["A1"] = "xmitter Rev D — Parts List"
    cover["A1"].font = Font(bold=True, size=16)
    cover["A2"] = f"Generated: {date.today().isoformat()}"
    cover["A2"].font = Font(italic=True, color="555555")
    cover["A4"] = "Boards in scope:"
    cover["A4"].font = Font(bold=True)
    cover["A5"] = "  • analog       (KiCAD/analog/analog.net)"
    cover["A6"] = "  • ss_pa        (KiCAD/ss_pa/ss_pa.net)"
    cover["A7"] = "  • lpf (Output) (KiCAD/Output LPF/Output LPF.net)"
    cover["A8"] = "  • protoshield  (KiCAD/protoshield/protoshield.net)"
    cover["A10"] = "DNP components are excluded.  Quantities are physical placements"
    cover["A11"] = "(so e.g. a 10 kΩ resistor used 24× appears as qty 24)."
    cover["A13"] = "Tabs:"
    cover["A13"].font = Font(bold=True)
    cover["A14"] = "  • Summary_*  — consolidated by category across all 4 boards"
    cover["A15"] = "  • analog / ss_pa / lpf / protoshield — per-board detail"
    cover.column_dimensions["A"].width = 80

    # Per-category consolidated tabs (from _bom_total.xlsx)
    total_src = load_workbook(TOOLS / "_bom_total.xlsx")
    for sn in total_src.sheetnames:
        src = total_src[sn]
        dst_name = f"Summary_{sn}"[:31]
        dst = wb.create_sheet(title=dst_name)
        for row in src.iter_rows():
            for cell in row:
                new_cell = dst.cell(row=cell.row, column=cell.column, value=cell.value)
                if cell.has_style:
                    new_cell.font  = cell.font.copy()
                    new_cell.fill  = cell.fill.copy()
                    new_cell.alignment = cell.alignment.copy()
        for col_letter, dim in src.column_dimensions.items():
            dst.column_dimensions[col_letter].width = dim.width

    # Per-board tabs — put each board's BOM into one tab (first category tab)
    # by flattening every category into a single sheet.
    for board in ("analog", "ss_pa", "lpf", "protoshield"):
        src_path = TOOLS / f"_bom_{board}.xlsx"
        if not src_path.exists():
            continue
        src_wb = load_workbook(src_path)
        dst = wb.create_sheet(title=board[:31])
        dst.cell(row=1, column=1, value=f"Board: {board}").font = Font(bold=True, size=14)
        row_idx = 3
        for sn in src_wb.sheetnames:
            src = src_wb[sn]
            # Category header row
            dst.cell(row=row_idx, column=1, value=sn).font = Font(bold=True, size=12,
                                                                   color="FFFFFF")
            for c in range(1, 7):
                dst.cell(row=row_idx, column=c).fill = TITLE_FILL
            row_idx += 1
            # Copy src rows (skip the first row which is just the category header)
            src_iter = src.iter_rows(min_row=1, values_only=False)
            for r_num, src_row in enumerate(src_iter, start=1):
                dst_row = row_idx + r_num - 1
                for cell in src_row:
                    new_cell = dst.cell(row=dst_row, column=cell.column, value=cell.value)
                    if cell.has_style:
                        new_cell.font = cell.font.copy()
                        new_cell.fill = cell.fill.copy()
                        new_cell.alignment = cell.alignment.copy()
            row_idx = dst_row + 2
        for col, w in zip("ABCDEF", (18, 6, 40, 50, 25, 50)):
            dst.column_dimensions[col].width = w

    wb.save(out)
    return out


def build_cart_diff_copy():
    out = DOCS / f"Cart_Diff_{date.today().isoformat()}.xlsx"
    src = load_workbook(TOOLS / "_cart_diff.xlsx")
    dst = Workbook()
    dst.remove(dst.active)

    # Cover sheet
    cover = dst.create_sheet("Overview")
    cover["A1"] = "xmitter Rev D — Mouser Cart vs BOM Diff"
    cover["A1"].font = Font(bold=True, size=16)
    cover["A2"] = f"Cart file : Cart_Nov03_1245PM.xls"
    cover["A3"] = f"BOM source: live KiCad netlists (analog, ss_pa, lpf, protoshield)"
    cover["A4"] = f"Generated : {date.today().isoformat()}"
    cover["A4"].font = Font(italic=True, color="555555")
    cover["A6"] = "Tabs:"
    cover["A6"].font = Font(bold=True)
    cover["A7"] = "  • Add              — BOM items missing from cart (or short)."
    cover["A8"] = "                        1/4 W resistor qty is rounded UP to the next 10"
    cover["A9"] = "                        for the Mouser price break."
    cover["A10"] = "  • Remove_Overstock — cart lines not needed by the BOM, or over-ordered."
    cover["A11"] = "                        Yellow fill = may match a BOM item by footprint hint;"
    cover["A12"] = "                        verify before removing."
    cover["A13"] = "  • Matched          — pairings the matcher found (sanity check)."
    cover.column_dimensions["A"].width = 90

    for sn in src.sheetnames:
        src_ws = src[sn]
        dst_ws = dst.create_sheet(title=sn[:31])
        for row in src_ws.iter_rows():
            for cell in row:
                new_cell = dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)
                if cell.has_style:
                    new_cell.font  = cell.font.copy()
                    new_cell.fill  = cell.fill.copy()
                    new_cell.alignment = cell.alignment.copy()
        for col_letter, dim in src_ws.column_dimensions.items():
            dst_ws.column_dimensions[col_letter].width = dim.width

    dst.save(out)
    return out


def main():
    pl = build_parts_list()
    cd = build_cart_diff_copy()
    print(f"Wrote {pl}")
    print(f"Wrote {cd}")


if __name__ == "__main__":
    main()

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
    cover["A8"] = "  (protoshield dropped — passives migrated onto analog)"
    cover["A10"] = "DNP components are excluded.  Quantities are physical placements"
    cover["A11"] = "(so e.g. a 10 kΩ resistor used 24× appears as qty 24)."
    cover["A13"] = "Tabs:"
    cover["A13"].font = Font(bold=True)
    cover["A14"] = "  • Summary_*  — consolidated by category across all 3 boards"
    cover["A15"] = "  • analog / ss_pa / lpf — per-board detail"
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
    for board in ("analog", "ss_pa", "lpf"):
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

    # Preserve any "Done" marks the user added to column A of
    # Remove_Overstock in the prior Documentation file.
    #
    # Lesson from 2026-11-06: an earlier version keyed on cart LINE
    # NUMBER and only read the file whose name matched TODAY's date.
    # Both choices lost user marks silently:
    #   * Mouser renumbers cart lines every time an item is deleted,
    #     so a line-number key doesn't survive a cart refresh.
    #   * Running the packager on a new calendar day created a fresh
    #     dated filename whose prior-same-date lookup found nothing,
    #     so marks from yesterday's file were dropped without warning.
    #
    # Current logic: scan ALL prior Cart_Diff_*.xlsx files in reverse
    # date order, pick the most recent one that has any marks, and
    # match by MOUSER # (robust to cart-line renumbering and to
    # cross-day regens).
    # Marks on the Remove_Overstock tab key on Mouser # (stable across
    # cart-line renumbering).  Marks on the Add tab key on
    # (Kind, Value/MPN, Footprint) because Add rows describe items NOT
    # in the cart and so have no Mouser #.
    prior_remove_marks: dict[str, str] = {}       # Mouser#     -> mark
    prior_add_marks:    dict[tuple, str] = {}     # (K,V,FP)    -> mark
    prior_src = None
    candidates = sorted(DOCS.glob("Cart_Diff_*.xlsx"), reverse=True)
    for cand in candidates:
        try:
            wb = load_workbook(cand, data_only=True)
        except Exception:
            continue

        # --- Remove_Overstock marks (by Mouser #) ---
        remove_candidate: dict[str, str] = {}
        if "Remove_Overstock" in wb.sheetnames:
            pws = wb["Remove_Overstock"]
            header = [str(c.value) if c.value is not None else "" for c in pws[1]]
            try:
                done_col   = header.index("Done")     + 1
                mouser_col = header.index("Mouser #") + 1
                for r in range(2, pws.max_row + 1):
                    mark = pws.cell(row=r, column=done_col).value
                    mpn  = pws.cell(row=r, column=mouser_col).value
                    if mark and str(mark).strip() and mpn and str(mpn).strip():
                        remove_candidate[str(mpn).strip()] = str(mark).strip()
            except ValueError:
                pass

        # --- Add-tab marks (by Kind, Value, Footprint).  Supports both
        # the legacy no-Done-column format (col A was empty, user inserted
        # their own) and the new "In stock" column A format. ---
        add_candidate: dict[tuple, str] = {}
        if "Add" in wb.sheetnames:
            aws = wb["Add"]
            header = [str(c.value) if c.value is not None else "" for c in aws[1]]
            # Figure out column indices robustly
            def col_of(names):
                for n in names:
                    if n in header:
                        return header.index(n) + 1
                return None
            mark_col = col_of(["In stock", "Done", ""])
            kind_col = col_of(["Kind"])
            val_col  = col_of(["Value / MPN", "Value"])
            fp_col   = col_of(["Footprint"])
            if mark_col and kind_col and val_col and fp_col:
                for r in range(2, aws.max_row + 1):
                    mark = aws.cell(row=r, column=mark_col).value
                    kind = aws.cell(row=r, column=kind_col).value
                    val  = aws.cell(row=r, column=val_col).value
                    fp   = aws.cell(row=r, column=fp_col).value
                    if mark and str(mark).strip():
                        key = (str(kind or "").strip(),
                               str(val  or "").strip(),
                               str(fp   or "").strip())
                        add_candidate[key] = str(mark).strip()

        wb.close()
        if remove_candidate or add_candidate:
            prior_remove_marks = remove_candidate
            prior_add_marks    = add_candidate
            prior_src          = cand.name
            break
    if prior_remove_marks or prior_add_marks:
        print(f"Carrying forward marks from {prior_src}: "
              f"{len(prior_remove_marks)} Remove_Overstock + "
              f"{len(prior_add_marks)} Add")

    src = load_workbook(TOOLS / "_cart_diff.xlsx")
    dst = Workbook()
    dst.remove(dst.active)

    # Cover sheet
    cover = dst.create_sheet("Overview")
    cover["A1"] = "xmitter Rev D — Mouser Cart vs BOM Diff"
    cover["A1"].font = Font(bold=True, size=16)
    cover["A2"] = f"Cart file : Cart_Nov04_0836PM.xls"
    cover["A3"] = f"BOM source: live KiCad netlists (analog, ss_pa, lpf)"
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

        # Restore user marks.  Report any that couldn't be matched so a
        # silent loss can't happen again (the exact failure mode that
        # motivated this rewrite on 2026-11-06).
        if sn == "Remove_Overstock" and prior_remove_marks:
            hdr = [str(c.value) if c.value is not None else "" for c in dst_ws[1]]
            try:
                done_col   = hdr.index("Done")     + 1
                mouser_col = hdr.index("Mouser #") + 1
            except ValueError:
                print("WARNING: Remove_Overstock header missing Done or Mouser # "
                      "— cannot restore prior marks")
            else:
                restored = set()
                for r in range(2, dst_ws.max_row + 1):
                    mpn = dst_ws.cell(row=r, column=mouser_col).value
                    if mpn is None:
                        continue
                    key = str(mpn).strip()
                    if key in prior_remove_marks:
                        dst_ws.cell(row=r, column=done_col,
                                    value=prior_remove_marks[key])
                        restored.add(key)
                missing = set(prior_remove_marks) - restored
                if missing:
                    print(f"WARNING: {len(missing)} prior Remove_Overstock mark(s) "
                          f"could NOT be matched (Mouser # no longer in the diff):")
                    for m in sorted(missing):
                        print(f"    {m}  (mark was '{prior_remove_marks[m]}')")

        if sn == "Add" and prior_add_marks:
            hdr = [str(c.value) if c.value is not None else "" for c in dst_ws[1]]
            def _col(names):
                for n in names:
                    if n in hdr:
                        return hdr.index(n) + 1
                return None
            mark_col = _col(["In stock", "Done"])
            kind_col = _col(["Kind"])
            val_col  = _col(["Value / MPN", "Value"])
            fp_col   = _col(["Footprint"])
            if not (mark_col and kind_col and val_col and fp_col):
                print("WARNING: Add tab header missing required columns "
                      "— cannot restore prior marks")
            else:
                restored = set()
                for r in range(2, dst_ws.max_row + 1):
                    kind = dst_ws.cell(row=r, column=kind_col).value
                    val  = dst_ws.cell(row=r, column=val_col).value
                    fp   = dst_ws.cell(row=r, column=fp_col).value
                    key = (str(kind or "").strip(),
                           str(val  or "").strip(),
                           str(fp   or "").strip())
                    if key in prior_add_marks:
                        dst_ws.cell(row=r, column=mark_col,
                                    value=prior_add_marks[key])
                        restored.add(key)
                missing = set(prior_add_marks) - restored
                if missing:
                    print(f"WARNING: {len(missing)} prior Add mark(s) could NOT "
                          f"be matched (no row with same Kind/Value/Footprint):")
                    for k in sorted(missing):
                        print(f"    {k}  (mark was '{prior_add_marks[k]}')")

    dst.save(out)
    return out


def main():
    pl = build_parts_list()
    cd = build_cart_diff_copy()
    print(f"Wrote {pl}")
    print(f"Wrote {cd}")


if __name__ == "__main__":
    main()

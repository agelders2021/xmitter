"""Strip vestigial pins/wires/labels from the root schematic.

Path A of the pre-layout refactor. Now that every cross-sheet net is a
global_label (on the child sheets), the root sheet needs no stitching:
- pins on the sheet blocks are unused,
- wires between them are dangling,
- labels placed for readability are meaningless.

This script removes all of them, leaving each (sheet ...) block with its
identity properties (Sheetname, Sheetfile) but no pins.

Writes UTF-8 without BOM.
"""

import re
from pathlib import Path

ROOT = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\KiCAD.kicad_sch")


def find_balanced_block(text, start_idx):
    """Return (start, end_exclusive) of s-expression starting at start_idx."""
    assert text[start_idx] == "("
    depth = 0
    i = start_idx
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == "\\":
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return start_idx, i + 1
        i += 1
    raise ValueError("Unbalanced")


def strip_toplevel(text, keyword):
    """Remove every top-level `(keyword ...)` s-expression from text.

    Detects by scanning left-to-right at whatever depth level the wire/label
    happens to sit; in practice these constructs are always at file-scope
    inside the root (kicad_sch ...) form so we treat "at start of line, after
    any leading whitespace" as the mark."""
    pattern = re.compile(r"[ \t]*\(" + re.escape(keyword) + r"\b")
    result = []
    i = 0
    removed = 0
    while True:
        m = pattern.search(text, i)
        if not m:
            result.append(text[i:])
            break
        result.append(text[i:m.start()])
        s, e = find_balanced_block(text, m.start() + (m.end() - m.start() - len(keyword) - 1))
        # Consume trailing newline if present so we don't leave blank lines
        while e < len(text) and text[e] in "\r\n":
            e += 1
            if e < len(text) and text[e - 1] == "\r" and text[e] == "\n":
                e += 1
                break
        i = e
        removed += 1
    return "".join(result), removed


def strip_pins_from_sheets(text):
    """Inside every (sheet ...) block, remove nested (pin "NAME" ...) blocks."""
    result = []
    i = 0
    total_pins = 0
    while True:
        j = text.find("(sheet\b", i) if False else text.find("(sheet", i)
        # Match "(sheet" only when followed by non-alphanumeric (to avoid "(sheet_instances" or similar)
        while j >= 0 and j + 6 < len(text) and text[j + 6].isalnum():
            j = text.find("(sheet", j + 1)
        if j < 0:
            result.append(text[i:])
            break
        s, e = find_balanced_block(text, j)
        result.append(text[i:s])
        sheet_block = text[s:e]
        # Strip pins inside this block
        # Find each (pin "NAME" ... ) at any depth inside — but only at direct
        # child-of-sheet depth. Simplest: walk inner chars, look for "\n\t\t(pin ".
        inner_result = []
        ii = 0
        while True:
            jj = sheet_block.find("(pin ", ii)
            if jj < 0:
                inner_result.append(sheet_block[ii:])
                break
            # Confirm this is a real pin block by looking back for the
            # preceding indent — pins are second-level inside sheet
            ss, ee = find_balanced_block(sheet_block, jj)
            # Consume leading whitespace on this line
            back = jj
            while back > 0 and sheet_block[back - 1] in " \t":
                back -= 1
            # Consume trailing newline
            while ee < len(sheet_block) and sheet_block[ee] in "\r\n":
                ee += 1
                if ee < len(sheet_block) and sheet_block[ee - 1] == "\r" and sheet_block[ee] == "\n":
                    ee += 1
                    break
            inner_result.append(sheet_block[ii:back])
            total_pins += 1
            ii = ee
        result.append("".join(inner_result))
        i = e
    return "".join(result), total_pins


def main():
    raw = ROOT.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("WARNING: root had BOM — stripping")
        raw = raw[3:]
    text = raw.decode("utf-8")

    original_size = len(text)

    # Order: pins first (inside sheet blocks), then junctions, wires, labels
    text, n_pins = strip_pins_from_sheets(text)
    print(f"  Stripped {n_pins} sheet pins")

    text, n_junc = strip_toplevel(text, "junction")
    print(f"  Stripped {n_junc} junctions")

    text, n_wire = strip_toplevel(text, "wire")
    print(f"  Stripped {n_wire} wires")

    text, n_label = strip_toplevel(text, "label")
    print(f"  Stripped {n_label} labels")

    opens = text.count("(")
    closes = text.count(")")
    print(f"\nSize: {original_size} -> {len(text)} bytes")
    print(f"Parens: {opens} opens, {closes} closes (balanced: {opens == closes})")
    assert opens == closes, "PAREN MISMATCH — aborting write"

    ROOT.write_bytes(text.encode("utf-8"))
    print(f"Wrote {ROOT.name} (UTF-8, no BOM)")


if __name__ == "__main__":
    main()

"""Convert every hierarchical_label to global_label in the listed schematics.

Path A of the pre-layout refactor. Global labels connect across all sheets
by name automatically, so this obsoletes root-sheet sheet-pins + stitching
wires. Root-sheet cleanup happens in a separate script.

Preserves: label name, shape, at, effects, uuid.
Adds: fields_autoplaced, Intersheetrefs property (standard KiCad 10
global_label fields).

Writes UTF-8 without BOM to avoid the KiCad-10 empty-file trap.
"""

import re
import sys
from pathlib import Path

SHEETS = [
    "arduino.kicad_sch",
    "bias.kicad_sch",
    "buffer_keyer.kicad_sch",
    "vfo.kicad_sch",
    "interface.kicad_sch",
    "front_panel.kicad_sch",
]

KICAD_DIR = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD")


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


def extract_inner_field(block, field_name):
    """Extract the first `(field_name ...)` s-exp inside a balanced block.
    Returns the entire s-exp string, or None if not found."""
    # Find `(field_name ` respecting paren depth
    i = 1  # skip opening paren of block
    depth = 0
    while i < len(block):
        c = block[i]
        if c == '"':
            i += 1
            while i < len(block) and block[i] != '"':
                if block[i] == "\\":
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if c == "(":
            if depth == 0 and block[i:].startswith(f"({field_name}") and block[i + 1 + len(field_name)] in (" ", "\t", "\n", "\r"):
                s, e = find_balanced_block(block, i)
                return block[s:e]
            depth += 1
        elif c == ")":
            depth -= 1
        i += 1
    return None


def convert_one(block, indent_hint="\t"):
    """Given a `(hierarchical_label ...)` s-exp, return the global_label rewrite."""
    # First token after '(hierarchical_label ' is the name string
    m = re.match(r'\(hierarchical_label\s+("(?:[^"\\]|\\.)*")', block)
    assert m, f"Bad hier_label header: {block[:80]!r}"
    name_q = m.group(1)

    # Extract needed sub-fields verbatim
    shape = extract_inner_field(block, "shape")
    at = extract_inner_field(block, "at")
    effects = extract_inner_field(block, "effects")
    uuid = extract_inner_field(block, "uuid")

    assert shape and at and effects and uuid, f"Missing fields in {block[:120]!r}"

    # Normalize any CRLF inside the extracted sub-fields to LF, so the caller's
    # unconditional "\n" -> line_end pass produces clean output. Otherwise CRLF
    # inputs turn into CRCRLF.
    shape = shape.replace("\r\n", "\n")
    at = at.replace("\r\n", "\n")
    effects = effects.replace("\r\n", "\n")
    uuid = uuid.replace("\r\n", "\n")

    # Detect indent from the original — count leading tab/space chars on the
    # `(shape` line so the rewrite matches surrounding formatting.
    inner_indent = indent_hint * 2
    # Try to detect actual inner indent
    m2 = re.search(r"\n([ \t]+)\(shape", block)
    if m2:
        inner_indent = m2.group(1)
    outer_indent = inner_indent[:-1] if inner_indent.endswith(("\t", " ")) else inner_indent

    # Parse (at X Y ANGLE) so we can put Intersheetrefs at the same location
    m3 = re.match(r"\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)", at)
    ax, ay, aa = m3.group(1), m3.group(2), m3.group(3)

    # Build the new block
    parts = [
        f"(global_label {name_q}",
        f"{inner_indent}{shape}",
        f"{inner_indent}{at}",
        f"{inner_indent}(fields_autoplaced yes)",
        f"{inner_indent}{effects}",
        f"{inner_indent}{uuid}",
        f'{inner_indent}(property "Intersheetrefs" "${{INTERSHEET_REFS}}"',
        f"{inner_indent}\t(at {ax} {ay} 0)",
        f"{inner_indent}\t(effects",
        f"{inner_indent}\t\t(font",
        f"{inner_indent}\t\t\t(size 1.27 1.27)",
        f"{inner_indent}\t\t)",
        f"{inner_indent}\t\t(hide yes)",
        f"{inner_indent}\t)",
        f"{inner_indent})",
        f"{outer_indent})",
    ]
    return "\n".join(parts)


def convert_sheet(path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print(f"  WARNING: {path.name} had BOM — stripping")
        raw = raw[3:]
    text = raw.decode("utf-8")

    # Detect line ending style
    crlf = "\r\n" in text
    line_end = "\r\n" if crlf else "\n"

    # Find and convert each (hierarchical_label ...) block
    result = []
    i = 0
    n_converted = 0
    while True:
        j = text.find("(hierarchical_label ", i)
        if j < 0:
            result.append(text[i:])
            break
        result.append(text[i:j])
        s, e = find_balanced_block(text, j)
        original = text[s:e]
        new = convert_one(original).replace("\n", line_end)
        result.append(new)
        i = e
        n_converted += 1

    new_text = "".join(result)

    # Sanity: paren balance
    opens = new_text.count("(")
    closes = new_text.count(")")
    assert opens == closes, f"Paren mismatch in {path.name}: {opens} opens, {closes} closes"

    # Write back UTF-8 no BOM, preserving line endings
    path.write_bytes(new_text.encode("utf-8"))
    print(f"  {path.name}: converted {n_converted} labels, "
          f"{len(raw)} -> {len(new_text.encode('utf-8'))} bytes, parens balanced ({opens})")
    return n_converted


def main():
    total = 0
    for name in SHEETS:
        p = KICAD_DIR / name
        if not p.exists():
            print(f"SKIP: {name} (not found)")
            continue
        total += convert_sheet(p)
    print(f"\nTotal hierarchical_label -> global_label conversions: {total}")


if __name__ == "__main__":
    main()

"""
Generate Documentation/doc_index.md — a searchable topic-organized index
of every .md file in the project.

Two sections:
  1. "By topic" — hand-curated topic patterns (regex) mapped to hits
     across all docs. This is what you scan when you don't remember
     which file contains what.
  2. "By file"  — each .md file's H1/H2/H3 outline. This is what you
     scan when you know the file but not the section.

Regenerate any time docs are edited:

    python tools/gen_doc_index.py

Reads:  **/*.md   (excludes .git/, Documentation/legacy/, xmitter_prj/legacy/)
Writes: Documentation/doc_index.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Windows default console is cp1252; docs contain ≈ µ Ω → em-dash etc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "Documentation" / "doc_index.md"

EXCLUDE_DIRS = {".git", "legacy", ".vscode", "__pycache__", ".claude"}

# ---------------------------------------------------------------------------
# Topic patterns: (topic_label, regex). Regex is case-insensitive, matched
# against each line body. Add topics here as new recurring queries surface.
# ---------------------------------------------------------------------------
TOPICS: list[tuple[str, str]] = [
    ("Toroid winding & cores (T50-6, T68-6, T106-2, FT37, FT82, FT114)",
        r"\b(T\d{2,3}-\d+|FT\d{2,3}-\d+|toroid|hand.?wound|A[_\-]?L\b|AL\s*≈|"
        r"bifilar|\d+\s*turns?|turns?\s+ratio|magnet\s*wire|#\d{2}\s*AWG)"),
    ("Grid bias (OPA454, DAC, slam)",
        r"\b(grid\s*bias|OPA454|bias\s*DAC|MCP4921|bias\s*slam|slam\s*handoff|"
        r"\-\s*60\s*V|Vgg)\b"),
    ("Cathode monitor, failsafe, fault chain",
        r"\b(cathode\s*monitor|LM393|OPA1641|diode.?OR|failsafe|fault\s*handler|"
        r"NVS\s*fault|hysteresis)\b"),
    ("PA (6146B, operating point, push-pull, tank)",
        r"\b(6146B|push.?pull|PA\s*stage|plate\s*current|R17|V6|180\s*V|"
        r"tank\s*circuit|Koren)\b"),
    ("Driver (12HG7, 12BY7A, output xfmr)",
        r"\b(12HG7|12BY7A|driver\s*stage|driver\s*output|6CL6)\b"),
    ("Balun / broadband transformer",
        r"\b(balun|broadband\s*transformer|4:1|6:1)\b"),
    ("Output LPF (7-pole, Chebyshev)",
        r"\b(LPF|low.?pass|Chebyshev|540\s*nH|7.?pole)\b"),
    ("VFO / Si5351 / VFO buffer",
        r"\b(VFO|Si5351|J310|source\s*follower|drain\s*follower|VCXO)\b"),
    ("Keyer / CW envelope / raised cosine",
        r"\b(keyer|envelope|raised\s*cosine|LUT|WinKey|MC1496|"
        r"predistortion|25\s*[µu]s\s*tick)\b"),
    ("Front panel / RJ45 umbilical / PCF8575 / LCD",
        r"\b(front\s*panel|RJ45|RJE1D|umbilical|PCF8575|HD44770|HD44780|"
        r"WH2004A|LCD|MBL.?600|MCP4725)\b"),
    ("I²C bus, addresses",
        r"\b(I2C|I²C|0x[26]\d|MCP4728|MAX17048|STEMMA)\b"),
    ("Power supply, rails, transformer, sequencing",
        r"\b(power\s*supply|\+?\d{1,3}\s*V\s*rail|rail\s*inventory|inrush|"
        r"soft.?start|filament|HV\s*rail|xfmr|sequencing)\b"),
    ("PCB fab, DRC, ERC, footprint, JLCPCB",
        r"\b(JLCPCB|DRC|ERC|footprint|gerber|clearance|net.?class|"
        r"HASL|OSP|PCB\s*layout|via\s*size|drill|silkscreen|solder\s*mask)\b"),
    ("Firmware, ESP-IDF, FreeRTOS, tasks",
        r"\b(ESP.?IDF|FreeRTOS|esp32.?s3|core.?pinn?ing|xTask|CORE_MONITOR|"
        r"CORE_KEYING|sdkconfig|CMake)\b"),
    ("BOM, sourcing, cost",
        r"\b(BOM|sourcing|Mouser|Digi.?Key|Kits\s*and\s*Parts|Amidon|"
        r"unit\s*cost|part\s*number|MPN)\b"),
    ("Build checklist, phases, long-lead",
        r"\b(build\s*checklist|phase\s*\d|long.?lead|order\s*now|"
        r"before\s*fab|pre.?flight)\b"),
    ("Component bins / physical inventory",
        r"\b(bin\s+\d|component\s*bin|anti.?static\s*bag|drawer)\b"),
    ("Legacy / obsolete / superseded",
        r"\b(legacy|obsolete|superseded|deprecated|no longer|removed)\b"),
]


@dataclass
class Heading:
    file: Path
    line: int
    level: int
    text: str


def walk_md_files() -> list[Path]:
    files: list[Path] = []
    for p in REPO.rglob("*.md"):
        parts = set(p.relative_to(REPO).parts)
        if parts & EXCLUDE_DIRS:
            continue
        if p.resolve() == OUT.resolve():
            continue  # never index this file into itself
        files.append(p)
    return sorted(files, key=lambda x: str(x.relative_to(REPO)).lower())


def extract_headings(path: Path) -> list[Heading]:
    out: list[Heading] = []
    in_fence = False
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if m:
            out.append(Heading(path, i, len(m.group(1)), m.group(2)))
    return out


def find_topic_hits(files: list[Path]) -> dict[str, list[tuple[Path, int, str]]]:
    """Return {topic_label: [(file, line, heading_text), ...]}.

    Only H1/H2/H3 heading lines are matched — this keeps the "By topic"
    section a curated map of *sections* per topic, not every incidental
    mention. For body-level search use `--search <regex>`.

    Additionally, if a file has NO matching heading but the topic pattern
    matches any body line, the file is listed once with a "(body only)"
    marker so it doesn't disappear from the topic view.
    """
    compiled = [(label, re.compile(pat, re.IGNORECASE)) for label, pat in TOPICS]
    hits: dict[str, list[tuple[Path, int, str]]] = {label: [] for label, _ in TOPICS}

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        heading_matches: dict[str, list[tuple[int, str]]] = {label: [] for label, _ in TOPICS}
        body_only: dict[str, tuple[int, str] | None] = {label: None for label, _ in TOPICS}
        in_fence = False

        for i, raw in enumerate(text.splitlines(), 1):
            if raw.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            body = raw.strip()
            if not body:
                continue
            heading_m = re.match(r"^(#{1,3})\s+(.+?)\s*$", raw)
            if heading_m:
                htext = heading_m.group(2)
                for label, rx in compiled:
                    if rx.search(htext):
                        heading_matches[label].append((i, htext))
            else:
                if body.startswith(("│", "├", "└", "┌", "┬", "─")):
                    continue
                for label, rx in compiled:
                    if body_only[label] is None and rx.search(body):
                        body_only[label] = (i, body)

        for label, _ in TOPICS:
            for i, htext in heading_matches[label]:
                hits[label].append((path, i, htext))
            if not heading_matches[label] and body_only[label] is not None:
                i, body = body_only[label]
                snippet = body if len(body) <= 90 else body[:87] + "..."
                hits[label].append((path, i, f"(body) {snippet}"))

    return hits


def rel(p: Path) -> str:
    return str(p.relative_to(REPO)).replace("\\", "/")


def render(files: list[Path], topic_hits: dict[str, list], today: str) -> str:
    lines: list[str] = []
    a = lines.append

    a("# Documentation index")
    a("")
    a(f"Auto-generated by `tools/gen_doc_index.py` on {today}.  Do not")
    a("hand-edit — rerun the script after editing docs.")
    a("")
    a("Two ways to find things:")
    a("")
    a("- **By topic** — scan when you don't remember which file has what.")
    a("  Each topic lists file:line hits with the matching line quoted.")
    a("- **By file** — each .md's H1/H2/H3 outline. Scan when you know")
    a("  the file but not the section.")
    a("")
    a("To search interactively in `less`, use `/pattern` inside the viewer.")
    a("For a raw search across all docs from the shell:")
    a("")
    a("    python tools/gen_doc_index.py --search <regex>")
    a("")
    a("---")
    a("")

    # ---- By topic ------------------------------------------------------
    a("## By topic")
    a("")
    for label, _ in TOPICS:
        rows = topic_hits.get(label, [])
        a(f"### {label}")
        a("")
        if not rows:
            a("_no hits_")
            a("")
            continue
        per_file: dict[Path, list[tuple[int, str]]] = {}
        for path, ln, text in rows:
            per_file.setdefault(path, []).append((ln, text))
        for path in sorted(per_file, key=lambda p: rel(p).lower()):
            a(f"- **{rel(path)}**")
            for ln, text in per_file[path]:
                a(f"    - L{ln}: {text}")
        a("")

    a("---")
    a("")

    # ---- By file -------------------------------------------------------
    a("## By file (outline)")
    a("")
    for path in files:
        heads = extract_headings(path)
        a(f"### {rel(path)}")
        a("")
        if not heads:
            a("_no headings_")
            a("")
            continue
        for h in heads:
            indent = "  " * (h.level - 1)
            a(f"{indent}- L{h.line}: {h.text}")
        a("")

    return "\n".join(lines) + "\n"


def cli_search(pattern: str) -> None:
    """Run an ad-hoc regex search across all indexed docs and print hits."""
    rx = re.compile(pattern, re.IGNORECASE)
    files = walk_md_files()
    total = 0
    for path in files:
        for i, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if rx.search(raw):
                print(f"{rel(path)}:{i}: {raw.strip()}")
                total += 1
    print(f"\n[{total} hits across {len(files)} files]")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--search":
        cli_search(sys.argv[2])
        return

    files = walk_md_files()
    hits = find_topic_hits(files)
    text = render(files, hits, today=str(date.today()))
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {rel(OUT)} — {len(files)} files, "
          f"{sum(len(v) for v in hits.values())} topic hits.")


if __name__ == "__main__":
    main()

"""
Compare the KiCad BOM demand (analog + ss_pa + lpf + protoshield) against
the Mouser cart export and emit a cart-diff spreadsheet.

Outputs tools/_cart_diff.xlsx with three tabs:
  - Add               : BOM demand not covered (or short) by the cart.
                        Resistors with 1/4W bodies are rounded UP to the
                        next multiple of 10 for the Mouser price break.
  - Remove_Overstock  : cart lines with no BOM demand or with excess qty.
  - Matched           : all pairs we were able to pair up (sanity check).

Matching strategy:
  - Resistors  : normalize both sides to ohms ("6K8" → 6800, "0.22R" → 0.22).
  - Capacitors : normalize both sides to picofarads
                 ("0.1uF" ↔ "100nF", "0.22uF" ↔ "220nF").
  - Semis / ICs / relays : fuzzy MPN match (strip common suffix noise
                 like "/NOPB", "E/P", "-E/P", "EE4", "NE4", etc.).
  - Connectors / toroids / breakouts : no auto-match - left for user review.

Reads BOM demand straight from the live netlists via gen_board_boms,
so the diff always reflects whatever the schematics currently say.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_board_boms import (
    BOARDS,
    parse_netlist,
    collect_dnp_refs,
    ref_to_sheet,
)


CART_XLS = Path(r"C:\Users\AlAnd\Downloads\Cart_Nov03_0411PM.xls")
OUT      = Path(__file__).resolve().parent / "_cart_diff.xlsx"


# ── Value normalization ────────────────────────────────────────────────────

_R_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*([RrKkMm])?\s*(.*)$"
)
_R_RE_BURIED = re.compile(
    r"(\d+)([RrKkMm])(\d+)"   # "6K8" → 6.8 kΩ, "0R22" → 0.22 Ω
)


def norm_ohms(s: str):
    """Return (ohms_float, extras_lowercase) or (None, '')."""
    if not s:
        return None, ""
    s0 = str(s).strip()
    # "0.22R 2W", "750R 1W", "15R 5W" style: split off trailing wattage/notes
    extras = ""
    m_tail = re.search(r"\s+([^A-Za-z0-9].*|\d+\s*W.*)$", s0)
    # Just capture the chunk after the first space, that's good enough
    parts = s0.split(None, 1)
    head = parts[0]
    extras = parts[1].lower() if len(parts) > 1 else ""

    # 6K8 / 0R22 / 1R5 (buried-dot notation)
    m = _R_RE_BURIED.fullmatch(head.replace(",", ""))
    if m:
        whole, mult, frac = m.group(1), m.group(2), m.group(3)
        val = float(f"{whole}.{frac}")
    else:
        m = _R_RE.match(head)
        if not m:
            return None, extras
        val = float(m.group(1))
        mult = m.group(2) or ""
    mult = (mult or "").lower()
    if mult == "r" or mult == "":
        ohms = val
    elif mult == "k":
        ohms = val * 1e3
    elif mult == "m":
        ohms = val * 1e6
    else:
        return None, extras
    return ohms, extras


_C_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(p|n|u|µ|m)?\s*[fF]?\s*$",
    re.IGNORECASE,
)


def norm_farads(s: str):
    """Return capacitance in picofarads (float) or None."""
    if not s:
        return None
    s0 = str(s).strip()
    # First token only — some BOM entries have trailing voltage, etc.
    head = s0.split()[0]
    m = _C_RE.match(head)
    if not m:
        return None
    val = float(m.group(1))
    mult = (m.group(2) or "").lower()
    if mult in ("", "p"):
        return val
    if mult == "n":
        return val * 1e3
    if mult in ("u", "µ"):
        return val * 1e6
    if mult == "m":
        return val * 1e9
    return None


# Pull a capacitance from a free-form Mouser description.
def cap_from_desc(desc: str):
    """Scan a Mouser description string for the first cap value we recognise."""
    if not desc:
        return None
    # Patterns like "0.33uF", "100 F" (missing u due to Mouser bug), "0.01uF",
    # "100V 0.01uF X7R", "250V 2pF C0G", "50V 220nF"
    pats = [
        r"(\d+\.?\d*)\s*(?:u|µ|U)F?\b",
        r"(\d+\.?\d*)\s*nF\b",
        r"(\d+\.?\d*)\s*pF\b",
    ]
    for pat, mult_name in zip(pats, ("u", "n", "p")):
        for m in re.finditer(pat, desc):
            try:
                v = float(m.group(1))
            except Exception:
                continue
            if mult_name == "u":
                return v * 1e6
            if mult_name == "n":
                return v * 1e3
            if mult_name == "p":
                return v
    # Also catch patterns like "100 F 50V" (Mouser web export sometimes drops
    # the µ character — treat bare F values alongside electrolytic voltage as µF)
    m = re.search(r"(\d+)\s+F\s+(\d+V)", desc)
    if m:
        return float(m.group(1)) * 1e6
    return None


def ohms_from_desc(desc: str):
    """Scan a Mouser description for the first resistor value we recognise."""
    if not desc:
        return None
    # "6.8K OHM 1/4W", "50 OHM", "0.22 OHM"
    m = re.search(r"(\d+\.?\d*)\s*K\s*OHM", desc, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 1e3
    m = re.search(r"(\d+\.?\d*)\s*OHM", desc, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"\b(\d+\.?\d*)\s*ohm\b", desc, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def ohms_from_mfr(mfr: str):
    """Fallback: parse the trailing resistor value from a Mfr PN.
    Handles YAGEO/Vishay style suffixes like
    MFR-25FBF52-6K8 (= 6.8 k), MFR-25FTE52-50R (= 50 R),
    MFR-25FTE52-240R, MFR-25FTE52-3K9, RSF200JT-73-0R22, SQPW515RJ.
    """
    if not mfr:
        return None
    # Buried-dot form: 6K8, 0R22, 3K9, 1R5, 15R, 0R47 — ignore trailing "LF"/"J" etc
    m = re.search(r"[-_]?(\d+)([RrKkMm])(\d+)\b", mfr)
    if m:
        whole, mult, frac = m.groups()
        val = float(f"{whole}.{frac}")
        if mult.lower() == "r": return val
        if mult.lower() == "k": return val * 1e3
        if mult.lower() == "m": return val * 1e6
    # Pure "-50R" / "-240R" / "-10K" with no fractional notation
    m = re.search(r"[-_](\d+(?:\.\d+)?)([RrKkMm])(?:LF|RLF|J|F|K)?$", mfr)
    if m:
        val, mult = float(m.group(1)), m.group(2).lower()
        if mult == "r": return val
        if mult == "k": return val * 1e3
        if mult == "m": return val * 1e6
    # Inline SQPW515RJ: "515" with "R" wedged mid-string. Specific to this product; skip.
    return None


# ── Semi / IC MPN matching ─────────────────────────────────────────────────

_MPN_STRIP = [
    r"/NOPB$",      # TI suffix
    r"-E/P$", r"E/P$", r"-EP$",       # Microchip
    r"EE4$", r"NE4$", r"CPE4$",       # TI logistics
    r"-E/TO$", r"E/TO$",              # Microchip TO-92
    r"[-]?[DN]G5TA?$",                # Kemet packaging suffixes
    r"J5R7210$", r"5R7210$",          # Kemet 0805 suffixes
]


def norm_mpn(mpn: str) -> str:
    """Normalize a manufacturer PN for approximate match."""
    if not mpn:
        return ""
    s = mpn.upper().replace(" ", "")
    for pat in _MPN_STRIP:
        s = re.sub(pat, "", s)
    return s


# ── Component kind inference from BOM row ──────────────────────────────────

@dataclass
class Demand:
    kind: str                      # R, C, L, D, Q, U, J, K, RV, TP, Other
    board_refs: list = field(default_factory=list)
    value: str = ""                # raw BOM value
    footprint: str = ""
    desc: str = ""
    ohms: float | None = None      # parsed if R
    farads_pf: float | None = None # parsed if C
    extras: str = ""               # trailing text like "1W", "5W"

    @property
    def qty(self):
        return len(self.board_refs)


def kind_of(ref: str) -> str:
    if ref.startswith("TP"): return "TP"
    if ref.startswith("RP") or ref.startswith("RT"): return "R"
    if ref.startswith("RV"): return "RV"
    if ref.startswith("R"):  return "R"
    if ref.startswith("CF") or ref.startswith("CP") or ref.startswith("C"): return "C"
    if ref.startswith("LED"): return "D"
    if ref.startswith("L"):  return "L"
    if ref.startswith("D"):  return "D"
    if ref.startswith("Q"):  return "Q"
    if ref.startswith("K"):  return "K"
    if ref.startswith("U"):  return "U"
    if ref.startswith("T"):  return "T"
    if ref.startswith("J"):  return "J"
    if ref.startswith("SW"): return "SW"
    if ref.startswith("F"):  return "F"
    return "X"


def load_bom():
    """Return list[Demand], grouped by (kind, normalized key)."""
    all_items = []
    for board, netfile in BOARDS:
        if not Path(netfile).exists():
            continue
        comps = parse_netlist(netfile)
        dnp = collect_dnp_refs(board)
        sheet_map = ref_to_sheet(board)
        for c in comps:
            if c["ref"] in dnp or c["ref"].startswith("#"):
                continue
            all_items.append({
                "board": board,
                "ref": c["ref"],
                "value": c["value"],
                "footprint": c["footprint"],
                "description": c["description"],
                "sheet": sheet_map.get(c["ref"], "?"),
            })

    # Group by (kind, canonical key)
    groups: dict[tuple, Demand] = {}
    for it in all_items:
        kind = kind_of(it["ref"])
        value = it["value"] or ""
        key_extra = ""
        ohms = farads_pf = None
        if kind == "R":
            ohms, extras = norm_ohms(value)
            key = ("R", round(ohms, 6) if ohms is not None else None, extras)
            key_extra = extras
        elif kind == "C":
            farads_pf = norm_farads(value)
            # Group by capacitance + footprint (0805 SMD vs leaded disc vs CP)
            fp_bucket = ""
            fp = (it["footprint"] or "").lower()
            if "0805" in fp:
                fp_bucket = "0805"
            elif "0603" in fp:
                fp_bucket = "0603"
            elif "cp_radial" in fp or "cp " in fp or fp.endswith("cp"):
                fp_bucket = "elec"
            elif "aximax" in fp:
                fp_bucket = "aximax"
            else:
                fp_bucket = "leaded"
            key = ("C", round(farads_pf, 3) if farads_pf is not None else value, fp_bucket)
        elif kind == "RV":
            ohms, extras = norm_ohms(value)
            key = ("RV", round(ohms, 6) if ohms is not None else value)
        elif kind == "L":
            key = ("L", value, it["footprint"])
        elif kind == "D":
            key = ("D", value)
        elif kind == "Q":
            key = ("Q", value)
        elif kind == "U":
            key = ("U", norm_mpn(value))
        elif kind == "K":
            key = ("K", value)
        elif kind == "T":
            key = ("T", value)
        elif kind == "J":
            key = ("J", value, it["footprint"])
        elif kind == "SW":
            key = ("SW", value)
        else:
            key = (kind, value, it["footprint"])

        if key not in groups:
            d = Demand(kind=kind, value=value, footprint=it["footprint"],
                       desc=it["description"], ohms=ohms, farads_pf=farads_pf,
                       extras=key_extra)
            groups[key] = d
        else:
            d = groups[key]
            # Keep the first-seen value / footprint text (used for display)
            if not d.value:
                d.value = value
        groups[key].board_refs.append((it["board"], it["ref"]))
    return groups


# ── Cart loader ────────────────────────────────────────────────────────────

@dataclass
class CartLine:
    line: int
    mouser: str
    mfr: str
    manufacturer: str
    desc: str
    qty: int
    # Inferred
    ohms: float | None = None
    extras: str = ""   # "1W" etc.
    farads_pf: float | None = None
    mpn_key: str = ""
    mpn_raw: str = ""     # pre-strip uppercase MPN (for wildcard matching)
    kind_hint: str = ""   # R, C, D, Q, U, K, Other


def load_cart() -> list[CartLine]:
    df = pd.read_excel(CART_XLS, engine="xlrd", header=None)
    lines = []
    for i in range(9, len(df)):
        row = df.iloc[i].values
        ln = row[0]
        if pd.isna(ln):
            continue
        try:
            ln_int = int(ln)
        except Exception:
            continue
        mouser = str(row[1]) if pd.notna(row[1]) else ""
        mfr = str(row[2]) if pd.notna(row[2]) else ""
        manuf = str(row[3]) if pd.notna(row[3]) else ""
        desc = str(row[5]) if pd.notna(row[5]) else ""
        qty_raw = row[8]
        try:
            qty = int(qty_raw)
        except Exception:
            try:
                qty = int(float(qty_raw))
            except Exception:
                qty = 0
        c = CartLine(line=ln_int, mouser=mouser, mfr=mfr,
                     manufacturer=manuf, desc=desc, qty=qty,
                     mpn_raw=(mfr or "").upper().replace(" ", ""))

        desc_lo = desc.lower()
        # Classify kind + extract value
        if "trimmer resistor" in desc_lo:
            # Must come BEFORE the generic 'resistor' branch
            c.kind_hint = "RV"
            c.ohms = ohms_from_desc(desc) or ohms_from_mfr(mfr)
        elif "resistor" in desc_lo or re.search(r"\bohm\b", desc_lo):
            c.kind_hint = "R"
            c.ohms = ohms_from_desc(desc)
            if c.ohms is None:
                c.ohms = ohms_from_mfr(mfr)
            if "1w" in desc_lo:
                c.extras = "1w"
            elif "2w" in desc_lo:
                c.extras = "2w"
            elif "5w" in desc_lo or "sqp5" in mfr.lower():
                c.extras = "5w"
            elif "10w" in desc_lo:
                c.extras = "10w"
            elif "metal oxide" in desc_lo and "0r22" in mfr.lower():
                # YAGEO RSF200JT-73-0R22 is a 2 W metal oxide
                c.extras = "2w"
        elif ("capacitor" in desc_lo and
              any(k in desc_lo for k in ("mlcc", "ceramic", "electrolytic",
                                          "tantalum", "film capacitor",
                                          "multilayer", "aluminum"))):
            # Only treat as a passive capacitor when a cap family keyword is
            # also present; this prevents "Switched-Capacitor Voltage
            # Converter" (LT1054) from being mis-classified.
            c.kind_hint = "C"
            c.farads_pf = cap_from_desc(desc)
        elif "zener" in desc_lo or "schottky" in desc_lo or "rectifier" in desc_lo or "diode" in desc_lo:
            c.kind_hint = "D"
            c.mpn_key = norm_mpn(mfr)
        elif "transistor" in desc_lo or "mosfet" in desc_lo or "bipolar" in desc_lo:
            c.kind_hint = "Q"
            c.mpn_key = norm_mpn(mfr)
        elif "relay" in desc_lo:
            c.kind_hint = "K"
            c.mpn_key = norm_mpn(mfr)
        elif "op amp" in desc_lo or "operational" in desc_lo or "ldo" in desc_lo \
                or "regulator" in desc_lo or "dac" in desc_lo or "logic" in desc_lo \
                or "buffer" in desc_lo or "line driver" in desc_lo \
                or "analog switch" in desc_lo or "voltage converter" in desc_lo:
            c.kind_hint = "U"
            c.mpn_key = norm_mpn(mfr)
        elif "trimmer" in desc_lo:
            c.kind_hint = "C_TRIM"
        elif "polyfuse" in desc_lo or "fuse" in desc_lo:
            c.kind_hint = "F"
            c.mpn_key = norm_mpn(mfr)
        elif "switch" in desc_lo:
            c.kind_hint = "SW"
            c.mpn_key = norm_mpn(mfr)
        elif "connector" in desc_lo or "terminal block" in desc_lo or "jack" in desc_lo:
            c.kind_hint = "J"
            c.mpn_key = norm_mpn(mfr)
        elif "accessor" in desc_lo:
            c.kind_hint = "U"
            c.mpn_key = norm_mpn(mfr)
        else:
            c.kind_hint = "Other"
            c.mpn_key = norm_mpn(mfr)
        lines.append(c)
    return lines


# ── Matcher ────────────────────────────────────────────────────────────────

def mpn_match(a: str, b: str, b_raw: str = "") -> bool:
    """Strict MPN match. a=BOM mpn, b=cart mpn (post-strip),
    b_raw=cart mpn pre-strip (for wildcard matching only).

    Equal → match. Otherwise one must contain the other with ≥6-char overlap
    AND the matching region must start/end at the same side.  Distinguishes
    CD74HC4050 ≠ CD74HC4066 and MCP4921 ≠ MCP4922.

    If BOM MPN contains 'X' placeholder characters (e.g. MCP1700X-330XXTO
    where x stands for 'any character sequence'), treat each X as `.*?`
    and search against the pre-strip raw cart MPN so suffixes like E/TO
    still appear in the target string.
    """
    if not a or not b:
        return False
    if "X" in a:
        pat = re.escape(a).replace(r"X", r".*?")
        target = b_raw if b_raw else b
        if re.search(pat, target):
            return True
    if a == b:
        return True
    if len(a) >= 6 and a in b:
        return b.startswith(a) or b.endswith(a)
    if len(b) >= 6 and b in a:
        return a.startswith(b) or a.endswith(b)
    return False


def match_cart_to_demand(demand_groups, cart_lines):
    """Return (matches, add_rows, remove_rows, overstock_rows).

    matches : list of dicts {demand, cart, qty_used, note} — pairs we recognise.
    add_rows: list of (demand, shortfall_qty, note) — BOM items not yet covered.
    remove: list of CartLine — cart lines with no BOM demand matched to them.
    overstock: list of (CartLine, used_qty) — matched but cart has more than needed.
    """
    matches = []
    cart_remaining = {c.line: c.qty for c in cart_lines}
    cart_by_line = {c.line: c for c in cart_lines}
    demand_items = list(demand_groups.values())
    demand_remaining = {id(d): d.qty for d in demand_items}

    def consume(d, c, note=""):
        want = demand_remaining[id(d)]
        have = cart_remaining[c.line]
        used = min(want, have)
        if used <= 0:
            return 0
        demand_remaining[id(d)] -= used
        cart_remaining[c.line] -= used
        matches.append({
            "demand": d, "cart": c, "qty_used": used, "note": note,
        })
        return used

    # ── Resistors (match on ohms; exclude trimmers) ─────────────────────────
    for d in demand_items:
        if d.kind != "R" or d.ohms is None:
            continue
        for c in cart_lines:
            if demand_remaining[id(d)] <= 0:
                break
            if c.kind_hint != "R" or c.ohms is None:
                continue
            if cart_remaining[c.line] <= 0:
                continue
            if abs(c.ohms - d.ohms) / max(d.ohms, 1e-9) >= 0.01:
                continue
            # Prefer matching wattage; a cart line with mismatched wattage still
            # matches (we flag it) rather than causing both sides to look wrong.
            d_watt = (d.extras or "").strip().lower().replace(" ", "")
            c_watt = (c.extras or "").strip().lower().replace(" ", "")
            note = ""
            if d_watt and d_watt != c_watt:
                note = f"wattage mismatch: BOM {d.extras} vs cart {c.extras or '1/4W'}"
            elif c_watt and not d_watt:
                note = f"cart is {c.extras}, BOM assumed 1/4W"
            consume(d, c, note)

    # ── Capacitors (match on pF; SMD prefers SMD) ───────────────────────────
    for d in demand_items:
        if d.kind != "C" or d.farads_pf is None:
            continue
        if demand_remaining[id(d)] <= 0:
            continue
        fp = (d.footprint or "").lower()
        d_is_smd = ("0805" in fp or "0603" in fp or "smd" in fp)
        # Rank candidate cart lines
        candidates = []
        for c in cart_lines:
            if c.kind_hint != "C" or c.farads_pf is None:
                continue
            if cart_remaining[c.line] <= 0:
                continue
            if abs(c.farads_pf - d.farads_pf) / max(d.farads_pf, 1e-9) >= 0.03:
                continue
            c_desc = c.desc.lower()
            c_is_smd = ("smd" in c_desc or "0805" in c_desc or "0603" in c_desc)
            # SMD-SMD match preferred, else leaded-leaded, else cross
            if d_is_smd == c_is_smd:
                candidates.insert(0, c)
            else:
                candidates.append(c)
        for c in candidates:
            if demand_remaining[id(d)] <= 0:
                break
            consume(d, c)

    # ── Trimmers (RV) ───────────────────────────────────────────────────────
    for d in demand_items:
        if d.kind != "RV" or d.ohms is None:
            continue
        for c in cart_lines:
            if demand_remaining[id(d)] <= 0:
                break
            if c.kind_hint != "RV" or c.ohms is None:
                continue
            if cart_remaining[c.line] <= 0:
                continue
            if abs(c.ohms - d.ohms) / max(d.ohms, 1e-9) < 0.01:
                consume(d, c)

    # ── MPN match (semis, ICs, relays, LDOs) ────────────────────────────────
    for d in demand_items:
        if d.kind not in ("U", "D", "Q", "K", "F", "SW"):
            continue
        d_key = norm_mpn(d.value)
        if not d_key:
            continue
        for c in cart_lines:
            if demand_remaining[id(d)] <= 0:
                break
            if not c.mpn_key:
                continue
            if cart_remaining[c.line] <= 0:
                continue
            if mpn_match(d_key, c.mpn_key, c.mpn_raw):
                consume(d, c)

    # ── Footprint-token fallback ────────────────────────────────────────────
    # Some BOM values are generic descriptors (SW_Slide_DPDT, Polyfuse,
    # LevelShifter_BSS138_x4, Fuse_3A_SlowBlow, Conn_Coaxial_Small) with the
    # real MPN baked into the footprint string instead.  Match those by
    # looking for the full canonicalized cart Mfr# inside the canonicalized
    # BOM footprint.  Canonicalize both sides to alnum-only uppercase so
    # hyphens, slashes, spaces are irrelevant.  Require the Mfr# chunk to
    # be ≥4 chars AND contain a digit — short tokens like "757" would false-
    # match too easily (e.g. ingesting into an unrelated footprint).
    def canon(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())
    for d in demand_items:
        if d.kind not in ("U", "D", "Q", "K", "F", "SW", "J"):
            continue
        if demand_remaining[id(d)] <= 0:
            continue
        fp_canon = canon(d.footprint)
        if not fp_canon:
            continue
        # No guard on d.value here: strict MPN match already ran first for
        # every kind in this list, so demand that reaches this fallback is
        # genuinely unresolved regardless of whether its value text had
        # digits in it ("Fuse_3A_SlowBlow", "LM2940CT-5.0", etc.).
        for c in cart_lines:
            if demand_remaining[id(d)] <= 0:
                break
            if cart_remaining[c.line] <= 0:
                continue
            mfr_canon = canon(c.mfr)
            if len(mfr_canon) < 3 or not re.search(r"\d", mfr_canon):
                continue
            manuf_canon = canon(c.manufacturer)
            manuf_in_fp = bool(manuf_canon) and manuf_canon in fp_canon

            # Path 1: full canonical Mfr# is embedded in the BOM footprint.
            # Short (3-char) MPNs need manufacturer corroboration to avoid
            # "757"-style false positives in unrelated footprints.
            if mfr_canon in fp_canon:
                if len(mfr_canon) < 4 and not manuf_in_fp:
                    continue
                consume(d, c, note=f"matched via footprint hint ({c.mfr})")
                continue

            # Path 2: manufacturer is baked into the BOM footprint (e.g.
            # xmitter:Fuse_Littelfuse_60R_*, xmitter:Adafruit_*_Breakout,
            # xmitter:SMA_Cinch_*) and a leading-prefix of the cart Mfr#
            # appears in the footprint.  This catches "60R050XU" against
            # a footprint whose author only named the family (60R), and
            # won't fire on unrelated footprints because they don't carry
            # the manufacturer name.
            if manuf_in_fp:
                for plen in range(len(mfr_canon) - 1, 2, -1):
                    prefix = mfr_canon[:plen]
                    if not re.search(r"\d", prefix):
                        continue
                    if prefix in fp_canon:
                        consume(d, c, note=f"matched via footprint hint "
                                            f"({c.mfr} family prefix {prefix})")
                        break

    # ── Build output lists ─────────────────────────────────────────────────
    add_rows = []
    for d in demand_items:
        short = demand_remaining[id(d)]
        if short <= 0:
            continue
        if d.kind == "TP":
            continue
        note = ""
        if short < d.qty:
            note = f"PARTIAL — cart has {d.qty - short}, {short} still needed"
        add_rows.append((d, short, note))

    remove_rows = []
    overstock_rows = []
    for ln, left in cart_remaining.items():
        c = cart_by_line[ln]
        if left == c.qty:
            remove_rows.append(c)
        elif left > 0:
            overstock_rows.append((c, c.qty - left))

    return matches, add_rows, remove_rows, overstock_rows


# ── Qty rounding for 1/4W resistor price break ─────────────────────────────

def round_up_10(n: int) -> int:
    return ((n + 9) // 10) * 10


def is_quarter_watt_resistor(d: Demand) -> bool:
    if d.kind != "R":
        return False
    fp = (d.footprint or "").lower()
    if "din0207" in fp:
        return True
    # BOM extras explicitly flag higher wattage; if none set and it's a R, assume 1/4W
    if d.extras:
        return False
    return True


# ── Spreadsheet writer ─────────────────────────────────────────────────────

HEADER_FILL = PatternFill("solid", fgColor="DDDDDD")
RED_FILL    = PatternFill("solid", fgColor="FFE4E1")
GREEN_FILL  = PatternFill("solid", fgColor="E6F4EA")
YELLOW_FILL = PatternFill("solid", fgColor="FFF8DC")


def refs_display(d: Demand) -> str:
    by_board = defaultdict(list)
    for b, r in d.board_refs:
        by_board[b].append(r)
    parts = []
    for b in sorted(by_board):
        rs = sorted(by_board[b], key=lambda r: (r[:2], int(re.search(r"(\d+)", r).group(1)) if re.search(r"(\d+)", r) else 0))
        parts.append(f"{b}:{','.join(rs)}")
    return "  |  ".join(parts)


def write_diff(matches, add_rows, remove_rows, overstock_rows):
    wb = Workbook()
    wb.remove(wb.active)

    kind_order = {"R":0,"RV":1,"C":2,"L":3,"D":5,"Q":6,"K":7,"U":8,
                  "F":9,"SW":10,"J":11,"T":12,"TP":99,"X":100}

    # ── Add tab ──
    ws = wb.create_sheet("Add")
    headers = ["Kind", "Value / MPN", "BOM qty short", "Order qty (10× for 1/4 W)",
               "Footprint", "Boards : Refs", "Notes"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True); cell.fill = HEADER_FILL
    for d, short, note in sorted(add_rows, key=lambda t: (kind_order.get(t[0].kind, 50), t[0].value or "")):
        order_qty = round_up_10(short) if is_quarter_watt_resistor(d) else short
        extras_note = ""
        if d.kind == "R" and d.extras:
            extras_note = f"wattage: {d.extras}"
        combined = "  |  ".join(filter(None, [note, extras_note]))
        row = [d.kind, d.value, short, order_qty, d.footprint, refs_display(d), combined]
        ws.append(row)
        ws.cell(row=ws.max_row, column=1).fill = RED_FILL

    # Build a footprint-hint index so cart Mfr#s that appear embedded in a
    # BOM footprint string get flagged as a "may match this BOM item".
    fp_hint_map = []
    for d, _, _ in add_rows:
        fp = (d.footprint or "")
        if fp:
            fp_hint_map.append((fp, d))

    def fp_hint_for(cart_mfr: str) -> str:
        """Return a 'may match' hint if any digit-bearing alphanumeric chunk
        of cart_mfr (length ≥ 3) appears literally in an un-matched BOM
        footprint string."""
        mfr_up = (cart_mfr or "").upper()
        tokens = [t for t in re.findall(r"[A-Z0-9]{3,}", mfr_up) if re.search(r"\d", t)]
        for fp, d in fp_hint_map:
            fp_up = fp.upper()
            for tok in tokens:
                if tok in fp_up:
                    return f"BOM {d.value} ({fp})"
        return ""

    # ── Remove / Overstock tab ──
    ws = wb.create_sheet("Remove_Overstock")
    # Column A is reserved for the user to mark progress ("x", "done", etc.)
    # — leave it blank here so reruns don't trample those marks.  The
    # packager (package_bom_deliverables.py) migrates values from the prior
    # Documentation file into this column keyed by cart line number.
    headers = ["Done", "Line", "Mouser #", "Mfr #", "Manufacturer",
               "Description", "Cart qty", "BOM need", "Action", "Reason"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True); cell.fill = HEADER_FILL
    # Single pass, primary sort: cart line number descending.  Mouser
    # renumbers lines after each delete, so operating top-down from the
    # highest line keeps the lower line numbers stable while the user
    # works through deletions.  REMOVE and REDUCE rows are interleaved
    # so the user walks the cart in one consistent top-down order.
    combined = [("REMOVE", c, 0) for c in remove_rows] + \
               [("REDUCE", c, used) for c, used in overstock_rows]
    combined.sort(key=lambda t: t[1].line, reverse=True)
    for action, c, used in combined:
        if action == "REMOVE":
            hint = fp_hint_for(c.mfr)
            reason = "No matching BOM demand"
            if hint:
                reason += f"  (may match: {hint} — verify before removing)"
            ws.append(["", c.line, c.mouser, c.mfr, c.manufacturer, c.desc,
                       c.qty, 0, "REMOVE", reason])
            ws.cell(row=ws.max_row, column=9).fill = (
                YELLOW_FILL if hint else RED_FILL)
        else:  # REDUCE
            excess = c.qty - used
            ws.append(["", c.line, c.mouser, c.mfr, c.manufacturer, c.desc,
                       c.qty, used, f"REDUCE by {excess}",
                       f"Only {used} needed by BOM, {excess} overstock"])
            ws.cell(row=ws.max_row, column=9).fill = YELLOW_FILL

    # ── Matched (sanity) tab ──
    ws = wb.create_sheet("Matched")
    headers = ["Kind", "BOM value", "BOM qty total", "Qty used from cart",
               "Cart line", "Cart Mouser #", "Cart Mfr #", "Cart qty",
               "Cart desc", "Note"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True); cell.fill = HEADER_FILL
    for m in sorted(matches, key=lambda m: (kind_order.get(m["demand"].kind, 50), m["demand"].value or "")):
        d = m["demand"]; c = m["cart"]
        ws.append([d.kind, d.value, d.qty, m["qty_used"], c.line, c.mouser,
                   c.mfr, c.qty, c.desc, m["note"]])
        if m["note"]:
            ws.cell(row=ws.max_row, column=10).fill = YELLOW_FILL

    widths = {
        "Add":              [6, 22, 14, 18, 50, 50, 50],
        "Remove_Overstock": [6, 6, 22, 24, 20, 60, 8, 8, 16, 40],
        "Matched":          [6, 22, 14, 14, 6, 22, 22, 8, 60, 40],
    }
    for sn, ws_widths in widths.items():
        ws = wb[sn]
        for col, w in enumerate(ws_widths, start=1):
            ws.column_dimensions[chr(ord("A") + col - 1)].width = w

    wb.save(OUT)
    return OUT


def main():
    print("Loading BOM demand...")
    demand_groups = load_bom()
    print(f"  {len(demand_groups)} grouped demand entries")

    print("Loading Mouser cart...")
    cart = load_cart()
    print(f"  {len(cart)} cart lines")

    print("Matching...")
    matches, add_rows, remove_rows, overstock_rows = \
        match_cart_to_demand(demand_groups, cart)
    print(f"  matched demand pairings : {len(matches)}")
    print(f"  add rows (short/missing): {len(add_rows)}")
    print(f"  cart lines to remove    : {len(remove_rows)}")
    print(f"  cart lines overstock    : {len(overstock_rows)}")

    out = write_diff(matches, add_rows, remove_rows, overstock_rows)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

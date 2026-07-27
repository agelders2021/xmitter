"""One-at-a-time sensitivity study for a filter netlist (Method B, AC sweep).

Perturbs each named .param by +/- <tolerance>, runs ngspice on each variant
in parallel, extracts insertion loss |H(f)| at target frequencies by log-f
interpolation on the AC sweep, and prints a table of delta-IL vs the
unperturbed baseline.

Default targets are the VFO LPF: it perturbs CF1/CF3/CF5/CF7/LF2/LF4/LF6 and
reports at 14.2 / 42.6 / 71 / 99.4 MHz (fundamental + odd harmonics of a
14.2 MHz Si5351 square wave). Suits xmitter_prj/vfo_lpf_ac.cir out of the
box.

Usage:
    python tools\\lpf_sensitivity.py xmitter_prj\\vfo_lpf_ac.cir
    python tools\\lpf_sensitivity.py xmitter_prj\\vfo_lpf_ac.cir --tolerance 0.10
    python tools\\lpf_sensitivity.py xmitter_prj\\vfo_lpf_ac.cir \\
        --params CF1,CF3,LF2 --freqs 14.2Meg,42.6Meg
"""

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_ngspice  # noqa: E402

NGSPICE = r"D:\Program Files\Qucs-S\bin\ngspice_con.exe"

DEFAULT_PARAMS = ("CF1", "CF3", "CF5", "CF7", "LF2", "LF4", "LF6")
DEFAULT_FREQS = "14.2Meg,42.6Meg,71Meg,99.4Meg"
DEFAULT_VIN = "v(in)"
DEFAULT_VOUT = "v(n4)"

_SPICE_MULT = {
    "t": 1e12, "g": 1e9, "k": 1e3,
    "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15,
}


def spice_to_float(s):
    """Parse '220p', '4.8uH', '1MEG', '2.31e-10', '17.5Meg' -> float."""
    s = s.strip().lower()
    m = re.fullmatch(r"([\d.eE+\-]+)([a-z]*)", s)
    if not m:
        raise ValueError(f"can't parse SPICE numeric: {s!r}")
    num = float(m.group(1))
    suffix = m.group(2)
    # Strip trailing dimension letter (H, F, etc.) after multiplier suffix.
    suffix = re.sub(r"(h|f|hz|ohm|v|a)$", "", suffix)
    if suffix.startswith("meg"):
        return num * 1e6
    if suffix and suffix[0] in _SPICE_MULT:
        return num * _SPICE_MULT[suffix[0]]
    return num


def _param_regex(name):
    return re.compile(
        rf"^(\s*\.param\s+{re.escape(name)}\s*=\s*)([\d.eE+\-]+[a-zA-Z]*)"
        rf"(\s*(?:[\*\$;].*)?)$",
        re.MULTILINE | re.IGNORECASE,
    )


def read_nominal(text, name):
    m = _param_regex(name).search(text)
    if not m:
        raise ValueError(f".param {name} not found in netlist")
    return spice_to_float(m.group(2))


def substitute_param(text, name, new_value):
    """Replace the numeric value on the .param <name> = ... line."""
    new_str = f"{new_value:.6g}"
    return _param_regex(name).subn(
        lambda m: m.group(1) + new_str + m.group(3),
        text, count=1,
    )


def _interp_log_x(x_axis, y_axis, x_target):
    """Linear interpolation in log10(x), linear y. x_axis assumed increasing."""
    if x_target <= x_axis[0]:
        return y_axis[0]
    if x_target >= x_axis[-1]:
        return y_axis[-1]
    lo, hi = 0, len(x_axis) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if x_axis[mid] <= x_target:
            lo = mid
        else:
            hi = mid
    lx0 = math.log10(x_axis[lo])
    lx1 = math.log10(x_axis[hi])
    lxt = math.log10(x_target)
    frac = (lxt - lx0) / (lx1 - lx0)
    return y_axis[lo] + frac * (y_axis[hi] - y_axis[lo])


def _extract_ac(plots, vin_name, vout_name):
    """From parsed plots, return (freq_axis, |V(vin)|, |V(vout)|) for the AC plot."""
    vin_lc, vout_lc = vin_name.lower(), vout_name.lower()
    for plot in plots:
        first = plot["vars"][0]["name"].lower()
        if first != "frequency":
            continue
        names = [v["name"].lower() for v in plot["vars"]]
        if vin_lc not in names or vout_lc not in names:
            continue
        freqs = [v.real for v in plot["data"][0]]
        vin_c = plot["data"][names.index(vin_lc)]
        vout_c = plot["data"][names.index(vout_lc)]
        return freqs, [abs(c) for c in vin_c], [abs(c) for c in vout_c]
    return None, None, None


def run_case(args):
    (case_id, netlist_text, work_dir_str,
     freqs_hz, vin_name, vout_name) = args
    work_dir = Path(work_dir_str)

    netlist_path = work_dir / "netlist.cir"
    netlist_path.write_text(netlist_text)

    for f in work_dir.glob("spice4qucs.*.plot"):
        f.unlink()

    try:
        result = subprocess.run(
            [NGSPICE, "-b", netlist_path.name],
            cwd=str(work_dir), capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return (case_id, None, "timeout")

    if result.returncode != 0:
        err = (result.stderr or "").strip().splitlines()
        tail = err[-1] if err else "(no stderr)"
        return (case_id, None, f"ngspice exit {result.returncode}: {tail[:80]}")

    rawfiles = sorted(work_dir.glob("spice4qucs.*.plot"))
    if not rawfiles:
        return (case_id, None, "no rawfile")

    plots = []
    for rf in rawfiles:
        plots.extend(run_ngspice.parse_rawfile(rf))

    freqs, mag_in, mag_out = _extract_ac(plots, vin_name, vout_name)
    if freqs is None:
        return (case_id, None,
                f"AC plot with {vin_name} and {vout_name} not found")

    # Insertion loss (dB); +6.02 dB de-embeds the 50/50 source-load divider.
    il_db = []
    for vi, vo in zip(mag_in, mag_out):
        if vi > 0 and vo > 0:
            il_db.append(20.0 * math.log10(vo / vi) + 6.02)
        else:
            il_db.append(-999.0)

    return (case_id,
            {f_hz: _interp_log_x(freqs, il_db, f_hz) for f_hz in freqs_hz},
            "OK")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("netlist",
                    help="Base .cir with .param LF*/CF* lines (see vfo_lpf_ac.cir)")
    ap.add_argument("--params", default=",".join(DEFAULT_PARAMS),
                    help="Comma-separated .param names to perturb")
    ap.add_argument("--freqs", default=DEFAULT_FREQS,
                    help="Comma-separated eval frequencies (e.g. '14.2Meg,42.6Meg')")
    ap.add_argument("--tolerance", type=float, default=0.05,
                    help="Fractional perturbation, e.g. 0.05 for +/-5%%")
    ap.add_argument("--shifts",
                    help="Comma-separated fractional shifts, e.g. "
                         "'-0.20,-0.10,0,0.10,0.20'. If provided, ALL --params "
                         "are shifted TOGETHER by each value (correlated-shift "
                         "mode, matches same-batch hand-wound inductors). "
                         "Overrides --tolerance.")
    ap.add_argument("--vin", default=DEFAULT_VIN,
                    help=f"Input node probe (default {DEFAULT_VIN})")
    ap.add_argument("--vout", default=DEFAULT_VOUT,
                    help=f"Output node probe (default {DEFAULT_VOUT})")
    ap.add_argument("--workers", type=int,
                    help="Worker processes (default: cpu_count - 1)")
    ap.add_argument("--sweep-dir", default="lpf_sensitivity",
                    help="Subdirectory for per-case runs (wiped and recreated)")
    args = ap.parse_args()

    netlist = Path(args.netlist).resolve()
    if not netlist.exists():
        sys.exit(f"Not found: {netlist}")
    if not Path(NGSPICE).exists():
        sys.exit(f"ngspice not found at {NGSPICE}")

    base_text = netlist.read_text()
    params = [p.strip() for p in args.params.split(",") if p.strip()]
    freqs_hz = [spice_to_float(f) for f in args.freqs.split(",") if f.strip()]
    nominals = {p: read_nominal(base_text, p) for p in params}
    tol = args.tolerance

    sweep_dir = netlist.parent / args.sweep_dir
    if sweep_dir.exists():
        shutil.rmtree(sweep_dir)
    sweep_dir.mkdir()

    correlated = args.shifts is not None
    if correlated:
        shifts = [float(s.strip()) for s in args.shifts.split(",") if s.strip()]

    # Assemble jobs
    cases = []
    wd0 = sweep_dir / "baseline"
    wd0.mkdir()
    cases.append(("baseline", base_text, str(wd0),
                  tuple(freqs_hz), args.vin, args.vout))

    if correlated:
        # Shift ALL params together by each entry in --shifts.
        for shift in shifts:
            new_text = base_text
            for p in params:
                new_text, n = substitute_param(new_text, p,
                                               nominals[p] * (1 + shift))
                if n == 0:
                    sys.exit(f"failed to substitute .param {p}")
            cid = f"{shift*100:+.1f}%".replace(".0%", "%")
            wd_name = re.sub(r"[^\w.+-]", "_", cid)
            wd = sweep_dir / wd_name
            wd.mkdir()
            cases.append((cid, new_text, str(wd),
                          tuple(freqs_hz), args.vin, args.vout))
    else:
        # One-at-a-time: each param separately at +/-tol.
        for p in params:
            for sign, mult in (("+", 1 + tol), ("-", 1 - tol)):
                new_text, n = substitute_param(base_text, p, nominals[p] * mult)
                if n == 0:
                    sys.exit(f"failed to substitute .param {p}")
                cid = f"{p}{sign}"
                wd = sweep_dir / cid
                wd.mkdir()
                cases.append((cid, new_text, str(wd),
                              tuple(freqs_hz), args.vin, args.vout))

    n_workers = args.workers or max(1, (os.cpu_count() or 4) - 1)
    n_workers = min(n_workers, len(cases))

    print(f"Base netlist : {netlist}")
    print(f"Params       : {params}")
    print(f"Nominals     : " + ", ".join(f"{p}={nominals[p]:.4g}" for p in params))
    if correlated:
        print(f"Mode         : CORRELATED shift (all params move together)")
        print(f"Shifts       : {', '.join(f'{s*100:+g}%' for s in shifts)}")
    else:
        print(f"Mode         : one-at-a-time perturbation")
        print(f"Tolerance    : +/-{tol*100:.1f}%")
    print(f"Frequencies  : " + ", ".join(f"{f/1e6:g} MHz" for f in freqs_hz))
    print(f"Cases        : {len(cases)}")
    print(f"Workers      : {n_workers}\n")

    results = {}
    with ProcessPoolExecutor(max_workers=n_workers) as exe:
        futs = {exe.submit(run_case, c): c[0] for c in cases}
        for fut in as_completed(futs):
            cid = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = (cid, None, f"exception: {e}")
            results[cid] = r
            _, il, status = r
            if il is None:
                print(f"  {cid:12s}  FAIL  ({status})")
            else:
                cells = "  ".join(f"{il[f]:+7.2f}" for f in freqs_hz)
                print(f"  {cid:12s}  {cells}")

    baseline = results.get("baseline", (None, None, None))[1]
    if baseline is None:
        sys.exit("\nBaseline failed; cannot compute deltas.")

    print()
    print("=" * 72)
    print("BASELINE insertion loss / rejection (dB)")
    print("  positive = signal attenuated by that many dB")
    print("=" * 72)
    for f in freqs_hz:
        print(f"  {f/1e6:7.2f} MHz   {baseline[f]:+8.2f} dB")

    print()
    print("=" * 72)
    if correlated:
        print(f"CORRELATED SHIFT: absolute IL (dB) with all {'/'.join(params)}")
        print(f"                  moved together by each shift value")
        print("=" * 72)
        header = "  ".join(f"{f/1e6:>6.1f} MHz" for f in freqs_hz)
        print(f"  {'shift':>7s}    {header}")
        print("  " + "-" * (11 + len(header)))
        row0 = "  ".join(f"{baseline[f]:+8.2f}" for f in freqs_hz)
        print(f"  {'  0%':>7s}    {row0}   (baseline)")
        for shift in shifts:
            if shift == 0:
                continue
            cid = f"{shift*100:+.1f}%".replace(".0%", "%")
            r = results.get(cid)
            if r is None or r[1] is None:
                print(f"  {cid:>7s}    FAIL")
                continue
            row = "  ".join(f"{r[1][f]:+8.2f}" for f in freqs_hz)
            deltas = [r[1][f] - baseline[f] for f in freqs_hz]
            drow = "  ".join(f"({d:+.2f})" for d in deltas)
            print(f"  {cid:>7s}    {row}   {drow}")
    else:
        print(f"ONE-AT-A-TIME SENSITIVITY (delta IL vs baseline, dB)")
        print( "  delta > 0 at 14.2 MHz  = MORE loss on carrier (bad)")
        print( "  delta > 0 at harmonics = MORE rejection      (good)")
        print("=" * 72)
        header = "  ".join(f"{f/1e6:>6.1f} MHz" for f in freqs_hz)
        print(f"  {'part':6s} {'step':6s}  {header}")
        print("  " + "-" * (14 + len(header)))
        for p in params:
            for sign in "+-":
                cid = f"{p}{sign}"
                r = results.get(cid)
                if r is None or r[1] is None:
                    print(f"  {p:6s} {sign+f'{tol*100:.0f}%':6s}  FAIL")
                    continue
                deltas = [r[1][f] - baseline[f] for f in freqs_hz]
                cells = "  ".join(f"{d:+8.2f}" for d in deltas)
                print(f"  {p:6s} {sign+f'{tol*100:.0f}%':6s}  {cells}")

    print(f"\nPer-case rawfiles under: {sweep_dir}")


if __name__ == "__main__":
    main()

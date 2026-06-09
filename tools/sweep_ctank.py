"""Sweep PA_subcircuit's .PARAM C_TANK, run ngspice in parallel, compute P_out into R17.

Edits the .PARAM C_TANK = NNpF line in a base netlist, fans out one ngspice run
per value across N worker processes, parses each run's spice4qucs.tr1.plot,
computes V_rms of Pr1 (the differential load probe) over the last half of the
transient window, and reports P = V_rms^2 / R_load.

Usage:
    python sweep_ctank.py [base_netlist] [R_load_ohms]

Defaults:
    base_netlist  -> ../xmitter_prj/PA_netlist.cir (relative to script dir)
    R_load_ohms   -> 850
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Local import for the rawfile parser
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_ngspice  # noqa: E402

NGSPICE = r"D:\Program Files\Qucs-S\bin\ngspice_con.exe"

# Sweep values (pF). Covers from "much smaller than current 33pF" through
# "much larger than the 42pF theoretical tank-resonance value".
C_TANK_VALUES_PF = [
    8, 10, 12, 15, 18, 20, 22, 24, 27, 30, 33, 36, 39, 42, 45,
    50, 56, 62, 68, 75, 82, 91, 100, 120, 150, 180, 220,
]


def sweep_one(args):
    """Run ngspice for one C_TANK value. Returns (c_pF, P_W, V_rms, status)."""
    c_pF, base_netlist_text, work_dir = args
    work_dir = Path(work_dir)

    # Substitute C_TANK value
    new_text = re.sub(
        r"(\.PARAM\s+C_TANK\s*=\s*)[\d.]+\s*[pPnNuUmM]?[fF]?",
        rf"\g<1>{c_pF}pF",
        base_netlist_text,
    )

    netlist_path = work_dir / "netlist.cir"
    netlist_path.write_text(new_text)

    # Clear any stale rawfiles
    for f in work_dir.glob("spice4qucs.*.plot"):
        f.unlink()

    try:
        result = subprocess.run(
            [NGSPICE, "-b", netlist_path.name],
            cwd=str(work_dir), capture_output=True, text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return (c_pF, None, None, "timeout")

    if result.returncode != 0:
        # Capture last line of stderr for diagnosis
        err = (result.stderr or "").strip().splitlines()
        tail = err[-1] if err else "(no stderr)"
        return (c_pF, None, None, f"exit {result.returncode}: {tail}")

    rawfiles = sorted(work_dir.glob("spice4qucs.*.plot"))
    if not rawfiles:
        return (c_pF, None, None, "no rawfile")

    plots = []
    for rf in rawfiles:
        plots.extend(run_ngspice.parse_rawfile(rf))

    if not plots:
        return (c_pF, None, None, "empty plots")

    # PA_netlist.cir writes only the transient plot; Pr1 is the differential
    # load voltage (EPr1 between _net12 and _net13).
    plot = plots[0]
    var_names_lower = [v["name"].lower() for v in plot["vars"]]
    if "v(pr1)" not in var_names_lower:
        return (c_pF, None, None, f"no v(pr1) in {var_names_lower}")

    pr1_idx = var_names_lower.index("v(pr1)")
    voltages = [v.real for v in plot["data"][pr1_idx]]
    n = len(voltages)
    if n < 100:
        return (c_pF, None, None, f"only {n} pts")

    # Use last half of the transient window for steady-state RMS
    ss = voltages[n // 2:]
    m = len(ss)
    # Subtract DC offset before RMS, in case there's any common-mode bias
    mean = sum(ss) / m
    rms = (sum((v - mean) ** 2 for v in ss) / m) ** 0.5
    P = (rms ** 2) / R_LOAD_GLOBAL
    return (c_pF, P, rms, "OK")


# Global so worker processes inherit it (set in main before pool start)
R_LOAD_GLOBAL = 850.0


def main():
    global R_LOAD_GLOBAL

    base_netlist = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        SCRIPT_DIR.parent / "xmitter_prj" / "PA_netlist.cir"
    )
    R_LOAD_GLOBAL = float(sys.argv[2]) if len(sys.argv) > 2 else 850.0

    base_netlist = base_netlist.resolve()
    if not base_netlist.exists():
        sys.exit(f"Not found: {base_netlist}")

    print(f"Base netlist : {base_netlist}")
    print(f"R_load       : {R_LOAD_GLOBAL} ohm")
    print(f"Sweep values : {C_TANK_VALUES_PF} pF")
    print(f"CPU count    : {os.cpu_count()}")

    base_text = base_netlist.read_text()

    # Confirm the parameter to be substituted is present
    if not re.search(r"\.PARAM\s+C_TANK\s*=", base_text):
        sys.exit("ERROR: .PARAM C_TANK = ... not found in base netlist")

    # Set up sweep directories
    sweep_dir = base_netlist.parent / "ctank_sweep"
    if sweep_dir.exists():
        shutil.rmtree(sweep_dir)
    sweep_dir.mkdir()

    jobs = []
    for c in C_TANK_VALUES_PF:
        wd = sweep_dir / f"c{c}pF"
        wd.mkdir()
        jobs.append((c, base_text, str(wd)))

    n_workers = min(len(jobs), max(1, (os.cpu_count() or 4) - 1))
    print(f"Running {len(jobs)} ngspice jobs across {n_workers} workers...\n")

    results = {}
    with ProcessPoolExecutor(max_workers=n_workers) as exe:
        futures = {exe.submit(sweep_one, j): j[0] for j in jobs}
        for f in as_completed(futures):
            c_pF = futures[f]
            try:
                r = f.result()
            except Exception as e:
                r = (c_pF, None, None, f"exception: {e}")
            results[c_pF] = r
            _, p, v, status = r
            if p is None:
                print(f"  C_TANK = {c_pF:>4g} pF  FAIL  ({status})")
            else:
                print(f"  C_TANK = {c_pF:>4g} pF  V_rms = {v:6.2f} V  "
                      f"P_out = {p:7.2f} W")

    print(f"\n=== Summary: P_out into {R_LOAD_GLOBAL:.0f} ohm vs C_TANK ===")
    print(f"{'C_TANK (pF)':>12}  {'V_rms (V)':>12}  {'P_out (W)':>12}")
    print("-" * 42)
    for c in C_TANK_VALUES_PF:
        if c not in results:
            continue
        _, p, v, status = results[c]
        if p is None:
            print(f"{c:>12g}  {'--':>12}  {'--':>12}   ({status})")
        else:
            print(f"{c:>12g}  {v:>12.2f}  {p:>12.2f}")

    # Identify peak
    valid = [(c, p) for c, (_, p, _, _) in results.items() if p is not None]
    if valid:
        c_best, p_best = max(valid, key=lambda x: x[1])
        print(f"\nPeak P_out at C_TANK = {c_best} pF  ->  {p_best:.2f} W")


if __name__ == "__main__":
    main()

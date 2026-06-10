"""Run ngspice on a .cir and produce a .dat.ngspice you can open in gui_plot.

Usage:
    python ngspice.py grid_bias_check          # adds .cir if missing
    python ngspice.py grid_bias_check.cir
    python ngspice.py                          # defaults to netlist.cir

Workflow:
    1. Runs ngspice_con.exe -b <netlist> in the netlist's directory
       so any relative .INCLUDE paths resolve correctly.
    2. Parses every spice4qucs.*.plot rawfile ngspice wrote.
    3. Combines them into <netlist_stem>.dat.ngspice in QUCS dataset
       format, which gui_plot's "Open .dat.ngspice" reads directly.

Delegates the heavy lifting to tools/run_ngspice.py's parsing routines
(via direct import) -- one copy of the conversion logic, two callers.
"""
import os
import sys
import subprocess
from pathlib import Path

NGSPICE = r"D:\Program Files\Qucs-S\bin\ngspice_con.exe"

# Pull in run_ngspice's parser / writer so we don't duplicate it
THIS = Path(__file__).resolve()
TOOLS = THIS.parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import run_ngspice  # noqa: E402


def resolve_netlist(arg: str) -> Path:
    p = Path(arg)
    if p.exists():
        return p.resolve()
    if not p.suffix:
        p_cir = p.with_suffix(".cir")
        if p_cir.exists():
            return p_cir.resolve()
    raise FileNotFoundError(f"Not found: {arg} (also tried {arg}.cir)")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "netlist.cir"
    try:
        netlist = resolve_netlist(arg)
    except FileNotFoundError as e:
        sys.exit(str(e))

    if not Path(NGSPICE).exists():
        sys.exit(
            f"ngspice_con.exe not found at {NGSPICE}.\n"
            f"Edit NGSPICE at the top of {THIS.name}."
        )

    workdir = netlist.parent
    out_dat = netlist.with_suffix(".dat.ngspice")

    # Clear any stale rawfiles so we don't pick up old plots
    for f in workdir.glob("spice4qucs.*.plot"):
        f.unlink()

    print(f"Running ngspice on {netlist.name} (cwd={workdir})...")
    result = subprocess.run([NGSPICE, "-b", netlist.name], cwd=str(workdir))
    if result.returncode != 0:
        print(f"\nWARNING: ngspice exited with code {result.returncode}")

    # Find what ngspice wrote
    rawfiles = sorted(workdir.glob("spice4qucs.*.plot"))
    if not rawfiles:
        sys.exit(
            "No spice4qucs.*.plot files were produced.\n"
            "Check that your netlist's .control block has "
            "`write spice4qucs.<type>.plot ...` lines, or use the .SW / .DC "
            "components in QUCS-S that auto-generate them."
        )

    # Convert rawfiles → QUCS dataset format
    all_plots = []
    for rf in rawfiles:
        print(f"  parsing {rf.name}")
        all_plots.extend(run_ngspice.parse_rawfile(rf))
    if not all_plots:
        sys.exit("Rawfile parsed empty -- no data to write.")

    run_ngspice.write_qucs_dataset(all_plots, out_dat)
    print(f"\nWrote {out_dat}")
    print(f"  Open this file in gui_plot:  python gui_plot.py  ->  Open .dat.ngspice...")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

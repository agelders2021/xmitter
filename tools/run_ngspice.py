"""Run ngspice on a QUCS-saved netlist, convert results to QUCS .dat.ngspice
format so plot.py can read them.

This bypasses QUCS's transient display, which has been observed to differ from
what ngspice actually computes (see Documentation/lesson_qucs_ngspice_discrepancy.md).

Usage:
    python run_ngspice.py [netlist.cir] [output.dat.ngspice]

Defaults:
    netlist  -> netlist.cir in current directory
    output   -> <netlist_stem>.dat.ngspice in same directory

The netlist must already contain `write spice4qucs.<type>.plot ...` lines in
its .control block (QUCS-generated netlists do).  This script runs ngspice on
the netlist, parses the produced spice4qucs.*.plot rawfiles (which are ASCII
because the QUCS-S ngspice spinit sets filetype=ascii), and rewrites them in
the .dat.ngspice format that QUCS-S and plot.py both understand.
"""

import re
import sys
import subprocess
from pathlib import Path


NGSPICE = r"D:\Program Files\Qucs-S\bin\ngspice_con.exe"


def parse_rawfile(path):
    """Parse an ngspice ASCII rawfile. Returns list of plot dicts."""
    text = Path(path).read_text().splitlines()
    plots = []
    cur = None
    i = 0
    n = len(text)
    while i < n:
        line = text[i].rstrip()
        if line.startswith("Title:"):
            if cur:
                plots.append(cur)
            cur = {"vars": [], "data": []}
        elif line.startswith("Plotname:"):
            cur["plotname"] = line[len("Plotname:"):].strip()
        elif line.startswith("Flags:"):
            cur["flags"] = line[len("Flags:"):].strip()
        elif line.startswith("No. Variables:"):
            cur["nvars"] = int(line.split(":", 1)[1])
        elif line.startswith("No. Points:"):
            cur["npoints"] = int(line.split(":", 1)[1])
        elif line == "Variables:":
            for _ in range(cur["nvars"]):
                i += 1
                parts = text[i].split()
                # "<idx>\t<name>\t<type>"
                cur["vars"].append({"name": parts[1],
                                    "type": parts[2] if len(parts) > 2 else ""})
            cur["data"] = [[] for _ in range(cur["nvars"])]
        elif line == "Values:":
            for _ in range(cur["npoints"]):
                # Skip any blank separator lines from the previous point
                while i + 1 < n and text[i + 1].strip() == "":
                    i += 1
                # Header line: "<idx>\t<indep_value>"
                i += 1
                header = text[i].split()
                cur["data"][0].append(_parse_value(header[1]))
                # Then (nvars - 1) indented value lines
                for v in range(1, cur["nvars"]):
                    i += 1
                    cur["data"][v].append(_parse_value(text[i].strip()))
        i += 1
    if cur:
        plots.append(cur)
    return plots


def _parse_value(s):
    """Parse 'real' or 'real,imag' string -> complex."""
    s = s.strip()
    if "," in s:
        re_s, im_s = s.split(",")
        return complex(float(re_s), float(im_s))
    return complex(float(s), 0.0)


def write_qucs_dataset(plots, out_path):
    """Convert plots to QUCS .dat.ngspice format (compatible with plot.py)."""
    with open(out_path, "w") as f:
        f.write("<Qucs Dataset 26.1.1>\n")
        for plot in plots:
            if not plot.get("data"):
                continue
            is_ac = "complex" in plot.get("flags", "").lower()
            prefix = "ac" if is_ac else "tran"

            indep_var = plot["vars"][0]
            indep_name = indep_var["name"]
            indep_data = plot["data"][0]
            n = len(indep_data)

            f.write(f"<indep {indep_name} {n}>\n")
            for v in indep_data:
                f.write(f"{v.real:.12e}\n")
            f.write("</indep>\n")

            for vi in range(1, len(plot["vars"])):
                var = plot["vars"][vi]
                qname = f"{prefix}.{var['name'].lower()}"
                f.write(f"<dep {qname} {indep_name}>\n")
                for v in plot["data"][vi]:
                    if v.imag != 0:
                        sign = "+" if v.imag >= 0 else "-"
                        f.write(f"{v.real:+.12e}{sign}j{abs(v.imag):.12e}\n")
                    else:
                        f.write(f"{v.real:+.12e}\n")
                f.write("</dep>\n")


def main():
    netlist = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("netlist.cir")
    if not netlist.exists():
        sys.exit(f"Not found: {netlist}")

    out_path = (Path(sys.argv[2]) if len(sys.argv) > 2
                else netlist.with_suffix(".dat.ngspice"))

    workdir = netlist.parent.resolve()

    # Clear any old spice4qucs rawfiles
    for f in workdir.glob("spice4qucs.*.plot"):
        f.unlink()

    print(f"Running ngspice on {netlist} (cwd={workdir})...")
    result = subprocess.run(
        [NGSPICE, "-b", netlist.name],
        cwd=workdir, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"WARNING: ngspice exit code {result.returncode}")
    # Always show last bit of stderr in case of warnings/errors
    err_tail = (result.stderr or "").strip().splitlines()[-10:]
    if err_tail:
        print("ngspice stderr (last lines):")
        for line in err_tail:
            print("  " + line)

    rawfiles = sorted(workdir.glob("spice4qucs.*.plot"))
    if not rawfiles:
        sys.exit("No spice4qucs.*.plot files were produced. "
                 "Check that the netlist's .control block contains `write` lines.")

    all_plots = []
    for rf in rawfiles:
        print(f"  parsing {rf.name}")
        all_plots.extend(parse_rawfile(rf))

    write_qucs_dataset(all_plots, out_path)
    print(f"Wrote {out_path}")
    print(f"Plots in output: {len(all_plots)}")
    for p in all_plots:
        nv = len(p['vars']) - 1
        np_ = len(p['data'][0]) if p['data'] else 0
        print(f"  - {p.get('plotname', '?'):20s}  "
              f"{nv} dep vars, {np_} points")


if __name__ == "__main__":
    main()

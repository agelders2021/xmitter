"""Paired (GRID bias, V6 drive) sweep for PA dissipation/output analysis.

For each (bias, V6) pair on the command-line list, substitutes BOTH values in
the base netlist, runs ngspice in parallel, captures three metrics
(V_rms across R17, mean i(VPr3), peak |i(VPr3)|), and prints a combined
power/dissipation table.

The pairs are designed so each operating point sits exactly at the −150 V
grid voltage spec: V6 = 2 × (150 − |bias|).
"""

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

# (bias_magnitude_V, V6_amplitude_V) — each pair sets the negative grid peak
# to exactly −150 V (the spec limit) at the bias point.
PAIRS = [
    (75, 150),
    (70, 160),
    (65, 170),
    (60, 180),
    (55, 190),
    (50, 200),
    (45, 210),
]

R_LOAD = 300.0  # R17 value (used for P_out = V_rms²/R)


def _trap_mean(t, v):
    if len(v) < 2:
        return v[0] if v else 0.0
    s = sum(0.5 * (v[i] + v[i + 1]) * (t[i + 1] - t[i]) for i in range(len(v) - 1))
    T = t[-1] - t[0]
    return s / T if T > 0 else 0.0


def _trap_rms(t, v, m):
    if len(v) < 2:
        return 0.0
    s = sum(0.5 * ((v[i] - m) ** 2 + (v[i + 1] - m) ** 2) * (t[i + 1] - t[i])
            for i in range(len(v) - 1))
    T = t[-1] - t[0]
    return (s / T) ** 0.5 if T > 0 else 0.0


def run_one(args):
    bias, v6, base_text, work_dir = args
    work_dir = Path(work_dir)

    # Substitute both PARAM GRID and V6 SIN amplitude
    text = re.sub(r"(\.PARAM\s+GRID\s*=\s*)\d+\s*V?", rf"\g<1>{bias}V", base_text, count=1)
    text = re.sub(r"(V6\s+\S+\s+\S+\s+DC\s+0\s+SIN\(0\s+)[\d.]+",
                  rf"\g<1>{v6}", text, count=1)

    netlist_path = work_dir / "netlist.cir"
    netlist_path.write_text(text)
    for f in work_dir.glob("spice4qucs.*.plot"):
        f.unlink()

    try:
        result = subprocess.run(
            [NGSPICE, "-b", netlist_path.name],
            cwd=str(work_dir), capture_output=True, text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return (bias, v6, None, "timeout")

    if result.returncode != 0:
        err = (result.stderr or "").strip().splitlines()
        tail = err[-1] if err else "(no stderr)"
        return (bias, v6, None, f"exit {result.returncode}: {tail[:80]}")

    rawfiles = sorted(work_dir.glob("spice4qucs.*.plot"))
    if not rawfiles:
        return (bias, v6, None, "no rawfile")

    plots = []
    for rf in rawfiles:
        plots.extend(run_ngspice.parse_rawfile(rf))
    if not plots:
        return (bias, v6, None, "empty plots")

    plot = plots[0]
    names = [v["name"].lower() for v in plot["vars"]]
    if "time" not in names:
        return (bias, v6, None, "no time axis")
    t_idx = names.index("time")
    times = [v.real for v in plot["data"][t_idx]]
    n = len(times)
    half = n // 2
    t_ss = times[half:]

    def get(probe):
        if probe not in names:
            return None
        idx = names.index(probe)
        return [v.real for v in plot["data"][idx]][half:]

    pr1 = get("v(pr1)")
    ivpr = get("i(vpr3)")
    if pr1 is None or ivpr is None:
        return (bias, v6, None, f"missing probe in {names}")

    pr1_mean = _trap_mean(t_ss, pr1)
    pr1_rms = _trap_rms(t_ss, pr1, pr1_mean)
    ivpr_mean = _trap_mean(t_ss, ivpr)
    ivpr_peak = max(abs(v) for v in ivpr)

    P_out = (pr1_rms ** 2) / R_LOAD
    I_avg = abs(ivpr_mean)
    I_peak = ivpr_peak

    return (bias, v6, {
        "V_rms": pr1_rms,
        "P_out": P_out,
        "I_avg": I_avg,
        "I_peak": I_peak,
    }, "OK")


def main():
    base_netlist = (SCRIPT_DIR.parent / "xmitter_prj" / "PA_netlist.cir").resolve()
    if not base_netlist.exists():
        sys.exit(f"Not found: {base_netlist}")
    base_text = base_netlist.read_text()

    # Sanity check the patterns
    if not re.search(r"\.PARAM\s+GRID\s*=", base_text):
        sys.exit("Pattern .PARAM GRID = not found")
    if not re.search(r"V6\s+\S+\s+\S+\s+DC\s+0\s+SIN\(0\s+[\d.]+", base_text):
        sys.exit("Pattern for V6 SIN amplitude not found")

    sweep_dir = base_netlist.parent / "bias_drive_sweep"
    if sweep_dir.exists():
        shutil.rmtree(sweep_dir)
    sweep_dir.mkdir()

    jobs = []
    for bias, v6 in PAIRS:
        wd = sweep_dir / f"bias{bias}_v6{v6}"
        wd.mkdir()
        jobs.append((bias, v6, base_text, str(wd)))

    n_workers = min(len(jobs), max(1, (os.cpu_count() or 4) - 1))
    print(f"Running {len(jobs)} jobs across {n_workers} workers...")
    print(f"R17 = {R_LOAD:.0f} ohm (hard-coded; verify it matches netlist)")
    print()

    results = {}
    with ProcessPoolExecutor(max_workers=n_workers) as exe:
        futs = {exe.submit(run_one, j): (j[0], j[1]) for j in jobs}
        for f in as_completed(futs):
            key = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = (*key, None, f"exception: {e}")
            results[key] = r
            bias, v6, data, status = r
            if data is None:
                print(f"  bias=-{bias:>3d}V V6={v6:>3d}V  FAIL  ({status})")
            else:
                print(f"  bias=-{bias:>3d}V V6={v6:>3d}V  P_out={data['P_out']:5.1f}W  "
                      f"I_avg={data['I_avg']*1000:5.1f}mA  "
                      f"I_peak={data['I_peak']*1000:5.0f}mA")

    print()
    print("=" * 96)
    print(f"{'Bias':>6}  {'V6':>4}  {'I_peak':>9}  {'I_avg':>8}  {'P_in/tube':>10}  "
          f"{'P_out':>8}  {'P_out/tube':>11}  {'P_diss/tube':>12}  {'Eff':>6}")
    print("-" * 96)
    for bias, v6 in PAIRS:
        d = results.get((bias, v6))
        if d is None or d[2] is None:
            continue
        data = d[2]
        # Per-tube quantities (push-pull)
        V_supply = 600.0  # TODO: parse from netlist if you want exactness
        P_in_tube = V_supply * data["I_avg"]
        P_out_tube = data["P_out"] / 2
        P_diss_tube = P_in_tube - P_out_tube
        eff = (data["P_out"] / (2 * P_in_tube)) * 100 if P_in_tube > 0 else 0
        # Mark over-spec values
        diss_mark = " !" if P_diss_tube > 25 else "  "
        print(f"  -{bias:>3d}V  {v6:>4d}V  {data['I_peak']*1000:>6.0f}mA  "
              f"{data['I_avg']*1000:>5.1f}mA  {P_in_tube:>7.1f}W   "
              f"{data['P_out']:>5.1f}W  {P_out_tube:>8.2f}W   "
              f"{P_diss_tube:>8.2f}W{diss_mark}  {eff:>4.1f}%")
    print()
    print("Operating points marked '!' exceed the 25 W/tube CW plate dissipation rating.")


if __name__ == "__main__":
    main()

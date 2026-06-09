"""Generic parameter sweep for ngspice netlists.

Edits one matched value in a base netlist (via a regex with a single capture
group), fans out one ngspice run per substituted value across many worker
processes, parses each spice4qucs.*.plot rawfile, extracts the requested
probe, computes a requested metric on the last 50 percent of the trace
(steady-state window), and prints a results table.

Common invocations:

  # Sweep .PARAM C_TANK (the value AND the suffix are inside the capture):
  python sweep_param.py PA_netlist.cir \\
      --pattern '\\.PARAM\\s+C_TANK\\s*=\\s*([\\d.]+\\s*p?F?)' \\
      --values 20pF,27pF,33pF,42pF,56pF \\
      --probe v(pr1) --load 850 --metric p_into_r

  # Sweep a resistor value (R17 between two plate-side nodes):
  python sweep_param.py PA_netlist.cir \\
      --pattern 'R17\\s+\\S+\\s+\\S+\\s+(\\d+)' \\
      --values 200,300,450,600,850,1200,1500,2000 \\
      --probe v(pr1) --metric p_into_r --load 1

  # Sweep a SIN source amplitude (V6 drive):
  python sweep_param.py PA_netlist.cir \\
      --pattern 'V6\\s+\\S+\\s+\\S+\\s+DC\\s+0\\s+SIN\\(0\\s+([\\d.]+)' \\
      --values 60,80,100,120,140,160,180 \\
      --probe 'i(vpr3)' --metric peak_abs

The regex must contain one capture group around the text to replace. Tip:
run with --dry-run first to confirm what the pattern matched and what would
be substituted before running the (potentially long) parallel sweep.
"""

import argparse
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

METRICS = ("mean", "peak", "peak_neg", "peak_abs", "peak_to_peak",
           "rms", "p_into_r")


def _trap_mean(times, values):
    """Time-weighted mean via trapezoidal integration."""
    if len(values) < 2:
        return values[0] if values else 0.0
    integral = 0.0
    for i in range(len(values) - 1):
        dt = times[i + 1] - times[i]
        integral += 0.5 * (values[i] + values[i + 1]) * dt
    total_t = times[-1] - times[0]
    return integral / total_t if total_t > 0 else 0.0


def _trap_rms(times, values, mean):
    """Time-weighted RMS via trapezoidal integration of (v - mean)^2."""
    if len(values) < 2:
        return 0.0
    integral = 0.0
    for i in range(len(values) - 1):
        dt = times[i + 1] - times[i]
        a = (values[i] - mean) ** 2
        b = (values[i + 1] - mean) ** 2
        integral += 0.5 * (a + b) * dt
    total_t = times[-1] - times[0]
    return (integral / total_t) ** 0.5 if total_t > 0 else 0.0


def compute_metric(values, metric, R_load, times=None):
    """Compute the requested metric on the last 50% (steady-state) of values.

    If `times` is supplied, mean/RMS are computed with proper trapezoidal
    time-weighting. Otherwise falls back to simple arithmetic statistics
    (which can be biased when ngspice uses adaptive timesteps).
    """
    n = len(values)
    if n == 0:
        return None
    ss = values[n // 2:]
    m = len(ss)

    if times is not None and len(times) == n:
        t_ss = times[n // 2:]
        mean = _trap_mean(t_ss, ss)
    else:
        t_ss = None
        mean = sum(ss) / m

    if metric == "mean":
        return mean
    if metric == "peak":
        return max(ss)
    if metric == "peak_neg":
        return min(ss)
    if metric == "peak_abs":
        return max(abs(v) for v in ss)
    if metric == "peak_to_peak":
        return max(ss) - min(ss)
    if metric == "rms":
        if t_ss is not None:
            return _trap_rms(t_ss, ss, mean)
        return (sum((v - mean) ** 2 for v in ss) / m) ** 0.5
    if metric == "p_into_r":
        if t_ss is not None:
            rms = _trap_rms(t_ss, ss, mean)
        else:
            rms = (sum((v - mean) ** 2 for v in ss) / m) ** 0.5
        return (rms ** 2) / R_load
    raise ValueError(f"unknown metric: {metric}")


def _substitute(text, pattern, value):
    """Replace just the captured group in the first regex match with `value`."""
    def repl(m):
        full = m.group(0)
        a = m.start(1) - m.start(0)
        b = m.end(1) - m.start(0)
        return full[:a] + value + full[b:]
    return re.subn(pattern, repl, text, count=1)


def sweep_one(args):
    """One ngspice run. Returns (value, metric_result_or_None, status_str)."""
    (value, base_text, work_dir_str,
     pattern, probe, metric, R_load) = args
    work_dir = Path(work_dir_str)

    new_text, n = _substitute(base_text, pattern, value)
    if n == 0:
        return (value, None, "pattern not matched")

    netlist_path = work_dir / "netlist.cir"
    netlist_path.write_text(new_text)

    for f in work_dir.glob("spice4qucs.*.plot"):
        f.unlink()

    try:
        result = subprocess.run(
            [NGSPICE, "-b", netlist_path.name],
            cwd=str(work_dir), capture_output=True, text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return (value, None, "timeout")

    if result.returncode != 0:
        err = (result.stderr or "").strip().splitlines()
        tail = err[-1] if err else "(no stderr)"
        return (value, None, f"exit {result.returncode}: {tail[:80]}")

    rawfiles = sorted(work_dir.glob("spice4qucs.*.plot"))
    if not rawfiles:
        return (value, None, "no rawfile")

    plots = []
    for rf in rawfiles:
        plots.extend(run_ngspice.parse_rawfile(rf))
    if not plots:
        return (value, None, "empty plots")

    probe_lower = probe.lower()
    target = None
    times = None
    for plot in plots:
        names = [v["name"].lower() for v in plot["vars"]]
        if probe_lower in names:
            idx = names.index(probe_lower)
            target = [v.real for v in plot["data"][idx]]
            # First var in a transient plot is the time axis
            if plot["vars"][0]["name"].lower() in ("time", "frequency"):
                times = [v.real for v in plot["data"][0]]
            break
    if target is None:
        all_names = [v["name"] for p in plots for v in p["vars"]]
        return (value, None, f"probe '{probe}' not in {all_names}")

    return (value, compute_metric(target, metric, R_load, times=times), "OK")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("netlist", help="Base netlist (.cir)")
    ap.add_argument("--pattern", required=True,
                    help="Regex with ONE capture group around the value to substitute")
    ap.add_argument("--values", required=True,
                    help="Comma-separated list of replacement values")
    ap.add_argument("--probe", default="v(pr1)",
                    help="Probe variable name from rawfile, e.g. 'v(pr1)' or 'i(vpr3)'")
    ap.add_argument("--load", type=float, default=50.0,
                    help="Load impedance for p_into_r metric (ohms; default 50)")
    ap.add_argument("--metric", default="p_into_r", choices=METRICS,
                    help="Metric on the last 50%% of the probe trace")
    ap.add_argument("--workers", type=int,
                    help="Worker processes (default: cpu_count - 1)")
    ap.add_argument("--sweep-dir", default="param_sweep",
                    help="Subdirectory under netlist's parent for per-value outputs")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be substituted; don't run anything")
    args = ap.parse_args()

    netlist = Path(args.netlist).resolve()
    if not netlist.exists():
        sys.exit(f"Not found: {netlist}")
    base_text = netlist.read_text()
    values = [v.strip() for v in args.values.split(",") if v.strip()]

    m = re.search(args.pattern, base_text)
    if not m:
        sys.exit(f"Pattern not found in netlist:\n  {args.pattern}")
    if not m.groups():
        sys.exit("Pattern must include at least one capture group.")

    print(f"Base netlist : {netlist}")
    print(f"Pattern      : {args.pattern}")
    print(f"  matched    : {m.group(0)!r}")
    print(f"  captured   : {m.group(1)!r}")
    print(f"Values       : {values}")
    print(f"Probe        : {args.probe}")
    if args.metric == "p_into_r":
        print(f"Metric       : p_into_r (R_load = {args.load} ohm)")
    else:
        print(f"Metric       : {args.metric}")

    if args.dry_run:
        print("\nDry run; showing first substitution preview:")
        if values:
            new_text, _ = _substitute(base_text, args.pattern, values[0])
            m2 = re.search(args.pattern, new_text)
            preview = m2.group(0) if m2 else "(unable to re-find substituted line)"
            print(f"  Original: {m.group(0)!r}")
            print(f"  Becomes : {preview!r}")
        return

    sweep_dir = netlist.parent / args.sweep_dir
    if sweep_dir.exists():
        shutil.rmtree(sweep_dir)
    sweep_dir.mkdir()

    jobs = []
    for v in values:
        safe = re.sub(r"[^\w.+-]", "_", v)
        wd = sweep_dir / f"v_{safe}"
        wd.mkdir()
        jobs.append((v, base_text, str(wd), args.pattern, args.probe,
                     args.metric, args.load))

    n_workers = args.workers or max(1, (os.cpu_count() or 4) - 1)
    n_workers = min(n_workers, len(jobs))
    print(f"\nRunning {len(jobs)} jobs across {n_workers} workers...\n")

    results = {}
    with ProcessPoolExecutor(max_workers=n_workers) as exe:
        futs = {exe.submit(sweep_one, j): j[0] for j in jobs}
        for f in as_completed(futs):
            v = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = (v, None, f"exception: {e}")
            results[v] = r
            _, val, status = r
            if val is None:
                print(f"  {v:>14s}  FAIL  ({status})")
            else:
                print(f"  {v:>14s}  {val:>14.4g}")

    print(f"\n=== {args.metric}({args.probe}) vs swept value ===")
    print(f"{'value':>14s}  {args.metric:>14s}")
    print("-" * 32)
    for v in values:
        if v not in results:
            continue
        _, val, status = results[v]
        if val is None:
            print(f"{v:>14s}  {'--':>14}  ({status})")
        else:
            print(f"{v:>14s}  {val:>14.4g}")

    valid = [(v, val) for v, (_, val, _) in results.items() if val is not None]
    if valid:
        if args.metric == "peak_neg":
            v_best, val_best = min(valid, key=lambda x: x[1])
            print(f"\nMin (most negative) at {v_best}: {val_best:.4g}")
        else:
            v_best, val_best = max(valid, key=lambda x: x[1])
            print(f"\nMax at {v_best}: {val_best:.4g}")


if __name__ == "__main__":
    main()

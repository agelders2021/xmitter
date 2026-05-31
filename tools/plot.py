"""General-purpose QUCS-S/ngspice dataset plotter with GUI.

Usage:
    python plot.py [path/to/file.dat.ngspice]

File is selected via command line or auto-detected. All plot controls use GUI.
"""

import os
import re
import sys
import glob
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


# ── parser ────────────────────────────────────────────────────────────────────

def parse_qucs_dataset(path):
    """Return (indep, dep) dicts parsed from a .dat.ngspice file."""
    indep, dep = {}, {}
    cur_name = cur_kind = None
    cur_dims, cur_vals = [], []

    def _flush():
        if cur_name is None:
            return
        arr = np.array(cur_vals)
        if cur_kind == "indep":
            indep[cur_name] = arr.real
        else:
            dep[cur_name] = {"dims": cur_dims, "data": arr}

    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            m = re.match(r"<(indep|dep)\s+(\S+)(.*?)>", line)
            if m:
                _flush()
                cur_kind = m.group(1)
                cur_name = m.group(2)
                cur_dims = m.group(3).split() if cur_kind == "dep" else []
                cur_vals = []
                continue
            if line in ("</indep>", "</dep>"):
                _flush()
                cur_name = cur_kind = None
                cur_dims, cur_vals = [], []
                continue
            if cur_name and line:
                cx = re.match(r"([+-]?[\d.eE+-]+)([+-])j([\d.eE+-]+)", line)
                if cx:
                    re_p = float(cx.group(1))
                    im_p = float(cx.group(3)) * (1 if cx.group(2) == "+" else -1)
                    cur_vals.append(complex(re_p, im_p))
                else:
                    try:
                        cur_vals.append(float(line))
                    except ValueError:
                        pass

    return indep, dep


# ── helpers ───────────────────────────────────────────────────────────────────

TRANSFORMS = ["real", "mag", "dB", "imag", "phase"]


def extract_y(arr, transform):
    if transform == "mag":
        return np.abs(arr), "|·|"
    if transform == "dB":
        return 20 * np.log10(np.maximum(np.abs(arr), 1e-15)), "dB"
    if transform == "real":
        return arr.real, ""
    if transform == "imag":
        return arr.imag, "Im"
    if transform == "phase":
        return np.angle(arr, deg=True), "°"
    return arr.real, ""


def si_prefix(values):
    mx = np.max(np.abs(values))
    if mx == 0:
        return 1, ""
    exp3 = int(np.floor(np.log10(mx) / 3)) * 3
    exp3 = int(np.clip(exp3, -12, 12))
    pfx = {-12:"p", -9:"n", -6:"µ", -3:"m", 0:"", 3:"k", 6:"M", 9:"G", 12:"T"}.get(exp3, "")
    return 10**(-exp3), pfx


def unit_guess(name):
    n = name.lower()
    if "freq" in n:                         return "Hz"
    if "time" in n:                         return "s"
    if n.startswith("v(") or "volt" in n:   return "V"
    if n.startswith("i("):                  return "A"
    return ""


def _align_zeros(ax1, ax2):
    """Expand whichever axis needs more headroom so both zeros line up."""
    lo1, hi1 = ax1.get_ylim()
    lo2, hi2 = ax2.get_ylim()
    # Alignment only makes sense when both axes actually span zero
    if lo1 >= 0 or hi1 <= 0 or lo2 >= 0 or hi2 <= 0:
        return

    def frac(lo, hi):
        return -lo / (hi - lo)

    f1, f2 = frac(lo1, hi1), frac(lo2, hi2)
    if abs(f1 - f2) < 0.02:
        return
    span1, span2 = hi1 - lo1, hi2 - lo2
    if f1 > f2:
        new_lo2 = hi2 - span2 / (1 - f1 + 1e-9) * (1 - f2 + 1e-9)
        ax2.set_ylim(min(new_lo2, lo2), hi2)
    else:
        new_lo1 = hi1 - span1 / (1 - f2 + 1e-9) * (1 - f1 + 1e-9)
        ax1.set_ylim(min(new_lo1, lo1), hi1)


# ── GUI ───────────────────────────────────────────────────────────────────────

COLORS = ["#1f77b4", "#d62728"]   # blue (left), red (right)


class PlotApp(tk.Tk):
    def __init__(self, path, indep, dep):
        super().__init__()
        self.path  = path
        self.indep = indep
        self.dep   = dep

        fname = path.replace("\\", "/").split("/")[-1]
        self.title(f"QUCS-S Plotter — {fname}")
        self.resizable(True, True)

        self._build_controls()
        self._build_canvas()
        self._populate(reset_selections=True)
        self.do_plot()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_controls(self):
        ctrl = ttk.Frame(self, padding=6)
        ctrl.pack(side=tk.TOP, fill=tk.X)

        # Row 0 — file + refresh
        ttk.Label(ctrl, text="File:").grid(row=0, column=0, sticky="w")
        self.file_lbl = ttk.Label(ctrl, text=self.path, foreground="navy")
        self.file_lbl.grid(row=0, column=1, columnspan=5, sticky="w", padx=(4, 12))
        ttk.Button(ctrl, text="Refresh", command=self.refresh).grid(
            row=0, column=6, padx=4)

        ttk.Separator(ctrl, orient="horizontal").grid(
            row=1, column=0, columnspan=7, sticky="ew", pady=4)

        # Row 2 — X axis + scale
        ttk.Label(ctrl, text="X axis:").grid(row=2, column=0, sticky="w")
        self.x_var = tk.StringVar()
        self.x_cb  = ttk.Combobox(ctrl, textvariable=self.x_var,
                                   width=26, state="readonly")
        self.x_cb.grid(row=2, column=1, padx=4, pady=2)
        self.x_scale = tk.StringVar(value="linear")
        ttk.Combobox(ctrl, textvariable=self.x_scale, values=["linear", "log"],
                     width=7, state="readonly").grid(row=2, column=2, padx=4)

        ttk.Separator(ctrl, orient="horizontal").grid(
            row=3, column=0, columnspan=8, sticky="ew", pady=4)

        # Rows 4–5 — curve selectors
        self.curve_y     = []   # StringVar (variable name)
        self.curve_tr    = []   # StringVar (transform)
        self.curve_cb    = []   # Combobox (variable)
        self.curve_scale = []   # StringVar (linear/log)
        self.stats_vars  = []   # StringVar (min/max text)

        for i, (label, color) in enumerate([
            ("Curve 1  (left axis):",  COLORS[0]),
            ("Curve 2  (right axis):", COLORS[1]),
        ]):
            ttk.Label(ctrl, text=label, foreground=color).grid(
                row=4 + i, column=0, sticky="w", pady=3, padx=(0, 8))

            y_var = tk.StringVar()
            y_cb  = ttk.Combobox(ctrl, textvariable=y_var, width=26, state="readonly")
            y_cb.grid(row=4 + i, column=1, padx=4)

            tr_var = tk.StringVar(value="real")
            tr_cb  = ttk.Combobox(ctrl, textvariable=tr_var, values=TRANSFORMS,
                                   width=9, state="readonly")
            tr_cb.grid(row=4 + i, column=2, padx=4)

            sc_var = tk.StringVar(value="linear")
            ttk.Combobox(ctrl, textvariable=sc_var, values=["linear", "log"],
                         width=7, state="readonly").grid(row=4 + i, column=3, padx=4)

            stats_var = tk.StringVar(value="")
            ttk.Label(ctrl, textvariable=stats_var, foreground=color,
                      font=("Courier", 9), justify="left").grid(
                row=4 + i, column=4, columnspan=3, padx=(16, 4), sticky="w")

            self.curve_y.append(y_var)
            self.curve_tr.append(tr_var)
            self.curve_cb.append(y_cb)
            self.curve_scale.append(sc_var)
            self.stats_vars.append(stats_var)

        # Row 6 — Plot button
        ttk.Button(ctrl, text="Plot", command=self.do_plot, width=10).grid(
            row=6, column=6, padx=4, pady=(8, 2))

    def _build_canvas(self):
        frame = ttk.Frame(self)
        frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)

        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _populate(self, reset_selections=False):
        """Fill combo boxes; preserve selections unless reset_selections is True."""
        x_names = list(self.indep.keys())
        y_names = list(self.dep.keys())
        y_opts  = ["(none)"] + y_names

        self.x_cb["values"] = x_names
        if reset_selections or self.x_var.get() not in x_names:
            self.x_var.set(x_names[0] if x_names else "")

        for i, (y_var, y_cb) in enumerate(zip(self.curve_y, self.curve_cb)):
            y_cb["values"] = y_opts
            cur = y_var.get()
            if reset_selections or cur not in y_opts:
                y_var.set(y_names[i] if i < len(y_names) else "(none)")

    # ── actions ───────────────────────────────────────────────────────────────

    def refresh(self):
        """Re-read the data file and replot using current selections."""
        try:
            self.indep, self.dep = parse_qucs_dataset(self.path)
        except Exception as e:
            messagebox.showerror("Refresh error", str(e))
            return
        self._populate(reset_selections=False)
        self.do_plot()

    def do_plot(self):
        for sv in self.stats_vars:
            sv.set("")
        x_name = self.x_var.get()
        if not x_name or x_name not in self.indep:
            return

        x_data  = self.indep[x_name]
        x_sc, x_pfx = si_prefix(x_data)
        x_unit  = unit_guess(x_name)
        x_label = f"{x_name}  ({x_pfx}{x_unit})" if (x_pfx or x_unit) else x_name

        # Gather active curves: (var_name, display_label, y_values)
        curves = []
        for y_var, tr_var in zip(self.curve_y, self.curve_tr):
            name = y_var.get()
            if not name or name == "(none)" or name not in self.dep:
                continue
            arr = self.dep[name]["data"]
            if len(arr) != len(x_data):
                n_extra = len(arr) // len(x_data)
                if n_extra > 1:
                    arr = arr[::n_extra]
            transform = tr_var.get()
            y_vals, t_lbl = extract_y(arr, transform)
            display = f"{name} [{t_lbl}]" if t_lbl else name
            curves.append((name, display, y_vals))

        self.fig.clear()
        if not curves:
            self.canvas.draw()
            return

        ax1 = self.fig.add_subplot(111)
        fname = self.path.replace("\\", "/").split("/")[-1]
        ax1.set_title(fname)
        ax1.set_xscale(self.x_scale.get())
        ax1.set_xlabel(x_label)
        ax1.grid(True, alpha=0.35)

        # Curve 1 — left axis
        vn1, lbl1, y1 = curves[0]
        sc1, pfx1 = si_prefix(y1)
        u1 = unit_guess(vn1)
        ylabel1 = f"{lbl1}  ({pfx1}{u1})" if (pfx1 or u1) else lbl1
        line1, = ax1.plot(x_data * x_sc, y1 * sc1, color=COLORS[0], label=lbl1)
        ax1.set_yscale(self.curve_scale[0].get())
        ax1.set_ylabel(ylabel1, color=COLORS[0])
        ax1.tick_params(axis="y", labelcolor=COLORS[0])
        ax1.spines["left"].set_color(COLORS[0])

        self._print_stats(0, x_name, x_data, x_sc, x_pfx, x_unit,
                          lbl1, y1, sc1, pfx1, u1)

        lines, labels = [line1], [lbl1]

        if len(curves) >= 2:
            vn2, lbl2, y2 = curves[1]
            sc2, pfx2 = si_prefix(y2)
            u2 = unit_guess(vn2)
            ylabel2 = f"{lbl2}  ({pfx2}{u2})" if (pfx2 or u2) else lbl2
            ax2 = ax1.twinx()
            line2, = ax2.plot(x_data * x_sc, y2 * sc2, color=COLORS[1], label=lbl2)
            ax2.set_yscale(self.curve_scale[1].get())
            ax2.set_ylabel(ylabel2, color=COLORS[1])
            ax2.tick_params(axis="y", labelcolor=COLORS[1])
            ax2.spines["right"].set_color(COLORS[1])
            self._print_stats(1, x_name, x_data, x_sc, x_pfx, x_unit,
                              lbl2, y2, sc2, pfx2, u2)
            lines.append(line2)
            labels.append(lbl2)
            if self.curve_scale[0].get() == "linear" and self.curve_scale[1].get() == "linear":
                _align_zeros(ax1, ax2)

        ax1.legend(lines, labels, loc="best", fontsize=8)
        self.fig.tight_layout()
        self.canvas.draw()

    def _print_stats(self, curve_idx, x_name, x_data, x_sc, x_pfx, x_unit,
                     label, y_vals, y_sc, y_pfx, y_unit):
        if len(y_vals) == 0:
            return
        i_min = int(np.argmin(y_vals))
        i_max = int(np.argmax(y_vals))
        x_u = f"{x_pfx}{x_unit}" if (x_pfx or x_unit) else x_name
        y_u = f"{y_pfx}{y_unit}" if (y_pfx or y_unit) else ""
        min_str = (f"min {y_vals[i_min] * y_sc:.4g} {y_u}"
                   f"  @  {x_data[i_min] * x_sc:.4g} {x_u}")
        max_str = (f"max {y_vals[i_max] * y_sc:.4g} {y_u}"
                   f"  @  {x_data[i_max] * x_sc:.4g} {x_u}")
        self.stats_vars[curve_idx].set(f"{min_str}\n{max_str}")
        print(f"{label}:")
        print(f"  {min_str}")
        print(f"  {max_str}")


# ── entry point ───────────────────────────────────────────────────────────────

def find_file():
    if len(sys.argv) > 1:
        return sys.argv[1]
    seen, matches = set(), []
    for m in glob.glob("**/*.dat.ngspice", recursive=True):
        key = os.path.normpath(m)
        if key not in seen:
            seen.add(key)
            matches.append(m)
    if not matches:
        return input("Data file path: ").strip().strip('"')
    if len(matches) == 1:
        print(f"Using: {matches[0]}")
        return matches[0]
    print("Multiple data files found:")
    for i, m in enumerate(matches):
        print(f"  {i}  {m}")
    while True:
        try:
            idx = int(input("Select file: "))
            if 0 <= idx < len(matches):
                return matches[idx]
        except ValueError:
            pass


def main():
    path = find_file()
    print(f"Parsing {path} …")
    indep, dep = parse_qucs_dataset(path)
    if not indep and not dep:
        print("No data found — check the file path.")
        sys.exit(1)
    PlotApp(path, indep, dep).mainloop()


if __name__ == "__main__":
    main()

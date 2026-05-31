"""FFT viewer for QUCS-S transient datasets.

Loads a .dat.ngspice file, picks a variable (default v(pr1) if present),
resamples the variable-step ngspice data onto a uniform grid, computes
the FFT magnitude spectrum, and plots it. Harmonics of a chosen
fundamental (default 14.2 MHz) are marked.

Usage:
    py fft_view.py [path_to.dat.ngspice]

If launched without a path, opens a file picker. Also importable -
the FFTWindow class can be instantiated by other Tk apps to attach
as a child window.
"""
import sys
import numpy as np
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                                NavigationToolbar2Tk)

import plot  # for parse_qucs_dataset


DEFAULT_FUND_MHZ = 14.2


def resample_uniform(t, y, n_out=8192):
    """Linearly interpolate variable-step data onto a uniform time grid."""
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    # Keep only the unique-time, sorted subset (ngspice can repeat samples)
    order = np.argsort(t)
    t = t[order]; y = y[order]
    keep = np.concatenate(([True], np.diff(t) > 0))
    t = t[keep]; y = y[keep]
    if len(t) < 2:
        return t, y, 0.0
    t_u = np.linspace(t[0], t[-1], n_out)
    y_u = np.interp(t_u, t, y)
    fs = (n_out - 1) / (t[-1] - t[0])
    return t_u, y_u, fs


def compute_spectrum(t, y, n_out=8192, window="hann"):
    """Resample + windowed FFT. Returns (freqs_hz, mag_vrms)."""
    t_u, y_u, fs = resample_uniform(t, y, n_out)
    if fs == 0:
        return np.array([0.0]), np.array([0.0])
    N = len(y_u)
    # Apply window for cleaner spectrum
    if window == "hann":
        w = np.hanning(N)
    elif window == "blackman":
        w = np.blackman(N)
    else:
        w = np.ones(N)
    yw = y_u * w
    # Scale to recover peak amplitude after windowing
    win_scale = N / w.sum()
    Y = np.fft.rfft(yw)
    freqs = np.fft.rfftfreq(N, d=1.0 / fs)
    # Peak magnitude per bin -> RMS via /sqrt(2)
    mag_peak = (np.abs(Y) * 2.0 / N) * win_scale
    mag_rms = mag_peak / np.sqrt(2)
    return freqs, mag_rms


class FFTWindow(tk.Toplevel):
    """A tkinter Toplevel showing the FFT spectrum of a chosen variable."""

    def __init__(self, master=None, path=None, indep=None, dep=None,
                 default_var="tran.v(pr1)", fund_mhz=DEFAULT_FUND_MHZ):
        super().__init__(master)
        self.title(f"FFT view — {Path(path).name if path else '(no file)'}")
        self.geometry("980x640")
        self.path = path
        self.indep = indep or {}
        self.dep = dep or {}
        self.default_var = default_var
        self.fund_mhz = tk.DoubleVar(value=fund_mhz)

        self._build_controls()
        self._build_canvas()

        if path and indep is None and dep is None:
            self._load(path)
        elif indep or dep:
            self._populate()
            self._replot()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_controls(self):
        ctrl = ttk.Frame(self, padding=6)
        ctrl.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(ctrl, text="Open .dat.ngspice…",
                   command=self._open_dialog).grid(row=0, column=0, padx=(0, 8))

        ttk.Label(ctrl, text="Variable:").grid(row=0, column=1, padx=(0, 4))
        self.var_choice = tk.StringVar()
        self.var_cb = ttk.Combobox(ctrl, textvariable=self.var_choice,
                                    width=24, state="readonly")
        self.var_cb.grid(row=0, column=2, padx=(0, 12))
        self.var_cb.bind("<<ComboboxSelected>>", lambda _e: self._replot())

        ttk.Label(ctrl, text="Fundamental (MHz):").grid(row=0, column=3)
        ttk.Entry(ctrl, textvariable=self.fund_mhz, width=8).grid(
            row=0, column=4, padx=(4, 12))

        self.use_db = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text="dBc (relative to fundamental)",
                        variable=self.use_db,
                        command=self._replot).grid(row=0, column=5, padx=4)

        self.x_log = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Log freq",
                        variable=self.x_log,
                        command=self._replot).grid(row=0, column=6, padx=4)

        ttk.Button(ctrl, text="Replot",
                   command=self._replot).grid(row=0, column=7, padx=(12, 0))

        self.status = ttk.Label(self, text="", foreground="navy",
                                font=("Consolas", 9))
        self.status.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 4))

    def _build_canvas(self):
        frame = ttk.Frame(self)
        frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.fig = Figure(figsize=(9, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ── file actions ─────────────────────────────────────────────────────────

    def _open_dialog(self):
        path = filedialog.askopenfilename(
            title="Open .dat.ngspice",
            filetypes=[("ngspice dataset", "*.dat.ngspice"),
                       ("All files", "*.*")])
        if path:
            self._load(path)

    def _load(self, path):
        try:
            indep, dep = plot.parse_qucs_dataset(path)
        except Exception as e:
            messagebox.showerror("Parse error", str(e))
            return
        self.path = path
        self.indep = indep
        self.dep = dep
        self.title(f"FFT view — {Path(path).name}")
        self._populate()
        self._replot()

    def _populate(self):
        # Need a time-domain variable -> only show tran.* keys
        names = [n for n in self.dep.keys() if "tran" in n.lower()]
        if not names:
            names = list(self.dep.keys())
        self.var_cb["values"] = names
        cur = self.var_choice.get()
        if cur not in names:
            # Prefer Pr1 if available
            default = next((n for n in names
                            if self.default_var in n.lower()
                            or "pr1" in n.lower()), names[0] if names else "")
            self.var_choice.set(default)

    # ── plotting ─────────────────────────────────────────────────────────────

    def _replot(self):
        self.fig.clear()
        name = self.var_choice.get()
        if not name or name not in self.dep:
            self.canvas.draw()
            return
        # Find matching time vector
        time_key = next((k for k in self.indep
                         if "time" in k.lower()), None)
        if not time_key:
            self.status.config(text="No 'time' indep vector found.")
            self.canvas.draw()
            return
        t = np.asarray(self.indep[time_key], dtype=float)
        y = np.asarray(self.dep[name]["data"], dtype=float)
        if y.dtype == complex:
            y = y.real
        # Same-length check (ngspice sometimes pads)
        n = min(len(t), len(y))
        t, y = t[:n], y[:n]

        f0 = float(self.fund_mhz.get()) * 1e6
        freqs, mag = compute_spectrum(t, y, n_out=8192)

        # Find the bin closest to the fundamental and label it + harmonics
        fund_mag = np.interp(f0, freqs, mag)
        ax = self.fig.add_subplot(111)
        if self.use_db.get() and fund_mag > 0:
            mag_disp = 20 * np.log10(np.maximum(mag, 1e-12) / fund_mag)
            ylabel = "Magnitude (dBc, vs fundamental)"
            ymin = -120; ymax = 5
        else:
            mag_disp = mag
            ylabel = "Magnitude (V_rms)"
            ymin = None; ymax = None

        ax.plot(freqs / 1e6, mag_disp, lw=0.8, color="#1f77b4")

        # Mark harmonics
        harm_info = []
        for k in range(1, 8):
            fk = f0 * k
            if fk > freqs[-1]:
                break
            mk = np.interp(fk, freqs, mag)
            if self.use_db.get() and fund_mag > 0:
                dbc = 20 * np.log10(max(mk, 1e-12) / fund_mag)
                ax.annotate(f"{k}×",
                            xy=(fk / 1e6, dbc),
                            xytext=(2, 8), textcoords="offset points",
                            fontsize=8, color="red" if k == 1 else "darkred")
                harm_info.append(f"{k}f={fk/1e6:.2f}MHz: {dbc:+6.1f} dBc")
            else:
                ax.plot(fk / 1e6, mk, "ro", markersize=4)
                harm_info.append(f"{k}f={fk/1e6:.2f}MHz: {mk:.4g} V_rms")

        ax.set_xlabel("Frequency (MHz)")
        ax.set_ylabel(ylabel)
        if ymin is not None:
            ax.set_ylim(ymin, ymax)
        if self.x_log.get():
            ax.set_xscale("log")
            ax.set_xlim(left=max(freqs[1] / 1e6, 0.1))
        else:
            ax.set_xlim(0, min(freqs[-1] / 1e6, f0 * 10 / 1e6))
        ax.grid(True, which="both", alpha=0.3)
        ax.set_title(f"FFT of {name}  (f0 = {f0/1e6:.2f} MHz)")
        self.fig.tight_layout()

        # Status line: total power at fundamental + summary
        # Approximate load is 50 ohm; user can re-derive otherwise
        p_fund = (fund_mag ** 2) / 50  # if y is V_R1, power into 50 ohm
        v_rms_total = np.sqrt(np.mean(y ** 2))
        p_total = v_rms_total ** 2 / 50
        self.status.config(text=(
            f"  V_rms(total) = {v_rms_total:.3f} V   "
            f"P_total/50Ω = {p_total:.2f} W   |   "
            f"V_rms(fund) = {fund_mag:.3f} V   "
            f"P_fund/50Ω = {p_fund:.2f} W   |   "
            + "  ".join(harm_info[:4])
        ))
        self.canvas.draw()


def main():
    root = tk.Tk()
    root.withdraw()
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        path = filedialog.askopenfilename(
            title="Open .dat.ngspice for FFT",
            filetypes=[("ngspice dataset", "*.dat.ngspice"),
                       ("All files", "*.*")])
        if not path:
            return
    win = FFTWindow(master=root, path=path)
    win.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()

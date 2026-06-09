"""GUI wrapper around plot.py.

Lets you load either an existing .dat.ngspice file OR a .cir netlist (in which
case it runs ngspice via run_ngspice.py, showing live output in a progress
window, then loads the result).

Re-uses plot.py's PlotApp for the actual display, so all the existing plot
controls (curves, transforms, scales, stats, alignment) work as-is.

Usage:
    python gui_plot.py

Both plot.py and run_ngspice.py must be in the same directory as gui_plot.py.
"""

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import plot  # local module — provides PlotApp, parse_qucs_dataset
import fft_view  # local module — provides FFTWindow


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_NGSPICE = SCRIPT_DIR / "run_ngspice.py"


class GuiPlotApp(plot.PlotApp):
    """PlotApp + file-loader bar at the top."""

    def __init__(self):
        # Bypass PlotApp's required-args __init__; do our own initial setup
        tk.Tk.__init__(self)
        self.path = "(no file loaded)"
        self.indep = {}
        self.dep = {}

        self.title("xmitter — gui_plot")
        self.resizable(True, True)

        self._build_file_bar()        # our addition
        self._build_controls()        # from PlotApp
        self._build_canvas()          # from PlotApp
        # Don't call _populate() or do_plot() yet — no data loaded.

    # ── file bar ──────────────────────────────────────────────────────────────

    def _build_file_bar(self):
        bar = ttk.Frame(self, padding=(6, 6, 6, 0))
        bar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(bar, text="Open .dat.ngspice…",
                   command=self.open_dat).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="Open .cir (run ngspice & load)…",
                   command=self.open_cir).pack(side=tk.LEFT)
        ttk.Button(bar, text="FFT…",
                   command=self.open_fft).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Separator(self, orient="horizontal").pack(
            side=tk.TOP, fill=tk.X, pady=(4, 0))

    # ── file actions ──────────────────────────────────────────────────────────

    def open_dat(self):
        path = filedialog.askopenfilename(
            title="Select .dat.ngspice file",
            initialdir=str(Path.cwd()),
            filetypes=[("ngspice dataset", "*.dat.ngspice"),
                       ("All files", "*.*")],
        )
        if path:
            self._load_data(path)

    def open_cir(self):
        cir_path = filedialog.askopenfilename(
            title="Select SPICE netlist (.cir / .sp / .net)",
            initialdir=str(Path.cwd()),
            filetypes=[("SPICE netlists", "*.cir *.sp *.net"),
                       ("All files", "*.*")],
        )
        if not cir_path:
            return

        if not RUN_NGSPICE.exists():
            messagebox.showerror(
                "Missing tool",
                f"run_ngspice.py not found alongside gui_plot.py:\n  {RUN_NGSPICE}"
            )
            return

        cir = Path(cir_path)
        # Output goes next to the netlist (avoid clobbering an existing
        # .dat.ngspice from QUCS that has the same stem)
        out = cir.with_name(cir.stem + ".gui_plot.dat.ngspice")
        cmd = [sys.executable, "-u", str(RUN_NGSPICE), cir.name, out.name]
        self._run_with_progress(cmd, cwd=cir.parent, expected_output=out)

    def open_fft(self):
        """Open an FFT window on the currently loaded dataset."""
        if not self.dep:
            messagebox.showinfo("FFT",
                "Load a .dat.ngspice file (or run a .cir) first.")
            return
        fft_view.FFTWindow(master=self, path=self.path,
                            indep=self.indep, dep=self.dep)

    # ── progress window ──────────────────────────────────────────────────────

    def _run_with_progress(self, cmd, cwd, expected_output):
        """Spawn cmd; show live stdout in a Toplevel; load result on success."""
        win = tk.Toplevel(self)
        win.title("Running ngspice…")
        win.geometry("780x440")
        win.transient(self)

        ttk.Label(win, padding=4, foreground="navy",
                  text=" ".join(str(c) for c in cmd)).pack(fill=tk.X)
        text = scrolledtext.ScrolledText(win, wrap=tk.WORD,
                                          font=("Consolas", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        status = ttk.Label(win, text="Working…", padding=4)
        status.pack(side=tk.BOTTOM, fill=tk.X)
        close_btn = ttk.Button(win, text="Close",
                                command=win.destroy, state=tk.DISABLED)
        close_btn.pack(side=tk.BOTTOM, pady=(0, 4))

        q = queue.Queue()

        def reader():
            try:
                proc = subprocess.Popen(
                    cmd, cwd=str(cwd),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                for line in iter(proc.stdout.readline, ""):
                    q.put(("LINE", line))
                proc.wait()
                q.put(("DONE", proc.returncode))
            except Exception as exc:
                q.put(("LINE", f"\n*** error launching subprocess: {exc}\n"))
                q.put(("DONE", -1))

        threading.Thread(target=reader, daemon=True).start()

        def poll():
            try:
                while True:
                    kind, payload = q.get_nowait()
                    if kind == "LINE":
                        text.insert(tk.END, payload)
                        text.see(tk.END)
                    elif kind == "DONE":
                        status.config(text=f"Done — exit code {payload}")
                        close_btn.config(state=tk.NORMAL)
                        if payload == 0 and expected_output.exists():
                            self._load_data(str(expected_output))
                            # Leave the window open so the user can scan the log
                            # for warnings; the Close button is now enabled.
                        else:
                            messagebox.showerror(
                                "Run failed",
                                f"ngspice run exited with code {payload}.\n"
                                f"See progress window for details."
                            )
                        return
            except queue.Empty:
                pass
            win.after(60, poll)

        win.after(60, poll)

    # ── data load ─────────────────────────────────────────────────────────────

    def _load_data(self, path):
        try:
            indep, dep = plot.parse_qucs_dataset(path)
        except Exception as exc:
            messagebox.showerror("Parse error",
                                  f"Could not parse {path}\n\n{exc}")
            return
        if not indep and not dep:
            messagebox.showwarning("Empty data",
                                    f"No indep/dep sections found in:\n{path}")
            return

        self.path = path
        self.indep = indep
        self.dep = dep
        fname = path.replace("\\", "/").rsplit("/", 1)[-1]
        self.title(f"xmitter — gui_plot — {fname}")
        # PlotApp's existing file label
        if hasattr(self, "file_lbl"):
            self.file_lbl.config(text=path)
        self._populate(reset_selections=True)
        self.do_plot()


def main():
    GuiPlotApp().mainloop()


if __name__ == "__main__":
    main()

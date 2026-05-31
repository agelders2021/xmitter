"""Plot Koren model plate characteristics from an ngspice DC sweep output.

Reads a `wrdata`-format file with columns: Vp, -i(v_amm), Vp, i(v_s), Vp, Vg.

Usage:
    python plot_pchar.py <data.dat> [--title "Tube name + conditions"] [--vp-max 800]
"""

import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    raw = np.loadtxt(path)
    vp_all = raw[:, 0]
    ip_all = -raw[:, 1] * 1000.0  # to mA, sign-corrected
    vg_all = raw[:, 5]
    curves = []
    for vg in np.unique(vg_all):
        mask = vg_all == vg
        curves.append((float(vg), vp_all[mask], ip_all[mask]))
    curves.sort(key=lambda c: c[0])
    return curves


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path)
    p.add_argument("--title", default=None)
    p.add_argument("--vp-max", type=float, default=None)
    args = p.parse_args()

    if not args.path.exists():
        raise SystemExit(f"File not found: {args.path}")

    curves = load(args.path)
    title = args.title or f"Plate Characteristics ({args.path.name})"

    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)
    cmap = plt.colormaps["viridis"]
    for i, (vg, vp, ip) in enumerate(curves):
        color = cmap(i / max(1, len(curves) - 1))
        ax.plot(vp, ip, color=color, lw=1.5, label=f"Vg1 = {vg:+.1f} V")

    ax.set_xlabel("Plate Volts")
    ax.set_ylabel("Plate Milliamperes")
    ax.set_title(title)
    if args.vp_max:
        ax.set_xlim(0, args.vp_max)
    ax.set_ylim(0, max(np.max(ip) for _, _, ip in curves) * 1.05)
    ax.grid(True, which="both", linestyle=":", linewidth=0.5)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9, ncol=2)

    out = args.path.with_name(args.path.stem + ".png")
    fig.tight_layout()
    fig.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

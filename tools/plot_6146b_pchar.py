"""Plot 6146B Koren model plate characteristics from ngspice DC sweep output.

Reads 6146b_pchar.dat (output of test_6146b_koren.cir) and produces a PNG
comparable to RCA 6146B datasheet Fig.2 (typical plate characteristics at
Vs=200V).

Usage:
    python plot_6146b_pchar.py [path/to/6146b_pchar.dat]
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    """Return list of (Vg, Vp_array, Ip_array_mA) for each grid voltage."""
    raw = np.loadtxt(path)
    # cols: Vp, -i(v_amm), Vp, i(v_s), Vp, Vg
    vp_all = raw[:, 0]
    ip_all = -raw[:, 1] * 1000.0  # to mA, sign-correct
    vg_all = raw[:, 5]

    curves = []
    for vg in np.unique(vg_all):
        mask = vg_all == vg
        curves.append((float(vg), vp_all[mask], ip_all[mask]))
    curves.sort(key=lambda c: c[0])
    return curves


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("6146b_pchar.dat")
    if not path.exists():
        sys.exit(f"File not found: {path}")

    curves = load(path)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)
    cmap = plt.colormaps["viridis"]
    for i, (vg, vp, ip) in enumerate(curves):
        color = cmap(i / max(1, len(curves) - 1))
        ax.plot(vp, ip, color=color, lw=1.5, label=f"Vg1 = {vg:+.0f} V")

    ax.set_xlabel("Plate Volts")
    ax.set_ylabel("Plate Milliamperes")
    ax.set_title("6146B Koren model — Typical Plate Characteristics\n"
                 "Ef=6.3V, Vs(g2)=200V")
    ax.set_xlim(0, 800)
    ax.set_ylim(0, max(np.max(ip) for _, _, ip in curves) * 1.05)
    ax.grid(True, which="both", linestyle=":", linewidth=0.5)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.9)

    out = path.with_name(path.stem + ".png")
    fig.tight_layout()
    fig.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

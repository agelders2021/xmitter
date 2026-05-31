"""Generate ATU_analysis.pdf — 3-page balanced pi-network ATU analysis document."""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import sys, os

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

f  = 14.2e6
w  = 2 * np.pi * f
Rs = 300.0
L  = 2.14e-6

XL_k0   = 2 * w * L * (1 - 0.00)
XL_k09  = 2 * w * L * (1 - 0.90)
XL_k099 = 2 * w * L * (1 - 0.99)

XC_in_min  = 2 / (w * 100e-12)
XC_in_max  = 2 / (w * 8e-12)
XC_out_min = 2 / (w * 140e-12)
XC_out_max = 2 / (w * 8e-12)

# ── pi-network sweep ──────────────────────────────────────────────────────────
Q1_arr, RL_arr, Rm_arr, Q2_arr, C1_arr, C3_arr = [], [], [], [], [], []
for Q1 in np.linspace(0.001, 8.0, 100000):
    XC_in = Rs / Q1
    if not (XC_in_min <= XC_in <= XC_in_max):
        continue
    Rm = Rs / (1 + Q1 ** 2)
    Q2 = XL_k0 / Rm - Q1
    if Q2 < 0:
        continue
    RL = Rm * (1 + Q2 ** 2)
    XC_out = RL / Q2
    if not (XC_out_min <= XC_out <= XC_out_max):
        continue
    Q1_arr.append(Q1)
    RL_arr.append(RL)
    Rm_arr.append(Rm)
    Q2_arr.append(Q2)
    C1_arr.append(2 / (w * (Rs / Q1)) * 1e12)
    C3_arr.append(2 / (w * (RL / Q2)) * 1e12)

Q1_arr = np.array(Q1_arr)
RL_arr = np.array(RL_arr)
Rm_arr = np.array(Rm_arr)
C1_arr = np.array(C1_arr)
C3_arr = np.array(C3_arr)

RL_min = RL_arr.min()
RL_max = RL_arr.max()

TITLE_COLOR = "#1a3a5c"
ACCENT      = "#2166ac"
GREEN       = "#1a7a1a"
WARN        = "#d73027"


def page_header(fig, title):
    fig.text(0.5, 0.97, title, ha="center", va="top",
             fontsize=15, fontweight="bold", color=TITLE_COLOR)
    fig.text(0.5, 0.935,
             "20m CW Transmitter — Balanced Pi-Network ATU Analysis  |  14.2 MHz",
             ha="center", va="top", fontsize=9, color="gray")
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.925, 0.925],
                               transform=fig.transFigure,
                               color=TITLE_COLOR, linewidth=1.5))


with PdfPages("ATU_analysis.pdf") as pdf:

    # =========================================================================
    # PAGE 1 — Schematic + coupling constant analysis
    # =========================================================================
    fig = plt.figure(figsize=(8.5, 11))
    page_header(fig, "ATU Matching Range Analysis")

    # ── schematic ─────────────────────────────────────────────────────────────
    ax_sch = fig.add_axes([0.05, 0.60, 0.90, 0.32])
    ax_sch.set_xlim(0, 10)
    ax_sch.set_ylim(-1.5, 2.5)
    ax_sch.axis("off")
    ax_sch.set_title("Balanced Pi-Network Topology", fontsize=10,
                      fontweight="bold", color=TITLE_COLOR, pad=4)

    y_top, y_bot = 1.5, 0.0
    ax_sch.plot([0.5, 9.5], [y_top, y_top], "k-", lw=1.5)
    ax_sch.plot([0.5, 9.5], [y_bot, y_bot], "k-", lw=1.5)

    # source arrows + label
    ax_sch.annotate("", xy=(0.5, y_top), xytext=(0.05, y_top),
                    arrowprops=dict(arrowstyle="->", color="k", lw=1.2))
    ax_sch.annotate("", xy=(0.5, y_bot), xytext=(0.05, y_bot),
                    arrowprops=dict(arrowstyle="<-", color="k", lw=1.2))
    ax_sch.text(0.02, 0.75, "Xmtr\n300 ohm\nBalanced",
                fontsize=7.5, ha="center", va="center", color=TITLE_COLOR)

    def draw_shunt_cap(ax, x, y_rail, direction, label):
        """direction: +1 for cap below rail (top rail), -1 for cap above rail (bot)."""
        d = direction
        ax.plot([x, x], [y_rail, y_rail + d * 0.38], "k-", lw=1.5)
        ax.plot([x - 0.25, x + 0.25], [y_rail + d * 0.38] * 2, "k-", lw=2)
        ax.plot([x - 0.25, x + 0.25], [y_rail + d * 0.62] * 2, "k-", lw=2)
        ax.plot([x, x], [y_rail + d * 0.62, y_rail + d * 1.0], "k-", lw=1.5)
        ax.text(x + 0.35, y_rail + d * 0.5, label,
                fontsize=7, va="center", color=ACCENT)

    draw_shunt_cap(ax_sch, 2.0, y_top, -1, "C1\n8-100 pF")
    draw_shunt_cap(ax_sch, 2.0, y_bot, +1, "C2\n8-100 pF")

    # input chassis GND tie
    ax_sch.plot([2.0, 2.0], [y_top - 1.0, y_bot + 1.0], "k-", lw=1.5)
    for yg in [y_top - 1.0, y_bot + 1.0]:
        ax_sch.plot([1.85, 2.15], [yg, yg], "k-", lw=2)
        for i, hw in enumerate([0.22, 0.15, 0.08]):
            ax_sch.plot([2 - hw, 2 + hw], [yg - (i + 1) * 0.09] * 2, "k-", lw=1)

    # inductors
    xL = np.linspace(3.0, 6.5, 300)
    bump = 0.22 * np.abs(np.sin(4 * np.pi * (xL - 3.0) / 3.5))
    ax_sch.plot(xL, y_top + bump, "k-", lw=2)
    ax_sch.plot(xL, y_bot - bump, "k-", lw=2)
    ax_sch.text(4.75, y_top + 0.55, "L1  2.14 uH",
                fontsize=7.5, ha="center", color=ACCENT)
    ax_sch.text(4.75, y_bot - 0.68, "L2  2.14 uH",
                fontsize=7.5, ha="center", color=ACCENT)
    # coupling indicator
    for xc in [4.2, 5.3]:
        ax_sch.plot([xc, xc], [y_bot + 0.1, y_top - 0.1],
                    "--", color="gray", lw=1, alpha=0.7)
    ax_sch.text(4.75, 0.75, "k = 0\n(no coupling)",
                fontsize=7, ha="center", color=GREEN, style="italic")

    draw_shunt_cap(ax_sch, 7.5, y_top, -1, "C3\n8-140 pF")
    draw_shunt_cap(ax_sch, 7.5, y_bot, +1, "C4\n8-140 pF")

    # output chassis GND tie
    ax_sch.plot([7.5, 7.5], [y_top - 1.0, y_bot + 1.0], "k-", lw=1.5)
    for yg in [y_top - 1.0, y_bot + 1.0]:
        ax_sch.plot([7.35, 7.65], [yg, yg], "k-", lw=2)
        for i, hw in enumerate([0.22, 0.15, 0.08]):
            ax_sch.plot([7.5 - hw, 7.5 + hw], [yg - (i + 1) * 0.09] * 2, "k-", lw=1)

    # load arrows + label
    ax_sch.annotate("", xy=(9.5, y_top), xytext=(9.95, y_top),
                    arrowprops=dict(arrowstyle="<-", color="k", lw=1.2))
    ax_sch.annotate("", xy=(9.5, y_bot), xytext=(9.95, y_bot),
                    arrowprops=dict(arrowstyle="->", color="k", lw=1.2))
    ax_sch.text(9.98, 0.75, "Antenna\n(variable\nimpedance)",
                fontsize=7.5, ha="left", va="center", color=TITLE_COLOR)

    # ── coupling table ────────────────────────────────────────────────────────
    ax_tbl = fig.add_axes([0.05, 0.34, 0.90, 0.23])
    ax_tbl.axis("off")
    ax_tbl.set_title(
        "Coupling Constant Effect on Differential Inductance  (L = 2.14 uH each, f = 14.2 MHz)",
        fontsize=10, fontweight="bold", color=TITLE_COLOR, pad=6)
    rows = [
        ["0.99 (original)", f"{XL_k099:.1f} ohm",  "1%",   "Essentially zero — matching impossible"],
        ["0.90",            f"{XL_k09:.1f} ohm",   "10%",  "Severely limited matching range"],
        ["0.00 (recommended)", f"{XL_k0:.0f} ohm", "100%", "Full matching range available"],
    ]
    tbl = ax_tbl.table(
        cellText=rows,
        colLabels=["k", "Effective XL (diff.)", "% of k=0", "Assessment"],
        loc="center", cellLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.scale(1, 2.0)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if r == 0:
            cell.set_facecolor(TITLE_COLOR)
            cell.set_text_props(color="white", fontweight="bold")
        elif r == 1:
            cell.set_facecolor("#fde8e8")
        elif r == 2:
            cell.set_facecolor("#fff8e8")
        else:
            cell.set_facecolor("#e8f4e8")

    # ── explanation box ───────────────────────────────────────────────────────
    ax_box = fig.add_axes([0.05, 0.15, 0.90, 0.17])
    ax_box.axis("off")
    ax_box.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.02",
        facecolor="#f0f4ff", edgecolor=ACCENT, lw=1.2,
        transform=ax_box.transAxes))
    box_txt = (
        "For a balanced (push-pull) circuit the two inductors carry equal and opposite currents.\n"
        "The effective differential inductance is  2L(1-k),  so a high coupling constant drastically\n"
        "reduces the series reactance available for impedance matching.\n\n"
        "With k=0.99 the inductors act as near-perfect transformers and cancel each other differentially,\n"
        "leaving only 3.8 ohm of series reactance — far too little for any useful matching.\n"
        "The inductors must not be magnetically coupled: wind them on separate cores or orient at 90 deg."
    )
    ax_box.text(0.03, 0.90, "Why k = 0 is required:", fontsize=9, fontweight="bold",
                color=TITLE_COLOR, va="top", transform=ax_box.transAxes)
    ax_box.text(0.03, 0.70, box_txt, fontsize=8.2, va="top",
                transform=ax_box.transAxes, color="#222222")

    fig.text(0.5, 0.04, "Page 1 of 3", ha="center", fontsize=8, color="gray")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # =========================================================================
    # PAGE 2 — Component reactances + resistive matching sweep
    # =========================================================================
    fig = plt.figure(figsize=(8.5, 11))
    page_header(fig, "Component Reactances and Resistive Matching Range")

    # component table
    ax_t2 = fig.add_axes([0.05, 0.75, 0.56, 0.16])
    ax_t2.axis("off")
    ax_t2.set_title("Differential Reactances at 14.2 MHz  (k = 0)",
                     fontsize=10, fontweight="bold", color=TITLE_COLOR, pad=4)
    rows2 = [
        ["C1/C2 @ 8 pF each",   f"{XC_in_max:.0f} ohm",  "Min. shunt susceptance (input)"],
        ["C1/C2 @ 100 pF each", f"{XC_in_min:.0f} ohm",  "Max. shunt susceptance (input)"],
        ["C3/C4 @ 8 pF each",   f"{XC_out_max:.0f} ohm", "Min. shunt susceptance (output)"],
        ["C3/C4 @ 140 pF each", f"{XC_out_min:.0f} ohm", "Max. shunt susceptance (output)"],
        ["L1 + L2 (k=0)",       f"{XL_k0:.0f} ohm",      "Series reactance (both inductors)"],
    ]
    tbl2 = ax_t2.table(
        cellText=rows2,
        colLabels=["Component setting", "XC / XL", "Role"],
        loc="center", cellLoc="left")
    tbl2.auto_set_font_size(False)
    tbl2.set_fontsize(8.5)
    tbl2.scale(1, 1.9)
    for (r, c), cell in tbl2.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if r == 0:
            cell.set_facecolor(TITLE_COLOR)
            cell.set_text_props(color="white", fontweight="bold")
        elif r == 5:
            cell.set_facecolor("#e8f4e8")
        else:
            cell.set_facecolor("#f7f7f7")

    # design equations box
    ax_eq = fig.add_axes([0.63, 0.75, 0.34, 0.16])
    ax_eq.axis("off")
    ax_eq.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.04",
        facecolor="#f8f0ff", edgecolor="#7b3f9e", lw=1,
        transform=ax_eq.transAxes))
    ax_eq.text(0.5, 0.93, "Pi-Network Design Equations",
               fontsize=8.5, fontweight="bold", ha="center", va="top",
               transform=ax_eq.transAxes, color="#7b3f9e")
    eqs = (
        "Rm = Rs / (1 + Q1^2)\n"
        "RL = Rm x (1 + Q2^2)\n"
        "XL = (Q1 + Q2) x Rm\n"
        "Q1 = Rs / XC_in\n"
        "Q2 = RL / XC_out\n"
        "Rs = 300 ohm,  XL = 382 ohm"
    )
    ax_eq.text(0.08, 0.72, eqs, fontsize=8, va="top",
               transform=ax_eq.transAxes, fontfamily="monospace", color="#333333")

    # RL vs C1 scatter (coloured by C3 value)
    ax_rl = fig.add_axes([0.08, 0.40, 0.85, 0.32])
    sc = ax_rl.scatter(C1_arr, RL_arr, c=C3_arr, cmap="viridis", s=6, alpha=0.7, zorder=3)
    cb = fig.colorbar(sc, ax=ax_rl, pad=0.01, aspect=30)
    cb.set_label("C3 / C4 value (pF each)", fontsize=8)
    ax_rl.axhline(Rs,     color=WARN,   lw=1.2, ls="--", label=f"Source Rs = {Rs:.0f} ohm")
    ax_rl.axhline(RL_min, color="gray", lw=1,   ls=":",  alpha=0.8)
    ax_rl.axhline(RL_max, color="gray", lw=1,   ls=":",  alpha=0.8)
    ax_rl.text(101, RL_min + 8,  f"RL_min = {RL_min:.0f} ohm", fontsize=8, color="gray")
    ax_rl.text(101, RL_max + 8,  f"RL_max = {RL_max:.0f} ohm", fontsize=8, color="gray")
    ax_rl.set_xlabel("C1 / C2 value (pF each)", fontsize=9)
    ax_rl.set_ylabel("Matched load resistance RL (ohm)", fontsize=9)
    ax_rl.set_title("Resistive Load Matching Range vs. Input Capacitor Setting",
                     fontsize=10, fontweight="bold", color=TITLE_COLOR)
    ax_rl.legend(fontsize=8)
    ax_rl.grid(True, alpha=0.3)
    ax_rl.set_xlim(0, 110)

    # Intermediate Rm vs C1
    ax_rm = fig.add_axes([0.08, 0.09, 0.85, 0.27])
    ax_rm.plot(C1_arr, Rm_arr, color="#7b3f9e", lw=1.5, label="Intermediate Rm")
    ax_rm.fill_between(C1_arr, Rm_arr, alpha=0.15, color="#7b3f9e")
    ax_rm.set_xlabel("C1 / C2 value (pF each)", fontsize=9)
    ax_rm.set_ylabel("Intermediate impedance Rm (ohm)", fontsize=9)
    ax_rm.set_title("Intermediate Impedance Rm vs. Input Capacitor Setting",
                     fontsize=10, fontweight="bold", color=TITLE_COLOR)
    ax_rm.grid(True, alpha=0.3)
    ax_rm.set_xlim(0, 110)
    ax_rm.legend(fontsize=8)

    fig.text(0.5, 0.025, "Page 2 of 3", ha="center", fontsize=8, color="gray")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    # =========================================================================
    # PAGE 3 — Reactive range + summary table
    # =========================================================================
    fig = plt.figure(figsize=(8.5, 11))
    page_header(fig, "Reactive Load Range and Design Summary")

    # reactive range bar
    ax_rx = fig.add_axes([0.12, 0.63, 0.80, 0.26])
    ax_rx.barh(0,  XC_out_min, height=0.5, color="#aec7e8",
               label=f"Inductive loads  (output cap @ 140 pF: XC = {XC_out_min:.0f} ohm)")
    ax_rx.barh(0, -XL_k0,      height=0.5, color="#ffbb78",
               label=f"Capacitive loads  (series inductors: XL = {XL_k0:.0f} ohm)")
    ax_rx.axvline(0, color="black", lw=1.5)
    ax_rx.set_xlim(-520, 320)
    ax_rx.set_ylim(-0.9, 0.9)
    ax_rx.set_yticks([])
    ax_rx.set_xlabel("Load reactance X (ohm) — antenna terminal, differential", fontsize=9)
    ax_rx.set_title("Approximate Tunable Load Reactance Range",
                     fontsize=10, fontweight="bold", color=TITLE_COLOR)
    ax_rx.text( XC_out_min / 2, 0.0, f"+{XC_out_min:.0f}\nohm",
                ha="center", va="center", fontsize=9, fontweight="bold", color=TITLE_COLOR)
    ax_rx.text(-XL_k0 / 2, 0.0, f"-{XL_k0:.0f}\nohm",
                ha="center", va="center", fontsize=9, fontweight="bold", color=TITLE_COLOR)
    ax_rx.legend(fontsize=8, loc="lower right")
    ax_rx.grid(True, axis="x", alpha=0.3)
    ax_rx.annotate("Output C3/C4 @ 140 pF", xy=(XC_out_min, 0.25),
                   xytext=(220, 0.65), fontsize=7.5, color="#1f78b4",
                   arrowprops=dict(arrowstyle="->", color="#1f78b4", lw=1))
    ax_rx.annotate("Series inductors (k=0)", xy=(-XL_k0, 0.25),
                   xytext=(-470, 0.65), fontsize=7.5, color="#e08000",
                   arrowprops=dict(arrowstyle="->", color="#e08000", lw=1))

    # notes
    ax_note = fig.add_axes([0.05, 0.49, 0.90, 0.12])
    ax_note.axis("off")
    ax_note.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.04",
        facecolor="#fffce8", edgecolor="#c8a000", lw=1,
        transform=ax_note.transAxes))
    note = (
        "Inductive limit (+160 ohm): set by the maximum output capacitance (140 pF each).  "
        "The output cap must resonate the inductive load component.  Larger output caps extend this limit.\n\n"
        "Capacitive limit (-382 ohm): set by the total series inductance (XL = 382 ohm, k=0).  "
        "The inductor resonates a capacitive load; larger inductors extend this limit.  "
        "Both bounds are conservative — the actual tunable range for complex loads is somewhat wider "
        "because the resistive and reactive parts interact."
    )
    ax_note.text(0.03, 0.92, note, fontsize=8.0, va="top",
                 transform=ax_note.transAxes, color="#333333")

    # summary table
    ax_sum = fig.add_axes([0.05, 0.22, 0.90, 0.25])
    ax_sum.axis("off")
    ax_sum.set_title("Design Summary", fontsize=11, fontweight="bold",
                      color=TITLE_COLOR, pad=6)
    sum_rows = [
        ["Frequency",                "14.2 MHz  (20m CW)"],
        ["Source impedance",         "300 ohm balanced"],
        ["Each inductor",            "2.14 uH   ->   XL = 191 ohm per inductor"],
        ["Series XL (k=0, diff.)",   "382 ohm  (both inductors, push-pull drive)"],
        ["Input caps C1/C2",         "8 pF - 100 pF each   ->   XC_diff: 224 - 2800 ohm"],
        ["Output caps C3/C4",        "8 pF - 140 pF each   ->   XC_diff: 160 - 2800 ohm"],
        ["Coupling constant",        "k = 0  (physically separate, non-coupled inductors)"],
        ["Resistive load range",     f"{RL_min:.0f} - {RL_max:.0f} ohm  (always steps UP from 300 ohm source)"],
        ["Max inductive load X",     f"+{XC_out_min:.0f} ohm  (output cap limited)"],
        ["Max capacitive load X",    f"-{XL_k0:.0f} ohm  (series inductor limited)"],
        ["Approximate network Q",    "1.1 - 1.3  across the tuning range"],
    ]
    tbl3 = ax_sum.table(
        cellText=sum_rows,
        colLabels=["Parameter", "Value / Range"],
        loc="center", cellLoc="left")
    tbl3.auto_set_font_size(False)
    tbl3.set_fontsize(8.5)
    tbl3.scale(1, 1.9)
    for (r, c), cell in tbl3.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if r == 0:
            cell.set_facecolor(TITLE_COLOR)
            cell.set_text_props(color="white", fontweight="bold")
        elif r == 7:
            cell.set_facecolor("#e8f4e8")
        elif r % 2 == 0:
            cell.set_facecolor("#f7f7f7")
        else:
            cell.set_facecolor("white")

    # observations
    ax_obs = fig.add_axes([0.05, 0.07, 0.90, 0.13])
    ax_obs.axis("off")
    ax_obs.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.04",
        facecolor="#f0f4ff", edgecolor=ACCENT, lw=1.2,
        transform=ax_obs.transAxes))
    obs = (
        "Observations:  The network steps the 300 ohm source UP to 486 - 710 ohm for purely resistive loads. "
        "It cannot match loads below ~486 ohm because the series inductance (382 ohm > Rs = 300 ohm) "
        "forces a minimum network Q of ~1.1.  For a near-resonant folded dipole (~300 ohm +/- small X) "
        "this ATU works well.  For low-impedance loads (short antenna, ground-mounted vertical) a different "
        "topology or smaller inductors would be needed.  The inductive range (+160 ohm) may be limiting "
        "if the antenna operates well below resonance; larger output capacitors would extend it."
    )
    ax_obs.text(0.02, 0.90, obs, fontsize=8.2, va="top",
                transform=ax_obs.transAxes, color="#222222")

    fig.text(0.5, 0.025, "Page 3 of 3", ha="center", fontsize=8, color="gray")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

print("Done: ATU_analysis.pdf")

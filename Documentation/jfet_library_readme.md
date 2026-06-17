# Qucs-S Extended JFET & Dual-Gate MOSFET Library
## Files Included

┌──────────────────────┬──────────────────────────────────────────────────────────────────────────────────┐
│ File                 │ Contents                                                                         │
├──────────────────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ `DualGateMOSFET.lib` │ BF961, BF981, BF998, BF998R dual-gate MOSFETs (with schematic symbols)           │
│ `JFET_Extended.lib`  │ 18 N- and P-channel JFETs (2N3819, 2N5457–5462, 4117–4119, 4391, 4416, 5432,     │
│                      │ 5434, 3820) (with DefaultSymbol)                                                 │
└──────────────────────┴──────────────────────────────────────────────────────────────────────────────────┘

---

## Installation

Copy both `.lib` files to your Qucs-S library directory:

- **Linux:** `/usr/share/qucs_s/library/` (system) or `~/.qucs/library/` (user)
- **Windows:** `C:\Program Files\Qucs-S\share\qucs\library\` (typical)

Then restart Qucs-S. The libraries appear in **Project → Insert Component → User Libraries**.

---

## The BF961 — Important Notes

The BF961 is a **dual-gate depletion-mode MOSFET** (N-channel tetrode), not a JFET.
There is no single SPICE primitive for it. The model uses a **two-NMOS subcircuit** stack:

```
         Drain (pin 2)
            |
           [M2]  ← Gate 2 (pin 3): AGC / mixer injection
            |
       internal node
            |
           [M1]  ← Gate 1 (pin 4): RF signal input
            |
         Source (pin 1)
```

### Typical Bias (VHF Amplifier)
- VDS = 12–15 V
- VGS1 = 0 V (Gate 1 at DC ground through choke)
- VGS2 = +4 V (Gate 2 bias for maximum gain)
- ID ≈ 10–20 mA

### AGC Operation
Reducing VGS2 from +4 V to +1 V collapses gain by >50 dB. Gate 2 should be
bypassed to RF ground with a good HF capacitor (100–220 pF).

### BF961 vs BF981 vs BF998

┌───────┬─────────┬────────┬────────┬─────────────────────────────────────┐
│ Part  │ Freq.   │ VDSmax │ NF     │ Notes                               │
├───────┼─────────┼────────┼────────┼─────────────────────────────────────┤
│ BF961 │ 300 MHz │ 20 V   │ 1.8 dB │ TO-50/SOT-103, older Siemens/Vishay │
│ BF981 │ 500 MHz │ 20 V   │ ~2 dB  │ SOT-143, Philips/NXP                │
│ BF998 │ 800 MHz │ 12 V   │ 0.6 dB │ SOT-143, modern low-noise choice    │
└───────┴─────────┴────────┴────────┴─────────────────────────────────────┘

For new designs, **BF998** is the preferred device (still manufactured, better NF).

---

## JFET Library — Device Quick Reference

### N-Channel JFETs

┌──────────┬──────────────┬──────────────┬─────────┬───────────────────────────────┐
│ Part     │ IDSS         │ Vp (typical) │ Package │ Best Use                      │
├──────────┼──────────────┼──────────────┼─────────┼───────────────────────────────┤
│ J2N3819  │ 2–20 mA      │ −3 V         │ TO-92   │ General purpose, audio        │
│ J2N5457  │ 1–5 mA       │ −1.4 V       │ TO-92   │ Low-noise preamp              │
│ J2N5458  │ 2–9 mA       │ −2.9 V       │ TO-92   │ General purpose               │
│ J2N5459  │ 4–16 mA      │ −4.5 V       │ TO-92   │ Higher pinch-off              │
│ J2N4091  │ 15–60 mA     │ −5.7 V       │ TO-18   │ High-current switch           │
│ J2N4093  │ 25–75 mA     │ −2.0 V       │ TO-18   │ High-current analog           │
│ J2N4117  │ 30–600 µA    │ −1.2 V       │ TO-72   │ Electrometer, ultra-low-I     │
│ J2N4118  │ 80 µA–1.6 mA │ −1.7 V       │ TO-72   │ Electrometer                  │
│ J2N4119  │ 200 µA–3.6 mA│ −2.5 V       │ TO-72   │ Electrometer                  │
│ J2N4391  │ 50–150 mA    │ −5.8 V       │ TO-18   │ High-speed switch             │
│ J2N4416  │ 5–15 mA      │ −3.1 V       │ TO-72   │ VHF LNA, VFO buffer           │
│ J2N5245  │ 4–14 mA      │ −2.4 V       │ TO-92   │ Audio, general                │
│ J2N5432  │ 100–500 mA   │ −5.4 V       │ TO-52   │ Power switch                  │
│ J2N5434  │ 200 mA–1 A   │ −1.9 V       │ TO-52   │ Power switch                  │
└──────────┴──────────────┴──────────────┴─────────┴───────────────────────────────┘

### P-Channel JFETs

┌──────────┬────────────────┬──────────────┬─────────┬─────────────────────────────┐
│ Part     │ IDSS           │ Vp (typical) │ Package │ Best Use                    │
├──────────┼────────────────┼──────────────┼─────────┼─────────────────────────────┤
│ J2N3820  │ −1 to −12 mA   │ −2.5 V       │ TO-92   │ Complement to 2N3819        │
│ J2N5460  │ −1 to −5 mA    │ −1.75 V      │ TO-92   │ P-channel low-noise         │
│ J2N5461  │ −2 to −9 mA    │ −1.9 V       │ TO-92   │ P-channel general           │
│ J2N5462  │ −4 to −16 mA   │ −2.3 V       │ TO-92   │ P-channel higher current    │
└──────────┴────────────────┴──────────────┴─────────┴─────────────────────────────┘

---

## SPICE Model Caveats

- All JFET parameters derived from OrCAD/National Semiconductor datasheet characterization.
- Models are **typical** — real parts have wide spreads (often 3:1 in IDSS within a single
  grade). Use `.step` or Monte Carlo to bracket performance.
- The dual-gate MOSFET subcircuits use SPICE LEVEL=1 or LEVEL=3 NMOS primitives.
  ngspice is the recommended back-end for Qucs-S; these models have been validated with it.
- BF998 model is the original Philips Semiconductors 1993 characterization.
- BF961/BF981 models are derived from the same Philips BF981 model adapted to BF961
  datasheet parameters (gm=15 mS, Vgs(off)=−3.5 V, IDSS=20 mA typical).

---

## Simulation Tips for Dual-Gate MOSFETs in Qucs-S

1. Use the **SPICE netlist component** (not the native Qucs MOSFET primitive) — the
   subcircuit pins are: `1=S, 2=D, 3=G2, 4=G1` in the `.SUBCKT` declaration.
2. Add the library via: **Project → Add Files to Project**, then reference it with a
   `.lib` directive in a **SPICE Directive** component.
3. Instantiate with: `X1 S D G2 G1 BF961` in a SPICE netlist block, or drag from
   the component library browser.
4. For AC simulations above 100 MHz, ensure parasitic lead inductors in the subcircuit
   are retained (they are included in the BF998 model, approximated in BF961/BF981).

---

*Models compiled by Al from OrCAD JFET library (National Semiconductor, 1998),
Philips Semiconductors BF998 SPICE model (1993), and BF961/BF981 datasheet
characterization. For use with Qucs-S / ngspice.*

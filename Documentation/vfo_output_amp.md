# VFO Output Amplifier — Phase-Splitter Drive for 12HG7 Push-Pull

## Purpose

Take the filtered 14 MHz signal from the VFO / keyer chain and produce two
equal-amplitude, opposite-polarity outputs to drive the push-pull 12HG7
driver grids at 10–15 V peak each. The topology uses three through-hole
op amps: one front-end non-inverting stage, followed by a parallel
inverting / non-inverting pair that acts as a phase splitter.

## Signal budget

The upstream Q2 (RCA40673) keyer drops ~0.65 Vpk into the 50 Ω filter
input. After Chebyshev insertion loss the working assumption is
**~0.5 Vpk** at the input of the front-end op amp. Target at each
12HG7 grid is **10–15 Vpk**, so the total single-ended gain from
filter output to each grid is:

- Low end: 10 / 0.5 = **20×**
- High end: 15 / 0.5 = **30×**

## Topology

```
filter ─→ [A0 non-inv] ─┬─ [A1 inverting, −4.25]  ─→ grid A
                        └─ [A2 non-inverting, +4.25] ─→ grid B
```

- **A0** — front-end gain, single-ended. Sets total drive level.
- **A1, A2** — matched-magnitude pair. A1 inverts, A2 does not.
  Together they produce the differential drive.

Total single-ended gain to each grid = A0 × 4.25.

## Op amp choice

All three stages: **LM7171IN** (DIP-8, 200 MHz GBW, 4100 V/µs slew rate).
See `Documentation/vfo_input_stage.md` for the earlier op amp survey
that landed on this part.

## Resistor values

### Phase-splitter pair (A1 and A2), gain magnitude = 4.25 exact

Trick: pick the same input resistor for both stages. Then matched
gain magnitude requires **Rf(inverting) = Rf(non-inv) + Ri**, which
falls out algebraically without any resistor-ratio hunting.

- **Ri (both stages):** 1.2 kΩ, E24 5%
- **Rf, inverting (A1):** 5.1 kΩ, E24 5%
- **Rf, non-inverting (A2):** 3.9 kΩ, E24 5%

Verification:

- Inverting: |Rf1/Ri| = 5.1 / 1.2 = **4.25**
- Non-inverting: 1 + Rf2/Ri = 1 + 3.25 = **4.25**

All three resistors are under the self-imposed 6 kΩ ceiling. The
low feedback impedance keeps HF phase-margin loss from stray input
capacitance manageable at 14 MHz.

### Front-end (A0), gain = 5.7 (recommended)

- **Ri:** 1.0 kΩ, E24 5%
- **Rf:** 4.7 kΩ, E24 5%
- Gain = 1 + 4.7/1.0 = **5.7**

Total gain per grid = 5.7 × 4.25 = **24.2×**, giving ~12 Vpk at each
grid with 0.5 Vpk at the filter output — mid-band of the 10–15 V
target with headroom to trim in either direction.

### Series resistor on non-inverting inputs (A0 and A2)

Use **~100 Ω (or 0 Ω)** in series with each non-inverting input.
Do NOT use the classical Rs+ = (Rf ∥ Ri) ≈ 915 Ω bias-current
cancellation value:

- Bias-current cancellation isn't useful here — the signal chain is
  AC-coupled, so the resulting DC offset (LM7171 Ib × Rs ≈ 3.6 mV
  worst case) is blocked by the next coupling cap. High-speed VFB
  parts also don't match bias currents well enough for the trick to
  work as cleanly as it does on classic bipolar op amps.
- **HF pole matters.** LM7171 input capacitance (~2–3 pF) plus PCB
  stray (~1–2 pF) forms a pole with the series resistor. At 1.2 kΩ
  the pole sits at ~33 MHz — that's ~23° of phase shift at 14 MHz,
  eating into phase margin. At 100 Ω the pole is at ~400 MHz and
  contributes negligible phase shift.
- Lower Johnson noise is a minor secondary benefit
  (1.3 nV/√Hz vs 4.5 nV/√Hz — both dominated by the op amp itself).

A 0 Ω pad (populated with 100 Ω or left as a wire jumper) gives
layout flexibility without committing to bias-current compensation
that isn't earning its keep.

## Alternate gain sets

If the 6 kΩ Rf ceiling is relaxed slightly, or if a different final
gain lands better on the driver bench-test, these phase-splitter
matched-pair options were the other exact E24 solutions found in
the 4–6 gain range:

- **G = 4.13:** Ri = 1.5 kΩ, Rf1 = 6.2 kΩ, Rf2 = 4.7 kΩ (Rf1 above 6 k)
- **G = 4.27:** Ri = 1.1 kΩ, Rf1 = 4.7 kΩ, Rf2 = 3.6 kΩ (lowest impedance option)
- **G = 4.31:** Ri = 1.3 kΩ, Rf1 = 5.6 kΩ, Rf2 = 4.3 kΩ

Front-end (A0) alternatives in the 5–7 gain range with Rf ≤ 6 kΩ:

- **G = 5.67:** Ri = 1.2 kΩ, Rf = 5.6 kΩ
- **G = 6.10:** Ri = 1.0 kΩ, Rf = 5.1 kΩ
- **G = 6.64:** Ri = 1.1 kΩ, Rf = 6.2 kΩ (Rf at budget limit)

## HF precautions (LM7171 at 14 MHz)

- **Feedback capacitance Cf across Rf:** 1–3 pF on each stage.
  Compensates the pole formed by stray input capacitance (2–3 pF
  typical) at the inverting node — restores phase margin without
  measurably rolling off gain at 14 MHz.
- **Output isolation resistor:** 33–50 Ω in series with each op amp
  output before any capacitive load (cable, next-stage grid).
  Prevents oscillation from capacitive loading.
- **Supply bypassing at each op amp:** 100 nF ceramic + 10 µF bulk
  at both supply pins.
- **Neutralization not required.** LM7171 is internally compensated;
  neutralization capacitors are only relevant to discrete tuned RF
  amplifier stages (see the Q2 discussion for that context).

## Supply

Op amps require **±12 V**. The +12 V rail already exists on the
analog board. The −12 V rail is generated from +12 V by an
**ICL7662CPA** charge-pump inverter (DIP-8):

- Rated input: 20 V max (safe with 12 V)
- Output current: 20–40 mA at 12 V input
- Pin-compatible with the more common ICL7660S (which is only
  rated to 10.5 V input and cannot be used here)

Three LM7171s draw ~7 mA each quiescent = ~21 mA total, which is
right at the ICL7662's practical limit. If bench measurement shows
sag, swap to **LT1054CN8** (DIP-8, 3.5–15 V input, 100 mA output,
lower output impedance).

## Load presented to front-end

The two parallel stages present very different input impedances to
A0's output:

- Non-inverting stage (A2): input Z ≈ 100 kΩ (bias network dominates)
- Inverting stage (A1): input Z = Ri = 1.2 kΩ (summing junction is
  a virtual ground)

The 1.2 kΩ dominates; A0 effectively drives a 1.2 kΩ load. LM7171 is
rated for 100 Ω minimum, so this is comfortable — but note for layout
that most of A0's output current flows into A1's summing junction.
Keep the A1 and A2 feedback loops physically separated on the PCB to
avoid crosstalk between the two paths.

## References

- `Documentation/vfo_input_stage.md` — earlier op amp survey and Q2
  keyer chain analysis
- `Documentation/driver_stage.md` — 12HG7 driver requirements this
  amplifier is designed to satisfy
- `KiCAD/analog/vfo_complete.kicad_sch` — schematic sheet where this
  circuit will be added

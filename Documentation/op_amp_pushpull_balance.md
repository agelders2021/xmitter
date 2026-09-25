# RF Output Stage — Push-Pull Balance Analysis

Analysis of the single-ended-to-differential converter formed by U11 (non-inverting)
and U12 (inverting), both fed from U10's output on `vfo_complete.kicad_sch`.
Operating band: 14.000 – 14.350 MHz (20 m CW).

## Topology as built

**U10** — LM7171, input buffer / gain stage, non-inverting

- Input: filter output via R39 (0R jumper)
- Gain-setting: R32 = 1.0 kΩ (IN- to GND), R33 = 4.7 kΩ (feedback)
- Compensation: C71 = 2 pF across R33
- DC signal gain: G10 = 1 + 4.7 / 1.0 = **+5.7**

**U11** — LM7171, positive-side output, non-inverting

- Input: U10 output via R36 (0R jumper) → IN+
- Gain-setting: R34 = 1.2 kΩ (IN- to GND), R35 = 3.9 kΩ (feedback)
- Compensation: C70 = 2 pF across R35
- DC signal gain: G+ = 1 + 3.9 / 1.2 = **+4.25**

**U12** — LM7171, negative-side output, inverting

- Input: U10 output via R38 = 1.2 kΩ → IN-
- Feedback: R37 = 5.1 kΩ
- IN+ tied directly to GND
- Compensation: C69 = 2 pF across R37
- DC signal gain: G− = −5.1 / 1.2 = **−4.25**

Output stages: U11 → C2 (1 nF DC block) → R1 (50 Ω back-term) → J2 SMA
(RF_OUT+). U12 → C1 (1 nF DC block) → R2 (50 Ω back-term) → J10 SMA (RF_OUT−).

## Transfer functions

The 2 pF compensation cap creates a pole in the feedback branch. Closed-loop
transfer functions:

**Non-inverting (U11):**

    H+(jω) = 1 + Rf / [ Rg · (1 + jω·Rf·C) ]

    where Rf = R35, Rg = R34, C = C70

**Inverting (U12):**

    H−(jω) = − Rf / [ Ri · (1 + jω·Rf·C) ]

    where Rf = R37, Ri = R38, C = C69

The critical fact: **the HF pole frequency is 1/(2π·Rf·C)**. It is set by the
feedback resistor value, not the input resistor. If Rf differs between the two
sides, the HF poles differ, so at frequencies near the pole the two paths
disagree in both magnitude and phase.

## Numerical evaluation at 14.2 MHz (band center)

Compensation cap C = 2 pF.

**U10 (single-ended, both paths share):**

- τ10 = R33 · C = 4.7 kΩ · 2 pF = 9.4 ns
- x10 = 2π · 14.2 MHz · 9.4 ns = 0.838
- H10 at 14.2 MHz: magnitude 4.786 (vs DC 5.700), phase −29.05°
- HF rolloff: −1.52 dB from DC

Since U10 is common to both paths, its rolloff and phase shift cancel in the
differential comparison. Only U11/U12 differences matter for balance.

**U11 (current design, Rf = 3.9 kΩ):**

- τ+ = 3.9 kΩ · 2 pF = 7.8 ns
- x+ = 2π · 14.2 MHz · 7.8 ns = 0.696
- H+ = 1 + (R35/R34) / (1 + j·x+) = 1 + 3.25 / (1 + j·0.696)
- Result: H+ = 3.195 − j 1.529
- |H+| = **3.542**, ∠H+ = **−25.58°**
- HF rolloff from DC: −1.58 dB

**U12 (current design, Rf = 5.1 kΩ):**

- τ− = 5.1 kΩ · 2 pF = 10.2 ns
- x− = 2π · 14.2 MHz · 10.2 ns = 0.910
- H− = −(R37/R38) / (1 + j·x−) = −4.25 / (1 + j·0.910)
- Result: H− = −2.335 + j 2.125
- |H−| = **3.157**, ∠H− = **+137.71°**
- HF rolloff from DC: −2.59 dB

## Balance metrics at 14.2 MHz — current design

**Amplitude imbalance**

- |H+| / |H−| = 3.542 / 3.157 = 1.122 = **+1.00 dB**

**Phase imbalance from ideal 180°**

- Ideal: ∠H− = ∠H+ + 180° = −25.58° + 180° = 154.42°
- Actual: ∠H− = 137.71°
- Phase error: 154.42° − 137.71° = **16.71°**

**Common-mode leakage**

Differential output: D = H+ − H− = (3.195 − j 1.529) − (−2.335 + j 2.125)
= 5.530 − j 3.654 → |D| = 6.628

Common-mode: CM = (H+ + H−) / 2 = (0.860 − j 0.596) / 2 = 0.430 − j 0.298
→ |CM| = 0.523

- CMRR = 20·log(|D| / |CM|) = 20·log(6.628 / 0.523) = **22.06 dB**

## Where the imbalance goes

The RF_OUT+ / RF_OUT− pair drives a push-pull grid input on the 12BY7A
driver stage. In an ideal push-pull, common-mode signal at the grids is
suppressed by the tube's shared cathode and cancels in the plate current
sum. In practice:

- Common-mode drive → even-order harmonics on the plate combiner output.
- With CMRR of 22 dB at fundamental, expect roughly **−22 dBc second-harmonic
  contribution** from driver imbalance alone (before the downstream LPF).
- Phase imbalance of 17° means the two grids swing across their operating
  point at slightly different times — reduces effective peak plate drive
  by cos(17°/2) ≈ 1.1 %, negligible for gain but non-negligible for
  distortion products.

The downstream harmonic LPF in the antenna path knocks the 2nd harmonic down
another 40+ dB, so the *emitted* signal is clean regardless. The internal
balance matters for driver linearity and idle-state common-mode noise, not
for FCC compliance.

## Options for improving the balance

### Option A — leave it alone

- **Change:** none.
- **DC balance:** perfect (|G+| = |G−| = 4.25).
- **HF balance at 14.2 MHz:** 1.0 dB / 17° / 22 dB CMRR (as above).
- **Cost:** none.
- **When it's fine:** if the downstream LPF cleans up the harmonics well
  enough that the driver's own 2nd-harmonic contribution is buried under
  noise floor after filtering. For a receiving-mate 20 m CW transmitter,
  this is probably fine.

### Option B — match Rf on both sides (recommended if changing anything)

- **Change:** R37 from 5.1 kΩ → **3.9 kΩ** (match R35). Also change R38 from
  1.2 kΩ → **910 Ω** (E24) or **909 Ω** (E96) so that U12's gain still
  matches U11.
- **New U12:** G− = −3.9 / 0.910 = −4.286. Amplitude mismatch vs U11:
  4.286 / 4.25 = 1.0084 → 0.07 dB at DC.
- **New HF pole:** τ− = 3.9 kΩ · 2 pF = 7.8 ns (identical to U11).
- **HF balance at 14.2 MHz:**
  - |H−| = 4.286 / sqrt(1 + 0.696²) = 4.286 / 1.218 = 3.520
  - ∠H− = 180° − atan(0.696) = 180° − 34.85° = 145.15°
  - Ideal ∠H− = ∠H+ + 180° = 154.42°
  - Amplitude imbalance: 3.542 / 3.520 = 1.006 → **0.05 dB**
  - Phase imbalance: 154.42° − 145.15° = **9.27°**
  - CMRR: recompute → **~28 dB** (~6 dB improvement)
- **Cost:** two resistor value changes.
- **Downside:** noise gains still differ (U11 NG = 4.25, U12 NG = 5.29),
  so op-amp GBW rolloff hits U12 slightly harder. Effect at 14 MHz is
  under 0.1 dB — negligible.

### Option C — match R_in on both sides (matches noise gain, breaks amplitude)

- **Change:** R37 from 5.1 kΩ → 3.9 kΩ. R38 unchanged at 1.2 kΩ.
- **Result:** noise gain matched (both 4.25). Signal gain U12 = −3.9 / 1.2
  = −3.25. Amplitude mismatch at DC: 4.25 / 3.25 = **+2.3 dB** — worse than
  Option A.
- **Not recommended.** Only mentioned to close the design space.

### Option D — remove or shrink the 2 pF caps

- **Change:** delete C69/C70/C71, or reduce to 1 pF each.
- **Effect:** pushes the HF pole above the band; both sides then have flat
  response through 14 MHz.
- **Risk:** the 2 pF cap is there for **stability** — LM7171 is a
  wide-bandwidth decompensated op amp that can peak or oscillate at
  moderate closed-loop gains without a small feedback cap. Removing it
  entirely requires bench-verified stability. Reducing to 1 pF is a safer
  middle ground — pole moves to 40+ MHz on both sides.
- **Only try after bench verification with a scope on the outputs.**

### Option E — cascade U12 as an inverter of U11's output

- **Change:** rewire U12's input from U10's output to U11's output. Change
  U12 to unity-gain inverter (R37 = R38 = same value, e.g., 1 kΩ each).
- **Result:** U12 output = −U11 output by construction, so amplitudes are
  matched to within op-amp tolerances (~0.1 %). U11's HF rolloff is
  inherited by U12.
- **Downside:** U12's additional propagation delay adds phase shift on the
  − side that isn't present on the + side. LM7171 group delay is ~2 ns, so
  at 14 MHz that's 14e6 · 360° · 2e-9 = **10°** of phase mismatch — comparable
  to Option B, and requires more layout rework.
- **Historical note:** this topology is classic for audio and low-HF
  work, but breaks down as GBW is approached.

## Recommendation

**Option A** (leave alone) if the downstream LPF is adequate and you don't
want to spin the board again for a marginal 6 dB CMRR improvement.

**Option B** (match Rf, adjust R_in) if you're already making other schematic
changes and want the cleanest attainable balance. Two resistor value changes,
no layout impact. Roughly halves the amplitude and phase imbalance at 14 MHz.

**Do not use Option C**. It breaks amplitude match without a compensating benefit.

**Option D** (comp cap change) only after bench-verified stability — treat as
a post-prototype tuning exercise, not a schematic design decision.

## References for the math

- LM7171 datasheet, TI SNOS760D: GBW 200 MHz, slew 4100 V/µs, IN+ bias
  current 2 µA typ.
- Standard non-inverting op amp closed-loop transfer with Rf‖C feedback:
  H(s) = 1 + Rf / (Rg·(1 + s·Rf·C))
- Standard inverting op amp closed-loop transfer with Rf‖C feedback:
  H(s) = −Rf / (Ri·(1 + s·Rf·C))

## Verification path

- LTspice model: LM7171 macromodel + resistor/cap network, sweep 1 MHz – 100 MHz.
  Compare |H+| and |H−| and their phases on the same plot. Confirms
  numerical results here.
- Bench measurement: sweep U10 input with a signal generator, measure
  RF_OUT+ and RF_OUT− with two probes on a scope; use math channel for
  differential and common-mode. Should see ~22 dB CMRR (current) or
  ~28 dB (Option B) at 14 MHz.

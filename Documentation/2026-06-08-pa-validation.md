# PA Validation Session — 2026-06-08

End-to-end simulation work on the keyer → driver → PA chain, ending with confirmation that
the push-pull 6146B PA can hit ~50 W output safely within tube ratings. Captures every
change made this session, the sweep results that validated the design, and the lessons
learned about ngspice quirks that bit us along the way.

## Summary

| Question | Answer arrived at |
|---|---|
| Is C_TANK = 33 pF the right value? | **Yes.** Tank already accounts for ~8.5 pF 6146B output capacitance per tube → effective 41.5 pF per side → resonance lands at 14.2 MHz. Sweep showed peak power within ±1 pF. |
| Best R17 load for the PA in standalone test? | **~320 Ω** (broad peak from 290–360 Ω, all within 2 % of max). Equivalent to the ~300 Ω the balun + 50 Ω antenna naturally present in the full chain. |
| Max V6 drive without exceeding tube ratings? | **V6 = 220 V peak is safe** (15 W/tube dissipation, ~53 W out). V6 = 240 V is the rate-limit; above that the conduction angle widens enough that plate dissipation creeps up. |
| Can we hit 50 W output safely? | **Yes** — V6 = 200 V on R17 ≈ 300 Ω gives 50 W out, 15 W/tube dissipation (60 % of the 25 W rating), 63 % efficiency. |
| Does the modulator-port linear-mode redesign work? | **Yes.** 20 dB pad + 7-pole LPF + LM7171 post-amp (gain ~5.8) restored full driver input level while moving the MC1496 into true 4-quadrant multiplier behaviour (carrier port ~30 mV peak, well below switching threshold). |

## Changes committed this session

### VFO subcircuit (`vfo_subcircuit.sch`)

**Pi pad** upgraded from 6 dB to **20 dB** to reduce carrier amplitude into the keyer:

| Ref | Old | New |
|---|---|---|
| RP1, RP3 | 150 Ω | **62 Ω** |
| RP2 | 39 Ω | **240 Ω** |

Result: V_RF_IN to keyer drops from ~380 mV peak to ~38 mV peak, putting the MC1496
carrier port in linear-multiplier mode.

**LPF** upgraded from 5-pole to **7-pole Chebyshev** (same fc = 17.5 MHz, 0.1 dB ripple)
for deeper harmonic rejection — necessary now that the modulator passes carrier harmonics
directly to the output instead of generating its own from switching mode:

| Element | Old (5-pole) | New (7-pole) |
|---|---|---|
| CF1 / CF7 | 200 pF | **220 pF** |
| LF2 / LF6 | 13 t T50-6 (~624 nH) | 13 t T50-6 (~647 nH) ← same as before |
| CF3 / CF5 | 360 pF | **390 pF** |
| LF4 (center) | 13 t T50-6 | **14 t T50-6** (~715 nH) |

Stopband rejection improvement at the LPF output:

| Harmonic | 5-pole | 7-pole | Δ |
|---|---|---|---|
| 2f (28.4 MHz) | 13 dB | **28 dB** | +15 dB |
| 3f (42.6 MHz) | 33 dB | **60 dB** | +27 dB |
| 5f (71 MHz) | 58 dB | **95 dB** | +37 dB |

### Keyer subcircuit (`keyer.sch`)

- **R10 = 8.2 kΩ** (was 1 kΩ in earlier version) — completes the symmetry fix with R5, R7, R9 so the PNP null injection is balanced
- **Re = 200 Ω** (was 1 kΩ) — increases modulator gain (12HG7 driver wants ~8 V p-p input)
- **C1 = 330 pF** (unchanged) — cap divider not used for attenuation; the upstream pad does that work
- **R11, R12 = 22 kΩ** (was 1 kΩ) — carrier-port bias divider standing current dropped from 6 mA to ~0.3 mA (no functional change)
- **LM7171 post-amp** (one per differential side, gain = 5.8) — restores the ~8 V p-p drive the driver needs after the modulator runs in low-gain linear mode

### LM7171 post-keyer amplifier (new subcircuit `Op_Amp_Out.sch`)

Non-inverting gain-of-5.8 amp, AC-coupled in/out, powered from existing +12 V / −8.3 V:

| Part | Value | Role |
|---|---|---|
| LM7171AIN | — | 200 MHz GBW op-amp (DIP-8/SOIC-8) |
| C_IN, C_OUT | 100 nF X7R | Couples around the +10 V DC at MC1496 outputs |
| R_B | 100 kΩ 1% | + input bias to GND |
| R_F | 30 kΩ 1% | Feedback (gain = 1 + R_F/R_G = 4) |
| R_G | 10 kΩ 1% | Inverting-input leg to GND |

(Schematic ships with R_F = 30 kΩ for gain 4. After this session's analysis the
recommended value for production is R_F = 47 kΩ giving gain 5.8 — see
`cw_envelope_keyer.md` for the trade-off table.)

### PA subcircuit (`PA_subcircuit.sch`)

- Plate-current sense probe path restructured during diode experiments (then reverted)
- Tran window extended to 3.5 µs (was 200 ns) so RMS/mean stats can integrate over ~50 cycles instead of ~3
- R17 (standalone test load) = 300 Ω — represents the ~300 Ω the balun delivers in full chain
- V6 (standalone drive) = 160 V — useful single-point baseline; 200 V is the 50 W operating point

### Balun subcircuit (`Balun_6to1_subcircuit.sch`)

- Added 0.5 Ω Rser to break a singular-matrix between LP and the PA's L6 (both inductors between the same two nodes at DC — needed *any* non-zero R to disambiguate)

## PA sweep results

All numbers below: standalone PA sim, GRID = 70 V, SCREEN = 200 V, V_supply = 600 V,
C_TANK = 33 pF, sim window = 3.5 µs (50 cycles at 14.2 MHz), R17 = 300 Ω unless noted.

### R17 sweep at V6 = 160 V

| R17 (Ω) | V_rms (V) | P_out (W) |
|---|---|---|
| 220 | 92.3 | 38.7 |
| 240 | 98.6 | 40.5 |
| 260 | 104.4 | 41.9 |
| 275 | 108.3 | 42.7 |
| 290 | 111.8 | 43.1 |
| 300 | 114.0 | 43.3 |
| 310 | 115.9 | 43.3 |
| **325** | **118.7** | **43.4** ← peak |
| 340 | 121.1 | 43.1 |
| 360 | 124.0 | 42.7 |
| 380 | 126.5 | 42.1 |
| 420 | 130.6 | 40.6 |

Conclusion: broad plateau 290–360 Ω, peak ~325 Ω. Tube spread (±10 %) swamps any
finer optimization; **300 Ω is the production target**.

### V6 sweep at R17 = 300 Ω

Each V6 row gives peak current, average current, output power, plate dissipation per tube:

| V6 (V) | I_peak (mA/tube) | I_avg (mA/tube) | P_in/tube (W) | P_out total (W) | P_diss/tube (W) | Efficiency |
|---|---|---|---|---|---|---|
| 80 | 59 | 8.5 | 5.1 | 0.9 | 4.7 | 9 % |
| 100 | 133 | 20.2 | 12.1 | 5.0 | 9.6 | 21 % |
| 120 | 224 | 35.0 | 21.0 | 14.3 | 13.8 | 34 % |
| 140 | 318 | 50.8 | 30.5 | 29.3 | 15.8 | 48 % |
| 160 | 377 | 60.9 | 36.5 | 41.6 | 15.7 | 57 % |
| 180 | 400 | 64.6 | 38.8 | 47.0 | 15.3 | 61 % |
| **200** | **416** | **66.8** | **40.1** | **50.3** | **14.9** | **63 %** |
| 220 | 426 | 68.2 | 40.9 | 52.8 | 14.5 | 65 % |
| 240 | 433 | 69.1 | 41.5 | 54.6 | 14.2 | 66 % |

Tube envelope check (6146B: 25 W plate, 270 mA peak emission steady-state):

- **Dissipation peaks at V6 = 140–160 V (~15.8 W/tube)** — *60 % of rating* — well within envelope
- Above V6 ≈ 160 V, dissipation *decreases* even as output rises (efficiency improves faster than input power grows in class C)
- Peak plate current of 416 mA at V6 = 200 V looks scary but is fine — the 270 mA rating is steady-state, not instantaneous peak; what kills tubes is average dissipation, not peak current

### Operating point recommendation

| Metric | Value |
|---|---|
| V6 drive amplitude | **200 V peak** (full chain delivers ~8 V p-p at driver input → driver multiplies up → ~200 V grid-to-grid) |
| R17 / load impedance | **300 Ω** (matches the balun's 6:1 step-down from 50 Ω antenna) |
| Plate supply (V_supply) | 600 V DC |
| Screen voltage | +200 V |
| Grid bias | −70 V |
| Output power | **50 W** |
| Plate dissipation | 15 W/tube (60 % of CW rating) |
| Efficiency | 63 % |

## New tooling

### `tools/sweep_param.py` — generic ngspice parameter sweep

Substitutes a regex-captured value in a netlist, runs ngspice in parallel across N
workers, parses the spice4qucs rawfiles, computes a chosen metric on a chosen probe.
Replaces the earlier C_TANK-specific `sweep_ctank.py` (kept for reference).

Common invocations:

```bash
# C_TANK sweep
python sweep_param.py PA_netlist.cir \
  --pattern '\.PARAM\s+C_TANK\s*=\s*([\d.]+\s*p?F?)' \
  --values 27pF,30pF,33pF,36pF,42pF \
  --probe v(pr1) --load 300 --metric p_into_r

# R17 (load) sweep — note --metric rms since R changes per row
python sweep_param.py PA_netlist.cir \
  --pattern 'R17\s+\S+\s+\S+\s+(\d+)' \
  --values '220,260,290,300,325,360,420' \
  --probe v(pr1) --metric rms

# V6 (drive) sweep, peak plate current
python sweep_param.py PA_netlist.cir \
  --pattern 'V6\s+\S+\s+\S+\s+DC\s+0\s+SIN\(0\s+([\d.]+)' \
  --values '100,140,160,180,200,220' \
  --probe 'i(vpr3)' --metric peak_abs

# Same V6 sweep, average plate current (for dissipation analysis)
python sweep_param.py PA_netlist.cir \
  --pattern 'V6\s+\S+\s+\S+\s+DC\s+0\s+SIN\(0\s+([\d.]+)' \
  --values '100,140,160,180,200,220' \
  --probe 'i(vpr3)' --metric mean
```

Metrics supported: `mean`, `peak`, `peak_neg`, `peak_abs`, `peak_to_peak`, `rms`,
`p_into_r`. Mean and RMS use **trapezoidal time-weighting** (essential — see lessons
below). The `--dry-run` flag confirms the pattern matched the intended line before
launching a long-running sweep.

### `tools/gui_plot.py` change

Removed the 750 ms auto-close of the progress window after a successful ngspice run.
Window now stays open so the user can read through the log for warnings.

### `tools/plot.py` change

Second-and-beyond plot curves default to `(none)` instead of auto-populating with the
next variable in the dep list. The default is now: only curve A is auto-selected; B+
overlays are opt-in. Cleaner plots, no obscuring of curve A.

## Lessons learned (worth remembering)

### 1. ngspice transient sampling vs. RMS/mean accuracy

Adaptive timestep means samples cluster around fast-changing parts of the waveform. A
simple arithmetic mean of sample values is BIASED — it overweights wherever the solver
took small steps.

**Fix:** trapezoidal time-weighted integration:

```python
integral = sum(0.5 * (y[i] + y[i+1]) * (t[i+1] - t[i]) for i in range(n-1))
mean = integral / (t[-1] - t[0])
```

For RMS: same trapezoidal integration of `(y - mean)^2`.

This is now built into `sweep_param.py`.

### 2. ngspice transient window length vs. RMS/mean validity

You also need **enough complete cycles** in the sampled window for the statistic to be
representative. A class C pulse train sampled across 2.8 cycles gives wildly noisy
mean values; 50 cycles is plenty.

For 14.2 MHz: tstop - tstart ≥ ~3.5 µs (50 cycles).

`PA_netlist.cir` had `tran tstep=2.02ns tstop=1.0002ms tstart=1ms`, a **200 ns window
== 2.8 cycles**. Mean/RMS bogus. Bumped tstop to 1.0035 ms (3.5 µs window = 50 cycles).
Now stats are stable to <1 % run-to-run.

### 3. Koren tube model unphysical negative plate current

The 6146B Koren-style SPICE model can produce small negative plate current during the
off-half cycle (a physical tube can't emit electrons from its plate, so this is a model
artifact). It's small enough that it averages to nearly zero across a cycle and barely
affects output power calculations.

**Tried to fix with series diodes** — gave up after the diodes caused multiple cascading
convergence failures (initial-condition stiffness; diode-in-series-with-0V-voltage-source
underdetermined branch). The cure was worse than the disease.

**Conclusion: live with the artifact.** Peak positive plate current (which matters for
tube ratings) is correct regardless; the negative tail just looks ugly on the plot.

### 4. Diode in series with a 0 V voltage source = SPICE pain

Don't put an ideal voltage source (`Vname A B DC 0`, used as a current sense) in series
with a diode. When the diode blocks, the branch current must be 0, but the 0 V source
doesn't constrain current — only voltage. The solver finds the branch underdetermined
and either oscillates or hits "timestep too small."

**If you really need this**, reorder so the diode is BEFORE the 0 V source in the
direction of current flow. Then the diode constrains the current to its forward I-V
curve (or to 0 when blocking), and the 0 V source just measures it.

### 5. The `uic` flag and `.IC` components in QUCS-S

The QUCS-S netlist generator auto-emits `uic` on the `tran` line whenever there are
`.IC` (Initial Voltage) components in the schematic. There's no UI toggle that
overrides this.

`uic` means "skip operating-point analysis; use my `.IC` values to start the transient"
— which is fine for purely linear circuits but **catastrophic for nonlinear devices
that need to find their own bias point** (diodes, tubes near cutoff). The fix is to
remove `.IC` components from the schematic; `.NODESET` components are kept (they're
just OP hints, not fixed values, and don't trigger `uic`).

### 6. Parallel ngspice == real speedup

The sweep tool spawns one ngspice process per swept value, capped at `cpu_count - 1`
workers. On the 32-core dev machine, 27-value sweeps take seconds instead of minutes.

The trade-off vs. running them sequentially: each ngspice loads its own copy of the
6146B/12HG7/MC1496 model libraries. Memory use scales linearly with workers, but for
ngspice's ~20 MB footprint per process, that's nothing.

## Updated/replaced docs

- `cw_envelope_keyer.md` — added Reduced carrier injection + LM7171 post-amp sections
- `20m-leveled-keyed-buffer.md` — VFO pad/LPF sections rewritten; BOM updated; added "PA monitoring and control — design options" section (deferred work)

## Deferred (next session)

- Per-tube grid bias control (DAC + HV op-amp); per-tube grid current sense; ADC protection for cathode-current sense — design options captured in `20m-leveled-keyed-buffer.md`
- Calibration sweep at hardware bring-up to populate the keyer's `s_cal[]` predistortion LUT (deferred to actual hardware bench work — see `cw_envelope_keyer.md`)
- Bring `cw_envelope_keyer.md` LM7171 R_F default in line with R_F = 47 kΩ recommendation (currently the schematic ships with 30 kΩ; analysis says 47 kΩ is the right gain)

# VFO Input Stage — Current State

The VFO input stage takes a 14.2 MHz carrier from the Si5351 clock
generator, attenuates it, removes harmonics, and presents a clean
sinusoidal signal to the MC1496 carrier input.

This doc describes the current design only. Earlier design revisions
are referenced for context but their specifics live in legacy docs.

## Block diagram

```
Si5351 module          Pi pad (20 dB)         7-pole ladder LPF (as-built)
3.3 V CMOS sq wave  →  62 / 240 / 62 Ω     →  CF1=220p, LF2=677nH,
14.175 MHz, ~8 mA      sets level into        CF3=390p, LF4=677nH,
push-pull output       the LPF                CF5=390p, LF6=677nH,
                                              CF7=220p
                                                │
                                                ▼
                                              50 Ω termination (RT)
                                              + 10 nF coupling (CC1)
                                                │
                                                ▼
                                              [J310 source follower]
                                              [   — see open Q below]
                                                │
                                                ▼
                                              RGL (1 MΩ grid leak)
                                              → MC1496 RF input
```

Signal flow, end to end:
- Si5351 module produces a 3.3 V CMOS push-pull square wave at the
  programmed VFO frequency (14.175 MHz center, scanning across the
  20 m CW band)
- The pi-pad attenuator drops the level by 20 dB and provides a
  50 Ω impedance environment for the LPF
- The 7-pole Chebyshev LPF (f_c = 17.5 MHz) removes harmonics of the
  square wave, leaving a clean sinusoid at the fundamental
- The LPF output is terminated in 50 Ω (RT) and AC-coupled through
  CC1 to the J310 buffer (or directly to the MC1496, see open question)
- RGL provides a grid-leak return for the MC1496 carrier input

## Components and values

### Pi-pad attenuator (20 dB, 50 Ω in / 50 Ω out)

┌─────┬────────┬─────────────────────────┐
│ Ref │ Value  │ Position                │
├─────┼────────┼─────────────────────────┤
│ RP1 │ 62 Ω   │ Series, input side      │
│ RP2 │ 240 Ω  │ Shunt, center           │
│ RP3 │ 62 Ω   │ Series, output side     │
└─────┴────────┴─────────────────────────┘

### 7-pole low-pass filter (T68-6 inductors, original caps kept)

Built with three identical T68-6 inductors at 12 turns each
(uniform 677 nH). Capacitor values are kept at the original
Chebyshev 0.1 dB ripple design (220 / 390 / 390 / 220 pF) — both
are E12 standard silver mica values for easy sourcing. The slight
filter-shape consequence is intentional and documented below.

┌─────┬────────┬─────────────────────────────────────────────────┐
│ Ref │ Value  │ Construction                                    │
├─────┼────────┼─────────────────────────────────────────────────┤
│ CF1 │ 220 pF │ Silver mica E12, ≥ 500 V (CD15/CD19 series)     │
│ LF2 │ 677 nH │ 12 turns #24 AWG enameled on T68-6              │
│ CF3 │ 390 pF │ Silver mica E12, ≥ 500 V                        │
│ LF4 │ 677 nH │ 12 turns #24 AWG enameled on T68-6              │
│ CF5 │ 390 pF │ Silver mica E12, ≥ 500 V                        │
│ LF6 │ 677 nH │ 12 turns #24 AWG enameled on T68-6              │
│ CF7 │ 220 pF │ Silver mica E12, ≥ 500 V                        │
└─────┴────────┴─────────────────────────────────────────────────┘

#### Why uniform 677 nH (instead of a true 647 / 715 / 647 Chebyshev)

The original Chebyshev design used T50-6 cores with L = 647 nH on
the outer positions and 715 nH at the center — the asymmetric
values come from the per-position Chebyshev coefficients
(g₂ = g₆ ≈ 1.423, g₄ ≈ 1.573).

On T68-6 (AL ≈ 4.7 nH/t², Micrometals #6 material, L₁₀₀ = 47 µH),
the closest integer turn count for either target lands at 12 turns
= 677 nH:

- 11 turns = 569 nH (12 % low vs 647 nH target)
- 12 turns = 677 nH ( 5 % high vs 647 nH, 5 % low vs 715 nH)
- 13 turns = 794 nH (23 % high vs 647 nH, 11 % high vs 715 nH)

Twelve turns at every position is the practical choice. Three
identical windings are far easier to wind, count, and pack
uniformly around the core than mixing 11 t and 12 t, and 12 t is
within 5 % of both target values — closer to the average target
than any mixed scheme.

#### Why the caps are NOT retuned to compensate

The combined "all 677 nH + original caps" choice means the filter
is no longer a strict 7-pole 0.1 dB Chebyshev. It becomes an
equivalent 7-element LC ladder with a slight passband-ripple
change and a cutoff shifted from 17.5 MHz down to ~17.3 MHz — a
~1 % shift, essentially in the noise.

For this application that's invisible:

- **14.2 MHz operating frequency** sits at 82 % of the shifted
  cutoff — well in the passband; insertion loss < 0.3 dB
- **2nd harmonic at 28.4 MHz** is still 1.64× the cutoff regardless
  of which exact tuning is used; stopband suppression here is
  governed by the ladder structure, not the exact Chebyshev shape
  (28+ dB rejection holds)
- **MC1496 carrier input** doesn't care about an extra 0.1 dB
  ripple in the passband — its dynamic range absorbs it trivially

Alternatives considered and rejected:

- **Retune caps to 200 / 390 pF** (E12 values): the ~200 kHz
  cutoff shift is not worth the schematic churn
- **Redesign as true Chebyshev for 677 nH inductors**: would
  require recomputing all cap values from the Chebyshev coefficients
  (not a simple scale) and gives no practical benefit
- **Stick with T50-6 + original values**: gives exact original
  filter but requires winding 13/14/13 turns on the smaller, less
  finger-friendly core
- **11 / 12 / 11 turns on T68-6** (mimic the original asymmetry):
  gives 569 / 677 / 569 nH — closer to the g-coefficient pattern
  but ~12 % low on the outer positions; uniform 12 t is simpler
  and closer to the average target inductance

The trade is **constructional uniformity over the last ounce of
filter spec**. For a single-band VFO chain feeding a keyer, the
simpler build wins clearly.

### Output coupling and termination

┌─────┬─────────┬─────────────────────────────────────┐
│ Ref │ Value   │ Role                                │
├─────┼─────────┼─────────────────────────────────────┤
│ RT  │ 50 Ω    │ LPF output termination              │
│ CC1 │ 10 nF   │ AC coupling to buffer / MC1496      │
│ RGL │ 1 MΩ    │ Grid-leak return at MC1496 input    │
└─────┴─────────┴─────────────────────────────────────┘

### Optional J310 source follower

┌─────┬─────────┬──────────────────────────────────────┐
│ Ref │ Value   │ Role                                 │
├─────┼─────────┼──────────────────────────────────────┤
│ T1  │ J310    │ N-channel JFET, source follower      │
│ RS1 │ 270 Ω   │ Source resistor; sets gain ≈ 0.5     │
│ V+  │ +12 V   │ Drain supply (regulated)             │
└─────┴─────────┴──────────────────────────────────────┘

## Source of truth

The current QUCS schematic for this stage is
`xmitter_prj/vfo_subcircuit.sch`. Any time the component values
or topology differ between this doc and the schematic, the schematic
wins — update this doc to match.

The PA validation session 2026-06-08 (see
`2026-06-08-pa-validation.md`) drove the current pi-pad and LPF
values; the changes from earlier 6 dB pad + 5-pole LPF are documented
there.

## Simulation vs hardware

The QUCS simulation models the Si5351 with a Vrect pulse source
(V2 = 3.3 V, 33.275 ns rise/fall). The slow rise/fall in the
simulation produces a near-sinusoidal waveform with most energy in
the fundamental.

The real Si5351 produces a fast-edged CMOS square wave with
significant harmonic content. The LPF rejects these harmonics by
60+ dB beyond cutoff, but the fundamental amplitude entering the
pi pad is ~25 % higher than the simulation suggests:

┌─────────────────────────────────────┬──────────────┬───────────────────┐
│ Stage                               │ Simulation   │ Hardware (est.)   │
├─────────────────────────────────────┼──────────────┼───────────────────┤
│ Source fundamental (peak)           │ ~1.65 V      │ ~2.10 V           │
│ After 50 Ω source into 50 Ω pad     │ ~825 mV      │ ~1.05 V           │
│ After 20 dB pi pad                  │ ~83 mV       │ ~105 mV           │
│ At J310 output (gain ≈ 0.5)         │ ~43 mV       │ ~55 mV            │
│ Target at MC1496 RF in (peak)       │ 38 mV        │ 38 mV             │
└─────────────────────────────────────┴──────────────┴───────────────────┘

Implication: the MC1496 will still operate in linear 4-quadrant mode
at ~55 mV peak (the switching-mode threshold is around 150 mV peak),
but at the high end of "linear." Open question Q3 below covers
whether to bump the pi pad.

## Open design questions

### Q1 — J310 source follower: keep or remove?

Arguments to keep:
- Provides defined ~50 Ω output impedance independent of LPF
  termination state
- Isolates the MC1496 input loading from the LPF (preserves filter
  shape under variable MC1496 input impedance)
- Documented and simulated in `vfo_subcircuit.sch`

Arguments to remove:
- Si5351 output is already low impedance, so the LPF source is
  well defined
- LPF output is terminated by RT = 50 Ω, presenting 50 Ω to the
  MC1496 regardless of buffer presence
- One fewer active component on the board
- The MC1496 input impedance at pin 8 (carrier) is dominated by
  the input bias network (R5/R6/R8 in `keyer.sch`); buffer
  isolation may not be necessary

**Recommendation pending bench measurement**: include the J310
footprint on the PCB with provision for a 0 Ω jumper bypass.
Build the board with the jumper installed (bypass mode), verify
level and spectral purity at the MC1496 input, then decide whether
to populate the J310.

### Q2 — Si5351 output drive strength

The Si5351A has four programmable output drive levels (2, 4, 6, 8 mA).
The simulation assumes ~8 mA equivalent.

┌──────────┬─────────────────────────────────────────────────────────┐
│ Drive    │ Tradeoff                                                │
├──────────┼─────────────────────────────────────────────────────────┤
│ 2 mA     │ Cleanest spectrum, lowest fundamental                   │
│ 4 mA     │ Good compromise; ~half the level of 8 mA                │
│ 6 mA     │ Intermediate                                            │
│ 8 mA     │ Cleanest square wave, highest fundamental — sim default │
└──────────┴─────────────────────────────────────────────────────────┘

**Recommendation**: start at 8 mA, evaluate spectral purity at the
MC1496 input, drop to 4 mA if harmonics are well-suppressed and
excess level needs trimming.

### Q3 — Pi pad value if Si5351 fundamental is too high

If hardware bring-up shows > 100 mV peak at the MC1496 RF input,
deepen the pi-pad attenuation. Options:

┌─────────────────────────────┬─────────┬─────────────────────────────┐
│ Change                      │ New atn │ Result                      │
├─────────────────────────────┼─────────┼─────────────────────────────┤
│ RP2: 240 → 470 Ω            │ ~26 dB  │ Drops MC1496 input by ~6 dB │
│ Re-derive symmetric 25 dB   │ 25 dB   │ New RP1/RP3, new RP2        │
│ Re-derive symmetric 30 dB   │ 30 dB   │ New RP1/RP3, new RP2        │
│ Add a fixed pad downstream  │ +N dB   │ Independent of LPF section  │
└─────────────────────────────┴─────────┴─────────────────────────────┘

Precompute pi-pad values for 25, 30, and 35 dB symmetric versions
and include in the "if needed" parts list so bench trim is one
resistor swap.

### Q4 — Termination of unused Si5351 outputs

The Si5351A has three independent clock outputs. Only CLK0 is used
for the VFO carrier. CLK1 and CLK2 should be either programmed to
a disabled / high-Z state, or pulled to ground via 100 Ω resistors
to avoid radiating unintended frequencies. Firmware decision; verify
during bring-up.

## What is NOT in this stage

For clarity about scope boundaries:
- The MC1496 itself, its biasing, and the envelope DAC are part of
  the keyer stage (see `cw_envelope_keyer.md` and `keyer.sch`)
- The LM7171 differential post-amps live downstream of the MC1496,
  not in the VFO input chain
- The 12HG7 push-pull driver is on the driver board, not the
  control board
- The Si5351 control firmware (frequency programming, drive
  selection, output enable) is part of the MCU firmware scope
  (see `firmware/` when scaffolded)

## Related docs and files

- `xmitter_prj/vfo_subcircuit.sch` — the current QUCS simulation
- `Documentation/2026-06-08-pa-validation.md` — design history that
  arrived at the current pi pad and LPF values
- `Documentation/cw_envelope_keyer.md` — the MC1496 / envelope DAC
  stage that this VFO chain feeds
- `Documentation/control_board_BOM_and_wire_plan.md` — sourcing for
  the components listed here

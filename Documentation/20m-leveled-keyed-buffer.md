# 20 m Leveled, Keyed Buffer / Driver — Design Spec

CW transmitter buffer and keying stage for a vacuum-tube push-pull final.
Takes the Si5351A square-wave reference, conditions it to a clean sine
(resistive pad + 5-pole Chebyshev low-pass filter), and delivers a
digitally-leveled, envelope-shaped, antiphase grid drive.

## Scope and constraints

- **Band:** 20 m only, 14.000–14.350 MHz (tank center 14.175 MHz).
- **Controlled output:** 0.3–5 V peak RF *per grid*, set digitally over I²C.
- **Keying:** done at DC on the control line — never on the RF. ~5 ms
  rise/fall envelope for click suppression.
- **Parts policy:** through-hole semiconductors only. Small breakout boards
  (Si5351, MCP4725) are allowed. No surface-mount discrete parts.
- **Supply:** +12 V regulated for the buffer/driver and control circuitry.
  (Tube HV / bias supplies are out of scope for this stage.)

## Signal chain

```
Si5351A CLK0 (square, 8 mA) --> 6 dB Pi pad --> 5-pole Chebyshev LPF (50Ω) --> 50Ω term (RT)
   --0.01u--> Q1 J310 follower --0.01u--> Q2 dual-gate VGA --> tuned tank (14.175 MHz)
                                                                       |
                                                                  T1 secondary (CT)
                                                                   /          \
                                                              grid V1      grid V2  (push-pull)
                                                                   \
                                                              detector --> A1 error amp --> Q2 G2
                                                                              ^
                                                              MCP4725 DAC --> RC shaper (key)
```

Both ends of the filter are resistive terminations *we* set (pad output ≈ 50 Ω,
RT = 50 Ω load), so the filter response is independent of the Si5351's
ill-defined CMOS output impedance. See the conditioning stage below.

The tuned tank + push-pull split is the 20 m optimization: resonating the
interstage at 14.175 MHz rejects the 2nd/3rd harmonic 20–30 dB before the
grids, and push-pull cancels even harmonics, so the final sees a clean sine.

## Stage detail and values

### VFO output conditioning — pad + Chebyshev LPF + termination

The Si5351A CLK output is a CMOS switch, not a clean resistive source: its
effective output impedance is nonlinear and roughly 50–85 Ω depending on
drive-strength setting, level, and frequency. A passive LC filter's ripple,
cutoff, and stopband all depend on known terminations, so we **define both
ends with resistors** and stop relying on the chip.

**Pad — 6 dB Pi attenuator, 50 Ω** (swamps the chip impedance):

| Ref | Value | Position |
|-----|-------|----------|
| RP1 | 150 Ω | shunt, input side |
| RP2 | 39 Ω | series |
| RP3 | 150 Ω | shunt, output side |

- Set the Si5351 to **8 mA** drive strength to feed the pad.
- Pad output impedance stays within a few ohms of 50 Ω across the chip's
  50–85 Ω range → source return loss ≥ ~23 dB at the filter input (the pad's
  12 dB round-trip isolation buries the chip's mismatch).
- Drop to a 3 dB pad if more signal level is wanted (≈6 dB less isolation).

**5-pole Chebyshev LPF** — 0.1 dB ripple, n = 5, doubly-terminated 50 Ω,
shunt-input (C-L-C-L-C), ripple cutoff fc = 17.5 MHz:

| Element | Ideal | Practical realization |
|---------|-------|-----------------------|
| CF1 (shunt) | 209 pF | 200 pF C0G/silver mica (+~10 pF trim if sweeping) |
| LF2 (series) | 624 nH | 13 t on T50-6 (~676 nH); spread turns to trim down |
| CF3 (shunt) | 359 pF | 360 pF (or 330 + 27 pF) |
| LF4 (series) | 624 nH | 13 t on T50-6, as LF2 |
| CF5 (shunt) | 209 pF | 200 pF, as CF1 |

- Prototype g-values (0.1 dB, n=5): g1..g5 = 1.1468, 1.3712, 1.9750, 1.3712,
  1.1468; equal 50 Ω source/load (odd order).
- Denormalization: shunt C = g/(Z0·ωc), series L = g·Z0/ωc, Z0 = 50 Ω,
  ωc = 2π·17.5 MHz.
- 14.35 MHz band edge sits inside the ripple band → passband flat within
  0.1 dB across 14.0–14.35 MHz.
- Stopband: ~44 dB at 3rd harmonic (42 MHz), ~67 dB at 5th (70 MHz). This is
  *before* the buffer tank and PA tank add more.
- 0.1 dB ripple chosen for flat passband (consistent drive across band); use
  0.5 dB only if a steeper skirt is ever needed (it isn't, here).

**Termination + tap:**

- **RT = 50 Ω** from filter output to ground — this resistor *is* the filter's
  load termination.
- Q1's gate taps across RT through its 0.01 µF coupling cap; Q1's 1 MΩ
  gate-leak sits in parallel with RT and is electrically invisible.

**Level note:** the pad plus the doubly-terminated filter leave only a few
hundred mV pp of sine at Q1. This is fine — the Q2 VGA (~35 dB) and the
leveling loop recover it to the commanded 0.3–5 V/grid.

**Higher-impedance option:** scaling the pad/filter/RT to 100–200 Ω is gentler
on the chip and preserves more signal, at the cost of needing matching pads to
verify on 50 Ω test gear. 50 Ω chosen here for direct NanoVNA verification.

### Q1 — J310 source follower (input buffer)

| Node | Component |
|------|-----------|
| Gate input coupling | 0.01 µF, tapped across the 50 Ω filter termination RT |
| Gate-leak | 1 MΩ gate to ground (in parallel with RT — electrically invisible) |
| Drain | direct to +12 V, decoupled 0.01 µF to ground |
| Source | 270 Ω to ground; output tapped at source through 0.01 µF |

Purpose: read the filter output voltage without loading it. RT (50 Ω) sets the
filter's load impedance; Q1's high-Z gate taps across it. Provides a
low-impedance drive to Q2.

### Q2 — dual-gate MOSFET VGA (gain control element)

Device: BF961, 3N211, or 40673 (dual-gate MOSFET).

| Node | Component |
|------|-----------|
| G1 (signal) | 0.01 µF coupling in, 100 kΩ to ground |
| Source | 270 Ω to ground, bypassed 0.01 µF |
| Drain | into tuned tank (see below) |
| G2 (control) | from A1 output via 10 kΩ series, 0.01 µF RF bypass to ground |

G2 sweep of ~0 V → +4 V gives ~35 dB gain range. G2 is the loop's actuator.

**Substitute if dual-gate MOSFETs are hard to source:** cascode of two J310s
(lower JFET gate = signal, upper JFET gate = control). Behaves identically.

### Tuned tank (drain load) — 20 m

- **L1:** ~1.9 µH = 22 turns on a T50-6 toroid.
- **C1:** 60 pF trimmer (parallel with L1) → resonate at 14.175 MHz.
- **DC feed:** +12 V fed to the cold end of L1, bypassed 0.01 µF to ground.
  The inductor doubles as the DC feed — **no separate RF choke**. (A 1 mH
  molded choke is past self-resonance at 14 MHz and must not be used here.)

### T1 — interstage transformer / push-pull splitter

- **Secondary:** 2 × 10 turns, center-tapped, wound over L1 on the same
  T50-6 core.
- **Center tap:** returns through 22 kΩ grid-leak resistor (bypassed 0.01 µF)
  to ground → develops class-C self-bias from grid current, fed to both grids
  through the winding.
- **Ends:** to the two push-pull grids (V1, V2), 180° out of phase.

> **Fixed-bias finals:** return the center tap to the negative bias supply
> instead of through the 22 kΩ grid-leak.

> **Need more than 5 V/grid:** add secondary turns. The loop still holds to
> the DAC setpoint up to the drive headroom the +12 V rail allows (~8–10 V
> peak at the drain before clipping). Confirm headroom against the actual
> tube/class before committing turns.

### Leveling loop — makes "0.3–5 V" a real, stable number

| Block | Detail |
|-------|--------|
| Detector | 1N5711 Schottky; sample one grid through 1000 pF; peak-detect into smoothing cap |
| Detector bias | 330 kΩ trickle bias from +12 V keeps the diode linear at 0.3 V |
| Error amp A1 | TL071 as integrator (1 µF / 100 kΩ network) for zero steady-state error |
| A1 inputs | inverting = detected level; non-inverting = DAC setpoint |
| A1 output | drives Q2 G2 |

Loop forces detected grid drive = setpoint, so per-grid peak RF tracks the
command across temperature, device spread, and across the band. Because it
servos to the actual grid voltage, the exact T1 turns ratio is non-critical.

**Stability constraint:** loop bandwidth (a few kHz) must sit comfortably
above the 5 ms keying envelope so the loop tracks the ramp faithfully. It
does, with margin — preserve this if values are retuned.

### Digital control + keying

- **DAC:** MCP4725 (I²C breakout) on the same I²C bus as the Si5351 (second
  address). Scale Vref or the detector divider so full code = 5 V/grid, low
  code = 0.3 V/grid. Store one calibration pass in the MCU for volts-accurate
  drive.
- **Keying:** the key gates the DAC setpoint through a 4.7 kΩ / 1 µF RC shaper
  (~5 ms rise/fall). The loop reproduces that soft envelope on the RF. The key
  switches only a low-voltage control line — no RF chirp, no HV at the key,
  click-free edges. The Si5351/VFO runs continuously (no chirp on keying).

## Bill of materials (this stage)

| Ref | Value / Part | Notes |
|-----|--------------|-------|
| RP1, RP3 | 150 Ω | 6 dB pad, shunt |
| RP2 | 39 Ω | 6 dB pad, series |
| CF1, CF5 | 200 pF C0G/silver mica | Chebyshev LPF shunt |
| CF3 | 360 pF C0G/silver mica | Chebyshev LPF shunt (or 330 + 27 pF) |
| LF2, LF4 | 13 t on T50-6 (~0.62 µH) | Chebyshev LPF series |
| RT | 50 Ω | filter load termination |
| Q1 | J310 | JFET, TO-92 |
| Q2 | BF961 / 3N211 / 40673 | dual-gate MOSFET (or 2× J310 cascode) |
| A1 | TL071 | op-amp, DIP-8 |
| D1 | 1N5711 | Schottky detector |
| DAC | MCP4725 breakout | I²C |
| L1 | 22 t on T50-6 | ~1.9 µH (buffer tank — distinct from LF2/LF4) |
| T1 sec | 2 × 10 t on same T50-6 | center-tapped |
| C1 | 60 pF trimmer | tank tuning (buffer — distinct from CF1) |
| — | 0.01 µF (×several) | coupling / bypass |
| — | 1000 pF | detector coupling |
| — | 1 µF | shaper + loop integrator |
| — | 1 MΩ | Q1 gate-leak |
| — | 100 kΩ (×2) | Q2 G1 to gnd; loop integrator |
| — | 22 kΩ | grid-leak (class-C bias) |
| — | 10 kΩ | G2 series |
| — | 4.7 kΩ | keying shaper |
| — | 330 kΩ | detector trickle bias |
| — | 270 Ω (×2) | Q1, Q2 source |

## Alignment procedure

1. **Filter (bench, before integration):** terminate the pad input in 50 Ω,
   sweep the LPF on a 50 Ω VNA. Verify ripple cutoff ~17.5 MHz, passband flat
   within 0.1 dB across 14.0–14.35 MHz, and ≥40 dB down at 42 MHz. Trim
   CF1/CF3/CF5 or LF2/LF4 turn spacing to hit it.
2. Set the DAC to mid-range with a steady key-down.
3. Peak C1 for maximum detector DC at 14.175 MHz.
4. Sweep the Si5351 across 14.000–14.350 MHz; confirm the leveled output
   holds flat (a single-band tank barely moves across 350 kHz).
5. Verify key-up drops RF to zero and that the envelope rise/fall is ~5 ms.

## Layout notes (14 MHz)

- Keep RF leads short; use a ground plane / ground pour.
- Keep the I²C and MCU wiring physically separated from the RF tank and
  detector to keep digital hash out of the loop.
- Bypass +12 V locally at each stage.

## Open items for the build

- [ ] Final tube type and operating class → sets T1 secondary turns ratio and
      confirms drive headroom.
- [ ] Confirm grid-leak vs fixed-bias scheme for the chosen final.
- [ ] Choose MCP4725 Vref / detector scaling for exact 0.3–5 V mapping;
      capture calibration constants in MCU firmware.

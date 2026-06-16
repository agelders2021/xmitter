# 20 m Leveled, Keyed Buffer / Driver — Design Spec

CW transmitter buffer and keying stage for a vacuum-tube push-pull final.
Takes the Si5351A square-wave reference, conditions it to a clean sine
(resistive pad + 5-pole Chebyshev low-pass filter), and delivers a
digitally-leveled, envelope-shaped, antiphase grid drive.

## Scope and constraints

- **Band:** 20 m only, 14.000–14.350 MHz (broadband path, no tank to tune).
- **Controlled output:** 0.3–5 V peak RF *per grid*, set digitally over I²C.
- **Keying:** done at DC on the control line — never on the RF. ~5 ms
  rise/fall envelope for click suppression. MC1496 carrier null provides
  complete RF cutoff at key-up with no switching transients.
- **Parts policy:** through-hole semiconductors only. Small breakout boards
  (Si5351, MCP4725) are allowed. No surface-mount discrete parts.
- **Supply:** +12 V regulated for the buffer/driver and control circuitry.
  −8.2 V derived from the grid bias rail for the MC1496 and TL071.

## Signal chain

```
Si5351A CLK0 (square, 8 mA) --> 6 dB Pi pad --> 5-pole Chebyshev LPF (50Ω) --> 50Ω term (RT)
   --10nF--> Q1 J310 follower (Q1S) --10nF--> MC1496 carrier port (pin 6)
                                               |
                              MC1496 signal port (pin 4) <-- AGC divider (100k/5.1k) <-- A1 TL071
                                               |
                              RFC 100µH (VDD to T1CT) + T1 primary (10+10t FT37-43)
                                               |
                                        T1 secondary (10+10t, CT)
                                          /            \
                                     grid V1        grid V2  (push-pull, 180° apart)
                                          \
                                     detector (1N5711) --> A1 error amp --> MC1496 pin 4
                                                               ^
                                             MCP4725 DAC --> RC shaper (key)
```

The MC1496 replaces the tuned tank and the VGA. It is a Gilbert cell balanced
modulator used as a voltage-controlled attenuator. **At zero control differential
(key-up) the output is identically null**; no RF reaches the grids regardless of
carrier level. This eliminates the key-up leakage problem that a JFET cascode
with a tuned tank could not fully solve.

Removing the tuned tank also eliminates the alignment step of resonating the
tank at 14.175 MHz. T1 is now a broadband (FT37-43) transformer — flat across
14.0–14.35 MHz and beyond.

## Stage detail and values

### VFO output conditioning — pad + Chebyshev LPF + termination

The Si5351A CLK output is a CMOS switch, not a clean resistive source: its
effective output impedance is nonlinear and roughly 50–85 Ω depending on
drive-strength setting, level, and frequency. A passive LC filter's ripple,
cutoff, and stopband all depend on known terminations, so we **define both
ends with resistors** and stop relying on the chip.

**Pad — 20 dB Pi attenuator, 50 Ω** (swamps the chip impedance and brings
the carrier level into the modulator's linear-mode range):

| Ref | Value | Position |
|-----|-------|----------|
| RP1 | 61.9 Ω (E96) or 62 Ω (E24) | shunt, input side |
| RP2 | 249 Ω (E96) or 240 Ω (E24) | series |
| RP3 | 61.9 Ω (E96) or 62 Ω (E24) | shunt, output side |

- Set the Si5351 to **8 mA** drive strength to feed the pad.
- Pad output impedance stays within a few ohms of 50 Ω across the chip's
  50–85 Ω range → source return loss ≥ ~23 dB at the filter input.
- 20 dB (vs. the original 6 dB) puts V_RF_IN to the keyer at ~38 mV peak
  instead of ~380 mV; combined with C1 = 330 pF in keyer.sch, V_pin10
  sits at ~23 mV peak — squarely in the MC1496's linear-multiplier
  range, where harmonic content of the carrier translates directly
  to spurs at the modulator output (so a clean carrier matters).
- After bring-up, an additional discrete pad can be inserted downstream
  to fine-tune the carrier level if measured output differs from sim.

**7-pole Chebyshev LPF** — 0.1 dB ripple, n = 7, doubly-terminated 50 Ω,
shunt-input (C-L-C-L-C-L-C), ripple cutoff fc = 17.5 MHz. (Upgraded from
the original 5-pole specifically to push harmonic rejection deeper —
critical now that the modulator is operating linearly.)

| Element | Ideal | Practical realization |
|---------|-------|-----------------------|
| CF1 (shunt) | 215 pF | 220 pF C0G/silver mica |
| LF2 (series) | 647 nH | 13 t on T50-6 (~647 nH; same as the old LF2/LF4) |
| CF3 (shunt) | 381 pF | 390 pF (or 360 + 27 pF) |
| LF4 (series) | 715 nH | 14 t on T50-6 |
| CF5 (shunt) | 381 pF | 390 pF (same as CF3) |
| LF6 (series) | 647 nH | 13 t on T50-6 (same as LF2) |
| CF7 (shunt) | 215 pF | 220 pF (same as CF1) |

- 14.35 MHz band edge sits inside the ripple band → passband flat within
  0.1 dB across 14.0–14.35 MHz.
- Stopband: **~28 dB at 2f (28 MHz), ~60 dB at 3f (42 MHz), ~88 dB at
  5f (70 MHz)** — gains ~15 dB / ~27 dB / ~37 dB respectively vs. the
  original 5-pole.
- Two extra parts vs. 5-pole: one cap (CF7 vs. CF5 split) and one
  inductor (LF6). 9-pole gives another ~15 dB at each harmonic for the
  cost of another L+C pair, but 7-pole already pushes the worst harmonic
  spur (3rd) well below −60 dBc when combined with the upstream pad.

**Termination + tap:**

- **RT = 50 Ω** from filter output to ground — this resistor *is* the filter's
  load termination.
- Q1's gate taps across RT through its 10 nF coupling cap.

### Q1 — J310 source follower (input buffer)

| Node | Component |
|------|-----------|
| Gate input coupling | 10 nF, tapped across the 50 Ω filter termination RT |
| Gate-leak | 1 MΩ gate to ground (in parallel with RT — electrically invisible) |
| Drain | direct to +12 V, decoupled 10 nF to ground |
| Source | 270 Ω to ground; output (Q1S) tapped at source through 10 nF |

Purpose: read the filter output voltage without loading it. RT sets the
filter's load impedance; Q1's high-Z gate taps across it. Provides a
low-impedance drive (Q1S ≈ 378 mV peak) to the MC1496 carrier port.

### −8.2 V supply — derived from grid bias rail

The MC1496 requires a negative supply. The 12BY7A grid bias rail (−60 V to
−80 V nominal) is used as the source.

| Component | Value | Purpose |
|-----------|-------|---------|
| R_DROP | 15 kΩ, 1 W | Dropping resistor from bias rail to zener |
| DZ1 | 1N4738A | 8.2 V zener, cathode to GND, anode = −8.2 V rail |
| C_Z1 | 10 µF electrolytic | Bypass, −8.2 V to GND |
| C_Z2 | 100 nF ceramic | High-frequency bypass, −8.2 V to GND |

- Current: ≈ 4 mA at −70 V bias rail; 3.5 mA at −60 V, 4.8 mA at −80 V.
- Total dissipation in R_DROP: ≤ 300 mW at −80 V (within 1 W rating).
- VEE = −8.2 V is shared by the MC1496 (pin 7) and the TL071 V− supply.

### MC1496 — Gilbert cell VCA (voltage-controlled attenuator)

Device: MC1496 or LM1496, DIP-14. **Verify pin assignments against the ON
Semiconductor MC1496 datasheet before layout.**

**Function:** 4-quadrant analog multiplier. Carrier × control → output.
Output is identically zero when the control differential is zero. This is the
key-up null mechanism — no RF hardware switching required.

| MC1496 Port | Connected to | Notes |
|-------------|--------------|-------|
| Carrier + (pin 6) | Q1S via 10 nF | RF input |
| Carrier − (pin 8) | GND via 100 nF | Bypass; keep lead short |
| Signal + (pin 1) | 10 kΩ to GND | Fixed reference; null at 0 V diff |
| Signal − (pin 4) | AGC divider output | Receives scaled V_AGC |
| Bias (pin 2) | 1 kΩ to VEE | Quiescent bias |
| Gain set (pin 5) | 1 kΩ (RE_ext) to VEE | Sets Iee ≈ 1 mA |
| Output + (pin 10) | T1 primary half B | Open-collector; RFC feeds CT |
| Output − (pin 12) | T1 primary half A | Open-collector |
| V+ (pin 13) | VDD (+12 V) | |
| V− (pin 7) | VEE (−8.2 V) | |

**AGC scaling — TL071 output → MC1496 signal port:**

The TL071 output (V_AGC, 0–10 V range on +12/−8.2 V supply) is divided:

```
V_AGC → R_SCALE1 (100 kΩ) → sig_n node → R_SCALE2 (5.1 kΩ) → GND
```

Ratio = 5.1/(100 + 5.1) = 4.853 %. At V_AGC = 10 V → sig_n = 485 mV.

MC1496 linear control range: ±100 mV differential. The AGC loop will operate
with V_AGC in the 0–2 V range (where differential < 100 mV) for proportional
control. Above 2 V the MC1496 saturates at maximum output; the AGC loop
settles below saturation automatically.

**Control law:**

- Key-up: V_CMD = 0 → V_AGC → 0 → signal differential = 0 → **carrier null**
- Key-down: V_CMD = setpoint → loop raises V_AGC → positive differential →
  MC1496 output proportional to carrier (loop settles at commanded level)

**Simulation result (mc1496_buffer_test.sp, ngspice):**

| Condition | OUT_P peak-to-peak | Notes |
|-----------|-------------------|-------|
| V_AGC = 0 V (key-up) | 0.000 V | Perfect null |
| V_AGC = 10 V (key-down) | 3.64 V | With 3.9 kΩ resistive load, Iee = 1 mA |

Through the 1:1 T1 transformer: each 12BY7A grid sees ≈ **1.82 V peak** with
RE_ext = 1 kΩ. To reach 3.6 V peak per grid, reduce RE_ext to 500 Ω (doubles
Iee to 2 mA). The AGC loop servo will hold any commanded level within the
available headroom.

### RFC — +12 V to T1 primary center tap

| Component | Value | Notes |
|-----------|-------|-------|
| L_RFC | 100 µH | Any standard through-hole molded RFC rated ≥ 10 mA DC |
| (Alternative) | 15 t on FT37-43 | ≈ 94 µH; use if SRF of molded RFC is a concern |

Connects from VDD (+12 V) to T1 primary center tap (T1CT). Push-pull RF
currents from pins 10 and 12 are anti-phase and **cancel at T1CT** — the RFC
carries only the DC bias current (Iee ≈ 1–2 mA). A standard molded RFC is
acceptable here despite its limited SRF because the net RF current through it
is the common-mode residual, not the push-pull signal. (Compare: a tank circuit
using an RFC as single-ended drain load WOULD saturate at 14 MHz — that
constraint does not apply to a center-tapped push-pull RFC.)

### T1 — broadband push-pull interstage transformer

**Core:** FT37-43 (Fair-Rite type 43 ferrite toroid, 9.5 mm OD).
Flat frequency response from < 1 MHz to > 50 MHz. No tuning.

**Winding:**

| Winding | Turns | Wire | Connection |
|---------|-------|------|------------|
| Primary half A (LP1) | 10 turns bifilar | #28 AWG enamelled | T1CT to MC1496 pin 12 |
| Primary half B (LP2) | 10 turns bifilar | #28 AWG enamelled | T1CT to MC1496 pin 10 |
| Secondary half A (LS1) | 10 turns bifilar | #28 AWG enamelled | T1CTS to grid 1 stopper |
| Secondary half B (LS2) | 10 turns bifilar | #28 AWG enamelled | T1CTS to grid 2 stopper |

Wind the full 20-turn primary as a single bifilar pair (two wires in parallel),
then wind the 20-turn secondary as a second bifilar pair over the primary.
Coupling k ≈ 0.98–0.99. Turns ratio 1:1 (push-pull each side).

**Secondary center tap (T1CTS):**

| Ref | Value | Purpose |
|-----|-------|---------|
| R_GL | 22 kΩ | Grid-leak resistor (T1CTS to GND) |
| C_GL | 10 nF NP0 | RF bypass across R_GL |

> For class-C fixed bias: return T1CTS to the negative bias supply instead
> of through R_GL to GND.

**Grid stoppers:**

| Ref | Value | From | To |
|-----|-------|------|----|
| RGS_A | 100 Ω | T1 secondary end A | 12BY7A grid 1 |
| RGS_B | 100 Ω | T1 secondary end B | 12BY7A grid 2 |

### Leveling loop — makes "0.3–5 V" a real, stable number

| Block | Detail |
|-------|--------|
| Detector | 1N5711 Schottky; sample one grid through 1000 pF; peak-detect into smoothing cap |
| Detector bias | 330 kΩ trickle bias from +12 V keeps the diode linear at 0.3 V |
| Error amp A1 | TL071 as integrator (1 µF / 470 kΩ anti-windup network) for zero steady-state error |
| A1 supplies | V+ = +12 V, V− = −8.2 V (shared with MC1496 VEE) |
| A1 inputs | inverting: V_DET via 100 kΩ; non-inverting: V_CMD (DAC setpoint) |
| A1 output | V_AGC, drives 100 kΩ / 5.1 kΩ divider to MC1496 signal port |

Loop forces detected grid drive = setpoint. The TL071 on a split ±12/−8.2 V
supply can swing from ≈ −6.2 V to ≈ +10.5 V, fully covering the V_AGC range
(0–2 V for proportional control). No headroom problem.

The MC1496 null at V_AGC = 0 means **loop windup is safe at key-up**: when
V_CMD = 0, V_AGC → 0 → output is zero regardless of how far V_AGC integrated.

### Digital control + keying

- **Level DAC:** MCP4725 (I²C breakout). Full code → maximum grid drive; zero
  code → V_CMD = 0 → MC1496 null → key-up silence.
- **Keying:** **superseded** — the analog 4.7 kΩ / 1 µF RC shaper has been
  replaced by a firmware envelope generator on a dedicated MCP4921 SPI DAC.
  The MCU produces a raised-cosine envelope (predistortion-linearized) and
  drives MC1496 pin 1 through a single-pole reconstruction LPF (R_F = 1.5 kΩ,
  C_F = 680 nF). See `cw_envelope_keyer.md` for the full design — firmware
  module, LPF/level-scaler values, timing, fail-safe requirements.
- The key contact still switches only a low-voltage control line — no RF, no
  HV at the key. The Si5351/VFO runs continuously.

### Reduced carrier injection + post-keyer voltage amplifier

Carrier amplitude reduction is now done **upstream** in the VFO subcircuit
(20 dB Pi pad + 7-pole LPF — see the VFO section above) rather than at the
keyer's C1 coupling cap. C1 stays at the original 330 pF (its job is
coupling, not attenuation), and the carrier arrives at pin 10 at ~32 mV
peak — squarely in linear-multiplier territory for the MC1496.

The lower carrier drops modulator gain to ~55 % of its old switching-mode
value, so the keyer's differential output sits at ~1.4 V p-p instead of
the previous 2.5 V p-p. An **LM7171 voltage amp (one per differential
side, gain ≈ 5.8)** restores the 8 V p-p drive the 12HG7 driver was sized
for.

| Per-channel component | Value | Role |
|-----------------------|-------|------|
| LM7171AIN/AIM | — | High-speed op-amp (200 MHz GBW), DIP-8 or SOIC-8 |
| C_IN | 100 nF X7R | AC-couple from MC1496 OUT (+10 V DC) to op-amp input |
| C_OUT | 100 nF X7R | AC-couple to 12HG7 grounded-grid cathode input |
| R_B | 100 kΩ 1% | Holds + input at 0 V (op-amp bias reference) |
| R_F | 47 kΩ 1% | Feedback (gain = 1 + R_F/R_G = 5.8) |
| R_G | 10 kΩ 1% | Inverting-input leg to GND |

Shared supply bypass: 2× 10 µF aluminum electrolytic + 2× 100 nF ceramic
(one of each across +12 V→GND and −8.3 V→GND), within ~10 mm of the IC
supply pins.

**Why LM7171:** TL072 (used elsewhere for the AGC integrator) has only
3 MHz GBW — well below the 14 MHz carrier. LM7171 has 200 MHz GBW; at
gain 5.8 it still has ~34 MHz BW, flat through the carrier band. Both ICs
run from the existing +12 V / −8.3 V rails (20.3 V total, inside the
LM7171's ±18 V abs max).

**Tuning the trade-off after hardware bring-up:** if the measured carrier
amplitude needs trimming up or down, the right knob is the **Pi pad
attenuation** in the VFO chain (or an inserted discrete pad downstream),
not C1. If lowering the carrier further also drops the keyer output too
low, raise R_F to compensate. Practical limit with LM7171 is R_F ≈ 60 kΩ
(gain ~7, BW ~28 MHz); beyond that, swap to a faster op-amp (AD8055,
LMH6610, AD8009 — all 300+ MHz GBW).

| Pad atten. | V_RF_IN to keyer | V_pin10 (C1=330pF) | Keyer out p-p | R_F for 8 V p-p drive | LM7171 BW |
|------------|------------------|---------------------|---------------|------------------------|-----------|
| 6 dB (original) | ~380 mV peak | ~100 mV peak | 2.5 V | 30 kΩ (G=4) | 50 MHz ✓ |
| **20 dB** | **~38 mV peak** | **~32 mV peak** | **~1.4 V** | **47 kΩ (G=5.8)** | **34 MHz ✓ — designed** |
| 26 dB | ~19 mV peak | ~16 mV peak | ~0.7 V | 110 kΩ (G=12) | 17 MHz — switch to AD8055 |
| 14 dB | ~76 mV peak | ~63 mV peak | ~1.7 V | 38 kΩ (G=4.7) | 42 MHz ✓ |

V_pin10 and keyer output depend on the actual J310 follower output and
MC1496 model behavior; verify in sim by probing the keyer's Pr1
(carrier-port differential) and Pr2 (output differential).

## Simulation files

| File | Purpose |
|------|---------|
| `xmitter_prj/mc1496.lib` | ngspice behavioral subcircuit for MC1496 Gilbert cell |
| `xmitter_prj/mc1496_buffer_test.sp` | Standalone ngspice test; run with `ngspice -b mc1496_buffer_test.sp` |
| `xmitter_prj/keyer.sch` | QUCS-S schematic — MC1496 with PNP digital null + envelope drive |

## Bill of materials (this stage only — LPF and Q1 included)

| Ref | Value / Part | Notes |
|-----|--------------|-------|
| RP1, RP3 | 61.9 Ω 1% (or 62 Ω E24) | 20 dB pad, shunt |
| RP2 | 249 Ω 1% (or 240 Ω E24) | 20 dB pad, series |
| CF1, CF7 | 220 pF C0G/silver mica | 7-pole Chebyshev LPF shunt (outer) |
| CF3, CF5 | 390 pF C0G/silver mica | 7-pole Chebyshev LPF shunt (inner, or 360 + 27 pF) |
| LF2, LF6 | 13 t on T50-6 (~647 nH) | 7-pole Chebyshev LPF series (outer) |
| LF4 | 14 t on T50-6 (~715 nH) | 7-pole Chebyshev LPF series (center) |
| RT | 50 Ω | Filter load termination |
| Q1 | J310 | JFET source follower, TO-92 |
| DZ1 | 1N4738A | 8.2 V zener, −8.2 V supply |
| R_DROP | 15 kΩ, 1 W | −8.2 V supply dropping resistor (from grid bias rail) |
| U1 | MC1496 or LM1496 | VCA, DIP-14 |
| L_RFC | 100 µH, molded | Push-pull RFC, VDD to T1CT |
| T1 | FT37-43, 10+10 / 10+10 t | Broadband push-pull interstage transformer |
| A1 | TL071 | Integrator / error amp, DIP-8 |
| D1 | 1N5711 | Schottky detector diode |
| DAC | MCP4725 breakout | I²C DAC for setpoint |
| R_GL | 22 kΩ | T1CTS grid-leak (or return to fixed bias supply) |
| RGS_A, RGS_B | 100 Ω | Grid stoppers |
| R_SCALE1 | 100 kΩ | AGC divider upper leg |
| R_SCALE2 | 5.1 kΩ | AGC divider lower leg (4.85%) |
| R_SIG_P | 10 kΩ | MC1496 signal port + reference to GND |
| R_BIAS | 1 kΩ | MC1496 bias pin to VEE |
| R_RE | 1 kΩ (or 500 Ω) | MC1496 RE_ext gain set (1 kΩ → 1 mA, 500 Ω → 2 mA) |
| R_INT | 100 kΩ | A1 inverting input resistor |
| R_FB | 470 kΩ | A1 anti-windup / DC gain |
| C_INT | 1 µF film | A1 integrator cap |
| C_DET | 10 nF film | Detector smoothing |
| C_DET_IN | 1000 pF NP0 | Detector coupling from grid |
| C_GL | 10 nF NP0 | T1CTS bypass |
| C_Z1 | 10 µF electrolytic | −8.2 V bypass |
| C_Z2 | 100 nF ceramic | −8.2 V HF bypass |
| — | 10 nF NP0 (×several) | VDD bypass, coupling, RF bypass |
| — | 100 nF ceramic (×2) | MC1496 carrier port bypass, VEE bypass |
| U2, U3 | LM7171AIN (×2) | Post-keyer voltage amp, one per differential side |
| R_F (×2) | 47 kΩ 1% | Op-amp feedback (gain = 5.8) |
| R_G (×2) | 10 kΩ 1% | Op-amp inverting-input leg to GND |
| R_B (×2) | 100 kΩ 1% | Op-amp + input bias to GND |
| C_IN, C_OUT (×4) | 100 nF X7R | LM7171 AC coupling (in and out, per channel) |
| — | 10 µF aluminum (×2), 100 nF ceramic (×2) | LM7171 supply bypass (+12 V, −8.3 V) |

## Alignment procedure

1. **Filter (bench, before integration):** terminate the pad input in 50 Ω,
   sweep the LPF on a 50 Ω VNA. Verify ripple cutoff ~17.5 MHz, passband flat
   within 0.1 dB across 14.0–14.35 MHz, and ≥40 dB down at 42 MHz. Trim
   CF1/CF3/CF5 or LF2/LF4 turn spacing to hit it.
2. Apply +12 V and verify −8.2 V at the zener output.
3. Set V_CMD to mid-range with key-down. Verify A1 output is within 0–10 V.
4. Monitor a grid via an oscilloscope and confirm RF is present; adjust V_CMD
   and confirm output scales correctly.
5. Key-up: verify RF drops to zero (MC1496 null). No tank adjustment needed.
6. Sweep Si5351 across 14.000–14.350 MHz; confirm output stays flat (no tank
   to mistrack; T1 is broadband).

## Layout notes (14 MHz)

- Keep RF leads short; use a ground plane / ground pour.
- Place MC1496 decoupling caps (100 nF) within 10 mm of pins 7 and 13.
- Keep the I²C and MCU wiring physically separated from the RF path and
  detector to keep digital hash out of the loop.
- Place −8.2 V supply well away from the RF sections; route VEE trace with
  adequate bypass (10 µF + 100 nF) at the VEE bus.
- The T1 FT37-43 is small enough to mount directly on the board near the MC1496.

## Open items

- [ ] Confirm 12BY7A operating class → determines T1CTS bias scheme
      (grid-leak R_GL vs. return to fixed negative supply).
- [ ] Measure actual Q1 operating point (Q1S level) to verify 378 mV peak
      input to MC1496 carrier port.
- [ ] Choose RE_ext (1 kΩ or 500 Ω) based on measured output level vs. grid
      drive requirement after T1 is wound.
- [ ] MCP4725 Vref and detector divider scaling for exact 0.3–5 V/grid mapping.

---

## PA monitoring and control — design options (under consideration)

For per-tube grid bias control and per-tube grid/plate/screen current
monitoring on the push-pull 6146B PA. Options recorded here for future
decision — none committed to schematic yet. Output-power adjustment uses
the envelope DAC's `CODE_FULL` in firmware (see `cw_envelope_keyer.md`),
not bias.

### Grid current measurement (per tube)

Sense resistor in series with each grid leak, between R_GL and the bias
supply node. Voltage across R_sense × difference amp → ADC.

```
grid → R_GL (22 kΩ) → R_sense → bias supply (−V_bias)
                      │←  ΔV  →│
                            │
                  high-CMR difference amp → ADC
```

| R_sense | ΔV at 2 mA grid current | Notes |
|---------|--------------------------|-------|
| 100 Ω | 200 mV | Diff amp on the bias rail; needs ~−70 V CM tolerance |
| 1 kΩ | 2 V | Single-supply op-amp can sit on the bias rail directly; simpler but cable run to digital side is harder |

Difference amp candidates: **INA170** (±60 V CM), **LT1991 / AD629**
(±270 V CM, no external CM trim needed), or DIY OP07 + 1 % matched
resistor divider.

### Grid bias voltage control (per tube)

Per-tube DAC → high-voltage op-amp inverter → grid (via existing R_GL).

```
DAC out (0–5 V) ─ R_in ─┬─ (−)  OPA454  output ── R_GL (22 kΩ) → grid
                        │            │
                        R_F          ±100 V supply
                        │            │
                        └── output ──┘

V_out = − (R_F/R_in) × V_DAC + offset (from V_ref on + input)
```

| Stage | Part / value |
|-------|--------------|
| DAC (×2, one per tube) | MCP4725 I²C breakout |
| HV op-amp (×2) | OPA454 (±100 V, ±50 mA) — primary choice |
|  | OPA445 (±45 V) — workable if range stays > −40 V |
|  | Discrete level-shifter w/ KSP44 PNP (400 V) — cheaper alternative |
| HV supply | Small ±100 V dedicated, isolated DC-DC (e.g., Murata NMA0509 + voltage doubler), shared between channels |

**Safe-park behavior:** MCP4725 EEPROM startup value should map to the
*most negative* bias (deep cutoff = PA off) so the tubes are safe before
the MCU initializes. Pull-down on the DAC output to GND reinforces this.

**Range target:** −90 V (PA off / parked) to −40 V (shallow class, max
output). Scale R_F/R_in and the (+) input offset to suit.

### ADC protection (cathode current sense)

10 Ω cathode resistor can see hundreds of volts if it ever opens. Three
layers of defense:

```
cath. resistor top ── R_S (10 kΩ) ──┬── (+) opamp ── output ── ADC
                                    │   (+5 V / GND supply)
                              ┌─────┼─────┐
                             D1   C(100n) D2
                              │   │       │
                             GND GND    +3.3 V

D1, D2 = Schottky (BAT54 or 1N5817)
```

| Layer | Purpose |
|-------|---------|
| R_S = 10 kΩ series | Limits fault current; 600 V → 60 mA into clamp diodes (survivable briefly) |
| D1/D2 Schottky clamps | Shunt overvoltage to ±supply rails before reaching opamp |
| Op-amp buffer (low-V supply) | Output can only swing within its rails — ADC physically can't see > supply, no matter the input |

Op-amp choice: **OPA1641** (±20 V differential input protection) or
**LMC6041** (input protection diodes built in). Powered from the same
+5 V or +3.3 V the ADC uses.

**Optional 4th layer:** Bourns MF-R010 PTC fuse (100 mA hold) in series
ahead of R_S — opens on sustained fault, self-resets when fault clears.

**RF bypass on the cathode resistor** (planned addition): 0.01 µF NP0
ceramic directly across the 10 Ω, low-ESL, mounted right at the tube
socket. Tap the DC sense from the resistor top *before* the bypass cap on
the layout so RF can't reach the ADC chain.

### Output-power control

**No additional hardware.** The envelope MCP4921 DAC's `CODE_FULL`
calibration constant (in firmware) is the natural power-level knob —
12-bit DAC gives ~72 dB range, preserves envelope shape at every power
setting, and doesn't disturb PA bias / drive / loading. See
`cw_envelope_keyer.md` for details.

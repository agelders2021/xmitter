# xmitter Rev D sidetone: circuit and tuning notes

Date: 2026-11-15

Status: the circuit is in `analog.net` as of the 2026-11-15 20:01 export, and
the wiring there matches these notes. Two values and the footprints are still
open (section 10). Every number below comes from `sidetone_soft_hold.cir` run
in ngspice 42 with ideal comparators standing in for the U14 gates. None of it
has been measured on a board.

## 1. What the circuit does

GATE_2 is the only keying input. Three spare U14 (CD74HC4050E, 3.3 V) buffers
turn it into a soft-keyed tone:

1. **Key detect (pins 7 to 6).** R89 and R91 (100 kΩ each) put pin 7 at
   (GATE_2 + 5 V) / 2. R86 (1 MΩ) adds hysteresis. Pin 6 goes high when GATE_2 passes about -1.55 V and low
   again at about -1.83 V. RF turn-on is near -1.8 V.
2. **Envelope.** Pin 6 charges C67 (1 µF) through R93 (2.2 kΩ). This voltage
   sets the tone amplitude.
3. **Hold (pins 11 to 12).** Pin 6 charges C68 (100 nF) at once through D8;
   R94 (150 kΩ) discharges it. R95 (10 MΩ) adds hysteresis. Pin 12 stays high for about 9 ms after key-up so the
   tone keeps running while the envelope fades.
4. **Tone gate (pins 9 to 10).** A1 (free-running LEDC square wave, 3.3 V)
   reaches pin 9 through R84 (47 kΩ), and D10 holds pin 9 low unless pin 12 is
   high. So the tone passes to pin 10 only while pin 12 is high; otherwise
   pin 10 sits low.
5. **Chopper.** The audio node is fed from the envelope through R92 (22 kΩ).
   D11 pulls it low whenever pin 10 is low. When pin 10 is high the node rises
   to the envelope voltage. The result is a square wave whose height follows
   the envelope. C69 (1 nF) removes edge spikes.
6. **Level chain.** R90 (100 kΩ), C70 (10 nF), RV2, then U19 (LM386) at its
   gain of 20.
7. **Output.** C73 couples U19 pin 5 to the speaker on J4. R96 and C74 in
   series from pin 5 to ground are the Zobel network that keeps the LM386
   stable into an inductive load.

With the key up, pin 10 is static, so nothing reaches the audio node.

## 2. Parts

References are from the 20:01 export. The simulation netlist uses the same
names.

| Ref | Value | Role | Tuning parameter in the .cir |
|---|---|---|---|
| R89 | 100 kΩ | GATE_2 to pin 7 | |
| R91 | 100 kΩ | Pin 7 to +5 V | `rpu` |
| R86 | 1 MΩ | Pin 6 to pin 7, hysteresis | |
| R93 | 2.2 kΩ | Pin 6 to envelope node | `renv` |
| C67 | 1 µF film | Envelope node to GND | `cenv` |
| D8 | 1N5711 | Pin 6 to hold node, anode on pin 6 | |
| C68 | 100 nF | Hold node (pin 11) to GND | `chold` |
| R94 | 150 kΩ | Hold node (pin 11) to GND | `rhold` |
| R95 | 10 MΩ | Pin 12 to pin 11, hysteresis | |
| R84 | 47 kΩ | A1 to pin 9 | |
| D10 | 1N5711 | Pin 9 to pin 12, anode on pin 9 | |
| R92 | 22 kΩ | Envelope node to audio node | `rchop` |
| D11 | 1N5711 | Audio node to pin 10, anode on audio node | |
| C69 | 1 nF | Audio node to GND | `cx` |
| R90 | 100 kΩ | Audio node to C70 | `r90` |
| C70 | 10 nF | DC block | `c70` |
| RV2 | 10 kΩ, 25-turn | Level trimmer | `kpot` |
| C73 | 220 µF 35 V, intended | U19 pin 5 to J4 pin 1, positive on pin 5 | |
| R96 | 10 Ω | Zobel, from U19 pin 5 | |
| C74 | 47 nF, intended | Zobel, R96 to GND | |
| none yet | not fitted | Optional tone cap, top of RV2 to GND | `ctone` |

U14 pins 14 and 15 stay spare; pin 14 stays grounded. U202 switch 4 is not
used.

## 3. Baseline performance

700 Hz, RV2 at full rotation, U14 threshold 1.65 V.

| Quantity | Value |
|---|---|
| Sidetone on / off, at GATE_2 | -1.55 V / -1.83 V |
| LM386 input, fundamental | 122 mV peak |
| LM386 input, waveform peak | 127 mV (rating is ±400 mV) |
| Speaker, waveform peak | 2.7 V |
| Third / fifth harmonic | -9.6 dB / -14.2 dB |
| Rise, 10 to 90 % | 5.7 ms |
| Fall to 10 % / to 2 % | 4.4 ms / 6.9 ms |
| Hold after key-up | 9.2 ms |
| First cycle versus steady peak | 0.99 |
| Key up, after the hold ends | static (under 2 µV in the model) |

The same on and off points hold with the key-down level reduced to 40 % of DAC
full scale.

## 4. What to tune, in order of audible effect

### 4.1 Loudness: RV2, then R90

RV2 is the working control. R90 sets what full rotation means.

| R90 | LM386 input peak at full rotation | Speaker peak | Note |
|---|---|---|---|
| 220 kΩ | 55 mV | 1.2 V | Quiet |
| 100 kΩ | 127 mV | 2.7 V | Baseline |
| 47 kΩ | 279 mV | 5.3 V | Clips, and close to the input rating |

Do not go below about 68 kΩ.

### 4.2 Edge softness: C67, with R94

C67, the envelope capacitor, sets both edges. The hold must outlast the fade,
so change R94, the hold resistor, with it.

| C67 | R94 | Rise 10 to 90 % | Fall to 2 % | Hold |
|---|---|---|---|---|
| 0.47 µF | 100 kΩ | 3.6 ms | 4.8 ms | 6.1 ms |
| 1 µF | 150 kΩ | 5.7 ms | 6.9 ms | 9.2 ms |
| 2.2 µF | 330 kΩ | 11.0 ms | 14.0 ms | 20.3 ms |

The 0.47 µF rise time was simulated with R94 at 75 kΩ; R94 does not affect the
rise.

If the hold is too short the tone stops with a step. If it is too long, the
tone leaks faintly (about 53 dB down in the model) until the hold ends.

### 4.3 Brightness: optional capacitor across RV2

A capacitor from the top of RV2 to ground is the effective tone control.

| Cap across RV2 | Fundamental at LM386 input | Third | Fifth | Seventh |
|---|---|---|---|---|
| None | 122 mV | -9.6 dB | -14.2 dB | -17.5 dB |
| 10 nF | 115 mV | -12.2 dB | -19.7 dB | -25.3 dB |
| 22 nF | 97 mV | -15.4 dB | -24.0 dB | -30.1 dB |
| 47 nF | 64 mV | -17.8 dB | -26.8 dB | -32.9 dB |

22 nF is a reasonable first try for a rounder tone. This part is not in the
20:01 export; leave footprint space for it even if it starts unfitted.

### 4.4 Pitch: firmware

The fundamental at the LM386 input stays within 121 to 123 mV from 500 to
1000 Hz. The waveform peak varies more (140 mV at 500 Hz, 117 mV at 1000 Hz)
because C70 differentiates the square wave.

### 4.5 Smaller controls

| Part | Effect of changing it | Recommendation |
|---|---|---|
| C69 (1 nF) | Larger values mostly cost level: 4.7 nF gives 115 mV, 10 nF 99 mV, 22 nF 70 mV, with the third harmonic only 2 dB lower | Keep 1 nF; its job is removing edge spikes |
| C70 (10 nF) | 4.7 nF makes the waveform spikier (158 mV peak); 22 nF lengthens the fall to 2 % to 9.0 ms | Keep 10 nF |
| R92 (22 kΩ) | Sets the audio-node impedance and, with R90, the level | Keep |
| R86 (1 MΩ) and R95 (10 MΩ) | Hysteresis on the two slow edges | Keep |

## 5. Rules that must still hold after tuning

- **R91 equals R89.** Equal values put the on point at GATE_2 = -1.55 V
  and keep pin 7 between about +0.2 V and +5 V. A lower R91 raises the muted
  level at pin 7 toward the gate's threshold.
- **Hold outlasts the fade.** Rule of thumb from the table in 4.2: R94 of
  about 150 kΩ per microfarad of C67, with C68 at 100 nF.
- **LM386 input under ±400 mV at any RV2 position.** This is what limits R90.
- **R93 stays small against R92.** The chopper loads the envelope node; with
  R93 at 2.2 kΩ the keyed envelope sits near 3.1 V.

## 6. U14 threshold spread

The 0.94 V and 2.36 V rows are guaranteed limits interpolated from the
datasheet's 2 V and 4.5 V columns, so they are approximate and pessimistic.

| Threshold | Sidetone on at GATE_2 | Hold | Envelope left when the tone stops |
|---|---|---|---|
| 0.94 V | -3.05 V | 17.5 ms | 2 mV |
| 1.4 V | not run | 11.6 ms | 17 mV |
| 1.65 V | -1.55 V | 9.2 ms | 48 mV |
| 1.9 V | not run | 7.1 ms | 121 mV |
| 2.36 V | -0.06 V | 3.9 ms | 511 mV |

At 2.36 V the tone would stop with about 9 % of its level left. If a real
part behaves that way, raise R94.

## 7. Running the simulation

    ngspice sidetone_soft_hold.cir

Results go to `spice4qucs.tr1.plot` in the working directory.

Parameters at the top of the file:

| Parameter | Default | Meaning |
|---|---|---|
| `vz` | 4.8 | D3 Zener voltage |
| `klev` | 1.0 | Key-down level, fraction of DAC full scale |
| `vth` | 1.65 | U14 switching point |
| `kpot` | 0.10 | RV2 position, 0 = ground end, 1 = top |
| `ftone` | 700 | Pitch in Hz |
| `rpu` | 100k | R91; `1e12` removes it |
| `tr`, `t1`, `t2` | 5m, 5m, 45m | Envelope edge time, key-down and key-up instants |
| `renv`, `cenv` | 2.2k, 1u | R93, C67: envelope |
| `rhold`, `chold` | 150k, 100n | R94, C68: hold |
| `rchop`, `cx` | 22k, 1n | R92, C69: audio node |
| `r90`, `c70` | 100k, 10n | R90, C70: level and DC block |
| `ctone` | 1p | Cap across RV2; 1p means not fitted |

Vectors worth plotting:

| Vector | Node |
|---|---|
| `v(gate2)` | GATE_2 |
| `v(n7)`, `v(p6)` | U14 pin 7, pin 6 |
| `v(ekey)` | Envelope node |
| `v(hold)`, `v(p12)` | U14 pin 11, pin 12 |
| `v(n9)`, `v(p10)` | U14 pin 9, pin 10 |
| `v(x)` | Audio node (D11 anode) |
| `v(rvtop)`, `v(win)` | Top of RV2, wiper (LM386 pin 3) |
| `v(pin5)`, `v(spk)` | LM386 output, speaker |

## 8. Bench procedure

1. With the key up, confirm pin 7 sits between +0.2 V and +0.5 V and pin 10
   is static low.
2. Key at full level and at the lowest envelope setting in use; the sidetone
   should sound at both.
3. Scope pin 12 against pin 6 and read the hold time. Compare it with the
   table in section 6.
4. Scope the speaker on a string of dits. Look for a step where the tone
   stops (hold too short) or a faint tone between elements (hold too long).
5. Watch pin 12 as the hold ends. It should switch cleanly with R95 fitted.
6. Set RV2, then try 10 nF, 22 nF and 47 nF across it and pick by ear.
7. If the edges sound hard or mushy, change C67 and R94 together, per the
   table in 4.2.

## 9. Limits of the model

- The U14 gates are ideal comparators with a 50 Ω output. Real input clamping,
  output drive at 3.3 V and behaviour on slow edges are not represented.
- The LM386 is a gain of 20 with a 50 kΩ input and clipping at about 1 V and
  10.5 V. It has no bandwidth limit and no real distortion.
- The 1N5711 model leaks 315 nA in reverse, which is probably more than a real
  part at 3.3 V. The leak figure during the hold window is therefore likely
  pessimistic; it has not been checked against a datasheet curve.
- The speaker is 8 Ω resistive. Loudness and tone by ear will differ from the
  harmonic numbers here.

## 10. Open items in the 20:01 export

- **C73 is 220 nF; it should be 220 µF.** At 220 nF almost no audio reaches an
  8 Ω speaker. Use a polarised symbol so the orientation shows: positive on
  U19 pin 5.
- **C74 is 10 nF; the LM386 datasheet value is 47 nF** (shown there as
  0.05 µF with 10 Ω). At 10 nF the Zobel network starts working about five
  times higher in frequency.
- **No footprints** on C67, C68, C69, C73, C74, R84, R86, R89, R90, R91, R92,
  R93, R94, R95 and R96.
- **No voltage ratings** on the new capacitor values.
- **Optional tone capacitor** across RV2 is not drawn.
- **U19 pin 7** has no bypass capacitor.

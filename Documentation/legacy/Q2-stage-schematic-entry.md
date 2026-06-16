# Q2 Stage — Schematic Entry Guide

Companion to `20m-leveled-keyed-buffer.md`.  
Use this to build the QUCS-S schematic or draw the hardware layout.  
All values are also in the BOM table of the spec; this file adds the exact
node-by-node connections and winding instructions.

**Q2 is implemented as a dual-J310 cascode.**  
Q2a (lower) = common-source transconductance stage.  
Q2b (upper) = common-gate isolation/AGC stage, gate driven by the leveling loop.

---

## Net names

| Net | Description |
|-----|-------------|
| `VDD` | +12 V regulated rail |
| `GND` | Ground |
| `Q1S` | Q1 (J310) source — output of input stage, ~1.75 V DC + 378 mV peak AC |
| `Q2G1` | Q2a gate — AC-coupled signal input (lower JFET gate) |
| `Q2a_S` | Q2a source — DC self-bias node |
| `Q2a_D` | Q2a drain — internal cascode junction (= Q2b source) |
| `V_AGC` | Q2b gate — AGC control voltage from A1 output via R_VB |
| `TANK` | Q2b drain — parallel tank junction, large RF swing |
| `T1A` | T1 secondary end A — one push-pull grid feed |
| `T1B` | T1 secondary end B — other push-pull grid feed |
| `T1CT` | T1 secondary center tap — returns to bias or grid-leak |
| `V_DET` | Detector output — DC voltage proportional to RF level at grid |
| `V_CMD` | DAC setpoint from MCP4725 — the commanded level |
| `A1OUT` | TL071 output — AGC actuator voltage driving R_VB |

---

## Component connections

### Input coupling to Q2a

| Ref | Value | Pin / terminal | Net |
|-----|-------|----------------|-----|
| CC2 | 10 nF NP0 | A | Q1S |
| CC2 | | B | Q2G1 |
| RG1 | 100 kΩ | top | Q2G1 |
| RG1 | | bottom | GND |

---

### Q2a — J310 N-JFET (lower, common-source)

| Pin | Net | Notes |
|-----|-----|-------|
| G | Q2G1 | signal gate, AC-coupled from Q1S |
| D | Q2a_D | internal node, connects to Q2b source |
| S | Q2a_S | source, self-bias resistor below |

**Q2a source bias:**

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| RS2a | 270 Ω | top | Q2a_S |
| RS2a | | bottom | GND |
| CS2a | 10 nF NP0 | A | Q2a_S |
| CS2a | | B | GND |

---

### Q2b — J310 N-JFET (upper, common-gate)

| Pin | Net | Notes |
|-----|-----|-------|
| G | V_AGC | AGC control gate — driven by A1 via R_VB |
| S | Q2a_D | source, connected directly to Q2a drain |
| D | TANK | drain, RF output to tank circuit |

**Q2b gate control filter:**

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| R_VB | 10 kΩ | top | A1OUT |
| R_VB | | bottom | V_AGC |
| C_VB | 10 nF NP0 | A | V_AGC |
| C_VB | | B | Q2a_D |

> C_VB bypasses the Q2b gate to the internal cascode node at RF,
> presenting a low impedance at 14 MHz so Q2b acts as a true common-gate
> stage without RF voltage appearing on V_AGC.

**AGC bias range:**  
With Q2a self-biased at ~270 Ω and J310 operating at ~10–20 mA,  
Q2a_D will sit approximately 2–4 V above GND.  
V_AGC must be above Q2a_D for Q2b to conduct fully (maximum gain).  
Practical range: V_AGC = 3 V (min gain / near cutoff) to 8 V (max gain).  
A1OUT from the TL071 covers 0–10.5 V on a 12 V single supply — adequate margin.

---

### Tank circuit — L1 and C1

L1 is also the **primary of T1** (same physical winding on the same T50-6 core).

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| L1 | 22 t T50-6 (≈1.9 µH) | cold end | VDD |
| L1 | | hot end | TANK (= Q2b drain) |
| C1a | 47 pF NP0 / silver mica | A | TANK |
| C1a | | B | GND |
| C1b | 20 pF air trimmer | A | TANK |
| C1b | | B | GND |
| C_VDD1 | 10 nF NP0 | A | VDD (at cold end of L1) |
| C_VDD1 | | B | GND |
| C_VDD2 | 10 µF electrolytic | + | VDD |
| C_VDD2 | | − | GND |

> C1a + C1b in parallel = 47–67 pF total.  Resonate at 14.175 MHz with L1 = 1.9 µH →
> target capacitance ≈ 66 pF.  Peak C1b for maximum detector voltage during alignment.

---

### T1 — interstage transformer / push-pull splitter

**Winding on the same T50-6 core as L1:**

1. Wind L1 first: 22 turns #28 AWG enamelled, spread evenly around the core.
   Mark the cold (VDD) end as start, hot (TANK) end as finish.
2. Over L1, wind T1 secondary: 10 + 10 turns center-tapped, same #28 AWG.
   — Wind all 20 turns in one direction.
   — Tap the center after turn 10 — that wire is T1CT.
   — Start end = T1A, finish end = T1B.
   The sense of the secondary winding determines which grid leads which by 180°.
   Either polarity is fine; push-pull is symmetric.

| Pin / wire | Net | Goes to |
|------------|-----|---------|
| T1 hot end | TANK | Connects to Q2b drain (already joined via L1 hot end) |
| T1 cold end | VDD | Connects to VDD (already joined via L1 cold end) |
| T1A (secondary end A) | T1A | Grid stopper RG_A, then 6146B grid 1 |
| T1B (secondary end B) | T1B | Grid stopper RG_B, then 6146B grid 2 |
| T1CT (center tap) | T1CT | See bias scheme below |

**Grid bias return (choose one):**

*Class-C fixed bias (−70 V):* T1CT → negative bias supply rail.  
*Class-AB/B fixed bias:* T1CT → negative bias supply rail (lower magnitude).  
*Class-C self-bias grid-leak (no external negative supply):*

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| R_GL | 22 kΩ | top | T1CT |
| R_GL | | bottom | GND |
| C_GL | 10 nF NP0 | A | T1CT |
| C_GL | | B | GND |

**Grid stoppers:**

| Ref | Value | From | To |
|-----|-------|------|----|
| RGS_A | 100 Ω | T1A | 6146B grid 1 |
| RGS_B | 100 Ω | T1B | 6146B grid 2 |

---

### Leveling loop — detector + A1 integrator

**Detector (sample one grid, e.g. T1A side):**

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| C_DET_IN | 1000 pF NP0 | A | T1A |
| C_DET_IN | | B | D1 anode |
| D1 | 1N5711 Schottky | anode | D1 anode |
| D1 | | cathode | V_DET |
| R_BIAS | 330 kΩ | top | VDD |
| R_BIAS | | bottom | V_DET |
| C_DET_OUT | 10 nF film | A | V_DET |
| C_DET_OUT | | B | GND |

> R_BIAS (330 kΩ from VDD) forward-biases D1 with a ~35 µA trickle, keeping it
> in the linear region at low grid voltages (avoids the dead zone below ~0.3 V).
> V_DET rises with grid RF level.

**TL071 integrator (A1, DIP-8):**

| A1 pin | Net | Notes |
|--------|-----|-------|
| 2 (−) | via R_INT to V_DET | inverting |
| 3 (+) | V_CMD | DAC setpoint from MCP4725 |
| 6 (out) | A1OUT | drives Q2b gate via R_VB |
| 7 (V+) | VDD | supply |
| 4 (V−) | GND | single-supply; see note below |

| Ref | Value | From | To |
|-----|-------|------|-----|
| R_INT | 100 kΩ | V_DET | A1 pin 2 |
| C_INT | 1 µF film | A1 pin 2 | A1 pin 6 |
| R_FB | 470 kΩ | A1 pin 2 | A1 pin 6 |

> R_FB in parallel with C_INT sets the loop's DC gain (≈ 4.7×) and prevents
> integrator windup during key-up.

> **Single-supply note:** the TL071 output can only reach approximately VDD−1.5 V.
> With VDD = +12 V, A1OUT range is roughly 0–10.5 V, which covers V_AGC's
> operating range (3–8 V). The non-inverting input (pin 3) should have a
> resistor divider setting it near mid-range if V_CMD is 0–5 V from the DAC
> and you need the output to track correctly. Alternatively, run A1 from a
> split ±12 V supply (the TL071 handles up to ±18 V).

---

### Keying circuit

| Ref | Value | From | To |
|-----|-------|------|-----|
| R_KEY | 4.7 kΩ | Key switch (open = key-up) | V_CMD_RAW |
| C_KEY | 1 µF film | V_CMD_RAW | GND |
| — | — | V_CMD_RAW → MCP4725 output OR DAC setpoint mux | — |

The key switch pulls V_CMD toward the DAC output through R_KEY/C_KEY, giving
a ~5 ms RC envelope on the level command. Si5351 runs continuously — no chirp.

---

## Open items

- [ ] Confirm 6146B operating class → determines T1CT bias scheme (grid-leak vs fixed supply)
      and secondary turns needed.
- [ ] MCP4725 Vref and detector divider scaling for exact 0.3–5 V/grid mapping.
- [ ] Single-supply vs split-supply for TL071; if single-supply, verify A1OUT
      headroom covers the full V_AGC range (3–8 V).
- [ ] Measure actual J310 IDSS at operating point to confirm Q2a self-bias
      lands in the 2–4 V drain range needed for Q2b common-gate operation.

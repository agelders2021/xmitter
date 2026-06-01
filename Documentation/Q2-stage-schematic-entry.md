# Q2 Stage — Schematic Entry Guide

Companion to `20m-leveled-keyed-buffer.md`.  
Use this to build the QUCS-S schematic or draw the hardware layout.  
All values are also in the BOM table of the spec; this file adds the exact
node-by-node connections and winding instructions.

---

## Net names

| Net | Description |
|-----|-------------|
| `VDD` | +12 V regulated rail |
| `GND` | Ground |
| `Q1S` | Q1 (J310) source — output of input stage, ~1.75 V DC + 360 mV peak AC |
| `Q2G1` | Q2 gate-1 — AC-coupled signal input to VGA |
| `Q2S` | Q2 source — DC bias node |
| `Q2D` | Q2 drain — top of tank, large RF swing |
| `Q2G2` | Q2 gate-2 — AGC control, driven by A1 |
| `TANK` | Same as Q2D (parallel tank junction) |
| `T1A` | T1 secondary end A — one push-pull grid feed |
| `T1B` | T1 secondary end B — other push-pull grid feed |
| `T1CT` | T1 secondary center tap — returns to bias or grid-leak |
| `V_DET` | Detector output — DC voltage proportional to RF level at grid |
| `V_CMD` | DAC setpoint from MCP4725 — the commanded level |
| `A1OUT` | TL071 output — AGC actuator voltage |

---

## Component connections

### Input coupling to Q2

| Ref | Value | Pin / terminal | Net |
|-----|-------|----------------|-----|
| CC2 | 10 nF NP0 | A | Q1S |
| CC2 | | B | Q2G1 |
| RG1 | 100 kΩ | top | Q2G1 |
| RG1 | | bottom | GND |

### Q2 — BF961 (SOT-143) or 40673 / 3N211 (TO-72)

BF961 SOT-143 pin order (left to right, marking face up): **G1 – D – S – G2**  
40673 / 3N211 TO-72 pins (bottom view, tab = drain on 40673): **G1 – D – S – G2**

| Pin | Net | Notes |
|-----|-----|-------|
| G1 | Q2G1 | signal gate |
| D | Q2D (= TANK) | drain, RF swing here |
| S | Q2S | source, bias resistor below |
| G2 | Q2G2 | AGC control gate |

**Q2 source bias:**

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| RS2 | 270 Ω | top | Q2S |
| RS2 | | bottom | GND |
| CS1 | 10 nF NP0 | A | Q2S |
| CS1 | | B | GND |

**Q2 G2 control filter:**

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| RG2 | 10 kΩ | top | A1OUT |
| RG2 | | bottom | Q2G2 |
| CG2 | 10 nF NP0 | A | Q2G2 |
| CG2 | | B | GND |

---

### Tank circuit — L1 and C1

L1 is also the **primary of T1** (same physical winding on the same T50-6 core).

| Ref | Value | Pin | Net |
|-----|-------|-----|-----|
| L1 | 22 t T50-6 (≈1.9 µH) | cold end | VDD |
| L1 | | hot end | TANK (= Q2D) |
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
| T1 cold (hot) end | TANK | Connects to Q2D (already joined via L1 hot end) |
| T1 cold (cold) end | VDD | Connects to VDD (already joined via L1 cold end) |
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
| 6 (out) | A1OUT | drives Q2G2 via RG2 |
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
> With VDD = +12 V, A1OUT range is roughly 0–10.5 V, which covers G2's
> operating range (2–8 V). The non-inverting input (pin 3) should have a
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

## Cascode J310 substitute for Q2

If dual-gate MOSFETs are unavailable, two J310s in cascode:

| Device | Role | G net | D net | S net |
|--------|------|-------|-------|-------|
| Q2a (J310, lower) | common-source | Q2G1 | Q2a_D | Q2a_S |
| Q2b (J310, upper) | common-gate | V_AGC | TANK | Q2a_D |

Add:
- RS2a = 270 Ω from Q2a_S to GND (self-bias Q2a)
- CS2a = 10 nF from Q2a_S to GND
- R_VB = 10 kΩ from A1OUT to V_AGC (Q2b gate = AGC point)
- C_VB = 10 nF from V_AGC to Q2a_D (RF bypass of Q2b gate to its source)
- Q2b drain = TANK; connects to tank the same way as Q2 drain above

V_AGC ranges 0–8 V from A1 output; same leveling loop as with dual-gate MOSFET.

---

## Simulation probes to add in QUCS-S

| Probe name | Tapped across |
|------------|---------------|
| Pr_Q1S | Q1S to GND (already Pr4 in existing sim) |
| Pr_TANK | TANK (Q2D) to GND |
| Pr_T1A | T1A to GND |
| Pr_T1B | T1B to GND |
| Pr_VDET | V_DET to GND |
| Pr_G2 | Q2G2 to GND |

---

## Open items (from spec)

- [ ] Confirm 6146B operating class → determines T1CT bias scheme (grid-leak vs fixed supply),
      secondary turns needed, and whether the ±10 V drain swing is sufficient.
- [ ] MCP4725 Vref and detector divider scaling for exact 0.3–5 V/grid mapping.
- [ ] Single-supply vs split-supply for TL071; if single-supply, verify A1OUT
      headroom covers the full G2 range.

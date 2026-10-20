# Test points — analog and ss_pa boards

Quick-reference lookup for every TP on both boards. Group by functional
area. Use for benchwork — scope probe, DMM, logic analyzer. Last
updated 2026-10-20.

Format uses monospace-aligned columns (no markdown tables) so this
file renders cleanly in PDF/text exports as well as rendered markdown.

---

# Analog board test points

---

## Tube-PA control bus (parallel path to J35)

Every signal that leaves on J35 for a future tube PA is also brought
out to a test point for direct probing without unplugging the J35
cable.

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP2    GRID_CTL_A          MCP4728 U3 ch C (pin 9) -- future tube A
                           grid bias setpoint. 0..5 V DC, firmware set.
TP1    GRID_CTL_B          MCP4728 U3 ch D (pin 10) -- future tube B
                           grid bias setpoint.
TP5    I_CATHODE_A         Return from future tube A cathode sense
                           resistor. Should sit at ~0 V with no tube
                           connected. Analog low-pass to Metro ADC.
TP6    I_CATHODE_B         Same for tube B.
TP7    GRID_BLOCK_CRASH    Hardware fault signal commanding the (future)
                           grid-bias generator to crash to full negative.
                           Polarity: active-?? (confirm in future tube
                           PA design).
```

---

## SS PA bias / sense / fault (parallel path to J31)

The signals that cross the J31 umbilical to the ss_pa board, also
tapped locally on analog for debugging without unplugging J31.

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP4    PA_Bias_A_Raw       MCP4728 U3 ch A (pin 7) -- IRF510 Q3 bias
                           setpoint from firmware. 0..5 V DC.
TP3    PA_Bias_B_Raw       MCP4728 U3 ch B (pin 8) -- IRF510 Q4 bias
                           setpoint.
TP12   Source_Sense_A      Return from ss_pa (J31 pin 1). IRF510 Q3
                           source voltage after RC filter. Roughly
                           0..500 mV DC proportional to drain current.
TP14   Source_Sense_B      Same for Q4.
TP13   FAULT_N             Hardware fault latch output (J31 pin 3).
                           Normal: HIGH (~3.3 V). Fault latched: LOW.
                           Metro also reads this as a digital input.
TP15   DRIVER_BIAS         MCP4922 U4 ch B (pin 14) -- BS170 PP driver
                           bias setpoint on ss_pa. 0..5 V DC.
```

---

## Keyer / envelope / RF-generation chain

Points along the signal path from DGFET keyer to the LM7171 buffer
output.

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP20   Gate 2              DGFET Q2 pin 2 -- envelope VCA control.
                           ~0 V key-up, ~+4 V key-down steady state,
                           raised-cosine ramp during key transitions.
                           Driven by MCP4922 U4 ch A through Q11/Q12
                           KeyUp mute level shifter.
TP10   KeyUp               Logic signal from the keyer path; HIGH =
                           key is UP (no RF). Drives Q11/Q12 to mute
                           Gate 2 during key-up.
TP21   LM7171 U1 output    Immediately after U1 pin 6, BEFORE R2 50 ohm
                           back-match. Scope this to see the actual
                           op-amp output waveform (not loaded by the
                           coax). Expect ~0.5 Vpp (unity gain default)
                           or ~2 Vpp (if R_g populated for gain = 4).
```

---

## DAC control lines

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP8    DAC_SHDN_N          MCP4728 U3 shutdown pin. LOW = shutdown
                           (DACs off, outputs tri-state). Normally HIGH.
TP9    DAC_LDAC_N          MCP4728 U3 LDAC pin. Pulse LOW to latch
                           pending input-register writes to the output
                           registers simultaneously (used during the
                           first-boot 0x60 -> 0x67 address reprogram
                           sequence; also for synchronized updates).
```

---

## Relay driver gates (2N7000 FETs)

Each relay coil is switched by a 2N7000. Scoping the gate shows the
drive signal from PCF8575 / Metro before it reaches the relay.

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP16   Q4 gate             Drives relay via J6 screw terminal. (Likely
                           T/R switching or similar -- confirm in
                           schematic.)
TP17   Q5 gate             Drives SS_PWR_RLY (ss_pa +13.8 V enable
                           relay) through Q7 cascode. Both Q5 and Q7
                           must be ON for the SS PA to receive power
                           -- hardware interlock.
TP18   Q6 gate             Drives relay via J8 screw terminal.
TP11   Q7 gate             Upper FET in the SS_PWR_RLY cascode. See
                           TP17.
```

---

## Hardware watchdog

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP19   U18 +TR_A           CD14538B dual monostable, +trigger input
                           for channel A. Firmware must pulse this
                           periodically or the monostable times out
                           and de-energizes a critical safety relay.
                           Hardware heartbeat watchdog.
```

---

## How to use this doc at the bench

- **Debugging RF chain:** TP20 (Gate 2) first to confirm envelope,
  then TP21 (U1 output) to confirm buffered RF, then J1 to confirm
  back-matched coax drive to ss_pa.
- **Checking bias settings:** TP4/TP3 for IRF510 bias setpoints
  from firmware; TP12/TP14 to see the actual source current on
  each FET (via the voltage drop on the 0.11 ohm source
  resistors); TP15 for BS170 driver bias.
- **Verifying fault chain:** TP13 should sit high (~3.3 V) under
  normal operation. If it goes low, fault latched -- firmware
  should also see the LOW on J31 pin 3 and should display/log it.
- **Future tube PA bring-up:** TP2, TP1 give you direct scope
  access to grid-bias commands before plugging in a tube PA;
  TP5, TP6 become the cathode-current readback once a tube is
  connected. TP7 lets you force-trip the GRID_BLOCK_CRASH line
  from a bench function generator to validate fault behavior
  without having to actually overcurrent anything.
- **Watchdog verification:** TP19 should show a periodic pulse
  train from firmware; a flat line means the monostable is about
  to time out.

---

# SS PA board test points

Deliberately minimal set — only the nodes most useful during bring-up
and periodic smoke-testing. Hot-RF test points (drains + RF out) are
kept small-pad / short-stub to limit stray C perturbation of the
VHF-stability-tuned feedback network (see §12 of
Master_Description.md for the rationale).

## Local supply and bias monitors (DC-only, probe return anywhere)

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP1    +3.3V               Local U13 (MCP1700x-330) LDO output.
                           Confirms the on-board 3.3 V rail is up
                           (powers U1 LM393 + U2 CD74HC4066 fault
                           chain). Should sit at 3.30 V +/-1 %.
TP2    PA_Bias_A           After U2 (CD74HC4066) switch output and
                           before R8 (47 ohm) series to Q3 gate.
                           Normal operation: ~3.8 V (class-AB) or
                           ~1-2 V (class-C), tracks PA_Bias_A_Raw
                           from analog MCP4728 ch A. On FAULT_N
                           low: pulled to 0 V by R12 (100K)
                           within ~18 us.
TP3    PA_Bias_B           Same for Q4 (tracks PA_Bias_B_Raw from
                           analog MCP4728 ch B, pulled by R19).
```

## Hot-RF test points (short-stub, pair-matched to GND)

```
TP#    Signal              Source / description
---    ------              -------------------------------------------
TP4    RF IN (J3-In)       At J3 center pin, 50 ohm RF input from
                           the analog board. ~0.5 Vpp (U1 at unity
                           gain) or ~2 Vpp (U1 at gain 4). Lets
                           you confirm RF arrived from analog
                           before chasing problems further down
                           the chain.
TP5    RF OUT (J1-In)      At J1 center pin, final 50 ohm matched
                           RF output to the Output LPF board.
                           ~22 Vpk at 10 W. **Scope-probe GND to
                           TP8 or TP9 for clean waveform.**
TP6    Q3 drain            IRF510 Q3 drain, high-voltage RF node
                           swinging to ~28 V peak at full output.
                           Primary purpose: VHF parasitic
                           oscillation check during bring-up. Pair
                           probe GND with a nearby TP8/TP9.
TP7    Q4 drain            Same for Q4 (the other PP half).
TP8    GND                 Probe-return pad near Q3 drain (TP6)
TP9    GND                 Probe-return pad near Q4 drain (TP7)
TP10   GND                 Probe-return pad near J1 RF out (TP5)
TP11   GND                 Probe-return pad near J3 RF in (TP4)
```

All four GND probe-return pads are placed close to a hot-RF TP so
the scope-probe ground spring reaches directly — short probe loop =
clean HF waveform, no pickup-antenna behavior.

## How to use these at the bench

- **PA power-on sanity check (no RF yet):** TP1 for +3.3 V, TP2
  and TP3 for PA_Bias at idle (should match the DAC values analog
  commanded). TP6/TP7 should sit at +13.8 V (drain static DC via
  the T203 drain feed, no RF).
- **Oscillation check during first-RF bring-up:** scope at TP6 and
  TP7 (one at a time), probe GND spring to TP8 or TP9, drive the
  input with low-level CW. Look for any ringing above the carrier
  frequency — clean sinewave at the carrier is good, 100-300 MHz
  ripples riding on it means parasitic oscillation. Repeat at a
  few output levels and into a mismatched load as a stress test.
- **"Signal arrived" sanity:** if TP5 (output) is dead or weird,
  scope TP4 (input) first to see whether RF is actually reaching
  the board from analog. A dead TP4 means the problem is on
  analog or the coax, not the PA.
- **Fault chain verification:** command PA_Bias high from firmware
  then force-trip the fault latch (short Source_Sense to V_REF
  briefly, or trigger from the Metro). TP2 and TP3 should both
  drop to 0 V within ~18 µs, confirming the pulldowns are
  working. TP6/TP7 (idling at +13.8 V) should NOT swing
  afterward — if they do, bias is still arriving and the switch
  isn't actually opening.
- **RF-level check:** TP5 directly gives you the output amplitude.
  Compare to the computed value from V_rms = sqrt(P × 50) — 10 W
  → 22.4 V_rms → 31.6 V_pk.

**Not provided (intentionally):**

- Hot-RF TPs on BS170 drains, IRF510 gates, or RF input (J3).
  These nodes could not be test-pointed without longer stubs that
  risk disturbing the VHF-stability feedback network. If you need
  to probe these during bring-up, solder a short tack-wire or use
  a mini-grabber on the TO-220/TO-92 lead directly, remove when
  done.
- Driver-stage source current (BS170 Q2, Q6 sources through R15,
  R16). Measure these directly at the resistors with DMM leads
  if needed.
- V_REF: already exposed on J5 pin 2 (external terminal).

# Analog board test points

Quick-reference lookup for every TP on the analog board. Group by
functional area. Use for benchwork — scope probe, DMM, logic analyzer.
Last updated 2026-10-19.

Format uses monospace-aligned columns (no markdown tables) so this
file renders cleanly in PDF/text exports as well as rendered markdown.

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

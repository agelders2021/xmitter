<Qucs Schematic 26.1.1>
<Properties>
  <View=-390,10,1566,1098,1.72393,1244,265>
  <Grid=10,10,1>
  <DataSet=SS_Mod.dat>
  <DataDisplay=SS_Mod.dpl>
  <OpenDisplay=0>
  <Script=SS_Mod.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=SS PA Drain Modulator>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
</Symbol>
<Components>
  <Vdc V1 1 130 130 18 -26 0 1 "13.8 V" 1>
  <GND * 1 130 160 0 0 0 0>
  <C C_byp1 1 210 130 17 -26 0 1 "100 uF" 1 "" 0 "neutral" 0>
  <GND * 1 210 160 0 0 0 0>
  <C C_byp2 1 290 130 17 -26 0 1 "1 uF" 1 "" 0 "neutral" 0>
  <GND * 1 290 160 0 0 0 0>
  <Lib M1 1 430 230 8 -26 0 2 "PMOSFETs" 0 "IRF9540N" 0>
  <R R_gate 1 520 230 -26 15 0 0 "100 Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_pulldown 1 310 420 15 -26 0 1 "10 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 310 450 0 0 0 0>
  <C C_drain 1 370 420 17 -26 0 1 "100 uF" 1 "" 0 "neutral" 0>
  <GND * 1 370 450 0 0 0 0>
  <R R_load 1 430 420 15 -26 0 1 "20 Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 430 450 0 0 0 0>
  <R R_fb_top 1 640 420 15 -26 0 1 "22 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <C C_lead 1 710 420 17 -26 0 1 "100 nF" 1 "" 0 "neutral" 0>
  <R R_fb_bot 1 640 510 15 -26 0 1 "10 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 640 540 0 0 0 0>
  <Lib OP1 1 900 500 -26 42 0 0 "OpAmps" 0 "tl071(TI)" 0>
  <Vdc V2 1 1000 420 18 -26 0 1 "15 V" 1>
  <GND * 1 1000 450 0 0 0 0>
  <Vdc V3 1 1000 580 18 -26 0 1 "-15 V" 1>
  <GND * 1 1000 610 0 0 0 0>
  <Vpulse V4 1 770 600 18 -26 0 1 "0 V" 1 "1 V" 1 "1 ms" 1 "5 ms" 1 "100 us" 1 "100 us" 1>
  <GND * 1 770 630 0 0 0 0>
  <.TR TR1 1 100 760 0 54 0 0 "lin" 1 "0" 0 "15 ms" 1 "10000" 0 "Trapezoidal" 0 "2" 0 "1 ns" 0 "1e-16" 0 "150" 0 "0.001" 0 "1 pA" 0 "1 uV" 0 "26.85" 0 "1e-3" 0 "1e-6" 0 "1" 0 "CroutLU" 0 "no" 0 "yes" 0 "0" 0>
  <VProbe Pr1 1 720 370 28 -31 0 0>
  <GND * 1 820 390 0 0 0 0>
  <VProbe Pr2 1 580 430 -50 -31 1 2>
  <GND * 1 570 450 0 0 0 0>
</Components>
<Wires>
  <130 100 210 100 "" 0 0 0 "">
  <430 100 430 200 "" 0 0 0 "">
  <430 260 430 390 "" 0 0 0 "">
  <460 230 490 230 "" 0 0 0 "">
  <310 390 370 390 "" 0 0 0 "">
  <640 450 710 450 "" 0 0 0 "">
  <640 450 640 480 "" 0 0 0 "">
  <710 450 710 520 "" 0 0 0 "">
  <710 520 860 520 "" 0 0 0 "">
  <770 480 770 570 "" 0 0 0 "">
  <770 480 860 480 "" 0 0 0 "">
  <940 390 1000 390 "" 0 0 0 "">
  <870 480 860 480 "" 0 0 0 "">
  <860 480 860 460 "" 0 0 0 "">
  <870 520 860 520 "" 0 0 0 "">
  <860 520 860 540 "" 0 0 0 "">
  <210 100 290 100 "" 0 0 0 "">
  <290 100 430 100 "" 0 0 0 "">
  <370 390 430 390 "" 0 0 0 "">
  <430 390 640 390 "" 0 0 0 "">
  <640 390 710 390 "" 0 0 0 "">
  <940 460 940 390 "" 0 0 0 "">
  <940 540 1000 540 "" 0 0 0 "">
  <1000 540 1000 550 "" 0 0 0 "">
  <990 500 1100 500 "" 0 0 0 "">
  <1100 500 1100 230 "" 0 0 0 "">
  <1100 230 550 230 "" 0 0 0 "">
  <730 390 820 390 "" 0 0 0 "">
  <640 450 590 450 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
  <Text 100 700 10 #000000 0 "SS PA DRAIN MODULATOR (loop-stability test, rev 2)\n\nTopology: PMOS high-side pass (IRF9540N) + TL071 op-amp.\n Envelope on OP1 -IN, Vdrain-divided on +IN.  Equilibrium:\n   Vdrain = V_envelope * 3.2  (22k over 10k divider)\n   V_env = 1V -> Vdrain = 3.2V ; V_env = 4V -> Vdrain = 12.8V\n\nC_lead (100 nF) in parallel with R_fb_top creates a feedback\n zero at f = 1 / (2*pi*22k*100n) = 72 Hz, which cancels the\n drain pole at f = 1 / (2*pi*20*100uF) = 80 Hz.  Net result:\n single dominant pole from the op-amp, ~90 deg phase margin.\n\nTL071: GBW 3 MHz, slew 13 V/us.  Powered from +/-15V (V2, V3).\n Op-amp output swing ~ +/-13V, enough to drive PMOS gate from\n fully off (gate near +13V) to fully on (gate near -13V).\n Real circuit uses +12V/-12V rails (LM7171) - a bit less swing\n but still adequate; swap OP1 to lm7171 or ua741 if desired.\n\nR_load = 20 ohms = PA stand-in (~10W at 13.8V ~ 1A).\nR_pulldown (10k) at drain = safe-default-off if loop unpowered.\nC_drain (100uF) decouples 14MHz RF from the modulator loop.\n\nTo plot: add VProbe on drain-bus-to-GND and on fb-node-to-GND.\n Make sure the probe's + terminal points to the signal node\n (not GND); rotate 180 deg if the trace comes out negated.">
  <Text 100 50 10 #000000 0 "V+ = 13.8 V bus">
  <Text 440 390 10 #000000 0 "Vdrain">
  <Text 940 450 10 #0000ff 0 "+15 V (op-amp VCC)">
  <Text 940 560 10 #0000ff 0 "-15 V (op-amp VEE)">
  <Text 410 180 10 #0000ff 0 "M1 source (to V+)">
  <Text 440 300 10 #0000ff 0 "M1 drain (to bus)">
  <Text 460 215 10 #0000ff 0 "M1 gate">
  <Text 720 475 10 #ff0000 0 "C_lead parallel with R_fb_top\n(lead compensation)">
  <Text 790 480 10 #000000 0 "- IN (envelope)">
  <Text 790 520 10 #000000 0 "+ IN (feedback)">
  <Text 440 270 10 #ff0000 0 "If M1 pins look wrong in GUI,\nselect M1 and rotate so\nS=top (V+), D=bottom (drain).">
</Paintings>

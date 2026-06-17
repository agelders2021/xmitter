<Qucs Schematic 26.1.1>
<Properties>
  <View=57,-715,4297,1644,1.70469,733,1732>
  <Grid=10,10,1>
  <DataSet=test2.dat>
  <DataDisplay=test2.dpl>
  <OpenDisplay=0>
  <Script=test.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
</Symbol>
<Components>
  <SpLib X4 1 610 470 -26 201 0 0 "C:/Users/AlAnd/Git Backed Projects/xmitter/xmitter_prj/MC1496_MODEL.cir" 1 "MC1496" 0 "auto" 0 "" 0 "" 0>
  <Vdc V1 1 270 290 18 -26 0 1 "12 V" 1>
  <GND * 1 270 320 0 0 0 0>
  <Vdc V2 1 270 470 18 -26 0 1 "8.2 V" 1>
  <R R_RE 1 610 260 -26 15 0 0 "1 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_SIG_P 1 520 320 15 -26 0 1 "10 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 520 350 0 0 0 0>
  <R R_BIAS 1 480 410 -26 15 0 0 "6.8 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 450 410 0 0 0 0>
  <R R_LOAD_P 1 750 380 15 -26 0 1 "3.9 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_LOAD_N 1 750 560 15 -26 0 1 "3.9 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <C CC_CAR 1 730 470 -26 17 0 0 "10 nF" 1 "" 0 "neutral" 0>
  <C CCAR_N 1 700 560 17 -26 0 1 "100 nF" 1 "" 0 "neutral" 0>
  <GND * 1 700 590 0 0 0 0>
  <R R_SCALE1 1 790 280 -26 15 0 0 "100 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_SCALE2 1 720 400 15 -26 0 1 "5.1 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 720 430 0 0 0 0>
  <Vdc V_AGC 1 870 310 18 -26 0 1 "10 V" 1>
  <GND * 1 870 340 0 0 0 0>
  <Vac V_RF 1 820 490 18 -26 0 1 "0.378 V" 1 "14.175 MHz" 1 "0" 0 "0" 0 "0" 0 "0" 0>
  <GND * 1 820 520 0 0 0 0>
  <.TR TR1 1 100 200 0 54 0 0 "lin" 1 "0" 1 "1 us" 1 "500" 1 "Trapezoidal" 0 "2" 0 "1 ns" 0 "1e-16" 0 "150" 0 "0.001" 0 "1 pA" 0 "1 uV" 0 "26.85" 0 "1e-3" 0 "1e-6" 0 "1" 0 "CroutLU" 0 "no" 0 "no" 0 "0" 0>
</Components>
<Wires>
  <270 320 270 440 "" 0 0 0 "">
  <270 250 270 260 "vdd" 280 252 0 "">
  <270 500 270 510 "vee" 280 502 0 "">
  <540 350 580 350 "" 0 0 0 "">
  <540 260 540 350 "" 0 0 0 "">
  <540 260 580 260 "" 0 0 0 "">
  <640 260 700 260 "" 0 0 0 "">
  <700 260 700 290 "" 0 0 0 "">
  <640 290 700 290 "" 0 0 0 "">
  <520 290 580 290 "" 0 0 0 "">
  <510 410 580 410 "" 0 0 0 "">
  <640 410 750 410 "" 0 0 0 "">
  <750 340 750 350 "vdd" 760 342 0 "">
  <750 590 750 620 "" 0 0 0 "">
  <640 620 750 620 "" 0 0 0 "">
  <640 590 640 620 "" 0 0 0 "">
  <750 520 750 530 "vdd" 760 522 0 "">
  <640 470 700 470 "" 0 0 0 "">
  <760 460 760 470 "" 0 0 0 "">
  <760 460 820 460 "" 0 0 0 "">
  <640 530 700 530 "" 0 0 0 "">
  <640 350 720 350 "" 0 0 0 "">
  <720 350 720 370 "" 0 0 0 "">
  <720 350 760 350 "" 0 0 0 "">
  <760 280 760 350 "" 0 0 0 "">
  <820 280 870 280 "" 0 0 0 "">
  <640 650 640 660 "vee" 650 652 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
  <Text 100 680 10 #000000 0 "MC1496 VCA test, 14.175 MHz 20m CW TX. SpLib X4 (MC1496_MODEL.cir) at cx=610 cy=470; odd pins x=580, even x=640, 60-unit y-spacing. P1=SIG_P@y290 P2=GAIN_A@y290 P3=GAIN_B@y350 P4=SIG_N@y350 P5=BIAS@y410 P6=OUT_P@y410 P8=CAR_P@y470 P10=CAR_N@y530 P12=OUT_N@y590 P14=VEE@y650. Supply: V1=+12V V2=8.2V in series, GND between them: VDD=+12V VEE=-8.2V. Bias: R_BIAS=6.8k (P5-GND) sets tail current; R_RE=1k (P2-P3) sets gain; R_SIG_P=10k (P1-GND). AGC divider: R_SCALE1=100k + R_SCALE2=5.1k (V_AGC to P4). Carrier: V_RF=0.378V 14.175MHz into CC_CAR=10nF to P8; P10 AC-grounded via CCAR_N=100nF. Loads: R_LOAD_P=R_LOAD_N=3.9k (VDD to P6 and P12). VProbe = v(OUT_P)-v(OUT_N).">
  <Text 100 710 10 #000000 0 "Results 2026-06-06: AGC=0V: ~0.69V p-p differential (carrier feedthrough; port not nulled). AGC=10V: ~1.61V p-p differential (+1.03V / -0.58V peaks). Asymmetric waveform because P1 biased through 10k and P4 through 5.1k||100k=4.85k; unequal impedances give unequal Q1/Q2 tail currents and a DC offset in the differential output. For a clean null and symmetric swing, use equal resistors on P1 and P4 from a symmetric voltage divider. Subcircuit MC1496_MODEL.cir confirmed correct; circuit simulates cleanly with no convergence errors.">
</Paintings>

<Qucs Schematic 26.1.1>
<Properties>
  <View=-18,-181,2432,435,2.38939,222,117>
  <Grid=10,10,1>
  <DataSet=vfo_buffer_subcircuit.dat>
  <DataDisplay=vfo_buffer_subcircuit.dpl>
  <OpenDisplay=0>
  <Script=vfo_buffer_subcircuit.m>
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
  <.TR TR1 1 0 -200 0 54 0 0 "lin" 1 "500 ps" 1 "5000 ns" 1 "20000" 0 "Trapezoidal" 0 "2" 0 "1 ns" 0 "1e-16" 0 "150" 0 "0.001" 0 "1 pA" 0 "1 uV" 0 "26.85" 0 "1e-3" 0 "1e-6" 0 "1" 0 "CroutLU" 0 "no" 0 "yes" 0 "0" 0>
  <SpLib X1 1 400 300 110 69 0 0 "mc1496.lib" 1 "MC1496" 1 "spice" 0 "" 0 "1;2;3;4;5;6;7;8;9;10" 0>
  <Vac V_Q1S 1 140 240 -42 42 0 2 "0.378 V" 1 "14.175 MHz" 1 "0" 0 "0" 0 "0" 0 "0" 0>
  <GND * 1 110 240 0 0 0 0>
  <C CC_CAR 1 260 240 -59 -87 0 0 "10 nF" 1 "" 0 "neutral" 0>
  <C CCAR_N 1 520 250 22 58 0 1 "100 nF" 1 "" 0 "neutral" 0>
  <GND * 1 520 280 0 0 0 0>
  <R R_SIG_P 1 280 100 15 -26 0 1 "10 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 250 70 0 0 0 0>
  <R R_SCALE2 1 480 100 15 -26 0 1 "5.1 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 450 70 0 0 0 0>
  <R R_SCALE1 1 560 180 -61 -50 0 0 "100 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 700 180 0 0 0 0>
  <R R_BIAS 1 370 450 -95 -9 0 1 "1 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_RE 1 430 450 22 -1 0 1 "1 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_LOAD_P 1 250 270 15 -26 0 1 "3.9 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_LOAD_N 1 550 270 15 -26 0 1 "3.9 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <Vdc V_VDD 1 640 70 18 -26 0 3 "12 V" 1>
  <GND * 1 720 40 0 0 0 0>
  <Vdc V_VEE 1 600 510 18 -26 0 2 "-8.2 V" 1>
  <GND * 1 630 510 0 0 0 0>
  <Vdc V_AGC 1 670 180 18 -26 0 0 "10 V" 1>
</Components>
<Wires>
  <170 240 230 240 "" 0 0 0 "">
  <290 240 370 240 "car_p" 300 228 0 "">
  <430 240 520 240 "car_n" 440 228 0 "">
  <520 220 520 240 "car_n" 528 226 0 "">
  <280 180 370 180 "sig_p" 290 168 0 "">
  <430 180 480 180 "sig_n" 440 168 0 "">
  <480 180 530 180 "" 0 0 0 "">
  <590 180 640 180 "" 0 0 0 "">
  <250 300 370 300 "out_p" 290 288 0 "">
  <430 300 550 300 "out_n" 470 288 0 "">
  <340 360 370 360 "vdd" 345 348 0 "">
  <250 200 250 240 "vdd" 258 210 0 "">
  <550 200 550 240 "vdd" 558 210 0 "">
  <610 150 640 150 "vdd" 615 138 0 "">
  <430 360 470 360 "vee" 435 348 0 "">
  <370 480 370 510 "vee" 378 488 0 "">
  <430 480 430 510 "vee" 438 488 0 "">
  <540 510 570 510 "vee" 545 498 0 "">
  <310 420 370 420 "vbias" 320 408 0 "">
  <430 420 470 420 "vgain" 440 408 0 "">
  <280 180 280 130 "" 0 0 0 "">
  <480 180 480 130 "" 0 0 0 "">
  <640 150 640 100 "" 0 0 0 "">
  <250 70 280 70 "" 0 0 0 "">
  <450 70 480 70 "" 0 0 0 "">
  <640 40 720 40 "" 0 0 0 "">
</Wires>
<Diagrams>
  <Rect 290 0 240 160 3 #c0c0c0 1 00 1 0 1e-06 5e-06 1 -0.5 0.5 0.5 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/tran.v(out_n)" #0000ff 0 3 0 0 0>
  </Rect>
</Diagrams>
<Paintings>
  <Text 50 560 11 #000000 0 "MC1496 Gilbert-cell VCA buffer, 14.175 MHz 20m CW TX. SpLib X1 ports: 1=SIG_P 2=SIG_N 3=CAR_P 4=CAR_N 5=OUT_P 6=OUT_N 7=VCC 8=VEE 9=BIAS 10=GAIN_RE. If SpLib pin order differs, reconnect wires to match. V_AGC=0V: carrier null. Change to 10V for max gain. Expected out_p pp ~3.64V with 3.9k loads. HW: replace R_LOAD_P/N with 100uH RFC + FT37-43 T1.">
</Paintings>

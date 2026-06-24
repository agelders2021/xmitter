<Qucs Schematic 26.1.1>
<Properties>
  <View=157,80,1208,665,1.49667,0,0>
  <Grid=10,10,1>
  <DataSet=grid_bias_check.dat>
  <DataDisplay=grid_bias_check.dpl>
  <OpenDisplay=0>
  <Script=grid_bias_check.m>
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
  <R RL 1 990 460 15 -26 0 1 "1 MOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 990 490 0 0 0 0>
  <VProbe Pr1 1 1120 410 28 -31 0 0>
  <GND * 1 1130 430 0 0 0 0>
  <GND * 1 740 490 0 0 0 0>
  <.DC DC1 1 200 140 0 33 0 0 "26.85" 0 "0.001" 0 "1 pA" 0 "1 uV" 0 "no" 0 "150" 0 "no" 0 "none" 0 "CroutLU" 0>
  <Sub SUB1 1 960 460 -26 21 0 0 "grid_bias.sch" 0>
  <Vdc V2 1 370 580 18 -26 0 1 "1 V" 1>
  <R R1 1 550 480 -26 15 0 0 "470kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R2 1 440 550 -40 -79 0 0 "7.5kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 370 610 0 0 0 0>
  <GND * 1 480 650 0 0 0 0>
  <.SW SW1 1 550 140 0 54 0 0 "DC1" 1 "lin" 1 "V2" 1 "0V" 1 "5V" 1 "66" 1>
  <OpAmp OP1 1 540 570 -26 42 0 0 "1e4" 1 "15 V" 0>
  <Vdc V1 1 740 460 18 -26 0 1 "3.1V" 1>
  <Vdc V3 1 480 620 -71 -16 0 1 "1.0 V" 1>
</Components>
<Wires>
  <740 430 930 430 "" 0 0 0 "">
  <990 430 1110 430 "" 0 0 0 "">
  <510 550 500 550 "" 0 0 0 "">
  <410 550 370 550 "" 0 0 0 "">
  <370 550 370 540 "" 0 0 0 "">
  <520 480 500 480 "" 0 0 0 "">
  <500 550 470 550 "" 0 0 0 "">
  <500 480 500 550 "" 0 0 0 "">
  <580 480 580 570 "" 0 0 0 "">
  <580 570 930 570 "" 0 0 0 "">
  <930 570 930 490 "" 0 0 0 "">
  <510 590 480 590 "" 0 0 0 "">
</Wires>
<Diagrams>
  <Rect 770 250 240 160 3 #c0c0c0 1 00 1 0 0.2 1 1 -0.1 0.5 1.1 1 -0.1 0.5 1.1 315 0 225 1 0 0 "" "" "">
	<"ngspice/sw1.v(pr1)" #0000ff 1 3 0 0 0>
  </Rect>
</Diagrams>
<Paintings>
</Paintings>

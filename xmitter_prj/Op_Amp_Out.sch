<Qucs Schematic 26.1.1>
<Properties>
  <View=0,-60,1573,815,1,0,0>
  <Grid=10,10,1>
  <DataSet=Op_Amp_Out.dat>
  <DataDisplay=Op_Amp_Out.dpl>
  <OpenDisplay=0>
  <Script=Op_Amp_Out.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
  <.PortSym 40 20 1 0 IN>
  <.PortSym 40 60 2 0 OUT>
</Symbol>
<Components>
  <R R1 1 300 380 15 -26 0 1 "100kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 300 410 0 0 0 0>
  <Port IN 1 240 350 -33 -65 0 0 "1" 1 "analog" 0>
  <OpAmp LM7171 1 500 370 -26 42 0 0 "1e6" 1 "15 V" 0>
  <Port OUT 1 680 370 4 12 1 2 "2" 1 "analog" 0>
  <R RF 1 500 500 -143 3 0 0 "30 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <C C_IN 1 270 350 -55 29 0 0 "100 nF" 1 "" 0 "neutral" 0>
  <C C_OUT 1 650 370 -26 17 0 0 "100 nF" 1 "" 0 "neutral" 0>
  <GND * 1 470 560 0 0 0 0>
  <R RG 1 470 530 15 -26 0 1 "10 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
</Components>
<Wires>
  <470 350 300 350 "" 0 0 0 "">
  <540 370 590 370 "" 0 0 0 "">
  <590 370 620 370 "" 0 0 0 "">
  <590 500 590 370 "" 0 0 0 "">
  <590 500 530 500 "" 0 0 0 "">
  <470 500 470 390 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
  <Text 270 630 12 #000000 0 "CIN, COUT 100nF X7R, Ceramic,  50v\nAll resistors 1/4W metal film">
  <Text 280 240 12 #000000 0 "V+ 12V to GND\nV- -8.3V to GND\nBoth bypassed  10uF aluminum electolytic and 100nF ceramic">
</Paintings>

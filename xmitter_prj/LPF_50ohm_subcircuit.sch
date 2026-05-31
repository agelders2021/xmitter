<Qucs Schematic 26.1.1>
<Properties>
  <View=32,33,799,459,2.05352,0,0>
  <Grid=10,10,1>
  <DataSet=LPF_50ohm_subcircuit.dat>
  <DataDisplay=LPF_50ohm_subcircuit.dpl>
  <OpenDisplay=0>
  <Script=LPF_50ohm_subcircuit.m>
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
  <Port IN 1 100 200 -23 12 0 0 "1" 1 "analog" 0>
  <Port OUT 1 700 200 4 12 1 2 "2" 1 "analog" 0>
  <C C1 1 200 280 17 -26 0 1 "300pF" 1 "" 0 "neutral" 0>
  <L L1 1 300 200 -26 -52 0 2 "540nH" 1 "" 0>
  <C C2 1 400 280 17 -26 0 1 "450pF" 1 "" 0 "neutral" 0>
  <L L2 1 500 200 -26 -52 0 2 "540nH" 1 "" 0>
  <C C3 1 600 280 17 -26 0 1 "300pF" 1 "" 0 "neutral" 0>
  <GND * 1 200 320 0 0 0 0>
  <GND * 1 400 320 0 0 0 0>
  <GND * 1 600 320 0 0 0 0>
</Components>
<Wires>
  <100 200 200 200 "" 0 0 0 "">
  <200 200 270 200 "" 0 0 0 "">
  <200 200 200 250 "" 0 0 0 "">
  <330 200 400 200 "" 0 0 0 "">
  <400 200 470 200 "" 0 0 0 "">
  <400 200 400 250 "" 0 0 0 "">
  <530 200 600 200 "" 0 0 0 "">
  <600 200 700 200 "" 0 0 0 "">
  <600 200 600 250 "" 0 0 0 "">
  <200 310 200 320 "" 0 0 0 "">
  <400 310 400 320 "" 0 0 0 "">
  <600 310 600 320 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
</Paintings>

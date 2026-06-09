<Qucs Schematic 26.1.1>
<Properties>
  <View=-112,152,713,611,1.90632,0,0>
  <Grid=10,10,1>
  <DataSet=Balun_6to1_subcircuit.dat>
  <DataDisplay=Balun_6to1_subcircuit.dpl>
  <OpenDisplay=0>
  <Script=Balun_6to1_subcircuit.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
  <.PortSym 40 20 1 0 IN_HOT>
  <.PortSym 40 60 2 0 IN_COLD>
  <.PortSym 40 100 3 0 OUT>
</Symbol>
<Components>
  <Port IN_HOT 1 100 200 -23 12 0 0 "1" 1 "analog" 0>
  <Port IN_COLD 1 100 400 -23 12 0 0 "2" 1 "analog" 0>
  <Port OUT 1 470 240 4 12 1 2 "3" 1 "analog" 0>
  <L_SPICE LP 1 300 300 -64 -26 0 3 "14uH" 1 "" 0 "" 0 "" 0 "" 0>
  <L_SPICE LS 1 370 290 10 -26 0 1 "2.33uH" 1 "" 0 "" 0 "" 0 "" 0>
  <K_SPICE K1 1 400 470 -11 17 0 0 "LP" 1 "LS" 1 "0.95" 1>
  <GND * 1 370 370 0 0 0 0>
  <R R1 1 190 400 -26 15 0 0 "0.5Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
</Components>
<Wires>
  <100 200 300 200 "" 0 0 0 "">
  <100 400 160 400 "" 0 0 0 "">
  <370 240 470 240 "" 0 0 0 "">
  <300 200 300 270 "" 0 0 0 "">
  <300 330 300 400 "" 0 0 0 "">
  <370 320 370 370 "" 0 0 0 "">
  <370 240 370 260 "" 0 0 0 "">
  <220 400 300 400 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
</Paintings>

<Qucs Schematic 26.1.1>
<Properties>
  <View=300,-5,869,400,2.76937,0,244>
  <Grid=10,10,1>
  <DataSet=Driver_tank_subcircuit.dat>
  <DataDisplay=Driver_tank_subcircuit.dpl>
  <OpenDisplay=0>
  <Script=Driver_tank_subcircuit.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
  <.PortSym 40 20 1 0 P1>
  <.PortSym 40 60 2 0 P2>
  <.PortSym 40 100 3 0 P3>
  <.PortSym 40 140 4 0 P4>
  <.PortSym 40 180 5 0 P5>
</Symbol>
<Components>
  <Port P1 1 500 180 -23 12 0 0 "1" 1 "analog" 0>
  <Port P2 1 500 300 -23 12 0 0 "2" 1 "analog" 0>
  <Port P3 1 490 240 -23 12 0 0 "3" 1 "analog" 0>
  <Port P4 1 770 180 4 12 1 2 "4" 1 "analog" 0>
  <Port P5 1 770 300 4 12 1 2 "5" 1 "analog" 0>
  <INDQ LQ1 1 610 210 17 -26 0 1 "{L}" 1 "100" 1 "15 MHz" 0 "Linear" 0 "26.85" 0>
  <INDQ LQ2 1 610 270 17 -26 0 1 "{L}" 1 "100" 1 "15 MHz" 0 "Linear" 0 "26.85" 0>
  <SpicePar SpicePar1 1 370 140 -25 17 0 0 "L=2.0uH" 1>
  <C C1 1 710 240 17 -26 0 1 "25pF" 1 "" 0 "neutral" 0>
  <C C3 1 740 300 -26 17 0 0 "1000pF" 1 "" 0 "neutral" 0>
  <C C4 1 740 180 -26 17 0 0 "1000pF" 1 "" 0 "neutral" 0>
</Components>
<Wires>
  <500 180 610 180 "" 0 0 0 "">
  <490 240 610 240 "" 0 0 0 "">
  <500 300 610 300 "" 0 0 0 "">
  <610 180 710 180 "" 0 0 0 "">
  <610 300 710 300 "" 0 0 0 "">
  <710 270 710 300 "" 0 0 0 "">
  <710 180 710 210 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
</Paintings>

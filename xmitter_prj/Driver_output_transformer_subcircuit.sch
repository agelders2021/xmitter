<Qucs Schematic 26.1.1>
<Properties>
  <View=-218,64,979,731,1.31381,0,0>
  <Grid=10,10,1>
  <DataSet=Driver_output_transformer_subcircuit.dat>
  <DataDisplay=Driver_output_transformer_subcircuit.dpl>
  <OpenDisplay=0>
  <Script=Driver_output_transformer_subcircuit.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
  <.PortSym 40 20 2 0 IN_1>
  <.PortSym 40 60 1 0 IN_2>
  <.PortSym 40 100 3 0 IN_CT>
  <.PortSym 40 140 4 0 OUT_1>
  <.PortSym 20 170 5 0 OUT_2>
</Symbol>
<Components>
  <Port IN_1 1 260 270 -23 12 0 0 "2" 1 "analog" 0>
  <Port IN_2 1 260 440 -23 12 0 0 "1" 1 "analog" 0>
  <INDQ LQ1 1 350 300 -30 -189 0 3 "{INPUT_L}" 1 "100" 1 "15 MHz" 0 "Linear" 0 "26.85" 0>
  <INDQ LQ2 1 350 360 -2 99 0 3 "{INPUT_L}" 1 "100" 1 "15 MHz" 0 "Linear" 0 "26.85" 0>
  <GND * 1 500 330 0 0 0 0>
  <K_SPICE K1 1 190 590 -11 17 0 0 "LQ1" 1 "LQ2" 1 "0.95" 1>
  <K_SPICE K2 1 290 590 -11 17 0 0 "LQ1" 1 "LQ3" 1 "0.95" 1>
  <K_SPICE K3 1 380 590 -11 17 0 0 "LQ1" 1 "LQ4" 1 "0.95" 1>
  <K_SPICE K4 1 460 590 -11 17 0 0 "LQ2" 1 "LQ3" 1 "0.95" 1>
  <K_SPICE K5 1 550 590 -11 17 0 0 "LQ2" 1 "LQ4" 1 "0.95" 1>
  <K_SPICE K6 1 640 590 -11 17 0 0 "LQ3" 1 "LQ4" 1 "0.95" 1>
  <INDQ LQ3 1 400 300 8 -34 1 3 "{OUTPUT_L}" 1 "100" 1 "15 MHz" 0 "Linear" 0 "26.85" 0>
  <INDQ LQ4 1 400 360 14 -31 1 3 "{OUTPUT_L}" 1 "100" 1 "15MHz" 0 "Linear" 0 "26.85" 0>
  <Port OUT_2 1 580 390 4 12 1 2 "5" 1 "analog" 0>
  <Port OUT_1 1 570 270 4 12 1 2 "4" 1 "analog" 0>
  <Port IN_CT 1 260 330 -23 12 0 0 "3" 1 "analog" 0>
  <GND * 1 280 210 0 0 0 0>
  <GND * 1 320 500 0 0 0 0>
  <C C1 1 320 240 17 -26 0 1 "{C_IN}" 1 "" 0 "neutral" 0>
  <C C2 1 320 470 17 -26 0 1 "{C_IN}" 1 "" 0 "neutral" 0>
  <SpicePar SpicePar1 1 90 120 -25 17 0 0 "INPUT_L=4.8uH" 1 "OUTPUT_L=1.14uH" 1 "C_IN=6.0pF" 1>
  <C C3 1 500 270 -26 17 0 0 "1000pF" 1 "" 0 "neutral" 0>
  <C C4 1 500 390 -26 17 0 0 "1000pF" 1 "" 0 "neutral" 0>
</Components>
<Wires>
  <260 330 350 330 "" 0 0 0 "">
  <260 270 320 270 "" 0 0 0 "">
  <350 390 350 440 "" 0 0 0 "">
  <400 330 500 330 "" 0 0 0 "">
  <400 270 470 270 "" 0 0 0 "">
  <400 390 470 390 "" 0 0 0 "">
  <260 440 320 440 "" 0 0 0 "">
  <320 440 350 440 "" 0 0 0 "">
  <320 270 350 270 "" 0 0 0 "">
  <280 210 320 210 "" 0 0 0 "">
  <530 390 580 390 "" 0 0 0 "">
  <530 270 570 270 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
</Paintings>

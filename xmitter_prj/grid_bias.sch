<Qucs Schematic 26.1.1>
<Properties>
  <View=-192,74,1048,765,1.26812,0,0>
  <Grid=10,10,1>
  <DataSet=grid_bias.dat>
  <DataDisplay=grid_bias.dpl>
  <OpenDisplay=0>
  <Script=grid_bias.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
  <.PortSym 40 20 1 0 Control_In>
  <.PortSym 40 60 2 0 Grid_Bias_Out>
</Symbol>
<Components>
  <SpLib X1 1 340 490 -26 48 0 0 "C:/Users/AlAnd/Git Backed Projects/xmitter/xmitter_prj/opa454.lib" 0 "OPA454_5PIN" 0 "auto" 0 "" 0 "" 0>
  <Vdc LM40405 1 530 340 20 -16 1 1 "5 V" 1>
  <GND * 1 530 370 0 0 0 0>
  <R R_pad 1 200 430 -39 -55 0 0 "1 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <GND * 1 190 620 0 0 0 0>
  <GND * 1 320 700 0 0 0 0>
  <Vdc V2 1 320 670 18 -26 1 3 "85V" 1>
  <Vdc V3 1 240 590 18 -26 0 1 "12 V" 1>
  <Port Control_In 1 120 430 -23 12 0 0 "1" 1 "analog" 0>
  <Port Grid_Bias_Out 1 610 500 4 12 1 2 "2" 1 "analog" 0>
  <R R_GL 1 460 450 -26 15 0 0 "22kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_F 1 350 340 -124 -38 0 1 "170 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R_G 1 460 310 -30 -67 0 0 "10 kOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
</Components>
<Wires>
  <120 430 170 430 "" 0 0 0 "">
  <190 620 240 620 "" 0 0 0 "">
  <390 450 430 450 "" 0 0 0 "">
  <540 500 610 500 "" 0 0 0 "">
  <540 450 540 500 "" 0 0 0 "">
  <490 450 540 450 "" 0 0 0 "">
  <230 430 310 430 "" 0 0 0 "">
  <310 550 310 580 "" 0 0 0 "">
  <310 580 390 580 "" 0 0 0 "">
  <390 450 390 580 "" 0 0 0 "">
  <370 490 370 640 "" 0 0 0 "">
  <320 640 370 640 "" 0 0 0 "">
  <240 490 240 560 "" 0 0 0 "">
  <240 490 310 490 "" 0 0 0 "">
  <370 430 420 430 "" 0 0 0 "">
  <420 310 420 430 "" 0 0 0 "">
  <350 370 390 370 "" 0 0 0 "">
  <390 370 390 450 "" 0 0 0 "">
  <350 310 420 310 "" 0 0 0 "">
  <490 310 530 310 "" 0 0 0 "">
  <420 310 430 310 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
</Paintings>

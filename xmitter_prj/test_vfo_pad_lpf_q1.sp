* VFO Buffer — Input stage: 6 dB pad + 5-pole Chebyshev LPF + J310 source follower
*
* AC sweep : verifies filter passband, rolloff at 17.5 MHz, stopband at 42 MHz.
* Transient: 3.3 V CMOS square wave in -> clean sine at Q1 gate and source.
*
* Run:  python run_ngspice.py test_vfo_pad_lpf_q1.sp
*       then open test_vfo_pad_lpf_q1.dat.ngspice in gui_plot.py
*
* Expected AC results (relative to 1 V AC source, normalized):
*   14.175 MHz : ~-7.5 dB  (6 dB pad loss + filter insertion loss ~1.5 dB)
*   17.5  MHz  : ~-13 dB   (pad + ripple-band edge)
*   42.5  MHz  : < -55 dB  (pad + filter 3rd harmonic rejection)

* J310 N-JFET: Idss~35 mA, Vto~-3 V
.MODEL J310 NJF (VTO=-3 BETA=3.5E-3 LAMBDA=5E-3 CGS=15P CGD=5P IS=1E-14)

*---- Source: Si5351A CLK0 --------------------------------------------------
* AC amplitude = 1 V (normalized). Transient = 3.3 V CMOS square wave.
VIN src  0  AC 1  PULSE(0 3.3 0 2N 2N 35.28N 70.55N)
RS  src  pad_a  50      ; Si5351 output impedance (swamped by pad)

*---- 6 dB Pi pad -----------------------------------------------------------
RP1 pad_a  0       150
RP2 pad_a  lpf_in   39
RP3 lpf_in 0       150

*---- 5-pole Chebyshev LPF, fc=17.5 MHz, 0.1 dB ripple, 50 ohm doubly terminated
*    Topology: shunt-C input (C-L-C-L-C)
CF1 lpf_in  0        200P
LF2 lpf_in  lpf_mid  624N
CF3 lpf_mid 0        360P
LF4 lpf_mid lpf_out  624N
CF5 lpf_out 0        200P

*---- Load termination = filter output impedance ----------------------------
RT  lpf_out 0   50

*---- Coupling cap to Q1 gate (0.01 uF) ------------------------------------
CC1 lpf_out q1g  10N

*---- Q1 gate-leak: 1 MOhm to gnd (parallel with RT — negligible at RF) ----
RGL q1g  0  1MEG

*---- Q1: J310 source follower ----------------------------------------------
*    Quiescent: Id~6 mA, Vs~1.67 V, Vds~10.3 V (well in saturation)
J1  q1d  q1g  q1s  J310
VDD q1d  0  DC 12           ; drain supply; ideal source = AC short (good)
RS1 q1s  0  270             ; source resistor; output at q1s

.control
set filetype=ascii

* AC: 1 MHz to 200 MHz, 200 points/decade
ac dec 200 1MEG 200MEG
write spice4qucs.ac1.plot v(pad_a) v(lpf_out) v(q1g) v(q1s)

* Transient: ~14 cycles at 14.175 MHz (enough to see settled sine)
tran 0.5N 1000N
write spice4qucs.tr1.plot v(src) v(lpf_out) v(q1g) v(q1s)
.endc

.end

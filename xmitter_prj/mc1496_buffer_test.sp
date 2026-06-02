* MC1496 VCA Buffer — Standalone ngspice Verification
* 14.175 MHz push-pull driver for 12BY7A grids
* Run: ngspice mc1496_buffer_test.sp
*
* What this verifies:
*   RUN 1  V_AGC=0V   → carrier null (key-up), OUT_P/N pp should be < 5mV
*   RUN 2  V_AGC=10V  → max gain (key-down), OUT_P/N pp ≈ 3.9Vpp each
*   RUN 3  V_AGC sweep 0,2,5,10V → gain law spot check
*
* Hardware context:
*   Input:  Q1S = 0.378Vpeak @ 14.175 MHz (J310 source follower)
*   AGC:    TL071 output (0-10V) → 100kΩ/5.1kΩ divider (4.85%) → MC1496 SIG_N
*           10V → 485mV at sig_n: within MC1496 500mV linear range
*   Loads:  3.9kΩ resistive (datasheet app circuit)
*           Hardware uses 100µH RFC + T1 primary halves (35µH each, FT37-43)
*   Supply: VDD=+12V, VEE=-8.2V (1N4738A zener off grid bias rail)
*

.INCLUDE "mc1496.lib"

*=============================================================
* POWER SUPPLIES
*=============================================================
VDD  vdd  0  DC 12
VEE  vee  0  DC -8.2
CVDD1  vdd  0  10N
CVDD2  vdd  0  10U
CVEE1  vee  0  10N

*=============================================================
* RF CARRIER INPUT  (Q1 J310 source follower output)
*=============================================================
V_Q1S  q1s  0  SIN(0 0.378 14.175MEG 0 0 0)

* DC-block into MC1496 carrier port
CC_CAR  q1s   car_p  10N
* Carrier port minus bypassed to GND
CCAR_N  car_n  0  100N

*=============================================================
* AGC CONTROL (TL071 integrator output, 0-10V range)
* 0V = null/key-up,  10V = max gain
*=============================================================
V_AGC  v_agc_raw  0  DC 0

* Scaling: 100kΩ + 5.1kΩ divider → 4.853%
* V_sig_n = V_agc_raw * 0.04853  (485mV at 10V in)
R_SCALE1  v_agc_raw  sig_n  100K
R_SCALE2  sig_n      0      5.1K

* Signal port + reference at 0V (SIG_P = 0 → null when SIG_N = 0)
R_SIG_P  sig_p  0  10K

*=============================================================
* MC1496 VCA
* X1  SIG_P SIG_N CAR_P CAR_N OUT_P OUT_N VCC VEE BIAS GAIN_RE  MC1496
*=============================================================
X1  sig_p sig_n car_p car_n out_p out_n vdd vee vbias vgain  MC1496

R_BIAS  vbias  vee  1K    ; bias pin → VEE (quiescent bias)
R_RE    vgain  vee  1K    ; gain set RE_ext=1kΩ → Iee≈1mA

*=============================================================
* OUTPUT LOADS: 3.9kΩ to VDD per ON Semi datasheet
* Hardware: replace with L_RFC (100µH, VDD→T1CT) + T1 halves (35µH each)
* Peak swing per output ≈ ±(Iee/2) × 3.9kΩ = ±1.95V  (pp ≈ 3.9V)
*=============================================================
R_LOAD_P  vdd  out_p  3.9K
R_LOAD_N  vdd  out_n  3.9K

*=============================================================
* TRANSIENT SETUP: 500ps step, 5µs = 71 carrier cycles
*=============================================================
.TRAN 500P 5U 0

.control

  *------------------------------------------------------------
  * RUN 1: Key-up — null condition
  *------------------------------------------------------------
  echo ""
  echo "=============================="
  echo "RUN 1: Key-up, V_AGC = 0V"
  echo "=============================="
  run

  meas tran vmax1p MAX v(out_p) FROM=2u TO=5u
  meas tran vmin1p MIN v(out_p) FROM=2u TO=5u
  let vpp1p = vmax1p - vmin1p

  meas tran vmax1n MAX v(out_n) FROM=2u TO=5u
  meas tran vmin1n MIN v(out_n) FROM=2u TO=5u
  let vpp1n = vmax1n - vmin1n

  echo "OUT_P pp [null, expect < 5mV]:"
  print vpp1p
  echo "OUT_N pp [null, expect < 5mV]:"
  print vpp1n

  *------------------------------------------------------------
  * RUN 2: Key-down — max gain
  *------------------------------------------------------------
  echo ""
  echo "=============================="
  echo "RUN 2: Key-down, V_AGC = 10V"
  echo "=============================="
  alter @v_agc[dc] = 10
  run

  meas tran vmax2p MAX v(out_p) FROM=2u TO=5u
  meas tran vmin2p MIN v(out_p) FROM=2u TO=5u
  let vpp2p = vmax2p - vmin2p

  meas tran vmax2n MAX v(out_n) FROM=2u TO=5u
  meas tran vmin2n MIN v(out_n) FROM=2u TO=5u
  let vpp2n = vmax2n - vmin2n

  echo "OUT_P pp [max gain, expect ~3.9V]:"
  print vpp2p
  echo "OUT_N pp [push-pull complement, expect ~3.9V]:"
  print vpp2n

  * Differential swing approximation (add the two half-swings)
  let vdiff_pp = vpp2p + vpp2n
  echo "Differential OUT_P-OUT_N pp [expect ~7.8V through 1:1 T1]:"
  print vdiff_pp

  * Show quiescent output voltage (DC operating point at outputs)
  meas tran vdc_out_p AVG v(out_p) FROM=2u TO=5u
  echo "OUT_P quiescent DC [expect ~10V = VDD - Iee/2 x 3.9k]:"
  print vdc_out_p

  plot v(out_p) v(out_n) title "MC1496 outputs V_AGC=10V (max gain)"
  plot v(q1s) v(out_p) title "Carrier vs OUT_P (phase reference)"

  *------------------------------------------------------------
  * RUN 3: Gain law spot check — 4 representative V_AGC values
  * V_sig_n = V_AGC * 4.853%:  2V→97mV, 5V→243mV, 10V→485mV
  *------------------------------------------------------------
  echo ""
  echo "=============================="
  echo "RUN 3: Gain law spot check"
  echo "=============================="

  alter @v_agc[dc] = 0
  run
  meas tran vppA MAX v(out_p) FROM=2u TO=5u
  meas tran vppA2 MIN v(out_p) FROM=2u TO=5u
  let pp0 = vppA - vppA2
  echo "V_AGC=0V  (sig_n=0mV,  null): OUT_P pp ="
  print pp0

  alter @v_agc[dc] = 2
  run
  meas tran vppB MAX v(out_p) FROM=2u TO=5u
  meas tran vppB2 MIN v(out_p) FROM=2u TO=5u
  let pp2 = vppB - vppB2
  echo "V_AGC=2V  (sig_n=97mV,  linear region): OUT_P pp ="
  print pp2

  alter @v_agc[dc] = 5
  run
  meas tran vppC MAX v(out_p) FROM=2u TO=5u
  meas tran vppC2 MIN v(out_p) FROM=2u TO=5u
  let pp5 = vppC - vppC2
  echo "V_AGC=5V  (sig_n=243mV, transition): OUT_P pp ="
  print pp5

  alter @v_agc[dc] = 10
  run
  meas tran vppD MAX v(out_p) FROM=2u TO=5u
  meas tran vppD2 MIN v(out_p) FROM=2u TO=5u
  let pp10 = vppD - vppD2
  echo "V_AGC=10V (sig_n=485mV, saturated): OUT_P pp ="
  print pp10

  echo ""
  echo "Gain law summary (OUT_P pp in Volts):"
  echo "  V_AGC=0V  : "
  print pp0
  echo "  V_AGC=2V  : "
  print pp2
  echo "  V_AGC=5V  : "
  print pp5
  echo "  V_AGC=10V : "
  print pp10

.endc

.END

* 12HG7 Koren model validation
* Plate characteristic family at Vs=135V (datasheet page 2)
* Vg = -2.5 to 0 in 0.5V steps; Vp = 0..500V

.INCLUDE "12hg7_koren.lib"

V_PP PP 0 DC 0
V_AMM PP P DC 0
V_S  S  0 DC 135
V_G  G  0 DC 0

X1 P S G 0 12HG7_K       ; A S G K (cathode grounded)

.DC V_PP 0 500 5 V_G -2.5 0 0.5

.control
run
wrdata 12hg7_pchar.dat -i(v_amm) i(v_s) v(g)
echo "Wrote 12hg7_pchar.dat (cols: Vp, Ip, Vp, Is, Vp, Vg)"
.endc

.END

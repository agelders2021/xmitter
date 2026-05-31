* 12BY7A Koren model validation
* Plate characteristic family at Vs=180V (datasheet page 3 comparison)
* Outer: Vg = -8 to +0 in 1V steps; Inner: Vp = 0..500

.INCLUDE "12by7a_koren.lib"

V_PP PP 0 DC 0
V_AMM PP P DC 0          ; 0V ammeter - i(v_amm) is plate current
V_S  S  0 DC 180
V_G  G  0 DC 0

X1 P S G 0 12BY7A_K      ; A S G K (cathode grounded)

.DC V_PP 0 500 5 V_G -8 0 1

.control
run
wrdata 12by7a_pchar.dat -i(v_amm) i(v_s) v(g)
echo "Wrote 12by7a_pchar.dat (cols: Vp, Ip, Vp, Is, Vp, Vg)"
.endc

.END

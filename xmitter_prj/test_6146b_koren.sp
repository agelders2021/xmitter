* 6146B Koren model validation
* Plate characteristic family at Vs=200V (datasheet Fig.2 comparison)
* Outer: Vg = -50, -40, ..., +10  Inner: Vp = 0..800

.INCLUDE "6146b_koren.lib"

V_PP PP 0 DC 0
V_AMM PP P DC 0          ; 0V ammeter -- i(v_amm) is plate current
V_S  S  0 DC 200
V_G  G  0 DC 0

X1 P S G 0 6146B_K       ; A S G K  (cathode grounded)

.DC V_PP 0 800 5 V_G -50 10 10

.control
run
* dump everything to one file in CSV-ish form
wrdata 6146b_pchar.dat -i(v_amm) i(v_s) v(g)
echo "Wrote 6146b_pchar.dat  (cols: Vp, Ip, ?, Is, ?, Vg)"
.endc

.END

# Rev D pre-layout design review

**Purpose of this document.** This is a handoff package for a thorough schematic-level
review of the xmitter project at Rev D branch, immediately before committing any of
the three PCBs to layout. The review should flag design errors, overlooked
interactions, unrealistic component choices, poor safety margins, and any gotchas
that will be expensive to find in silicon rather than in paper. The accompanying
netlist files are the ground truth; this .md is only the narrative that explains
intent and highlights what to look at.

**Supporting materials.** Expected to be delivered alongside this file.
**This document (`revD_prelayout_review_handoff.md`) is the authoritative
current state;** supporting docs vary in freshness as noted:

Netlists (authoritative — regenerated 2026-10-23):

- `KiCAD/analog/analog.net` — analog control board netlist
- `KiCAD/ss_pa/ss_pa.net` — SS PA board netlist
- `KiCAD/Output LPF/Output LPF.net` — output LPF board netlist
- `KiCAD/frontpanel/frontpanel.net` — frontpanel board netlist
- `KiCAD/protoshield/protoshield.net` — Metro-mounted protoshield netlist

Current (updated 2026-10-23 for Rev D Option-C):

- `Documentation/i2c_bus.md` — I²C address assignments, HV/LV bus
  architecture, STEMMA reroute, level-shifter placement
- `Documentation/revD_interconnect.md` — cross-board signal map,
  board inventory

Partially current (contain targeted "see handoff doc" banners pointing
to the current state for recently-changed sections):

- `Documentation/Master_Description.md` — project narrative
- `Documentation/ss_pa.md` — SS PA topology, operating point, fault
  chain (banner notes Option-C changed +3.3 V → +5 V ss_pa rail and
  R10 10 K → 6.8 K; everything else in the doc still applies)
- `Documentation/cw_envelope_keyer.md` — envelope-generation firmware
  (banner notes envelope DAC is MCP4922 SPI in Rev D, not MCP4728
  I²C; STEMMA chain references are historical)
- `Documentation/front_panel_interface.md` — frontpanel umbilical
  pin map (banner notes I²C QT STEP/FUNC encoders are historical,
  current design uses only the MBL-600 RS-422 encoder)

Historical reference only (tube-PA upgrade path, not fabricated):

- `Documentation/pa_cathode_monitor.md`, `grid_bias.md`

Component datasheets:

- `Documentation/Components/Omron_05-18-2026_G6K-T1_Datasheet_EN.pdf` — band-select relay
- `Documentation/Components/Littlefuse 3568 holder.pdf` — Keystone 3568 fuse holder

---

## Project at a glance

- **What it is.** A 20 m CW transmitter (full build, not just 20 m band — see LPF
  bands below). Target: QRP ~10 W into 50 Ω from an IRF510 push-pull output stage
  running on shack 13.8 V. Hand-built by one hobbyist (ham radio operator / hardware
  designer, long-session collaborator style). Educational and personal use, no
  commercial intent.
- **Where we are.** Rev D is the current active branch. Rev A was fabricated
  2026-07-14; its MC1496 balanced-modulator keyer failed on built hardware, which
  drove the Rev B pivot (DGFET keyer + eventual full solid-state PA replacing the
  originally planned push-pull 6146B tube amp). Rev C was the DGFET + tube-PA
  intermediate; Rev D is DGFET + solid-state throughout. No Rev D hardware has
  been fabricated yet. This review is the gate.
- **Toolchain.** Hardware: KiCad 10, QUCS-S 26.1.1 (for simulations). Firmware:
  ESP-IDF v5.4.4 LTS targeting Adafruit Metro ESP32-S3. Firmware is not yet
  scaffolded, but any firmware architecture observations are welcome.
- **Workflow preferences.** Over-engineering and hypothetical future-proofing are
  not valued. The current design is intended to be the minimum viable xmitter;
  one tube-PA upgrade path is retained (connectors marked DNP, routing in place)
  but should not drive any current design decision.

---

## Topology summary

Signal chain from carrier generation to antenna, left to right:

- **Si5351 clock gen** (I²C, on analog board) → carrier RF, ~14.0 MHz for 20 m
- **DGFET VCA** (Q2 dual-gate FET on analog board, 40673): G1 = RF from Si5351
  (biased to +2.45 V via 39K/10K from +12 V, 100 nF bypass; R21 1 MΩ feed to
  G1; C26 AC-couples RF), G2 = envelope voltage from MCP4921 SPI DAC via an
  **LM7171 offset-mute op-amp (U10)** that remaps DAC 0–5 V to G2 −3.1 V to
  +5 V. The DAC-at-zero state drives G2 well below V_TO (−2 V), fully cutting
  off the DGFET (sim-verified ~10⁹ on/off ratio, no DC drain current in
  key-up). **No separate KEY_UP net or Q11/Q12 PNP mute transistors** — mute
  is intrinsic to the signal path via the op-amp's negative DC offset.
  Keyed-state operating point: I_D ≈ 13 mA, V_S ≈ 2.88 V, V_D ≈ 5.85 V.
- **32 MHz RC snubber** (R1 = 50 Ω series, C1 = 100 pF shunt) on DGFET drain —
  tames VHF ringing
- **Chebyshev LPF** (small, on-analog) — removes mixing products/sidebands from the
  DGFET output
- **Op-amp follower U1** (LM7171) — unity gain default; gain hedge via R_f = 3k
  installed + R_g unpopulated, user can populate R_g for gain = 4 if more PA drive
  is needed
- **LM7171 push-pull driver stage** (U4/U5) → differential RF to the SS PA
- **Analog ↔ SS PA umbilical** (J31 on analog, J4 on ss_pa, RJ45) carries
  PA_Bias_A/B, DRIVER_BIAS, Source_Sense_A/B, FAULT_N, GND. RF goes separately
  over coax (J3/J4 on ss_pa).
- **SS PA board**: BS170 PP pre-driver (Q203/Q204) → IRF510 PP output (Q3/Q4)
  with per-FET drain-gate feedback and 0.11 Ω unbypassed source resistance →
  T204 output transformer (BN43-202, 2:3) → RF OUT
- **Analog ↔ Output LPF umbilical** (J2 both ends, RJ45) carries +12 V + GND +
  4 band-select coil drives (RLY_40/20/17/15)
- **Output LPF board**: 4-band LPF bank (40/20/17/15 m), one DPDT G6K relay per
  band, 7-pole Chebyshev per band → antenna J1

---

## Boards

### analog (`KiCAD/analog/`)

**Role:** Control + RF front-end + bias + power regulation + umbilicals to every
other board.

**Sub-sheets:** `analog.kicad_sch` (root), `vfo_complete.kicad_sch` (Si5351 →
DGFET → RC snubber → Chebyshev LPF → U1 follower → LM7171 PP),
`arduino.kicad_sch` (Metro socket, MCP4728 I²C DAC, MCP4921 SPI DAC, control
relays, CD14538B heartbeat watchdog, RJ45 umbilicals J2/J4/J31/J35),
`interface.kicad_sch` (frontpanel umbilical + RS-422 termination + PCF8575
expander), `dac.kicad_sch` (MCP4728 I²C DAC + MCP4922 SPI DAC + U10 LM7171
offset-mute op-amp with 5.1 V Zener reference and R20/R23 feedback network;
replaces the retired Q11/Q12 PNP mute path),
`power.kicad_sch` (regulators + supply chain).

**DAC assignments:**

- **MCP4922 (U4, SPI, 2-ch):** ch A = envelope (to DGFET G2), ch B = DRIVER_BIAS (to
  ss_pa BS170 bias)
- **MCP4728 (U3, I²C @ 0x67, 4-ch):** ch A/B = PA_Bias_A / PA_Bias_B (IRF510 pair
  on ss_pa), ch C/D = GRID_CTL_A/B (tube-PA upgrade path, kept routed but
  DNP output connectors — see "tube-PA upgrade path" below)

**Power rails:**

- Shack supply input (J5, nominally 13.8 V) → **3 A slow-blow blade fuse
  (Keystone 3568)** + **1N5822 Schottky in series** for reverse-polarity
  protection → protected +13.8 V bus → also feeds heartbeat relay K5 → J33
  → ss_pa drain
- U8 LM2940CT-12 → +12 V (op-amp +rail, G6K LPF coils via J2 umbilical, LT1054
  inverter input)
- U7 LT1054 switched-cap inverter → −12 V (LM7171 negative rail)
- U6 LM2940CT-5.0 → +5 V (I²C bus HV side, SPI 5V side via 74HCT125,
  Si5351 / MCP4728 / MCP4922 / PCF8575 / CD14538B / AM26LS32ACN,
  frontpanel umbilical pin 4)
- U13 MCP1700x-330 → +3.3 V (local-only; feeds only the Adafruit #757 shifter
  LV side pin 1 — Metro provides its own 3.3 V internally)
- **Note:** Earlier Rev C design had a second LT1054 (U9) as a +28 V voltage
  doubler for the big RelComm reed relay coils. **This is deleted in Rev D** —
  the LPF now uses 12 V G6K signal relays, so the +28 V rail is gone from every
  sheet.

**I²C bus voltage architecture (changed from first review pass):**

The Metro's native I²C is 3.3 V but every I²C slave in the system (Si5351,
MCP4728, PCF8575 ×2, MCP4725 on frontpanel, CD74HC4066 on ss_pa) runs
cleanest at 5 V — especially the MCP4728, whose output voltage range sets
the IRF510 bias range and needs the full 0–5 V span to cover the Vgs(th)
spec. Rather than put each slave on its own level shifter, Rev D uses a
single-point translation:

- **Adafruit #757 BSS138 breakout (U2 on analog)** sits at the Metro I²C
  entry on the analog board. LV side (pins 1-6) = +3.3 V, HV side (pins
  7-12) = +5 V. 10 K pull-ups on both sides are built in.
- Pull-ups on the Si5351 and MCP4728 breakouts (which also tie to their
  own VIN) should be **depopulated** so the shifter is the only
  pull-up source on the HV bus — this is a manual breakout
  modification before populating the board; worth calling out in the
  assembly notes.
- STEMMA QT connectors on MCP4728 and Si5351 breakouts are **no longer
  used for I²C**. Those breakouts get both power and I²C from PCB
  header pins only. The 0 Ω jumpers that would route STEMMA to those
  breakouts remain unpopulated.
- Metro's STEMMA QT port now routes directly to the **frontpanel
  rotary-encoder chain** (3.3 V STEMMA-native devices on the Metro's
  native 3.3 V bus — same electrical bus as the LV side of the shifter).

**SPI level shifting to MCP4922 (new):**

The MCP4922 runs at 5 V VDD (its V_IH = 0.7 × VDD = 3.5 V doesn't tolerate
3.3 V logic directly). Rather than drop MCP4922 to 3.3 V (which would then
cap its V_OUT at 3.3 V and halve the useful envelope / DRIVER_BIAS range),
Rev D runs it at 5 V and translates the Metro's 3.3 V SPI up through a
**74HCT125 quad buffer (U9, in the custom `xmitter` library)**:

- 74HCT125 at VCC = +5 V, all four OE̅ pins tied to GND (always enabled).
- Four TTL-level inputs (74HCT family V_IH = 2 V @ 5 V VDD) accept
  Metro's 3.3 V HIGH as a valid HIGH.
- MOSI → U9 pin 2 → pin 3 → U4 SDI (pin 5)
- SCK → U9 pin 5 → pin 6 → U4 SCK (pin 4)
- CS_DAC → U9 pin 9 → pin 8 → U4 CS̅ (pin 3)
- DAC_LDAC_N → U9 pin 12 → pin 11 → U4 LDAC̅ (pin 8)
- DAC_SHDN_N remains driven by PCF8575 at 5 V (not time-critical, I²C
  write latency is fine for shutdown control).

**DGFET keyer mute topology (changed 2026-10-23):**

Prior design: Q11/Q12 PNP level-shifter clamped G2 to ~0 V (via a 220 Ω
source resistor R9 on the DGFET source), controlled by a KEY_UP net
from the Metro. Sim showed this did NOT cut off the DGFET — G1
biased at 0 V keeps the lower cascode device on, forcing an
equilibrium at I_D ≈ 5 mA leaking through the stack. Only ~2.6:1
on/off ratio, unusable for CW mute.

Current design: an LM7171 (U10, on `dac.kicad_sch`) is wired as a
non-inverting amp with a positive DC reference on the inverting
summing node. Transfer function: `V_G2 = V_DAC × 1.62 − 3.13`.

- Reference node X: fed from a 1N4733A 5.1 V Zener (D2) via R24 = 1 kΩ
  from +12 V; summing-node divider R25 = 1 kΩ, R32 = 100 kΩ gives
  V_X ≈ 5.05 V at the summing side.
- Feedback: R20 = 6.2 kΩ (feedback) and R23 = 10 kΩ (reference input
  to summing node) → gain `(1 + R20/R23) = 1.62` on the DAC side,
  offset `−V_ref × R20/R23 ≈ −3.1 V` at V_DAC = 0.
- DAC at 0 V → G2 ≈ −3.1 V (0.1 V margin below −3 V target, 1.1 V
  below 40673 V_TO = −2 V) → clean DGFET cutoff
- DAC at +5 V → G2 ≈ +5.0 V (matches prior keyed-state operating
  point, well below 40673 V_G2S_peak = +6 V spec)
- Op-amp output needs to swing −3.1 V to +5 V — well within LM7171's
  ±10 V output on the existing ±12 V rails
- **KEY_UP net eliminated** — mute is intrinsic to the signal path.
  The firmware controls RF enable/disable solely by what it writes
  to the MCP4921's envelope channel: write 0 → V_G2 = −3.1 V → DGFET
  off; write envelope sample → DGFET follows the raised-cosine shape.
- Sim-verified in `xmitter_prj/dgfet_opamp_offset_mute.cir`

Rationale and sim data for the topology choice: see git log on
`revD` branch commits touching U10 / R20 / R23 / R32 / D2 (1N4733A).

**Si5351 bringup isolation switch (new, but currently mis-wired — see
"Known open items"):**

A DPDT slide switch (SW1) is placed on the HV-side SDA/SCL bus right at
the Si5351 header, so Si5351 can be electrically removed from the I²C bus
during bringup without unseating the breakout. Intent is DPST behavior
(both lines break together) using a DPDT body. See open items for current
wiring issue.

**Umbilicals from analog (RJ45, 8P8C shielded, T568B pair-aware):**

- **J2 → Output LPF:** pins 1-4 = RLY_15/17/20/40 (open-drain FET sinks on LPF
  side), pins 6/7/SH = GND, pin 8 = **+12 V** (coil supply for LPF relays)
- **J31 → ss_pa:** pins 1/2/3 = Source_Sense_A, Source_Sense_B, FAULT_N; pins
  4/5 = PA_Bias_A_Raw / PA_Bias_B_Raw; pin 6 = DRIVER_BIAS; pins 7/8/SH = GND
- **J4 → frontpanel:** PCF8575 I²C expander + MBL-600 differential rotary encoder
  + display power (see `front_panel_interface.md`)
- **J35 → future tube PA:** GRID_CTL_A, GRID_CTL_B, I_CATHODE_A, I_CATHODE_B,
  GRID_BLOCK_CRASH + GND + SH. All signals are electrically present and routed
  but the physical J35 connector is **DNP** by default; populate only if adding
  a tube PA later.

**Test points:** 21 TPs cover tube-PA control bus (TP1/2/5/6/7),
SS PA bias/sense/fault (TP3/4/12/13/14/15), keyer/envelope/RF chain
(TP10/20/21), DAC control (TP8/9), relay driver gates (TP11/16/17/18), hardware
watchdog (TP19). All DC-level TPs, no hot-RF TPs on analog.

### ss_pa (`KiCAD/ss_pa/`)

**Role:** Power amplifier. QRP Labs 10 W Linear PA kit RF topology, copied with
minimal modifications; see `ss_pa.md`. Modifications vs stock kit: bias is
sourced from analog's MCP4728 (not an on-board trimpot), source-sense taps feed
analog's ADC for closed-loop monitoring, fault_shutdown chain is self-latching
instead of simple over-current trip.

**Sub-sheets:** `ss_pa.kicad_sch` (root), `pa_stage.kicad_sch` (BS170 pre-driver
+ IRF510 PP + transformers + L18 bias RFC + source-sense taps),
`fault_shutdown.kicad_sch` (LM393 self-latching + CD74HC4066 bias switch + startup
auto-reset + 100K pulldowns on PA_Bias_A/B + local LM2936Z-5.0 LDO for the
entire ss_pa logic rail).

**Transformers (hand-wound):**

- T201 — BN61-2402 secondary-CT, input xfmr (DRIVER_BIAS center-tap)
- T202 — BN61-2402 primary-CT, interstage BS170 → IRF510 (PA_Bias_x center-tap)
- T203 — T50-43 bifilar, drain supply feed (bifilar winding, both windings
  carry drain current, +13.8 V center node)
- T204 — BN43-202, 2:3 output transformer (IRF510 drains → 50 Ω antenna match)
- L18 — BN43-2402 bias RFC

**Fault chain (summary):** On overcurrent, LM393 (U1) comparator trips, latches
LOW via self-latching V_REF path, and asserts FAULT_N. CD74HC4066 (U2) analog
switch opens the PA_Bias_A/B path to the IRF510 gates → PA_Bias collapses to
0 V in ~18 µs via R12/R19 100 K pulldowns → IRF510s cut off → PA stops drawing
current. Reset: startup cap + diode (C12 1 µF + D1 1N4148) give power-on
auto-reset only; latch has to be released by cycling supply (intentional —
makes the operator intervene after a fault). The Metro also reads FAULT_N
digitally and logs/displays.

**V_REF divider sized for +5 V supply:** R11 = 100 K (positive-feedback /
top of divider, between FAULT_N and V_REF), R10 = **6.8 K** (V_REF to GND) →
V_REF ≈ 0.318 V at V+ = 5 V (trip threshold ~3.2 A at R_sense = 0.1 Ω).
Rev C ran this at 3.3 V with R10 = 10 K and the same R11; the 10 K → 6.8 K
swap preserves the original 0.3 V trip threshold under the new +5 V rail.

**FAULT_N level translation (new):** FAULT_N is pulled up to +5 V on ss_pa
(R9 = 10 K) so it reliably drives CD74HC4066's control inputs. Metro ESP32-S3
pins are not 5 V tolerant, so a 10 K + 20 K resistor divider on the **analog
board** (R3 = 10 K series, R4 = 20 K to GND) scales FAULT_N down to 3.33 V
HIGH at the Metro input. The divider output is called FAULT_N_CLEAN.

**Supply:** +13.8 V direct from shack (via analog's heartbeat-gated K5 relay).
Local **+5 V** LDO (U13 LM2936Z-5.0/NOPB — TO-92, 40 V max input, 50 mA, ultra-
low Iq) powers all ss_pa logic: LM393 V+ (5 V), CD74HC4066 VCC (5 V), FAULT_N
pullup (R9 to +5 V). No +3.3 V rail on ss_pa anymore. +13.8 V appears on ss_pa
only — not on analog, not on LPF.

**PCB stackup:** 4 layers, inner planes for GND and +13.8 V, outer signal +
GND pour. Dense RF around the IRF510s, VHF-tuned feedback network, and
high-current drain path justify the 4-layer choice.

**Test points:** TP1 +5 V, TP2/3 PA_Bias_A/B (post-U2 switch), TP4 RF-In
(J3 center), TP5 RF-Out (J1 center), TP6/7 IRF510 drains (hot RF),
TP8-11 GND probe-return pads paired 1:1 with hot-RF TPs for scope-probe
short-ground discipline.

### Output LPF (`KiCAD/Output LPF/`)

**Role:** 4-band low-pass filter bank + band select, between ss_pa output and
antenna.

**Bands:** 40 m / 20 m / 17 m / 15 m. **10 m was deliberately dropped** — the
user has a main transceiver that covers 10 m, and dropping it saved one entire
bank (3 inductors, 4 caps, 1 relay, 1 coil driver, 1 flyback, 2 swamps).

**LPF design:** 7-pole 0.1 dB Chebyshev at 50 Ω per bank. Target cutoffs chosen
so that fc / top-of-band ≈ 1.15-1.20× and 2fh / fc ≈ 1.7× (giving ~40 dB of
2nd-harmonic rejection on the 7-pole response). Component values:

- 40 m: fc ≈ 8.0 MHz; C_outer = 470 pF, C_center = 820 pF;
  L_outer ideal 1416 nH / actual 1444 nH / 19 T on T50-6;
  L_center ideal 1565 nH / actual 1600 nH / 20 T
- 20 m: fc ≈ 17.1 MHz; C_outer = 220 pF, C_center = 390 pF;
  L_outer 662/676 nH / 13 T; L_center 733/784 nH / 14 T
- 17 m: fc ≈ 20.9 MHz; C_outer = 180 pF, C_center = 330 pF;
  L_outer 542/576 nH / 12 T; L_center 599/576 nH / 12 T (same-turn
  simplification, ~5 % mismatch accepted)
- 15 m: fc ≈ 25.0 MHz; C_outer = 150 pF, C_center = 270 pF;
  L_outer 452/484 nH / 11 T; L_center 499/484 nH / 11 T (same-turn
  simplification)

All inductors are hand-wound on T50-6 (A_L = 4.0 nH/N²). User is open to swapping
to T68-6 (A_L = 5.7 nH/N²) for easier winding; turn counts would drop ~15-20 %
if that swap is made but the schematic footprints currently target T50-6.
Footprints `xmitter:T50-6_Vertical_HandWound` and `T50-6_Flat_HandWound` are in
use.

**Band select:** One **DPDT Omron G6K-2P-Y-T1 DC12** per band — through-hole,
12 V coil, high-temp variant from datasheet. K1 = 15 m, K2 = 17 m, K3 = 20 m,
K4 = 40 m. Pole 1 switches the LPF output, Pole 2 switches the LPF input. The
NC (pin 2, pin 7) side of each pole terminates to GND via a 50 Ω swamp (R2-R9),
so when a bank is unselected the LPF presents a properly-terminated 50 Ω
two-port on both sides — kills LC-ringing on the unselected LPF and keeps the
LPF's own stopband working as isolation against leakage. When the bank IS
selected, the arm swings to NO and the 50 Ω swamp is physically disconnected
from the signal path (no active-path insertion loss).

**Coil drivers:** 2N7000 (Q1/Q5/Q8/Q10) one per band, open-drain to GND from a
+12 V coil supply. 1N4148 flyback (D7/D8/D9/D11) across each coil, cathode on
+12 V. Gate network per driver: 10 K series from analog's RLY_xx signal + 10 nF
X7R debounce to GND + 470 K pulldown to GND. The RLY_xx logic from the Metro
(via analog's J2) drives each 2N7000 through the gate network.

**T/R relay (K5):** fifth G6K DPDT, added at the LPF output. Pole 2 switches
the antenna port (J1) between RF_FINAL_OUT (TX side, from the LPF bank
outputs — energized) and the Schottky-protected RX port (de-energized,
fail-safe default). Pole 1 provides TX/RX state sense back to analog on
pins J2.6 (RECEIVE_N) and J2.7 (TRANSMIT_N): both signals use the PCF8575
internal pullup for the inactive HIGH state and the K5 pole-1 contact to
pull the active one LOW. Coil driver Q10 (2N7000) with 1N4148 flyback D10.

**RX port protection:** antiparallel Schottky clamp pair D1/D2 (1N5711) +
R19 10 Ω series fuse resistor between K5 pin 7 (NC, antenna in RX mode)
and the RX SMA J3. Clamps RX line to ±~0.4 V on any T/R-relay fault or
nearby strong-signal transient; the 10 Ω series limits peak current into
the clamp during a hard fault.

**No sub-sheets.** Everything is on a flat root schematic.

**PCB stackup:** 2-layer is probably sufficient for QRP HF — discussed and
decided this way. Smaller board than ss_pa; no high-current switching other than
the briefly-dissipated leakage power on the swamps.

### frontpanel (`KiCAD/frontpanel/`)

**Role:** Operator interface — 20×4 character LCD, optical rotary encoder with
RS-422 differential outputs, I²C button expander, LCD backlight RGB control,
local 3.3 V regulation. Umbilical to analog via RJ45 (J4 analog ↔ J1
frontpanel, Amphenol RJE1D-188-21401 shielded jacks). Schematic unchanged in
substance from the pre-Rev-D plan since the DGFET/SS-PA pivot only affected
the RF chain, not the control umbilical.

**Schematic complete, PCB footprints placed but not routed.** Same pre-layout
gate as the other three boards.

**Contents:**

- J1 — 8P8C_Shielded RJ45 (Amphenol RJE1D-188-21401) umbilical to analog
- J2 — 3-pin header (likely LCD contrast / backlight signals)
- J4 — 4-pin screw terminal (external connections, likely paddle or auxiliary)
- U1 — Adafruit PCF8575 I²C 16-bit I/O expander (button matrix / discretes)
- U2 — MCP4725 I²C 12-bit single-channel DAC (likely LCD contrast voltage)
- U4 — MCP1700x-330 3.3 V LDO (local regulation on frontpanel)
- LCD1 — WH2004A 20×4 character LCD module
- ENC3 — Encoder_5734 optical rotary encoder with differential outputs
  (feeds the MBL-600 RS-422 pair on the umbilical)
- Q1 / Q2 / Q3 — 2N7000 FETs driving RGB LCD backlight channels (gates =
  RED / GREEN / BLUE from Metro, drain = backlight LED cathodes)
- 5× resistors — R1 200 Ω (likely LCD contrast series), R2 / R3 120 Ω (RS-422
  termination for the MBL-600 differential pair back on the analog side —
  verify polarity and placement), R4 10 kΩ (pull-up, likely encoder
  interrupt), R5 330 Ω (LED current limit)
- 4× C_Polarized 10 µF + 4× 100 nF ceramic — standard bypass + LDO caps
- 2× 1 µF — likely MCP4725 output filter / LCD contrast smoothing
- 9× xTP test points for LCD backlight debug (VO / RED_IN / BLUE_IN /
  GREEN_IN / RED_OUT / BLUE_OUT / GREEN_OUT / ENABLE / GND)

**Signals that cross the frontpanel boundary (global labels in the netlist):**

- RED, GREEN, BLUE — backlight color logic from Metro
- MBL_A_P, MBL_A_N, MBL_B_P, MBL_B_N — RS-422 differential encoder channels
  (received back on analog by AM26LS32ACN receiver, terminated with
  120 Ω on the analog side per MBL-600 convention)
- ENC_INT_RAW → ENC_INT_CLEAN — encoder interrupt, with some cleanup
  (RC or Schmitt?) on frontpanel before going out
- SDA, SCL — I²C bus (for PCF8575 + MCP4725)

**I²C address check:** Frontpanel has PCF8575 (default 0x20 or 0x21) and
MCP4725 (default 0x62 or similar). Verify these don't collide with the
analog-side I²C devices (Si5351 0x60, MCP4728 reprogrammed to 0x67). See
`i2c_bus.md`.

**Known footprint-sourced caveat:** The RJE1D-188-21401 RJ45 footprint has
UNVERIFIED pin coordinates — see `front_panel_interface.md` "Open Items"
section before PCB fab. The schematic symbol / pin numbering is from the
datasheet, but the physical footprint pad positions have not been checked
against actual stock.

### protoshield (`KiCAD/protoshield/`)

**Role:** Adafruit Proto Shield (PID 2077) stacked on the Metro ESP32-S3.
Carries the Metro socket plus all GPIO signal-conditioning (series Rs,
pull-ups, RC filters, Zener clamps, bypass caps) between the Metro's
3.3 V GPIO rails and the outside-world screw-terminal boundaries.

**Schematic complete, PCB not yet laid out.** This is the last schematic
in the review scope.

**Contents:**

- U2 — Metro_ESP32S3 (socketed, not soldered — the Metro is a module)
- J1 - J8 — screw-terminal headers (2×, 3×, 4× pin variants) that bring
  all external I/O onto the shield
- 9× 100 nF bypass caps (C1, C4-C9) distributed across the shield for
  rail decoupling
- 2× 10 nF (C2, C3) — RC filtering on noise-prone inputs (likely
  paddle contacts to debounce RFI)
- 12× resistors: 1 kΩ series-protection on contact inputs
  (R1/R2/R5/R6/R9/R13/R14), 10 kΩ pull-ups
  (R8/R10/R11/R12), 1 kΩ (R7 — ENC_INT series feed to ENC_INT_FINAL),
  330 Ω (R?)
- 5× 1N4728A (3.3 V zener) clamps on analog-sense inputs — one each on
  I_CATHODE_A, I_CATHODE_B (future tube PA, DNP in use but kept routed),
  Source_Sense_A, Source_Sense_B (ss_pa IRF510 source current → Metro
  ADC), and one spare / TR_SENSE line

**Signals that cross the shield boundary (global labels in the netlist):**

- CW paddle: PADDLE_A, PADDLE_B
- RS-422 differential rotary encoder: MBL600_A, MBL600_B
- Encoder interrupt: ENC_INT → series R7 (1 kΩ) → ENC_INT_FINAL to Metro
- RESET_N (user reset button)
- T/R interlock: TR_SENSE
- SS PA fault: FAULT_N
- SS PA bias telemetry: Source_Sense_A, Source_Sense_B (0-500 mV
  range into Metro ADC, 1N4728A clamp)
- Tube-PA upgrade signals (routed but unused for first fab):
  I_CATHODE_A, I_CATHODE_B, GRID_BLOCK_CRASH
- SPI to MCP4921 envelope DAC: SCK, MOSI, CS_DAC
- I²C DAC load-pulse: LDAC_4728 (also DAC_LDAC_N)

**Where this sits in the system.** Metro-mounted. The protoshield's screw
terminals are the actual signal boundary between the Metro and the analog
board — on the analog board side, matching screw-terminal headers (J3,
J9, J12-J14, J20-J22) take over. Everything between the Metro's socket
pins and the external world passes through the protoshield's conditioning
network.

**Metro has no PCB footprint of its own.** The Adafruit Metro ESP32-S3 is
a physical module that plugs directly into the protoshield (the shield's
pin headers mate with the Metro's headers). The protoshield is the only
PCB in this review that physically carries the Metro. All inter-board
wiring to the Metro is routed through the protoshield's screw terminals,
not through any Metro-side footprint. On the analog board, where
protoshield-side signals arrive, they land on screw-terminal headers
(J3, J9, J12-J14, J20-J22) with matching conductor labels. Reviewer:
no need to look for a Metro footprint anywhere else in the netlists.

---

## Design decisions worth highlighting

- **DGFET keyer (not MC1496).** Original design used MC1496 balanced modulator
  for CW keying. Built hardware (Rev A) failed — minimal output, suspected
  balance-trim feedback issue. Pivot to DGFET VCA was the response. Envelope-
  generation firmware (`cw_envelope_keyer.md`) is topology-agnostic for the
  parts that matter (raised-cosine LUT, predistortion, 25 µs tick, core-1
  pinned task) — DAC/LUT math still applies; only the hardware MC1496-specific
  sections of that doc are historical.
- **Solid-state PA (not tubes).** Push-pull 6146B tube amp was the original
  plan. QRP-first was adopted as a philosophy change — tubes/HV/HV supply/
  cathode monitor/grid bias generator are all shelved. The analog board retains
  all tube control signals electrically present but the physical output
  connectors (J17-J19, J23/J24, moved to J35) are DNP. Un-DNP them to re-enable
  if adding a tube PA later. See `pa_cathode_monitor.md`, `grid_bias.md` for
  the historical design.
- **ss_pa is a near-verbatim copy of QRP Labs 10 W Linear PA kit RF topology.**
  Reviewer should recognize this is a proven, published design, not novel.
  Modifications vs stock kit are: bias from analog DACs (not on-board trimpot),
  source-sense feed to analog ADC, self-latching fault_shutdown with
  CD74HC4066 bias switch.
- **DPDT G6K replaces earlier RSS-SR042P RF reed.** Original Rev C LPF used
  large RelComm RSS-SR042P SPST relays (28 V coil, metal-case shielded, 500 W
  rated, ~22 × 8 mm per device, user has these from junk box). Analysis showed
  the big relays dominated board area and the 28 V coil required a dedicated
  voltage doubler. Swap to G6K DPDT allowed: one relay per band (vs two), no
  +28 V rail, much smaller board. The RelComm reeds have no planned future
  use in this project.
- **Swamp Rs on pin 7 (NC) at 50 Ω.** Design iteration: originally swamps were
  1 kΩ on the always-connected pin, giving 0.4 dB active-path loss. Moving to
  pin 7 (NC) made them "unselected-only" and dropped the active-path loss to
  zero. Then changing from 1 kΩ to 50 Ω made the unselected LPF a properly
  terminated 50 Ω two-port, killing any LC ringing in the dangling LPF.
  Reviewer: this is a non-obvious choice worth checking.
- **No PCB layout yet.** This review is schematic-only. All footprints have
  been assigned and ERC passes clean on all three boards; the gate is a
  schematic review before PCB spin.

---

## Review items addressed since prior pass (PDF review-1)

This design has gone through one external LLM review pass; the resulting
PDF flagged items M1-M15 (must-fix), S1-S12 (should-consider), plus nice-
to-haves. Status summary for the reviewer:

- **M1 (documentation only)** — no action, documentation-only item.
- **M2 (AC-couple LM7171)** — addressed in `vfo_complete.kicad_sch`.
- **M3 (DGFET source bias for cutoff)** — addressed in `vfo_complete.kicad_sch`.
- **M4 (ss_pa LDO input tolerance for 13.8 V)** — addressed (U13 now
  LM2936Z-5.0, 40 V input rating).
- **M5 (fuse + reverse-polarity protection at shack input)** — addressed
  (3 A slow-blow blade fuse Keystone 3568 + 1N5822 Schottky).
- **M6 (I²C level shifting)** — addressed (Adafruit #757 BSS138 at Metro
  I²C entry, HV bus at 5 V for all I²C slaves).
- **M7 (MCP4922 V_IH at 5 V VDD vs 3.3 V SPI)** — addressed (74HCT125
  quad buffer shifts MOSI/SCK/CS_DAC/DAC_LDAC_N from 3.3 V to 5 V, MCP4922
  now runs at 5 V VDD with full-range V_OUT).
- **M8 (IRF510 bias range)** — addressed (MCP4728 at 5 V VDD → 0-5 V bias
  output span → full IRF510 Vgs(th) coverage).
- **M8 (10 ms bias-kill)** — **still open.** Firmware will handle via I²C
  write to zero bias at keyup; no dedicated hardware fast-kill added. See
  open-items list.
- **M9 (ss_pa fault comparator sees raw 14 MHz)** — **still open**, not
  yet addressed. Reviewer: still a concern?
- **M10 (fault latch zero margin)** — **still open**, not yet addressed.
  V_REF now set from +5 V rail instead of +3.3 V, which gives more
  absolute margin on the comparator's input range but doesn't change the
  margin topology issue the PDF flagged.
- **M11, M12, M13, M14 (frontpanel issues)** — **still open**.
- **M15 (LPF relay contact function vs symbol text)** — not yet verified.
- **S-series and nice-to-have items** — not addressed this pass.

---

## Known open items / things worth prodding

- **Si5351 bringup DPDT switch (SW1).** DPDT slide switch (C&K JS202011CQN,
  THT, vertical slider) placed between HV-side SDA/SCL and the Si5351
  header for bringup isolation. Both lines break together on one slider
  position (DPST-via-DPDT). Note that the C&K JS202011 THT footprint has
  pin 1 physically above pin 6 (row 2 is numbered 6-5-4 in reverse), so
  wiring the DPDT as DPST requires using pins 1 and 6 as the two "closed"
  throws (same physical slider side) — this is the current wiring. The
  SMD variant of the same C&K part uses straight 1-2-3 / 4-5-6 numbering
  across rows; **do not substitute the SMD footprint** without rewiring,
  since pin 1 and pin 4 would be on the same physical side in SMD rather
  than pin 1 and pin 6.
- **M8 10 ms bias-kill still open.** Firmware will shutdown-DAC via I²C,
  but hardware fast-kill was not added. Reviewer: is firmware-only
  acceptable, or should a spare CD74HC4066 channel or a BSS138 be used
  for an additional hardware kill path?
- **M9 / M10 (fault comparator RC filter / fault latch margin)** —
  reviewer: still worth addressing with the +5 V rail change?
- **Shared swamp or dedicated swamp per bank?** Earlier iteration had a single
  shared pre-fanout R1 (100 Ω shunt) + R2 (68 Ω series) on the common input.
  That was replaced with the per-bank post-relay 50 Ω swamp. Reviewer: is the
  per-bank-only arrangement enough, or does the PA still want a load during
  switching gaps (when all relays are briefly open)?
- **Fault latch reset policy.** Current ss_pa fault chain requires power-cycle
  to clear a latched fault. Operator intervention is deliberate. Reviewer:
  acceptable or should firmware be able to clear it over I²C or GPIO?
- **IRF510 thermal.** User plans to use the heatsink from the QRP Labs 10 W
  kit (small finned extrusion). At 10 W out, ~50 % efficient PP → ~10 W total
  dissipation across the pair, ~5 W per device. Reviewer: adequate heatsink
  margin for CW duty cycle, or should user plan for a bigger sink?
- **Firmware architecture.** ESP-IDF v5.4.4 planned, FreeRTOS native, C++17,
  pinned tasks, `esp_timer_get_time()` µs timing. Keyer envelope generation
  is the one real-time task; everything else (I²C, SPI, display, serial) is
  soft. Reviewer: core-1 pinned raised-cosine LUT at 25 µs tick is the
  planned approach — is this the right factoring?
- **Front-panel RJ45 footprint.** `front_panel_interface.md` "Open Items"
  flags the RJE1D-188-21401 footprint pin coordinates as UNVERIFIED. Should
  be validated against physical stock before frontpanel fab.
- **I²C address collision resolved by EEPROM reprogramming.** Si5351 and
  MCP4728 both default to 0x60. User's solution: one-time firmware step to
  reprogram the MCP4728 EEPROM to 0x67 (requires LDAC pin wired to an
  ESP32 GPIO). See `i2c_bus.md`. Reviewer: is the sequencing of this
  reprogram-on-first-boot safe?
- **Netlists may lag schematic by one commit occasionally.** The user
  regenerates netlists before most commits but not every single one. If
  there's a discrepancy between what the netlist says and what the
  schematic says, the schematic wins.

---

## What specifically to review

Not an exhaustive list — follow the smell:

- **Correctness of the RF signal path:** DGFET G1/G2 DC bias at idle (no RF out
  without key down), transient response, DGFET-to-op-amp impedance matching,
  LM7171 slew/BW adequate for keyed envelope at 20 m carrier, stability
  margin of the LM7171 PP driver into the ss_pa input xfmr load.
- **Bias ramp dynamics on IRF510s.** The CD74HC4066 bias switch opens on
  FAULT_N and R12/R19 pulldowns kill PA_Bias in ~18 µs. Reviewer: can the
  IRF510 still get into breakdown during that 18 µs if the fault is a
  gate-oxide failure or a drain short?
- **Chebyshev LPF design soundness.** Values back-computed from standard
  Chebyshev tables look right to the writer, but reviewer should sanity-
  check cutoffs, cap E12 roundings, and whether the T50-6 (A_L = 4.0 nH/N²)
  core choice carries the current adequately.
- **LPF bank isolation.** With DPDT G6K + 50 Ω swamp on NC + the LPF's own
  stopband, is adjacent-band leakage small enough for FCC harmonic limits
  (−43 dBc for <25 W) at 10 W QRP? Especially the 20 m 2nd harmonic
  landing in the 10 m region — 10 m band is dropped from THIS LPF but is
  still a legal radio band to not pollute.
- **+12 V rail current budget.** Estimated ~75-100 mA worst case against
  LM2940CT-12's 1 A capacity. Reviewer: anything missed? (U7 LT1054
  inverter → −12 V bus feeding op-amp −rails, LM7171 +rails, one G6K
  coil active at a time.)
- **Watchdog + heartbeat chain.** CD14538B monostable gates the shack
  supply path to ss_pa via K5 (G6RL SPDT). Firmware must pulse the +TR_A
  input periodically. Reviewer: are the monostable timing R/C values
  sensible for a few-Hz heartbeat, and does the SS_PWR_RLY actually drop
  the ss_pa safely if firmware hangs?
- **Any ESD / inrush / power-sequencing gotchas** on initial power-on
  (shack supply applied cold, no firmware running yet).
- **BOM realism.** Any part that'll be hard to source for a hobbyist?
  (The G6K-2P-Y-T1 DC12 is a special-order variant — reviewer: is the
  "standard" G6K-2P DC12 OK as a substitute, or does the user actually
  need the T1 high-temperature spec?)
- **Any missed design-rule issues** (missing decoupling, floating inputs on
  logic ICs, pull-ups absent on open-drain nets, grounds that don't connect
  via a single-point to the chassis, etc).
- **Frontpanel-specific:**
  - **MBL-600 RS-422 termination placement.** 120 Ω termination resistors
    typically live at the receiver end of a differential pair. In this
    design the receiver (AM26LS32ACN) is on the analog board, but R2 / R3
    (120 Ω) are on the frontpanel. Reviewer: verify where termination
    should actually be, and whether R2 / R3 are serving source-end damping
    instead of termination (or if they're mislabeled / misplaced).
  - **LCD contrast / backlight generation.** MCP4725 feeds LCD contrast
    (V0); Q1/Q2/Q3 switch RGB backlight. Reviewer: do the Q-FET drive
    strengths and R5 (330 Ω) current limit math out at the LCD's typical
    backlight current (10 - 60 mA depending on module)? Is current-limit
    per color channel adequate, or does each color need its own series R?
  - **Local 3.3 V LDO (U4 MCP1700x-330) on frontpanel.** Metro side also
    has 3.3 V. Reviewer: is the frontpanel 3.3 V local-only (powers just
    PCF8575 / MCP4725 / encoder), or is it fighting / paralleling the
    Metro 3.3 V across the RJ45? Verify ground reference and that the
    two 3.3 V rails are either galvanically bridged or deliberately
    separate.
  - **I²C bus pull-ups.** The PCF8575 breakout board typically has
    built-in pull-ups. If there are also pull-ups on the analog side
    (there should be, at the Metro end of the I²C chain) the bus might
    be over-pulled — reviewer: check pull-up totals end-to-end and
    verify compliance with I²C spec minimum sink current.
- **Protoshield-specific:**
  - **Zener clamp sizing.** 1N4728A is a 3.3 V zener with ~ 0.3 Ω dynamic Z
    and 76 mA rated breakdown current. Reviewer: are these the right
    clamps for the Source_Sense_A/B lines (which normally sit at
    0 - 500 mV)? Any series R between the external terminal and the clamp
    to limit fault current, or is the clamp directly on the GPIO?
  - **Pull-up strength on paddle / encoder inputs.** 10 kΩ pulls to +3.3 V
    on PADDLE_A/B and friends. In a shack with transmit RFI, 10 kΩ may be
    too weak for key-up noise rejection. Reviewer: consider 2.2 kΩ or
    4.7 kΩ?
  - **Metro power routing.** Does the Metro take +5 V from the shield
    (via a screw terminal or a header pin from the analog board), from
    its own USB jack, or from its barrel connector? The protoshield
    schematic doesn't show an explicit +5 V source — review wants
    confirmation that the Metro has a defined power path once it's
    disconnected from USB.
  - **Series R on contact-close inputs.** PADDLE_A/B and RESET_N likely
    rely on the 1 kΩ series Rs for RFI and ESD protection. Reviewer:
    is 1 kΩ enough series impedance against stray RF pickup on a long
    paddle cable in a transmit environment?

---

## Review deliverable requested

A single markdown reply from the reviewer with:

1. **Must-fix issues** before PCB layout (anything that will cause a dead
   board or safety concern).
2. **Should-consider issues** (potential improvements, non-blocking).
3. **Nice-to-have observations** (not blocking, not priority, but worth
   knowing).
4. **Specific answers** to the "what to review" questions where the reviewer
   has an opinion.

Reviewer should ignore polish — brevity > exhaustive-but-wandering.

---

*Document generated 2026-10-22 as a Rev D pre-layout review handoff.
Revised 2026-10-23 to reflect M-item fixes from PDF review-1, I²C bus
voltage redesign (shifter at Metro, 5 V HV bus), 74HCT125 SPI shifter
for MCP4922, ss_pa Option C (full +5 V rail via LM2936Z-5.0), FAULT_N
divider at Metro, shack input fuse + Schottky, and SW1 bringup
isolation switch.*

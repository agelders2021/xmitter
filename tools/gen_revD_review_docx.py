"""
Generate the Rev D LLM-review DOCX.

Output: Documentation/xmitter_RevD_Review_Package_<today>.docx

Content:
  1. Intended operation (complete signal-chain walkthrough)
  2. Board + umbilical inventory
  3. Review-axis instructions (function / values / power / flaws)
     with explicit R + C size/voltage/power confirmation axis
  4. SW1 note: pinout is CONFIRMED CORRECT (reviewer may skip)
  5. Potential problem areas (by board / subsystem)
  6. Known open items the reviewer should NOT re-flag
"""
from __future__ import annotations
from pathlib import Path
import datetime as _dt
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT_DIR = Path(r"C:\Users\AlAnd\Git Backed Projects\xmitter\Documentation")
TODAY = _dt.date.today().isoformat()
OUT_PATH = OUT_DIR / f"xmitter_RevD_Review_Package_{TODAY}.docx"


def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    return h


def add_para(doc, text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(11)
    r.bold = bold
    r.italic = italic
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.25 + 0.25 * level)
    r = p.add_run(text)
    r.font.size = Pt(11)
    return p


def add_bullet_rich(doc, segments, level=0):
    """segments = list of (text, {"bold":bool, "italic":bool})"""
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.25 + 0.25 * level)
    for text, fmt in segments:
        r = p.add_run(text)
        r.font.size = Pt(11)
        r.bold = fmt.get("bold", False)
        r.italic = fmt.get("italic", False)
    return p


def build():
    doc = Document()

    # ----- Title block
    title = doc.add_heading("xmitter Rev D — External Design Review Package", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    sub = doc.add_paragraph()
    sub_r = sub.add_run(f"Prepared {TODAY} for external LLM review.")
    sub_r.italic = True
    sub_r.font.size = Pt(11)

    add_para(
        doc,
        "This document is a self-contained description of the xmitter Rev D "
        "design, written to be handed to a reviewing LLM together with the "
        "four board netlists listed in §4. The reviewer should flag potential "
        "problem areas; the specific review axes requested are in §3, and a "
        "pre-populated list of potential problem areas the designer is "
        "already curious about appears in §7.",
    )
    add_para(
        doc,
        "Where this document and the schematic disagree, the schematic is "
        "the gold standard. This brief orients the reviewer; the KiCad "
        "schematics and their exported netlists are authoritative.",
        italic=True,
    )

    # ----- 1. Intended operation
    add_heading(doc, "1. Intended operation (complete description)", level=1)

    add_para(
        doc,
        "xmitter is a ~10 W QRP CW transmitter covering the 40 m, 20 m, "
        "17 m, and 15 m amateur HF bands. 10 m is deliberately not covered. "
        "The design is built around an Adafruit Metro ESP32-S3 running "
        "ESP-IDF v5.4.4 firmware. Supply is 13.8 V DC from a shack supply; "
        "there is no mains-side circuitry.",
    )

    add_heading(doc, "1.1 Signal chain (Si5351 → antenna)", level=2)

    steps = [
        "Si5351A clock output drives Gate 1 of Q2 (40673 dual-gate MOSFET) on the analog board through a 100 nF AC coupling cap. G1 is DC-biased to roughly +2.45 V by a 39 kΩ / 10 kΩ divider from +12 V; R21 = 1 MΩ gate return.",
        "Gate 2 of Q2 receives the envelope voltage. MCP4922 (U4) channel B outputs 0 V…+5 V; this feeds U11 (TL071CP) configured as an offset-mute op-amp whose transfer function is V_G2 = V_DAC × 1.62 − 3.13, mapping 0 V…+5 V DAC output to −3.1 V…+5 V on G2. The negative DC offset is set by a 1N4733A 5.1 V Zener (D3) reference and the R20/R23 feedback ratio (6.2 kΩ / 10 kΩ). At DAC = 0 V the DGFET sits well below V_TO = −2 V (simulated I_D = 12 pA, on/off ratio ~10⁹). There is no separate KEY_UP GPIO — firmware controls RF on/off entirely by what it writes to the envelope DAC channel.",
        "DGFET drain → R1 (50 Ω) + C1 (100 pF) snubber → single-pole ~32 MHz LPF to tame Si5351's sub-nanosecond CMOS edges.",
        "U1 LM7171 non-inverting amp with build-time gain hedge: R_f = 3 kΩ installed in the feedback path; R_g to GND left unpopulated by default → unity gain. Populate R_g = 1 kΩ → gain = 4 → ~2 Vpp drive to the PA. Operator picks between class-AB (R_g open, gentle drive) and class-C (R_g = 1 kΩ, hard drive) at build time.",
        "R2 (50 Ω) series back-match into coax, SMA J1 on analog → short RG316 → SMA J3 on ss_pa.",
        "ss_pa T201 (BN61-2402) input transformer, 2-turn primary, 3-turn bifilar secondary, with DRIVER_BIAS injected at the center-tap. Phase-splits single-ended RF into push-pull drive for the BS170 pair.",
        "BS170 PP pre-driver (Q2, Q6). Each gate driven from one end of T201 secondary via 220 Ω series. Each source grounded through 2.2 Ω 1/4 W for source degeneration (no bypass cap — accepts the ~1.7 dB gain cost to buy stability and matched behavior against FET-to-FET β spread).",
        "ss_pa T202 (BN61-2402) interstage transformer. 3-pin bifilar primary (CT fed from +12 V through L18 ferrite choke; outer pins to the two BS170 drains); 2-pin secondary (5 T) drives the IRF510 gates.",
        "IRF510 PP finals (Q3, Q4). Each gate: driven from T202 secondary through a classic QRP-Labs drain-gate feedback network (C/R/L) for bandwidth flattening and VHF stability, DC-biased by PA_Bias_A/B through 47 Ω each. Each source: R1||R2 or R3||R4 (0.22 Ω 2 W × 2 in parallel = 0.11 Ω effective) for current sensing and thermal degeneration. Source voltage is RF-filtered on-board by four 220 nF 0805 X7R caps (two per source node, same value to parallel ESL without anti-resonance).",
        "ss_pa Source_Sense gain stage (U1 MCP6002 dual op-amp, powered from +5 V via J31 pin 3). Each source voltage goes to one op-amp half configured as a non-inverting 10× amp (R_g = 1 kΩ to GND, R_f = 9 kΩ in feedback). Source_Sense_X_Raw = 10 × V(source resistor) is routed out J31 pins 1 and 4. Boosting at the sensor dramatically reduces GND-return IR drop sensitivity.",
        "Analog-side 2:1 divider at the LM393 input: R65 + R68 = 10 kΩ each form a 2:1 attenuator from Source_Sense_A_Raw to GND. Net effective gain seen at the LM393 input (and at the Metro ADC tap on Source_Sense_X) = 5×. Keeps worst-case ADC voltage below 3.3 V (4.2 A × 0.11 Ω × 5 = 2.3 V). Firmware ADC conversion: I_source = ADC_voltage / (5 × 0.11 Ω) = ADC_voltage / 0.55.",
        "ss_pa T203 (Amidon T50-43) bifilar drain feed, DC +13.8 V to each IRF510 drain, transparent to differential-mode RF.",
        "ss_pa T204 (BN43-202) output transformer, 2:3 ratio → 2.25× impedance step-up. 50 Ω antenna load reflects as ~22 Ω drain-to-drain, matched to the IRF510 pair at ~10 W output.",
        "Coax to Output LPF board via SMA J1 (ss_pa) → SMA input of LPF.",
        "Output LPF — 7-pole Chebyshev CLCLCLC, 0.1 dB ripple, 50 Ω source/load. One bank per band, selected by a DPDT G6K-2P-Y-T1 (DC12 coil) relay per band — pole 1 switches the LPF input, pole 2 switches the output, both poles throw together so unused filters are fully isolated. A fifth relay (K5) performs TX/RX bypass. Simulated 20 m bank rejects 3rd harmonic by 68 dB and 5th by 84 dB — all harmonics sit > 27 dB below the FCC Part 97 −43 dBc floor.",
        "Antenna via SMA chassis-mount jack.",
    ]
    for s in steps:
        add_bullet(doc, s)

    add_heading(doc, "1.2 Control architecture", level=2)

    add_para(doc, "MCU: Adafruit Metro ESP32-S3, mounted directly on the analog board. The Metro symbol and all per-pin signal conditioning (bypass caps, series Rs, pull-ups for paddles and encoder interrupt, Zener clamps, small RC filters) live on the analog board's arduino.kicad_sch sub-sheet. There is no separate protoshield PCB in Rev D — the earlier plan to mount the Metro on an Adafruit Proto Shield has been dropped and the conditioning absorbed onto analog.")

    add_para(doc, "I²C bus (single bus, Metro 3.3 V side level-shifted to the +5 V HV bus by an Adafruit #757 BSS138 breakout at the Metro I²C entry):", bold=True)
    for s in [
        "Si5351A at 0x60 (factory default)",
        "MCP4728 (U3) at 0x67 (reprogrammed from factory 0x60 on first boot)",
        "PCF8575 (U17) at 0x20 (A0/A1/A2 all open)",
        "MCP4725 for LCD contrast on the front-panel sub-sheet — address TBD",
        "Metro on-board MAX17048 fuel gauge at 0x36 (hard-wired)",
        "Up to 3 Adafruit I²C QT rotary encoders on the front-panel chain (INT pins wire-OR'd into ENC_INT_RAW)",
    ]:
        add_bullet(doc, s)

    add_para(doc, "SPI bus: Metro native SPI (3.3 V) drives MCP4922 (U4) on analog. MCP4922 runs on +5 V V_DD so SPI lines are level-shifted 3.3 → 5 V by a 74HCT125 quad buffer (U9) before reaching the DAC. Channel A → envelope (via U11 offset-mute); channel B → DRIVER_BIAS.")

    add_para(doc, "MBL-600 primary tuning encoder: RS-422 differential quadrature on two pairs → AM26LS32 (U16) on analog → level-shift 5→3.3 V → ESP32-S3 PCNT peripheral for hardware-accelerated decode.")

    add_heading(doc, "1.3 Operating classes (both will be explored in firmware)", level=2)
    add_para(doc, "The design is deliberately set up so the operator can run the IRF510 PA in either class-AB or class-C without any hardware changes other than optionally populating R_g on U1.")
    add_bullet(doc, "Class-AB (default build): PA_Bias_A/B set to ~3.8 V by MCP4728; U1 at unity gain (R_g unpopulated) → ~500 mVpp drive; approximate efficiency 50 %, output ~5 W.")
    add_bullet(doc, "Class-C (alternate build): PA_Bias_A/B dropped to ~1–2 V by MCP4728; R_g populated at 1 kΩ on U1 → gain = 4 → ~2 Vpp drive; approximate efficiency 75–80 %, output ~10 W; harmonics are worse but caught by the output LPF.")
    add_para(doc, "Firmware PA monitoring is therefore not optional — the operator needs real-time per-FET current readings in both modes to tune bias safely without burning IRF510s.")

    add_heading(doc, "1.4 Fault chain (hardware, independent of firmware)", level=2)
    add_para(doc, "Entirely on the analog board (sub-sheet fault_shutdown.kicad_sch), with reference designators in the +200 series. Signal flow:")
    for s in [
        "Each Source_Sense input runs through a two-stage LC filter (L208/C223/C229 for channel A; L209/C224/C228 for B) before reaching the LM393.",
        "U201 LM393 open-collector dual comparator trips when Source_Sense exceeds V_REF. Trip outputs wire-OR into FAULT_N_RAW.",
        "U202 CD74HC4066 provides three bilateral switches: switches 1 and 2 series-pass PA_Bias_A/B and open on fault; switch 3 passes FAULT_N_RAW to FAULT_N and is opened for 1 ms during a reset.",
        "R219 = R212 = 2.2 kΩ sits on the IRF510 side of switches 1/2 so that when those switches open the IRF510 gate (C_iss ≈ 180 pF) discharges through 2.2 kΩ in τ ≈ 0.4 µs — PA conduction cuts well inside the thermal-damage window.",
        "V_REF generator uses RV1 (Bourns 3296W-103LF 10 kΩ trim) and R17/R41/R59 to set an operator-adjustable trip current of approximately 1.6 A to 4.3 A per FET. On trip, R16 drags V_REF negative so the comparator cannot un-trip itself — this is a true self-latch, not Schmitt hysteresis.",
        "Reset: firmware pulses PCF8575 P11 LOW. The trailing edge triggers U18B (second half of CD14538B); R61 = 10 kΩ, C19 = 0.1 µF → 1 ms pulse that opens 4066 switch 3, releases FAULT_N to the pull-up, and restores PA bias. If the fault is still present at the end of the 1 ms pulse the comparator re-latches within 18 µs.",
        "Separate half U18A is the ESP32-S3 heartbeat watchdog that gates K5 on the +13.8 V feed to ss_pa.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "1.5 Bringup power sequencing", level=2)
    add_bullet(doc, "F2 (3 A slow-blow fuse) + D1 (1N5822 Schottky) at the shack input J5.")
    add_bullet(doc, "R42 (24 Ω 10 W) in series with the SS PA power feed, bypassed in normal operation by relay K6.")
    add_bullet(doc, "K5 (G6RL-1-DC12) gated by the CD14538B heartbeat → kills SS PA rail if firmware hangs.")
    add_bullet(doc, "K6 (G6RL-1-DC12) bypasses the inrush resistor once validation is complete.")

    # ----- 2. Boards
    add_heading(doc, "2. Boards", level=1)
    add_para(doc, "Rev D is three PCBs: analog, ss_pa, and Output LPF. The Metro ESP32-S3 mounts directly on the analog board — there is no separate protoshield in Rev D.")

    add_heading(doc, "2.1 Analog board (KiCAD/analog/)", level=2)
    add_para(doc, "Hosts the Metro ESP32-S3 (on the arduino.kicad_sch sub-sheet) plus: Si5351A, DGFET keyer (Q2 40673), RC snubber, LM7171 output buffer (U1) with build-time gain hedge, MCP4728 (U3, I²C 4-channel DAC), MCP4922 (U4, SPI 2-channel DAC), TL071CP offset-mute op-amp (U11), PCF8575 I/O expander (U17), AM26LS32 RS-422 receiver (U16), CD14538B dual monostable (U18 — heartbeat + fault-reset timer), fault chain (U201 LM393, U202 CD74HC4066, V_REF + RV1 trim), BSS138 I²C level shifter breakout at the Metro entry, 74HCT125 SPI shifter (U9), onboard regulators (LM2940CT-12 → +12 V, LT1054 → −12 V, LM2940CT-5.0 → +5 V, MCP1700x-330 → +3.3 V local to front-panel sub-sheet), shack input (J5) with 3 A slow-blow fuse + 1N5822, inrush relay K6 with R42 24 Ω 10 W, heartbeat relay K5. Also hosts all per-pin Metro signal conditioning (previously planned for a protoshield — now absorbed) and the front-panel sub-sheets (LCD interface, encoder sockets, button matrix, LED indicators).")
    add_para(doc, "Analog sub-sheets of interest: analog.kicad_sch (root), arduino.kicad_sch (Metro + signal conditioning), vfo_complete.kicad_sch (Si5351 + DGFET keyer + LM7171 buffer), dac.kicad_sch (DACs + U11 offset-mute op-amp), interface.kicad_sch (frontpanel umbilical + RS-422 termination), front_panel.kicad_sch (LCD + encoders + buttons), power.kicad_sch (regulators), fault_shutdown.kicad_sch (fault chain, +200-series refs), Tube_PA.sch.kicad_sch (DNP, future tube-PA cable exit on J35).")

    add_heading(doc, "2.2 SS PA board (KiCAD/ss_pa/)", level=2)
    add_para(doc, "Almost a direct copy of the QRP Labs 10 W Linear PA kit: BS170 PP pre-driver → T201 → T202 → IRF510 PP → T203 bifilar drain feed → T204 output transformer. Two deliberate departures: (a) DAC-controlled bias replaces the kit's mechanical trimmers; (b) per-FET source-sense resistors (0.22 Ω × 2 parallel = 0.11 Ω effective) plus an on-board MCP6002 10× pre-amp (U1) so the sense signal crossing the J31 umbilical is amplified before any GND-return IR drop. No LDO, no fault chain, no bias switch on ss_pa — those all live on analog.")

    add_heading(doc, "2.3 Output LPF board (KiCAD/Output LPF/)", level=2)
    add_para(doc, "4-band 7-pole 0.1 dB Chebyshev LPF (40 / 20 / 17 / 15 m). One DPDT Omron G6K-2P-Y-T1 (DC12) relay per band; a fifth relay performs TX/RX bypass. Band-select coil drives come from the analog PCF8575 through 2N7000 open-drain FET sinks on the LPF board. Coil supply is SS_PA_Power (switched +13.8 V, dead at power-up until firmware arms the heartbeat); R28 (62 Ω 1 W) brings the G6K coil current back into spec at the higher 13.8 V rail. All 16 CF* shunt caps use 200 V C0G discs on the Capacitor_THT:C_Disc_D7.5mm_W2.5mm_P5.00mm footprint. All inductors are hand-wound T50-6 toroids with turn counts annotated on the schematic in TARGET/ACTUAL nH, NT format.")

    # ----- 3. Umbilicals
    add_heading(doc, "3. Umbilicals and board boundaries", level=1)
    for s in [
        "J1 — Analog → ss_pa : RF signal (SMA, 50 Ω)",
        "J2 — Analog → Output LPF : RJ45 CAT6. SS_PA_Power (pin 8), four band selects (pins 2–5), T/R control (pin 1), TRANSMIT_N sense back (pin 7), pin 6 spare (formerly RECEIVE_N — eliminated 2026-11-12, T/R state now inferred from TRANSMIT_N alone), shield = GND. SS_PA_Power is the switched 13.8 V rail — dead at power-up until firmware arms K5 or K6, so no band-select relay can accidentally energize before firmware takes control.",
        "J4 — Analog → Frontpanel : RJ45 CAT6. SDA, SCL, MBL_A±, MBL_B±, +5 V, ENC_INT_CLEAN, shield = GND.",
        "J31 — Analog ↔ ss_pa : RJ45 CAT6. Pin 1 Source_Sense_A_Raw (10× pre-amplified); pin 3 +5 V to ss_pa MCP6002; pin 4 Source_Sense_B_Raw; pin 6 DRIVER_BIAS; pins 7/8 PA_Bias_A/B; pins 2/5/shield = GND. FAULT_N does not cross J31.",
        "J33 (analog) → J2 (ss_pa) — dedicated screw terminals carry +13.8 V to the SS PA, gated by K5 (heartbeat) and R42/K6 (inrush/bypass).",
        "J35 (analog) — RJ45 provisioned for a possible future tube PA. DNP today; signals present on-board but no external destination.",
    ]:
        add_bullet(doc, s)

    # ----- 4. Netlists
    add_heading(doc, "4. Netlists for review", level=1)
    for s in [
        "KiCAD/analog/analog.net — includes Metro, all signal conditioning, and front-panel sub-sheets",
        "KiCAD/ss_pa/ss_pa.net",
        "KiCAD/Output LPF/Output LPF.net",
    ]:
        add_bullet(doc, s)
    add_para(doc, "Note on .sch vs .net: the KiCad .net exports contain every component (ref, value, footprint, description) and every net (with full ref/pin node lists) needed for a connectivity and component-value review. However, the .net format does NOT carry the DNP flag — DNP status lives only in the .kicad_sch files. To keep the reviewer from spending effort on parts that will not be populated, every DNP reference in Rev D is listed explicitly in §9 below. With that list in hand the .net files are sufficient and the .kicad_sch files are not needed for review.")

    # ----- 5. Review axes
    add_heading(doc, "5. Review axes", level=1)
    add_para(doc, "Please review across the following four axes and produce a report keyed to reference designators and pin numbers:")

    add_heading(doc, "5.1 Function", level=2)
    add_para(doc, "Confirm that every circuit block performs its intended function. Walk the signal path from Si5351 clock output to the antenna connector, trace each DAC output to its load, and trace each telemetry or fault signal back to the Metro.")

    add_heading(doc, "5.2 Component values — resistor and capacitor size / voltage / power confirmation (REQUESTED EXPLICITLY)", level=2)
    add_para(doc, "For every resistor and capacitor in the four netlists, confirm the chosen size / voltage rating / power rating is appropriate for its node. Specifically:")
    for s in [
        "Resistors — confirm each resistor's power dissipation under worst-case continuous operation (class-C transmit, maximum PA current, worst-case bias leakage, relay-coil current, etc.) sits comfortably inside the rated wattage. Convention in this design: all resistors are 1/4 W DIN0207 axial unless the Value field explicitly carries a different wattage tag (e.g. 0.22R 2W, 15R 5W, 24R 10W). Flag any part where the netlist footprint looks inconsistent with the wattage tag (a 2 W part still showing DIN0207, or a mismatched pitch).",
        "Capacitors — confirm each capacitor's voltage rating is appropriate for its node. Known voltage-critical nodes: ss_pa C3 (drain-to-drain, up to ~55 V P-P differential — specified 200 V C0G); all 16 LPF CF* shunt caps (10 W into 50 Ω = 22.4 V RMS, 31.6 V peak nominal, ~63 V peak under 3:1 VSWR — specified 200 V C0G); analog power-rail bulk + ceramic bypass caps on +13.8 V (worst-case transient is shack-supply overshoot during switch-on). Flag any capacitor on an RF, high-voltage, or power-rail node where the rating looks marginal.",
        "Capacitors — confirm each capacitor's dielectric type is appropriate for the node (C0G/NP0 for RF and timing nodes; X7R acceptable for bypass; electrolytic/tantalum appropriate for bulk but not RF).",
        "Inductors — the LPF uses the TARGET/ACTUAL nH, NT annotation format. Confirm integer turn counts round sensibly from the Chebyshev prototype (N = round(√(L_target / A_L)), A_L = 4.0 nH/N² for T50-6).",
        "Transformer ratios — confirm T201 (2:3 bifilar, BN61-2402), T202 (bifilar BN61-2402), T203 (bifilar T50-43 drain feed), T204 (2:3 BN43-202 output) give the intended impedance transformation.",
        "Bias points — confirm the 40673 G1 divider (39K / 10K from +12 V → +2.45 V) and G2 offset-mute transfer function (V_G2 = V_DAC × 1.62 − 3.13) land where expected. Confirm the IRF510 PA bias setpoints that the MCP4728 can produce reach the needed class-AB and class-C bias ranges.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "5.3 Power dissipation", level=2)
    add_para(doc, "For every resistor, FET, LDO, relay coil, and transformer winding, estimate worst-case continuous dissipation and compare to the rated part. Pay particular attention to: ss_pa R1–R4 (0.22 Ω 2 W, per-FET source current), the BS170 pair (worst-case drain dissipation under class-C drive), the IRF510 pair (nominal ~5 W per FET at class-C, heat-sink-dependent), the LM2940CT regulators (dropout × worst-case load), the LT1054 charge pump (continuous load vs rating), and the relay coil currents (G6K coils on 13.8 V via R28, G6RL coils K5/K6 on +12 V).")

    add_heading(doc, "5.4 Design flaws", level=2)
    add_para(doc, "Anything else — stability, race conditions, grounding, start-up order, decoupling adequacy, EMI/radiation paths, firmware/hardware interlock gaps.")

    # ----- 6. Confirmed-correct item
    add_heading(doc, "6. Items the reviewer may skip (already confirmed)", level=1)

    add_heading(doc, "6.1 SW1 slide-switch pinout (CONFIRMED CORRECT)", level=2)
    add_para(
        doc,
        "SW1 on the analog board is the Si5351 bringup DPDT isolation slide switch. "
        "The schematic wiring of SW1 against the C&K JS202011CQN physical pin numbering "
        "has been verified by the designer and is confirmed correct. The reviewer need NOT "
        "re-check SW1 connectivity, pole-A / pole-B mapping, or common/NO/NC per pole.",
        bold=True,
    )
    add_para(
        doc,
        "For context: SW1 uses library symbol Switch:SW_Slide_DPDT with footprint "
        "Button_Switch_THT:SW_CK_JS202011CQN_DPDT_Straight. In one position the Si5351 clock "
        "reaches the DGFET Gate 1; in the other the clock is isolated for bringup.",
    )

    # ----- 7. Potential problem areas
    add_heading(doc, "7. Potential problem areas (designer's own curiosity list)", level=1)
    add_para(doc, "These are areas where the designer would particularly welcome an independent look. The reviewer is of course free to flag anything else as well.")

    add_heading(doc, "7.1 SS PA — IRF510 PA stage", level=2)
    for s in [
        "ss_pa C3 (drain-to-drain cap across the IRF510 pair, 33 pF 200 V C0G) — confirm the voltage rating still holds under worst-case mismatched-load VSWR (not just 3:1) and under the half-cycle transient when one FET switches on before the other has fully turned off.",
        "The 2.2 Ω 1/4 W source-degeneration resistors on the BS170 pre-driver (R15/R16 on ss_pa) — worst-case class-C drive levels. Comfortable, marginal, or over-rated?",
        "0.22 Ω 2 W source-sense pair (R1||R2, R3||R4) in parallel = 0.11 Ω effective. At the top of the RV1-adjustable 4.3 A trip range, each FET dissipates ~4.3² × 0.11 = ~2 W in the pair combined — within rating per FET pair, but confirm it holds with worst-case thermal rise.",
        "MCP6002 sense pre-amp (U1 on ss_pa) running on +5 V from J31 pin 3 — any concern about supply drop with the ~30 cm umbilical cable, or RF ingress on the sense inputs that might saturate the 10× gain stage? The 220 nF X7R pair on each source node is the only RF filtering before the op-amp.",
        "T204 output transformer (BN43-202, 2:3) — 2.25× impedance step-up giving ~22 Ω drain-to-drain target. Is the ratio correct for the IRF510 operating-point, or should it be 1:2 (4× step-up, ~12.5 Ω drain-to-drain)?",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.2 Analog — fault chain", level=2)
    for s in [
        "V_REF generator with RV1 10 kΩ trim — confirm the operator-adjustable trip range (quoted as ~1.6 A to 4.3 A per FET, assuming 5× effective signal-chain gain at the LM393 input) actually comes out in that range given the R16/R17/R41/R59 values.",
        "The self-latching mechanism relies on V_REF going negative when FAULT_N drops. Confirm that under all tolerance corners and over the 0 °C to 55 °C operating range the latch does not miss — i.e. V_REF stays comfortably below ground in the latched state.",
        "LM393 input bias — R221/R222 = 100 kΩ series, R224/R225 = 4.7 MΩ pull-up to +5 V. Does this input network produce any unintended quiescent trip at zero source current (worst-case LM393 input offset + leakage)?",
        "CD74HC4066 switch 1/2 series resistance (~100 Ω typ) vs the 47 Ω gate-stopper on the ss_pa side — any concern about the IRF510 turn-on time being limited by the 4066 switch resistance into C_iss?",
        "Firmware fault-clear sequence (PCF8575 P11 LOW → trailing edge → 1 ms monostable → FAULT_N_OVERRIDE_N). Any power-on hazard where PCF8575 outputs power up HIGH, then the Metro's first write pulls them LOW spuriously, triggering a reset at boot? The trailing-edge polarity of U18B is supposed to prevent spurious firing, but worth a second look.",
        "FAULT_N_CLEAN divider (R3 100 kΩ + R4 200 kΩ to GND) — this produces a 3.3 V-domain copy for the Metro input. Confirm the loading on FAULT_N doesn't disturb the self-latch.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.3 Analog — DAC / envelope path", level=2)
    for s in [
        "TL071CP (U11) offset-mute op-amp: R20/R23 = 6.2 kΩ / 10 kΩ + 1N4733A 5.1 V Zener reference. Confirm the transfer function V_G2 = V_DAC × 1.62 − 3.13 comes out as expected with the TL071's input offset and over temperature.",
        "40673 Gate 1 DC bias divider (39 kΩ / 10 kΩ from +12 V → +2.45 V) and R21 = 1 MΩ gate return — any concern about G1 bias stability under DC-coupled transients from the Si5351 CMOS output before the 100 nF coupling cap settles?",
        "U1 LM7171 output buffer — the build-time gain hedge (R_g unpopulated = unity gain; populate R_g = 1 kΩ for gain = 4) uses R_f = 3 kΩ. Confirm unity-gain stability and the ~500 mVpp / ~2 Vpp output levels at the two build options.",
        "74HCT125 (U9) SPI level shifter — propagation delay vs MCP4922 max SPI clock. Is there margin for a 10 MHz SPI clock through the shifter?",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.4 Output LPF", level=2)
    for s in [
        "40 m band: Fc ≈ 8.0 MHz with 7.3 MHz at 0.91·Fc — in-band but tolerance-tight. Confirm the chosen E12 cap values and T50-6 integer turn counts leave enough passband margin that production tolerances won't shift the −3 dB corner down below 7.3 MHz.",
        "G6K-2P-Y-T1 on 13.8 V via R28 (62 Ω 1 W) — confirm the coil current comes out in spec at both the 12 V nominal and the ~13.8 V actual rail, and that R28 dissipation sits comfortably under its 1 W rating even at the high end of 13.8 V supply tolerance.",
        "LPF-board 2N7000 open-drain FET sinks driving the G6K coils — confirm each 2N7000 can sink the full coil current and that any flyback diode is correctly placed across the coil.",
        "SS_PA_Power as the coil supply — the K5 heartbeat + K6 inrush-bypass gating on analog means the LPF relays are dead at power-up, which is intentional. Confirm there is no spurious energization path (e.g. leakage through the 2N7000 drain-source) that could latch a band-select before firmware is ready.",
        "T/R sense is now TRANSMIT_N alone (J2 pin 7); the previously-paired RECEIVE_N on pin 6 was eliminated 2026-11-12. Confirm there is no case where the loss of RECEIVE_N creates ambiguity — e.g. a startup window where TRANSMIT_N floats before the PCF8575 input pull-up takes effect and firmware could mis-read the T/R state.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.4a Firmware-enforced LPF relay self-test (reviewer: please evaluate the hazard)", level=2)
    add_para(doc, "LPF relay power (SS_PA_Power on J2 pin 8) is gated by analog's K5 heartbeat relay in parallel with K6 inrush-bypass relay. Either K5 or K6 being closed delivers power to the LPF relay coils; both open = LPF relays dead and no RF path through any band filter. The design relies on firmware to run a pre-TX self-test every transmit: command the correct band-select relay, command T/R to TX, read back TRANSMIT_N (J2 pin 7), and refuse to key the PA if the sense state is wrong. Please comment on:")
    for s in [
        "Is a single TRANSMIT_N sense sufficient to catch all plausible failure modes of the LPF relay chain, now that RECEIVE_N has been eliminated? Specifically: a stuck band-select relay would not be detected by the T/R sense alone — the PA would key into whatever filter the last-energized band-select left behind. Is this acceptable given that firmware controls the band select directly and can keep a software-side shadow?",
        "Is there a hardware interlock that could catch this independently of firmware (e.g. an SWR fault tied into the fault chain)? The current fault chain triggers only on IRF510 source current, not on output-side mismatch.",
        "Dead SS_PA_Power (K5 and K6 both open) means no relay can throw. In that state TRANSMIT_N would stay in its de-energized state and firmware's self-test would correctly refuse to key — confirm this is the observed behavior and that the pull-up / pull-down convention on TRANSMIT_N preserves it under a dead-rail condition.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.5 Power sequencing / rails", level=2)
    for s in [
        "LM2940CT-12 (U8) sourcing the analog +12 V — worst-case load is roughly: op-amps (LM7171 ×2, TL071, MCP6002 via umbilical), AM26LS32 receiver, CD14538B, relay coils through steering, Si5351 if powered on +12 V upstream regulation. Confirm worst-case combined current under transmit is within the LM2940's thermal limits with the supply dropout from 13.8 V.",
        "LT1054 (U7) charge-pump −12 V — confirm the continuous load (LM7171 negative rail + TL071 negative rail) stays within the LT1054's spec.",
        "Inrush bypass sequence (R42 24 Ω 10 W → K6 bypass) — any concern about K6's contact rating for the switch-on inrush current when K6 closes with ss_pa already drawing current through the inrush limiter?",
        "Shack input protection: F2 (3 A slow-blow) + D1 (1N5822 Schottky) at J5. Confirm the fuse rating is appropriate for the worst-case continuous draw (~5 A during class-C transmit) — 3 A sounds tight.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.6 Metro signal-conditioning (arduino sub-sheet)", level=2)
    for s in [
        "Metro GPIO12 (D12) carries GRID_BLOCK_CRASH (active HIGH, tube-PA fault). Analog has a 100 kΩ external pull-down. Firmware must disable internal pulls on D12 (documented). Is 100 kΩ the right pull-down value given the open-collector / diode-OR drive and the ESP32-S3 ~45 kΩ internal-pull strength?",
        "The Metro now sits directly on analog (previously planned as a daughter protoshield). Flag any signal where moving onto analog created an unintended short path (e.g. a sensitive ADC trace running next to a switching node, or a shared return that was fine as a short cable now becoming a ground-loop on the PCB).",
        "Encoder interrupt path (ENC_INT): confirm the chosen pull-up (R53 = 10 kΩ to +3.3 V on analog, upstream of the Metro pin; R78 = 10K at the Metro pin left DNP) is sufficient given the wire-OR'd open-drain INT outputs from up to 3 Adafruit I²C QT encoders.",
        "Decoupling on the Metro's power-input pins — any ceramic bypass needed close to the Metro VIN / 3V3 / 5V pins on analog beyond what the Metro board itself carries? Flag any Metro power pin on the arduino sub-sheet without bypass.",
    ]:
        add_bullet(doc, s)

    add_heading(doc, "7.7 General / cross-cutting", level=2)
    for s in [
        "Decoupling adequacy — every IC should have a 100 nF ceramic bypass within a few mm of its V_DD pin. Flag any IC without obvious bypass in the netlist.",
        "Grounding topology — the analog board has +12 V, +5 V, +3.3 V, and three separate signal/current grounds (analog, digital, PA return). Flag any node where a sensitive analog signal shares a return path with a high-current or switching node.",
        "EMI/radiation — Si5351 CMOS output has sub-nanosecond edges; the 50 Ω / 100 pF snubber at the DGFET drain is the only hard low-pass before the LM7171. Any concern about VHF+ harmonics coupling into analog's control lines before they're attenuated by the output LPF?",
    ]:
        add_bullet(doc, s)

    # ----- 8. Known open items
    add_heading(doc, "8. Known open items the reviewer should NOT re-flag", level=1)
    for s in [
        "Metro ESP32-S3 is now mounted directly on the analog board (arduino.kicad_sch). The earlier Adafruit Proto Shield plan has been dropped; KiCAD/protoshield/ in the repo is obsolete and is NOT part of this review (no protoshield.net is included in §4).",
        "J35 on analog will connect to a future tube-PA board that has not yet been designed. The connector sits on analog as a provisioned cable exit (DNP today). Signals it carries (I_CATHODE_A/B, GRID_CTL_A/B, GRID_BLOCK_CRASH) are routed on-board but have no electrical destination outside analog today.",
        "KiCAD/bias/ (OPA454 grid bias generator) and KiCAD/power/ (HV rectifier + filter) are retained drawings for a possible future tube-PA upgrade; they are not being fabricated and are not part of this review package.",
        "KiCAD/analog/Tube_PA.sch.kicad_sch is the DNP future-tube-PA cable-exit sub-sheet (every component on it is DNP — see §9). Its signals appear in analog.net but should be treated as not-present for review purposes.",
        "KiCAD/analog/test.kicad_sch, proto.sch.kicad_sch, ss_PA_Interface.sch.kicad_sch, and untitled.kicad_sch are orphan scratch files (not referenced from the active hierarchy).",
        "SW1 slide-switch pinout (see §6.1) — confirmed correct; reviewer may skip.",
    ]:
        add_bullet(doc, s)

    # ----- 9. DNP list (since .net doesn't carry DNP state)
    add_heading(doc, "9. DNP reference list (not populated — ignore for review)", level=1)
    add_para(doc, "The KiCad .net export does not carry DNP flags. Every reference in the list below is marked DNP on its schematic sub-sheet and will NOT be placed. Treat these as electrically absent even though they appear in analog.net.")
    add_para(doc, "arduino.kicad_sch:", bold=True)
    for s in [
        "J7, J10 (2-pin screw terminals — legacy protoshield power/paddle pairs)",
        "R78 (10K — alternate ENC_INT pull-up at the Metro pin; the upstream R53 10K to +3.3 V on analog serves this role)",
    ]:
        add_bullet(doc, s)
    add_para(doc, "front_panel.kicad_sch:", bold=True)
    add_bullet(doc, "R49, R50, R51 (0R jumpers — alternate routing options)")
    add_para(doc, "interface.kicad_sch:", bold=True)
    add_bullet(doc, "R28, R29, R32, R38, R39, R40 (10K — optional pull-ups, PCF8575 side)")
    add_para(doc, "vfo_complete.kicad_sch:", bold=True)
    add_bullet(doc, "R5 (1K)")
    add_para(doc, "Tube_PA.sch.kicad_sch (entire sub-sheet is DNP — future tube-PA cable exit on J35):", bold=True)
    add_bullet(doc, "C39, C40, C44, C66, C71, C72 (100nF bypass caps on tube-PA conditioning)")
    add_bullet(doc, "D2, D4, D6 (1N4728A Zener clamps on tube-PA sense inputs)")
    add_bullet(doc, "J35 (8P8C_Shielded — the RJ45 to a future tube-PA board)")
    add_bullet(doc, "R85, R87, R88 (1K series on tube-PA signals)")

    # ----- 10. Deliverables
    add_heading(doc, "10. Deliverables", level=1)
    add_para(doc, "A single report, organized by board, that for each board addresses the four review axes (function, component values incl. R/C size/voltage/power, power dissipation, design flaws). Within each board, group by functional block if useful. Cite reference designators and pin numbers so the designer can jump directly to the schematic or netlist location.")

    doc.save(OUT_PATH)
    print(f"wrote {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    build()

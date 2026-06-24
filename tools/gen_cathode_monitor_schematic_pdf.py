"""Generate per-tube cathode monitor + failsafe chain PDF.

  Page 1: schematic (landscape)
  Page 2-3: BOM + defensive-layer table + calibration + open items
"""

import os
import sys
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from draw_cathode_monitor_schematic import make_schematic

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, NextPageTemplate, PageTemplate, Frame,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'Documentation',
                        'Cathode_Monitor_Schematic.pdf')


def _figure_to_image(fig, page_size, margin_in=0.5, dpi=200):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    avail_w = page_size[0] - 2 * margin_in * inch
    avail_h = page_size[1] - 2 * margin_in * inch
    iw, ih = img.imageWidth, img.imageHeight
    scale = min(avail_w / iw, avail_h / ih)
    img.drawWidth = iw * scale
    img.drawHeight = ih * scale
    return img


def _styles():
    s = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('title', parent=s['Title'],
                                fontSize=18, leading=22, alignment=TA_CENTER),
        'h2': ParagraphStyle('h2', parent=s['Heading2'],
                             fontSize=13, leading=16, spaceAfter=6,
                             textColor=colors.HexColor('#222244')),
        'body': ParagraphStyle('body', parent=s['BodyText'],
                               fontSize=10, leading=13, alignment=TA_LEFT),
        'small': ParagraphStyle('small', parent=s['BodyText'],
                                fontSize=9, leading=11),
        'caption': ParagraphStyle('caption', parent=s['BodyText'],
                                  fontSize=9, leading=11, alignment=TA_CENTER,
                                  textColor=colors.HexColor('#555555'),
                                  fontName='Helvetica-Oblique'),
    }


_CELL_STYLE = ParagraphStyle('cell', fontSize=9, leading=11)


def _table(rows, col_widths):
    # Auto-wrap long string cells in Paragraph so reportlab word-wraps instead
    # of overflowing the column. Header row (row 0) stays as plain strings so
    # the bold/centered styling from TableStyle applies cleanly.
    def _wrap_body(cell):
        if isinstance(cell, str) and len(cell) > 28:
            return Paragraph(cell, _CELL_STYLE)
        return cell

    wrapped = [rows[0]] + [
        [_wrap_body(c) for c in row] for row in rows[1:]
    ]
    t = Table(wrapped, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    page_landscape = landscape(letter)
    page_portrait = letter

    frame_landscape = Frame(0.5 * inch, 0.4 * inch,
                            page_landscape[0] - 1.0 * inch,
                            page_landscape[1] - 0.8 * inch,
                            id='landscape')
    frame_portrait = Frame(0.5 * inch, 0.5 * inch,
                           page_portrait[0] - 1.0 * inch,
                           page_portrait[1] - 1.0 * inch,
                           id='portrait')

    doc = SimpleDocTemplate(OUT_PATH, pagesize=page_landscape,
                            leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=0.4 * inch, bottomMargin=0.4 * inch)
    doc.addPageTemplates([
        PageTemplate(id='landscape', frames=[frame_landscape],
                     pagesize=page_landscape),
        PageTemplate(id='portrait', frames=[frame_portrait],
                     pagesize=page_portrait),
    ])

    styles = _styles()
    story = []

    # ─── Page 1: schematic (landscape) ──────────────────────────────────
    story.append(NextPageTemplate('landscape'))
    story.append(_figure_to_image(make_schematic(), page_landscape))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        'Figure 1. Per-tube cathode current monitor + failsafe chain. '
        'Levels 0–5 + the L5b diode-OR combiner shown; Levels 6–7 (firmware) '
        'are described on the next page.',
        styles['caption']))

    # ─── Page 2: defensive layer table + BOM (portrait) ─────────────────
    story.append(NextPageTemplate('portrait'))
    story.append(PageBreak())
    story.append(Paragraph('Defensive Layers and Bill of Materials',
                           styles['title']))
    story.append(Spacer(1, 0.10 * inch))

    layers = [
        ['Level', 'Component(s)', 'Response time', 'Failure mode caught'],
        ['L0', 'R_C (10 Ω, 1 W), C_BYP (0.01 µF NP0)',
         '—', 'Normal sense + RF rejection at tube socket'],
        ['L1', 'F1 = Bourns MF-R010 PTC (100 mA hold)',
         '~ 1 s', 'Sustained fault thermal cooking of downstream parts'],
        ['L2', 'R_S = 10 kΩ 1/4 W series limiter',
         'instant', 'Fault current limited to 60 mA at 600 V cathode short'],
        ['L3', 'D1, D2 = 1N5817 Schottky clamps; C_FILT = 1 nF',
         'instant', 'Voltage spikes beyond ±supply rails; RF anti-alias'],
        ['L4', 'U13, U14 = OPA1641 unity-gain buffer (+5 V / GND)',
         '< 1 µs', 'ADC physically isolated; OPA1641 has ±20 V input protection'],
        ['L5', 'U12 = LM393, V_THR = 1.06–2.13 V (R17/RV1/R18 trim), '
         'R_SOURCE = 7.5 kΩ, R_HYST = 470 kΩ (per channel)',
         '< 10 µs', 'Hardware overcurrent trip → fault HIGH at LM393 OC'],
        ['L5b', 'Diode-OR: D_OR_A, D_OR_B (1N4148) + R_PD = 100 kΩ pulldown',
         '< 1 µs', 'Combine both channels → GRID_BLOCK_CRASH (active HIGH) → '
         'Q2/Q3 bias-slam on bias sheet → grid bias to −85 V → tubes cut off'],
        ['L6', 'Firmware ADC sampling at 1 kHz on ESP32-S3 ADC1, threshold checks',
         '~ 5 ms', 'Soft trip + warnings + UI alerts'],
        ['L7', 'NVS fault log (timestamp, tube_id, type, current, duration)',
         'persistent', 'Post-mortem analysis across power cycles'],
    ]
    story.append(_table(layers, [0.5 * inch, 2.5 * inch, 1.0 * inch, 3.5 * inch]))
    story.append(Spacer(1, 0.20 * inch))

    story.append(Paragraph('Bill of Materials (per tube unless noted; ×2 for the push-pair)',
                           styles['h2']))
    bom = [
        ['Ref', 'Part', 'Qty', 'Notes'],
        ['R_C', '10 Ω 1 % 1 W metal film', '1/tube',
         'Mount AT the tube socket. Vishay PR01000101000JR500 or similar.'],
        ['C_BYP', '0.01 µF NP0 ceramic, 100 V', '1/tube',
         'Low-ESL package, ≤5 mm leads, at socket pin'],
        ['F1', 'Bourns MF-R010 PTC', '1/tube', '100 mA hold, 200 mA trip, V_max 60 V'],
        ['R_S', '10 kΩ 1 % 1/4 W metal film', '1/tube', 'Fault current limit'],
        ['D1, D2', '1N5817 Schottky', '2/tube',
         'Clamps to GND and +3.3 V'],
        ['C_FILT', '1 nF X7R 50 V', '1/tube', 'Anti-alias + RF reject'],
        ['U13, U14', 'OPA1641 single op-amp', '1/tube',
         'Unity-gain buffer. Built-in ±20 V differential input protection.'],
        ['U12', 'LM393 dual comparator', '1',
         'One IC handles both tubes'],
        ['U11', 'LM4040DIZ-5.0', '0',
         'Already in grid_bias BOM. Same +5 V_REF rail powers the threshold divider.'],
        ['R17 / RV1 / R18', '27 kΩ / 10 kΩ 25-turn cermet / 10 kΩ',
         '1 each', 'Shared threshold divider on +5 V_REF. Wiper range 1.06–2.13 V; '
         'nominal set point ~1.5 V (≈150 mA cathode trip).'],
        ['R_SOURCE', '7.5 kΩ 1 %', '1/tube',
         'R20 (ch.B) and R22 (ch.A). OPA1641 OUT → LM393 (+) input. Sets hysteresis with R_HYST.'],
        ['R_HYST', '470 kΩ 1 %', '1/tube',
         'R21 (ch.B) and R23 (ch.A). LM393 OUT → (+) input. ~50 mV hysteresis.'],
        ['R_PULL', '4.7 kΩ 1 %', '1/tube',
         'Pull-up on each LM393 OC output to +3.3 V (NOT shared — see diode-OR below).'],
        ['D_OR_A, D_OR_B', '1N4148 (or 1N5817 from stock)', '1/tube',
         'Diode-OR combiner. Anode at LM393 OC, cathodes tied at GRID_BLOCK_CRASH node.'],
        ['R_PD', '100 kΩ 1 %', '1',
         'Pulldown at the diode-OR common node — defines LOW when no fault.'],
        ['C_DEC', '100 nF X7R + 10 µF bulk', 'several',
         'Decoupling at OPA1641, LM393, LM4040 supply pins.'],
    ]
    story.append(_table(bom, [1.1 * inch, 1.7 * inch, 0.7 * inch, 4.0 * inch]))
    story.append(Spacer(1, 0.20 * inch))

    story.append(Paragraph('Operating Points and Trip Levels', styles['h2']))
    op_table = [
        ['Condition', 'I_cathode', 'V_sense', 'ADC count (12-bit)', 'Action'],
        ['Tubes cut off (key-up)', '0 mA', '0 V', '0', 'normal idle'],
        ['Nominal operating', '100 mA', '1.0 V', '~1240', 'normal log'],
        ['Soft warning threshold', '120 mA', '1.2 V', '~1490',
         'Firmware: warn UI, reduce envelope by 10 %'],
        ['Hard fault (trip)', '~150 mA', '~1.5 V', '~1860',
         'LM393 fault HIGH → diode-OR → GRID_BLOCK_CRASH → Q2/Q3 bias-slam → grid at −85 V'],
        ['Sustained overcurrent', '200 mA+', '2.0 V+', '~2480+',
         'PTC F1 also opens within ~1 s'],
    ]
    story.append(_table(op_table, [1.5 * inch, 0.8 * inch, 0.8 * inch,
                                    1.0 * inch, 3.4 * inch]))

    # ─── Page 3: design rationale + calibration + open items ────────────
    story.append(PageBreak())
    story.append(Paragraph('Design Rationale and Procedures', styles['title']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Why grid-bias slam (not screen, plate, or filament)?',
                           styles['h2']))
    story.append(Paragraph(
        '<b>Plate</b>: 600 V / 250 mA. Hard to switch reliably; relays slow, '
        'MOSFETs expensive at that V_DS. Capacitor discharge dumps significant energy.',
        styles['body']))
    story.append(Paragraph(
        '<b>Screen</b>: workable (low current, fast off) but adds a dedicated switching '
        'MOSFET and a separate failure surface. Not re-used by any other subsystem.',
        styles['body']))
    story.append(Paragraph(
        '<b>Filament</b>: cathode thermal mass means seconds to cool. No protection '
        'against an in-progress fault.',
        styles['body']))
    story.append(Paragraph(
        '<b>Grid bias (chosen)</b>: the OPA454 grid-bias generators on the bias sheet '
        'are already there for normal operation. A single 2N7000 per tube (Q2, Q3) sits '
        'across each OPA454 summing junction. When GRID_BLOCK_CRASH goes HIGH, Q2/Q3 '
        'short the summing junctions to GND; the OPA454 slams its output to the −90 V '
        'rail at 13 V/µs. Both tubes go to deep cutoff (~−85 V grid) in under 100 µs. '
        'No screen-voltage switch, no extra high-voltage MOSFETs, no firmware in the '
        'fast path.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Calibration Procedure', styles['h2']))
    story.append(Paragraph(
        '<b>1. Offset zero:</b> Tubes in deep cutoff (key-up). Read each tube\'s '
        'ADC count; store as <code>cathode_offset[tube_id]</code>.',
        styles['body']))
    story.append(Paragraph(
        '<b>2. Gain calibration:</b> Insert a known shunt resistor in series with '
        'the cathode return, with a DMM measuring I_cathode. Drive the PA to multiple '
        'current levels (50, 75, 100, 125 mA). Record ADC count at each. Fit a line: '
        '<code>I_cathode_mA = (ADC_count − offset) × gain</code>. Store '
        '<code>gain[tube_id]</code>.',
        styles['body']))
    story.append(Paragraph(
        '<b>3. Comparator threshold trim:</b> Drive the tube to I_cathode = 150 mA. '
        'Adjust RV1 (10 kΩ 25-turn cermet between R17 and R18) until LM393 just trips. '
        'Verify it un-trips at 100 mA (hysteresis check). Store the trim date in NVS '
        'as <code>trip_calibration_date</code>.',
        styles['body']))
    story.append(Paragraph(
        '<b>4. Verification:</b> Trip-test with the bias-slam path live. Verify the '
        'grid bias swings from its operating point (~−60 V) to the −85 V rail within '
        '100 µs of the LM393 trip event. Use a scope on a grid pin (with HV probe) to '
        'time-resolve the response.',
        styles['body']))
    story.append(Paragraph(
        'Re-run calibration every 100 operating hours or after any servicing.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Layout and Grounding Rules', styles['h2']))
    story.append(Paragraph(
        '• <b>R_C and C_BYP mount AT the tube socket cathode pin</b>, with leads '
        '≤ 5 mm. C_BYP\'s ground end goes to local chassis (GND_RF).',
        styles['body']))
    story.append(Paragraph(
        '• <b>DC sense tap leaves R_C top BEFORE C_BYP.</b> If reversed, 14 MHz RF '
        'currents flow through the sense path instead of through C_BYP — sense '
        'becomes useless.',
        styles['body']))
    story.append(Paragraph(
        '• <b>Sense wire is twisted pair</b>: hot signal + analog GND return. '
        'Common-mode pickup ≈ 0. Optionally shielded with shield grounded at the '
        'analog-board end only.',
        styles['body']))
    story.append(Paragraph(
        '• <b>Three separate "grounds":</b> GND_RF (tube socket area, bypass caps); '
        'GND_SENSE (analog board signal); GND_DIG (MCU board). All three converge '
        'at exactly one star point on the analog board. No daisy-chain.',
        styles['body']))
    story.append(Paragraph(
        '• <b>Op-amp and comparator on analog board</b>, NOT at the tube socket. '
        'Keeps them within their thermal envelope and away from the RF area.',
        styles['body']))
    story.append(Paragraph(
        '• <b>+3.3 V rail to which D2 clamps</b>: needs ≥ 10 µF bulk cap near the '
        'clamp node to absorb fault energy without sagging.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Open Items', styles['h2']))
    story.append(Paragraph(
        '<b>ADC choice — RESOLVED 2026-06-23:</b> built-in ESP32-S3 ADC1, 12-bit. '
        'Two channels (I_CATHODE_A, I_CATHODE_B) tap the OPA1641 outputs before '
        'R_SOURCE and route to ADC1-capable Metro pins.',
        styles['body']))
    story.append(Paragraph(
        '<b>SR latch — RESOLVED 2026-06-23:</b> no latch chip. The diode-OR + '
        'bias-slam path is unlatched; the slam holds as long as cathode current '
        'is above threshold (with ~50 mV hysteresis). Firmware logs the event from '
        'the ADC path. Cleanup of one part if needed: a firmware-asserted CLEAR '
        'GPIO that pulls the diode-OR common node LOW through a small resistor.',
        styles['body']))
    story.append(Paragraph(
        '<b>1N5817 current margin:</b> 60 mA F1-limited fault is well within the '
        '1 A continuous / 25 A surge rating. No upsizing needed.',
        styles['body']))
    story.append(Paragraph(
        '<b>Remaining bias-sheet work:</b> add the diode-OR diodes (D_OR_A, D_OR_B), '
        'second R_PULL, and R_PD = 100 kΩ pulldown on bias.kicad_sch; add '
        'I_CATHODE_A / I_CATHODE_B hierarchical labels routing to the Metro ADC1 pins '
        'on the arduino sheet.',
        styles['body']))
    story.append(Paragraph(
        '<b>Per-pair sum monitor:</b> optional third comparator with threshold at '
        '280 mA total cathode current (sum of both tubes), to catch the case where '
        'both tubes drift hot together without individual tube exceeding its '
        'threshold.',
        styles['body']))

    doc.build(story)
    print(f'Wrote {OUT_PATH}')


if __name__ == '__main__':
    main()

"""Generate per-tube grid bias control PDF with both design variants.

  Page 1: Design A (OPA454) schematic — landscape
  Page 2: Design A component table + transfer function — portrait
  Page 3: Design B (discrete PNP) schematic — landscape
  Page 4: Design B component table + transfer function — portrait
  Page 5: Shared design notes — power-up sequence, two-state operation,
          fail-safe, layout notes, comparison
"""

import os
import sys
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from draw_grid_bias_schematic import make_schematic_opa454, make_schematic_discrete

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
                        'Grid_Bias_Schematic.pdf')


def _figure_to_image(fig, page_size, margin_in=0.5, dpi=200):
    """Render the matplotlib Figure into a ReportLab Image flowable scaled
    to the given page size minus margins."""
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


def _table(rows, col_widths):
    t = Table(rows, colWidths=col_widths)
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

    # ── Set up document with both landscape and portrait page templates ──
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

    # ─── Page 1: Design A schematic (landscape) ─────────────────────────
    story.append(NextPageTemplate('landscape'))
    story.append(_figure_to_image(make_schematic_opa454(), page_landscape))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        'Figure 1. Design A — OPA454 HV op-amp version. One channel; '
        'replicate for the second tube.',
        styles['caption']))

    # ─── Page 2: Design A component table and notes (portrait) ──────────
    story.append(NextPageTemplate('portrait'))
    story.append(PageBreak())
    story.append(Paragraph('Design A — OPA454 Components & Transfer Function',
                           styles['title']))
    story.append(Spacer(1, 0.15 * inch))

    a_table = [
        ['Ref', 'Value / Part', 'Notes'],
        ['DAC', 'MCP4725 (×2)',
         'I²C 12-bit; EEPROM startup = 0 → output = 0 V → V_out = −85 V (IDLE)'],
        ['Op-amp', 'OPA454 (×2)',
         'HV op-amp, V+ = +12 V / V− = −85 V (97 V total, within 100 V op max)'],
        ['V_REF', 'LM4040DIZ-5.0', 'Precision +5 V shunt reference'],
        ['R_pad', '1 kΩ 1%', 'DAC → (+) input series; impedance matching'],
        ['R_G', '10 kΩ 1%', '(−) input ↔ V_REF (+5 V)'],
        ['R_F', '170 kΩ 1% (or 169 kΩ E96)', 'Feedback (−) ↔ V_out'],
        ['Decoupling', '100 nF X7R + 10 µF on each rail at the OPA454', ''],
        ['+5 V rail', 'Same as DAC / LM4040 supply',
         'Trivial current; share existing rail'],
        ['−85 V rail',
         'Isolated DC-DC (e.g., Murata NMA0509) + voltage doubler + TL431 shunt regulator',
         '~5 mA for both PA channels'],
        ['R_GL', '22 kΩ (already in PA subcircuit)', 'Unchanged'],
    ]
    story.append(_table(a_table, [1.0 * inch, 2.4 * inch, 4.0 * inch]))
    story.append(Spacer(1, 0.20 * inch))

    story.append(Paragraph('Transfer Function', styles['h2']))
    story.append(Paragraph(
        '<b>V_out = V_DAC × (1 + R_F/R_G) − V_REF × R_F/R_G '
        '= V_DAC × 18 − 85</b>',
        styles['body']))
    story.append(Paragraph(
        '<b>V_DAC = 0 V&nbsp;&nbsp;&nbsp;→&nbsp;&nbsp;&nbsp;V_out = −85 V</b>  '
        '(IDLE: tubes deeply cut off, zero plate current)',
        styles['small']))
    story.append(Paragraph(
        '<b>V_DAC = 1.94 V → V_out = −50 V</b>  '
        '(OPERATE: shallow class C, ready for envelope) — DAC code 2410 (of 4095)',
        styles['small']))
    story.append(Paragraph(
        '<b>V_DAC = 3.3 V&nbsp;→&nbsp;V_out = −25.6 V</b>  '
        '(<i>firmware MUST cap below this</i> — would forward-bias the grid)',
        styles['small']))
    story.append(Spacer(1, 0.10 * inch))
    story.append(Paragraph(
        '<b>Common-mode input range check:</b> with V+ = +12 V / V− = −85 V '
        'and OPA454\'s 3 V CM margin from V+, the (+) input range is roughly '
        '−82 V to +9 V. V_DAC at the (+) input swings 0 to ~2 V (firmware-'
        'bounded), comfortably inside with 7 V margin to the upper limit.',
        styles['body']))
    story.append(Paragraph(
        '<b>Output swing check:</b> the OPA454 rail-to-rail output reaches '
        'within ~1 V of either rail under light load (high-impedance grid '
        'leak). Range: −84 V to +11 V. Covers −85 V (IDLE) at the edge of '
        'rail-to-rail capability; for guaranteed 2 V swing margin, shift '
        'IDLE to −82 V by adjusting R_F (e.g., R_F = 164 kΩ → V_out at '
        'V_DAC=0 of −82 V).',
        styles['body']))
    story.append(Paragraph(
        '<b>Supply margin:</b> the +12 V / −85 V choice gives 97 V total — '
        '3 V under the OPA454 100 V operating max, well under the 120 V '
        'absolute max.',
        styles['body']))

    # ─── Page 3: Design B schematic (landscape) ─────────────────────────
    story.append(NextPageTemplate('landscape'))
    story.append(PageBreak())
    story.append(_figure_to_image(make_schematic_discrete(), page_landscape))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        'Figure 2. Design B — LM358 + discrete MPSA92 PNP level-shifter. '
        'Same transfer function as Design A; no op-amp voltage limit.',
        styles['caption']))

    # ─── Page 4: Design B component table and notes (portrait) ──────────
    story.append(NextPageTemplate('portrait'))
    story.append(PageBreak())
    story.append(Paragraph(
        'Design B — Discrete PNP Components & Notes', styles['title']))
    story.append(Spacer(1, 0.15 * inch))

    b_table = [
        ['Ref', 'Value / Part', 'Notes'],
        ['DAC', 'MCP4725 (×2)', 'Same as Design A'],
        ['Op-amp', 'LM358 (×2; one half each), or TL072',
         'LV op-amp, single +5 V supply — no HV constraint'],
        ['HV transistor', 'MPSA92 (×2)',
         'PNP, V_CEO = 300 V, TO-92; alternative: KSP44, ZTX560, 2N5401 (160 V)'],
        ['V_REF', 'LM4040DIZ-5.0', 'Same +5 V shunt reference as Design A'],
        ['R_pad', '1 kΩ 1%', 'DAC → (+) input series'],
        ['R_G', '10 kΩ 1%', '(−) input ↔ V_REF (+5 V)'],
        ['R_F', '170 kΩ 1% (or 169 kΩ E96)',
         'Feedback from PNP collector ↔ (−) input'],
        ['R_B', '10 kΩ', 'Base current limit; sets loop slew comfortably'],
        ['R_E', '10 kΩ', 'Emitter resistor to +5 V; sets ~0.4 mA emitter current'],
        ['R_L', '100 kΩ', 'Collector pull-down to −90 V; sets load impedance'],
        ['Decoupling',
         '100 nF X7R at each LM358 supply pin; '
         '1 nF NP0 across each transistor B-E for HF stability',
         ''],
        ['+5 V rail', 'Shared with DAC, LM4040, LM358', ''],
        ['−90 V rail', 'Same isolated DC-DC as Design A',
         'Loads R_L (×2 tubes); ~1 mA total'],
        ['R_GL', '22 kΩ (already in PA subcircuit)', 'Unchanged'],
    ]
    story.append(_table(b_table, [1.0 * inch, 2.4 * inch, 4.0 * inch]))
    story.append(Spacer(1, 0.20 * inch))

    story.append(Paragraph(
        'Transfer Function and Operation', styles['h2']))
    story.append(Paragraph(
        '<b>Same as Design A: V_out = V_DAC × 18 − 85</b>',
        styles['body']))
    story.append(Paragraph(
        'The PNP collector node is the output. LM358 closes the loop via R_F '
        'sensing the collector voltage; the op-amp drives the PNP base to '
        'whatever level forces V_(−) = V_(+) = V_DAC. No supply-voltage '
        'limits on the loop because the HV stress is borne entirely by '
        'the PNP transistor.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))
    story.append(Paragraph(
        '<b>PNP stress check:</b> V_CE_max ≈ V_E − V_C_min = +4.4 V − (−85 V) '
        '= 89 V — well below MPSA92\'s 300 V V_CEO rating (3.4× margin). '
        'Max I_C = (V_out − V_neg) / R_L = (−50 − (−90)) / 100 kΩ = 0.4 mA. '
        'Max P_diss = V_CE × I_C ≈ 35 mW (any TO-92 fits comfortably).',
        styles['body']))
    story.append(Paragraph(
        '<b>Op-amp swing required:</b> the LM358 only needs to swing about '
        '±0.7 V around the PNP base operating point — fully within single-'
        'supply LM358 specs. Even at the IDLE end (V_out = −85 V → I_C ≈ 0), '
        'the op-amp output stays within rails.',
        styles['body']))
    story.append(Paragraph(
        '<b>Why this exists:</b> if the OPA454 is unobtainable, of dubious '
        'authenticity (the marketplace has counterfeits), or you prefer not '
        'to operate any single part at its supply max, the discrete design '
        'is electrically equivalent and built from in-stock generics. The '
        'MPSA92 is a $0.10 part in singles.',
        styles['body']))

    # ─── Page 5: Shared design notes (portrait) ─────────────────────────
    story.append(PageBreak())
    story.append(Paragraph(
        'Shared: Two-State Operation, Power-Up, Fail-Safe, Layout',
        styles['title']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Two-State Operation', styles['h2']))
    story.append(Paragraph(
        'Bias has two firmware-managed states with smooth transitions:',
        styles['body']))
    story.append(Paragraph(
        '<b>IDLE</b> (key-up): DAC = 0 → V_out = −85 V → 6146B fully cut off, '
        'plate current = 0, standby dissipation = 0 W per tube. This is the '
        'safe-park state.',
        styles['body']))
    story.append(Paragraph(
        '<b>OPERATE</b> (key-down): DAC = 2410 (of 4095) → V_out = −50 V → '
        'shallow class C, smooth conduction onset, full envelope dynamic '
        'range available to the predistortion LUT.',
        styles['body']))
    story.append(Paragraph(
        '<b>Per-tube trim:</b> the OPERATE DAC code may differ by a few '
        'counts between tubes to balance for tube-to-tube spread. Calibrated '
        'at bring-up via the cathode-current monitor.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Power-Up Sequence and Firmware Timing',
                           styles['h2']))
    story.append(Paragraph(
        '<b>Power-on:</b> Rails come up (+5 V, −90 V). MCP4725 EEPROM '
        'startup value = 0 → DAC = 0 V → V_out = −85 V on both tubes. PA is '
        'in deep cutoff before the MCU finishes booting.',
        styles['body']))
    story.append(Paragraph(
        '<b>Key-down sequence:</b> (1) WinKey signals key-down; (2) per-tube '
        'bias DACs commanded IDLE → OPERATE (each ~25 µs over I²C); (3) wait '
        '200 µs for op-amp + grid input cap to settle; (4) launch envelope '
        'DAC raised-cosine ramp from 0 → CODE_FULL.',
        styles['body']))
    story.append(Paragraph(
        '<b>Key-up sequence:</b> (1) envelope DAC ramps to 0 over 3–5 ms; '
        '(2) wait 1 ms guard after envelope nulls; (3) bias DACs commanded '
        'OPERATE → IDLE; (4) wait 200 µs to confirm tubes back in cutoff.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Fail-Safe', styles['h2']))
    story.append(Paragraph(
        'Three independent layers:',
        styles['body']))
    story.append(Paragraph(
        '<b>(1) DAC EEPROM safe-park:</b> startup value 0 → IDLE bias on '
        'cold boot, before MCU initializes I²C.',
        styles['body']))
    story.append(Paragraph(
        '<b>(2) Watchdog gate:</b> esp_task_wdt pulls a hardware GPIO that '
        'removes screen voltage if the MCU hangs. PA goes dark even if the '
        'DAC is stuck in OPERATE.',
        styles['body']))
    story.append(Paragraph(
        '<b>(3) Cathode-current monitor:</b> independent ADC-based sense '
        '(separate circuit) triggers a soft-shutdown if either tube exceeds '
        'its current limit. Captured separately in the cathode-sense '
        'design notes.',
        styles['body']))
    story.append(Spacer(1, 0.10 * inch))

    story.append(Paragraph('Layout Notes', styles['h2']))
    story.append(Paragraph(
        '• Keep the op-amp/transistor output trace short and away from RF; '
        'the 22 kΩ grid leak provides isolation but route bias on a separate '
        'layer from RF signals where possible.',
        styles['body']))
    story.append(Paragraph(
        '• −90 V rail is small-current but high-voltage. Use ≥150 V rated '
        'film/ceramic capacitors for bypass. Standard 25 V ceramics will fail.',
        styles['body']))
    story.append(Paragraph(
        '• Allocate distinct I²C addresses for the two per-tube DACs '
        '(MCP4725 supports 0x60–0x67 via the A0/A1/A2 pads). Collisions kill '
        'the I²C bus.',
        styles['body']))
    story.append(Paragraph(
        '• <b>Design B only:</b> mount the PNP transistor close to its base '
        'resistor and decouple its emitter with 100 nF to its supply pin '
        'side. The PNP is fast (f_T ≈ 50 MHz) and can ring without proper '
        'damping if the base is driven through long inductive traces.',
        styles['body']))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph('Design A vs. Design B Comparison', styles['h2']))
    comp_table = [
        ['', 'Design A (OPA454)', 'Design B (Discrete PNP)'],
        ['Op-amp', 'OPA454 (HV)', 'LM358 (LV) + MPSA92 PNP'],
        ['Cost', '~$5 (single-source TI)',
         '~$0.50 (LM358 + MPSA92)'],
        ['Supply margin', '5 V under op max (100 V) — adequate',
         'Unlimited (PNP V_CEO = 300 V)'],
        ['Parts count', '5 R + 1 IC + 1 ref + bypass',
         '6 R + 1 IC + 1 transistor + 1 ref + bypass'],
        ['Convenience', 'Single IC handles everything',
         'Two-stage; transistor needs care for HF stability'],
        ['Counterfeit risk', 'OPA454 has known counterfeit sources',
         'MPSA92 / LM358 are generic — no incentive to fake'],
        ['Authenticity check', 'Power test before installing; '
         'check the laser-etched marking; '
         'genuine vs. relabel can be hard to tell',
         'Not really an issue'],
    ]
    story.append(_table(comp_table, [1.6 * inch, 2.7 * inch, 3.2 * inch]))

    doc.build(story)
    print(f'Wrote {OUT_PATH}')


if __name__ == '__main__':
    main()

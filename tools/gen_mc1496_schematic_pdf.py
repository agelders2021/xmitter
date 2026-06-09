"""Generate MC1496 VCA Buffer schematic-description PDF for review and web Claude handoff.

Page 1: full-page schematic diagram (landscape)
Page 2+: component tables and notes (portrait)
"""

import os, io, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add tools dir so we can import the drawing module
sys.path.insert(0, os.path.dirname(__file__))
from draw_mc1496_schematic import make_schematic

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted, Image, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'Documentation', 'MC1496_VCA_Buffer_Schematic.pdf')

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

title_style = ParagraphStyle('Title2', parent=styles['Title'],
    fontSize=16, spaceAfter=6, textColor=colors.HexColor('#1F3864'))

h1_style = ParagraphStyle('H1', parent=styles['Heading1'],
    fontSize=13, spaceBefore=14, spaceAfter=4,
    textColor=colors.HexColor('#2F5496'),
    borderPad=2)

h2_style = ParagraphStyle('H2', parent=styles['Heading2'],
    fontSize=11, spaceBefore=10, spaceAfter=3,
    textColor=colors.HexColor('#404040'))

body_style = ParagraphStyle('Body2', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=4)

note_style = ParagraphStyle('Note', parent=styles['Normal'],
    fontSize=9, leading=13, spaceAfter=4,
    textColor=colors.HexColor('#555555'),
    leftIndent=12,
    borderPad=4,
    backColor=colors.HexColor('#F5F5F5'))

warn_style = ParagraphStyle('Warn', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=4,
    textColor=colors.HexColor('#7B0000'),
    leftIndent=12)

code_style = ParagraphStyle('Code', parent=styles['Code'],
    fontSize=8.5, leading=13, fontName='Courier',
    leftIndent=18, spaceAfter=6,
    backColor=colors.HexColor('#F0F0F0'))

bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=3,
    leftIndent=18, firstLineIndent=-12)

# ── Table helpers ─────────────────────────────────────────────────────────────
HDR_FILL = colors.HexColor('#2F5496')
ROW_ALT  = colors.HexColor('#EEF2FF')

def hdr_row_style(n_cols):
    return [
        ('BACKGROUND', (0,0), (-1,0), HDR_FILL),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
        ('GRID',       (0,0), (-1,-1), 0.4, colors.HexColor('#AAAAAA')),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]

def p(text, style=None):
    return Paragraph(text, style or body_style)

def b(text):
    return Paragraph(f'• {text}', bullet_style)

def hr():
    return HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=6)

# ── Schematic page renderer ───────────────────────────────────────────────────
def _schematic_image():
    """Render the schematic figure to a reportlab Image at landscape letter size."""
    fig = make_schematic()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    # Landscape letter inner area: 11 × 8.5 inches, minus small margins
    img = Image(buf, width=9.8*inch, height=7.1*inch)
    return img


def _schematic_page(canvas, doc):
    """Draw schematic full-page on a landscape page (called as onFirstPage)."""
    pass  # content inserted via story


# ── Content ───────────────────────────────────────────────────────────────────
def build():
    # Page 1: landscape schematic
    # Pages 2+: portrait text — use a multi-page document with mixed sizes
    # Simplest approach: render schematic as a full-page Image in a landscape doc section,
    # then switch to portrait for the tables.
    # ReportLab SimpleDocTemplate doesn't support mixed page sizes, so we use two files
    # merged, OR we use one landscape doc with the text resized to fit.
    # Cleanest: use a single landscape document; tables are wide enough to fit.

    doc = SimpleDocTemplate(
        os.path.abspath(OUT_PATH),
        pagesize=landscape(letter),   # 11 × 8.5 inches
        leftMargin=0.4*inch, rightMargin=0.4*inch,
        topMargin=0.4*inch,  bottomMargin=0.4*inch,
    )

    story = []

    # ── Page 1: full-page schematic ───────────────────────────────────────────
    story.append(_schematic_image())
    story.append(PageBreak())

    # ── Page 2+: component tables ─────────────────────────────────────────────
    # Title block
    story.append(p('MC1496 VCA Buffer — Schematic Description', title_style))
    story.append(p('20m CW Transmitter · Keyed Buffer / Amplitude Control Stage', ParagraphStyle(
        'Sub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#555555'), spaceAfter=4)))
    story.append(p('For schematic drawing and verification. '
                   'Pin numbers are per ON Semiconductor MC1496 datasheet.',
                   ParagraphStyle('Sub2', parent=styles['Normal'],
                       fontSize=9, textColor=colors.HexColor('#AA0000'), spaceAfter=8)))
    story.append(hr())

    # ── Supply rails ──────────────────────────────────────────────────────────
    story.append(p('Supply Rails', h1_style))
    rails = [
        ['Net', 'Voltage', 'Notes'],
        ['VDD',  '+12 V',  'Enters only through output load resistors R_LOAD_P / R_LOAD_N — no dedicated VCC pin on MC1496'],
        ['VEE',  '−8.2 V', 'Pin 14 only'],
        ['GND',  '0 V',    'Signal references, bypass caps'],
    ]
    t = Table(rails, colWidths=[0.7*inch, 0.8*inch, 6.8*inch])
    t.setStyle(TableStyle(hdr_row_style(3)))
    story.append(t)
    story.append(Spacer(1, 8))

    # ── MC1496 pin table ──────────────────────────────────────────────────────
    story.append(p('MC1496 DIP-14 Pin Assignments', h1_style))
    story.append(p('Source: ON Semiconductor MC1496 datasheet. '
                   '<b>Earlier design documents had pins 6/8/10/12 swapped — this table is correct.</b>',
                   note_style))
    story.append(Spacer(1, 4))

    pins = [
        ['Pin', 'Datasheet Function', 'Circuit Net / Connection'],
        ['1',  'Signal input (+)',  'SIG_P → R_SIG_P (10 kΩ to GND); also receives R_INJ1 (330 kΩ) from DAC_NULL_P'],
        ['2',  'Gain adjust',       'Pin 2 end of R_RE (1 kΩ between pins 2 and 3)'],
        ['3',  'Gain adjust',       'Pin 3 end of R_RE (1 kΩ between pins 2 and 3)'],
        ['4',  'Signal input (−)',  'SIG_N → AGC divider (R_SCALE1 / R_SCALE2); also receives R_INJ2 (330 kΩ) from DAC_NULL_N'],
        ['5',  'Bias',              'VBIAS → R_BIAS (1 kΩ) to VEE'],
        ['6',  'Output (+)',        'OUT_P → R_LOAD_P bottom (3.9 kΩ to VDD) → driver P2'],
        ['7',  'NC',                '—'],
        ['8',  'Carrier input',     'CAR_P → CC_CAR (10 nF) → VFO RF input (14.175 MHz)'],
        ['9',  'NC',                '—'],
        ['10', 'Carrier input',     'CAR_N → CCAR_N (100 nF to GND)'],
        ['11', 'NC',                '—'],
        ['12', 'Output (−)',        'OUT_N → R_LOAD_N bottom (3.9 kΩ to VDD) → driver P4'],
        ['13', 'NC',                '—'],
        ['14', 'Vee',               'VEE rail (−8.2 V)'],
    ]
    t = Table(pins, colWidths=[0.4*inch, 1.4*inch, 4.3*inch])
    ts = hdr_row_style(3)
    # Highlight output and carrier rows
    for row, pin in enumerate(pins[1:], start=1):
        if pin[0] in ('6', '12'):
            ts.append(('TEXTCOLOR', (0,row), (-1,row), colors.HexColor('#1A5276')))
            ts.append(('FONTNAME',  (0,row), (-1,row), 'Helvetica-Bold'))
        elif pin[0] in ('8', '10'):
            ts.append(('TEXTCOLOR', (0,row), (-1,row), colors.HexColor('#186A3B')))
            ts.append(('FONTNAME',  (0,row), (-1,row), 'Helvetica-Bold'))
    t.setStyle(TableStyle(ts))
    story.append(t)
    story.append(p('Blue-bold = output pins. Green-bold = carrier input pins.', note_style))
    story.append(Spacer(1, 8))

    # ── Component list ────────────────────────────────────────────────────────
    story.append(p('All Components and Connections', h1_style))

    story.append(p('RF Carrier Input Path', h2_style))
    comps = [
        ['Ref', 'Value', 'Connection'],
        ['V_Q1S', '14.175 MHz, 0.378 V pk', 'Source (+) → _rf_in node; (−) → GND'],
        ['CC_CAR', '10 nF',  '_rf_in → CC_CAR → CAR_P (pin 8)'],
        ['CCAR_N', '100 nF', 'GND → CCAR_N → CAR_N (pin 10)  [bypass, keep short]'],
    ]
    t = Table(comps, colWidths=[0.8*inch, 1.4*inch, 3.9*inch])
    t.setStyle(TableStyle(hdr_row_style(3)))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(p('Output Load Resistors (VDD to MC1496 outputs)', h2_style))
    story.append(p('<b>VDD must connect only to R_LOAD_P and R_LOAD_N tops. '
                   'It shares NO node with the RF carrier input path.</b>', warn_style))
    comps = [
        ['Ref', 'Value', 'Connection'],
        ['R_LOAD_P', '3.9 kΩ', 'Top → VDD (+12 V);  Bottom → OUT_P (pin 6) → driver P2'],
        ['R_LOAD_N', '3.9 kΩ', 'Top → VDD (+12 V);  Bottom → OUT_N (pin 12) → driver P4'],
    ]
    t = Table(comps, colWidths=[0.8*inch, 1.0*inch, 4.3*inch])
    t.setStyle(TableStyle(hdr_row_style(3)))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(p('Signal Port / AGC Network', h2_style))
    comps = [
        ['Ref', 'Value', 'Connection'],
        ['R_SIG_P',  '10 kΩ',  'SIG_P (pin 1) → GND  [holds pin 1 reference near GND]'],
        ['R_SCALE1', '100 kΩ', 'V_AGC (+) → R_SCALE1 → SIG_N (pin 4)  [AGC upper divider leg]'],
        ['R_SCALE2', '5.1 kΩ', 'SIG_N (pin 4) → GND  [AGC lower divider leg; ratio 4.85%]'],
        ['V_AGC',    '10 V DC', '(Simulation stand-in for TL071 AGC integrator output)  (+) → R_SCALE1 bottom; (−) → GND'],
    ]
    t = Table(comps, colWidths=[0.8*inch, 1.0*inch, 4.3*inch])
    t.setStyle(TableStyle(hdr_row_style(3)))
    story.append(t)
    story.append(Spacer(1, 6))

    story.append(p('Digital Carrier Null Network', h2_style))
    story.append(p('Replaces mechanical trimmer pot. Two DAC outputs inject a differential offset to cancel '
                   'residual carrier caused by transistor mismatch inside the MC1496. '
                   'Target: ≥65 dB suppression. DAC_NULL_P and DAC_NULL_N are complementary 12-bit outputs; '
                   'midscale = no injection; firmware binary-searches for minimum carrier at key-down.', body_style))
    comps = [
        ['Ref', 'Value', 'Connection'],
        ['R_INJ1', '330 kΩ', 'DAC_NULL_P → R_INJ1 → SIG_P (pin 1);  joins existing R_SIG_P / pin 1 junction'],
        ['R_INJ2', '330 kΩ', 'DAC_NULL_N → R_INJ2 → SIG_N (pin 4);  joins existing AGC / pin 4 junction'],
    ]
    t = Table(comps, colWidths=[0.8*inch, 1.3*inch, 4.0*inch])
    t.setStyle(TableStyle(hdr_row_style(3)))
    story.append(t)
    story.append(p('Full-scale swing: ±16 mV per pin, ±33 mV differential total — covers MC1496 worst-case '
                   'input offset (≤5 mV). Step size at 12-bit: ~8 µV. No series protection resistors needed; '
                   '330 kΩ inherently limits injection current. Null stored in NVRAM, refreshed periodically.',
                   note_style))
    story.append(Spacer(1, 6))

    story.append(p('Bias and Gain-Set', h2_style))
    comps = [
        ['Ref', 'Value', 'Connection'],
        ['R_BIAS', '6.8 kΩ', 'VBIAS (pin 5) → R_BIAS → GND  [sets I5 ≈ 1 mA per AN531/D formula]'],
        ['R_RE',   '1 kΩ',   'Between pin 2 and pin 3 (NOT shorted to VEE); sets gain Av = R_LOAD / R_RE; may change to 500 Ω at bring-up'],
    ]
    t = Table(comps, colWidths=[0.8*inch, 1.0*inch, 4.3*inch])
    t.setStyle(TableStyle(hdr_row_style(3)))
    story.append(t)
    story.append(Spacer(1, 8))

    # ── Signal flow ───────────────────────────────────────────────────────────
    story.append(p('Signal Flow Diagram (ASCII)', h1_style))
    flow = """\
VFO (14.175 MHz) ─── CC_CAR (10nF) ─── pin 8 (CAR_P)
                                               │
                                          MC1496
                                               │
                    VDD ─ R_LOAD_P (3.9k) ─ pin 6 (OUT_P) ──► driver P2
                    VDD ─ R_LOAD_N (3.9k) ─ pin 12 (OUT_N) ─► driver P4

GND ── CCAR_N (100nF) ── pin 10 (CAR_N)

V_AGC ─ R_SCALE1 (100k) ─ pin 4 (SIG_N) ─ R_SCALE2 (5.1k) ─ GND

DAC_NULL_N ─ R_INJ2 (330kΩ) ─ SIG_N (pin 4)

GND ─ R_SIG_P (10k) ─ SIG_P (pin 1)

DAC_NULL_P ─ R_INJ1 (330kΩ) ─ SIG_P (pin 1)
(complementary DAC codes; midscale = no injection)

GND ─ R_BIAS (6.8k) ─ pin 5 (BIAS)
pin 2 ─ R_RE (1kΩ) ─ pin 3   (between gain-adjust pins, NOT to VEE)
VEE ──────────────── pin 14
"""
    story.append(Preformatted(flow, code_style))

    # ── Layout notes ──────────────────────────────────────────────────────────
    story.append(p('Key Layout / Drawing Notes', h1_style))
    notes = [
        '<b>Pin 6 = Output, Pin 8 = Carrier input.</b> Earlier documents had these swapped. Verify against datasheet before drawing.',
        'VDD connects <b>only</b> to R_LOAD_P top and R_LOAD_N top. It shares no node with the RF carrier input (CC_CAR / pin 8).',
        'Pin 6 (OUT_P) and pin 8 (CAR_P) are on the same side of the DIP but are <b>completely separate nets</b>.',
        'Pins 2 and 3 are both gain-adjust — connect R_RE (1 kΩ) between pin 2 and pin 3. Do NOT short to VEE.',
        'No VCC pin on the MC1496. +12 V enters only through R_LOAD_P and R_LOAD_N.',
        'Vee = pin 14, not pin 7. Pin 7 is NC.',
        'CCAR_N (100 nF) bypasses pin 10 to GND — keep lead very short.',
        '<b>Digital carrier null:</b> R_INJ1 (330 kΩ) from DAC_NULL_P to pin 1; R_INJ2 (330 kΩ) from DAC_NULL_N to pin 4. '
        'Complementary 12-bit DAC codes; midscale = no injection; firmware binary-searches for null at key-down. '
        'Null stored in NVRAM. No separate protection resistors needed — 330 kΩ limits current inherently.',
        'OUT_P and OUT_N feed the driver push-pull grids directly (no interstage transformer).',
    ]
    for n in notes:
        story.append(b(n))

    story.append(Spacer(1, 12))
    story.append(hr())
    story.append(p('Generated from Documentation/vfo_buffer_circuit_for_drawing.md and '
                   'xmitter_prj/mc1496_level_control.md · 20m CW Transmitter project',
                   ParagraphStyle('Footer', parent=styles['Normal'],
                       fontSize=8, textColor=colors.HexColor('#888888'))))

    doc.build(story)
    print(f'Saved: {os.path.abspath(OUT_PATH)}')


if __name__ == '__main__':
    build()

"""
gen_library_doc.py
Generate a PDF reference for xmitter.kicad_sym: pinouts and design gotchas.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pathlib import Path
import textwrap

OUT = Path(r'C:\Users\AlAnd\Git Backed Projects\xmitter\Documentation\kicad_library.pdf')

# ── page geometry ─────────────────────────────────────────────────────────────
PW, PH  = 8.5, 11.0
LM, RM  = 0.55, 8.10
TM, BM  = 10.20, 0.50

# ── component data ─────────────────────────────────────────────────────────────
COMPS = [
    dict(
        name='MC1496', desc='Balanced Modulator / Demodulator',
        package='DIP-14', mfr='onsemi', mpn='MC1496P',
        pins=[
            ('1',  'SIG_IN+',  'Signal input + (AGC/modulating port)'),
            ('2',  'GADJ_A',   'Gain adjust A'),
            ('3',  'GADJ_B',   'Gain adjust B'),
            ('4',  'SIG_IN-',  'Signal input − (AGC/modulating port)'),
            ('5',  'BIAS',     'Output bias'),
            ('6',  'OUT+',     'Collector output +'),
            ('7',  'NC',       '—'),
            ('8',  'CAR_IN-',  'Carrier input −'),
            ('9',  'NC',       '—'),
            ('10', 'CAR_IN+',  'Carrier input +'),
            ('11', 'NC',       '—'),
            ('12', 'OUT-',     'Collector output −'),
            ('13', 'NC',       '—'),
            ('14', 'VEE',      'Positive supply (+12 V)'),
        ],
        gotchas=[
            'VEE (pin 14) is the POSITIVE supply — counterintuitive Motorola naming convention.',
            'SIG_IN pins (1, 4) take the 0–10 V key-shaping voltage in this design (AGC/modulating port).',
            'Pins 7, 9, 11, 13 are NC — leave unconnected; no X markers required.',
            'MC1496P (DIP) has limited availability. SOIC MC1496DR2G is more readily stocked.',
        ],
    ),
    dict(
        name='MCP4921', desc='12-bit SPI DAC, Single Channel',
        package='DIP-8', mfr='Microchip Technology', mpn='MCP4921-E/P',
        pins=[
            ('1', 'VDD',   'Positive supply (3.3 V)'),
            ('2', '~CS',   'SPI chip select, active low'),
            ('3', 'SCK',   'SPI clock'),
            ('4', 'SDI',   'SPI data input'),
            ('5', '~LDAC', 'Latch DAC output, active low'),
            ('6', 'VREF',  'Reference voltage input'),
            ('7', 'VSS',   'Ground'),
            ('8', 'VOUT',  'DAC analog output (0 – VREF)'),
        ],
        gotchas=[
            'Connect VREF to 3.3 V rail — output range is 0–3.3 V before the TL072 gain stage (×3 → 0–9.9 V).',
            '~LDAC: pull permanently low for immediate output update on each SPI write.',
            'SPI command word: 0x3000 OR 12-bit data  (gain=1×, unbuffered, active mode).',
            'Shares SPI bus with ST7735 and W5500 — each device must have its own CS line.',
        ],
    ),
    dict(
        name='TL072', desc='Dual Low-Noise JFET Op-Amp  (3 units: A, B, Power)',
        package='DIP-8', mfr='Texas Instruments', mpn='TL072CP',
        pins=[
            ('1', 'OUT [A]',  'Op-amp 1 output'),
            ('2', 'IN− [A]',  'Op-amp 1 inverting input'),
            ('3', 'IN+ [A]',  'Op-amp 1 non-inverting input'),
            ('4', 'VCC−',     'Negative supply (−8.2 V from rig rail)'),
            ('5', 'IN+ [B]',  'Op-amp 2 non-inverting input'),
            ('6', 'IN− [B]',  'Op-amp 2 inverting input'),
            ('7', 'OUT [B]',  'Op-amp 2 output'),
            ('8', 'VCC+',     'Positive supply (+12 V from rig rail)'),
        ],
        gotchas=[
            'Multi-unit symbol: place U?A and U?B as separate op-amp instances; U?C for power connections.',
            'Supply: +12 V / −8.2 V from existing rig rails — 20.2 V total, within 36 V absolute max.',
            'Output swings to within ~2 V of +rail: 10 V output is achievable with a +12 V supply.',
            'Tie unused unit: IN+ to GND via 10 kΩ, IN− to its own output. Never leave inputs floating.',
        ],
    ),
    dict(
        name='ADS1115', desc='16-bit 4-Channel I²C ADC',
        package='MSOP-10', mfr='Texas Instruments', mpn='ADS1115IDGST',
        pins=[
            ('1',  'ADDR',       'I²C address select'),
            ('2',  '~ALERT/RDY', 'Alert / conversion ready, open-drain'),
            ('3',  'GND',        'Ground'),
            ('4',  'AIN0',       'Analog input 0'),
            ('5',  'AIN1',       'Analog input 1'),
            ('6',  'AIN2',       'Analog input 2'),
            ('7',  'AIN3',       'Analog input 3'),
            ('8',  'VDD',        'Positive supply (2.0–5.5 V)'),
            ('9',  'SDA',        'I²C data, bidirectional'),
            ('10', 'SCL',        'I²C clock'),
        ],
        gotchas=[
            'ADDR sets I²C address: GND→0x48, VDD→0x49, SDA→0x4A, SCL→0x4B.',
            '~ALERT/RDY is open-drain — pull-up resistor required (4.7 kΩ to VDD).',
            'ADS1115IDGST is tape-and-reel (2500 min). Verify single-piece orderable PN at Digi-Key.',
            'MSOP-10 is 0.5 mm pitch — use a breakout board for breadboard prototyping.',
            'Selected over the ESP32-S3 onboard ADC, which is notoriously nonlinear.',
        ],
    ),
    dict(
        name='ST7735_Display', desc='1.8″ SPI TFT Display Breakout (Adafruit #498)',
        package='10-pin header', mfr='Adafruit Industries', mpn='Adafruit #498',
        pins=[
            ('1',  'GND',      'Ground'),
            ('2',  'VCC',      'Supply (3.3–5 V)'),
            ('3',  '~RESET',   'Reset, active low'),
            ('4',  'D/C',      'Data / Command select'),
            ('5',  '~CARD_CS', 'SD card chip select, active low'),
            ('6',  '~TFT_CS',  'TFT chip select, active low'),
            ('7',  'MOSI',     'SPI data in'),
            ('8',  'SCK',      'SPI clock'),
            ('9',  'MISO',     'SPI data out (SD card only)'),
            ('10', 'LITE',     'Backlight LED anode'),
        ],
        gotchas=[
            'Pin numbers match the Adafruit #498 header order — verify against board before PCB layout.',
            '~CARD_CS and MISO only needed if using the onboard SD card; tie ~CARD_CS high if unused.',
            'LITE can be PWM-controlled for brightness, or tied directly to 3.3 V for always-on backlight.',
            'Shares SPI bus with MCP4921 and W5500 — separate CS lines required for each.',
            'Will be panel-mounted externally with a laser-cut acrylic bezel (SendCutSend).',
        ],
    ),
    dict(
        name='W5500', desc='Hardwired TCP/IP Ethernet Controller Module',
        package='8-pin header', mfr='WIZnet', mpn='W5500',
        pins=[
            ('1', '~INT',  'Interrupt, active low, open-drain'),
            ('2', '~CS',   'SPI chip select, active low'),
            ('3', 'SCK',   'SPI clock'),
            ('4', 'MOSI',  'SPI data in'),
            ('5', 'MISO',  'SPI data out'),
            ('6', '~RST',  'Reset, active low'),
            ('7', '3V3',   'Positive supply (3.3 V)'),
            ('8', 'GND',   'Ground'),
        ],
        gotchas=[
            'Currently backordered — all other subsystems can be developed and tested without it.',
            'Pin order varies by module vendor (Adafruit, WIZnet EVB, clones) — verify when module arrives.',
            '~INT is open-drain — pull-up resistor required to 3.3 V.',
            '~RST should be asserted briefly on power-up; drive from MCU GPIO or an RC reset circuit.',
            'Must be enclosed inside the RFI shielded box alongside the Metro ESP32-S3.',
        ],
    ),
    dict(
        name='6N137', desc='High-Speed Optoisolator (10 MBd, open-collector)',
        package='DIP-8', mfr='Lite-On', mpn='6N137',
        pins=[
            ('1', 'A',   'LED anode'),
            ('2', 'K',   'LED cathode'),
            ('3', 'NC',  '—'),
            ('4', 'GND', 'Output-side ground'),
            ('5', 'VO',  'Output, open-collector'),
            ('6', 'VE',  'Enable, active high'),
            ('7', 'VCC', 'Output-side supply'),
            ('8', 'NC',  '—'),
        ],
        gotchas=[
            '⚠  VE (pin 6, Enable) MUST be tied to VCC — leaving it floating causes erratic or no output.',
            'VO is open-collector — external pull-up resistor required (typ. 470 Ω to VCC).',
            'Two isolated power domains: LED side (pins 1–2) and logic side (pins 4, 7). Keep grounds separate.',
            'LED series resistor required on input: 270 Ω for ~10 mA at 5 V, 150 Ω at 3.3 V.',
            'One 6N137 per paddle input — use two devices for dit and dah isolation.',
        ],
    ),
    dict(
        name='Encoder_5734', desc='60 mm Rugged Rotary Encoder, 100 PPR (Adafruit #5734)',
        package='Panel-mount, screw terminals', mfr='Adafruit Industries', mpn='Adafruit #5734',
        pins=[
            ('1', 'A', 'Quadrature output A'),
            ('2', 'B', 'Quadrature output B'),
            ('3', 'C', 'Common (ground reference)'),
        ],
        gotchas=[
            'C (common) is the ground reference — connect to MCU ground.',
            'A and B need pull-up resistors (10 kΩ) or enable MCU internal pull-ups in firmware.',
            '100 PPR = 400 counts/revolution with quadrature (×4) decoding in software.',
            'If rotation direction is reversed, swap A and B in firmware — no hardware change needed.',
            '⚠  Poor manufacturer documentation — verify screw terminal labeling with ohmmeter before wiring.',
            'Footprint is a placeholder 3-pin header; replace with screw-terminal connector for PCB.',
        ],
    ),
    dict(
        name='Metro_ESP32S3', desc='Adafruit Metro ESP32-S3 Module (Adafruit #5500)',
        package='Module, dual headers', mfr='Adafruit Industries', mpn='Adafruit #5500',
        pins=[
            ('RESET',  '~{RESET}', 'Reset, active low'),
            ('3V3_L',  '3V3',      '3.3 V output (left header)'),
            ('AREF',   'AREF',     'Analog reference'),
            ('GND_L',  'GND',      'Ground (left header)'),
            ('D0',     'D0/RX',    'GPIO / UART0 RX'),
            ('D1',     'D1/TX',    'GPIO / UART0 TX'),
            ('D2',     'D2',       'GPIO'),
            ('D3',     'D3',       'GPIO'),
            ('D4',     'D4',       'GPIO'),
            ('D5',     'D5',       'GPIO'),
            ('D6',     'D6',       'GPIO'),
            ('D7',     'D7',       'GPIO'),
            ('D8',     'D8',       'GPIO'),
            ('D9',     'D9',       'GPIO'),
            ('D10',    'D10/SS',   'GPIO / SPI SS'),
            ('D11',    'D11/MOSI', 'GPIO / SPI MOSI'),
            ('D12',    'D12/MISO', 'GPIO / SPI MISO'),
            ('D13',    'D13/SCK',  'GPIO / SPI SCK / LED'),
            ('VIN',    'VIN',      '5 V power input'),
            ('GND_R1', 'GND',      'Ground (right header)'),
            ('GND_R2', 'GND',      'Ground (right header)'),
            ('5V',     '5V',       '5 V output (USB-powered)'),
            ('3V3_R',  '3V3',      '3.3 V output (right header)'),
            ('A0',     'A0',       'Analog / GPIO'),
            ('A1',     'A1',       'Analog / GPIO'),
            ('A2',     'A2',       'Analog / GPIO'),
            ('A3',     'A3',       'Analog / GPIO'),
            ('A4',     'A4/SDA',   'Analog / GPIO / I²C SDA / STEMMA QT'),
            ('A5',     'A5/SCL',   'Analog / GPIO / I²C SCL / STEMMA QT'),
            ('SCK_H',  'SCK',      'SPI breakout header SCK'),
            ('MOSI_H', 'MOSI',     'SPI breakout header MOSI'),
            ('MISO_H', 'MISO',     'SPI breakout header MISO'),
            ('TX1',    'TX1',      'UART1 TX'),
            ('RX1',    'RX1',      'UART1 RX'),
        ],
        gotchas=[
            '⚠  Verify pin order against Adafruit pinout diagram before wiring — ESP32-S3 GPIO mapping is board-specific.',
            'D11/MOSI, D12/MISO, D13/SCK and the right-side SPI header pins are the same physical signals.',
            'A4/SDA and A5/SCL are also the STEMMA QT connector signals — ADS1115 connects here via STEMMA QT cable.',
            'WiFi/BT must remain disabled in firmware for RFI control; entire board must be enclosed in shielded box.',
            '5V output (right header) is only present when powered via USB-C; use VIN for external 5 V supply input.',
        ],
    ),
]

# ── renderer state ─────────────────────────────────────────────────────────────
_pages   = []
_ax      = None
_y       = 0.0
_pgnum   = 0

ROW_H  = 0.162
HDR_H  = 0.180
GOT_H  = 0.178
COMP_H = 0.270
INFO_H = 0.195
GAP    = 0.075
SEP    = 0.200

WARN_RED  = '#cc0000'
BLUE      = '#1a3a5c'
LTBLUE    = '#e8f0f8'
GRAY      = '#555555'
LGRAY     = '#888888'
RULE      = '#cccccc'

def _new_page(title_page=False):
    global _ax, _y, _pgnum
    _pgnum += 1
    fig, ax = plt.subplots(figsize=(PW, PH))
    ax.set_xlim(0, PW)
    ax.set_ylim(0, PH)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    _pages.append(fig)
    _ax = ax
    _y  = TM
    if not title_page:
        ax.text(PW / 2, PH - 0.22,
                'xmitter KiCad Symbol Library  —  Pinouts & Design Gotchas',
                ha='center', va='top', fontsize=7.5, color=LGRAY)
        ax.plot([LM, RM], [PH - 0.34, PH - 0.34], '-', color=RULE, lw=0.5)
        _y = TM - 0.10

def _need(h):
    global _y
    if _y - h < BM + 0.15:
        _new_page()

def _T(x, s, size=8, weight='normal', color='k', style='normal', ha='left'):
    _ax.text(x, _y, s, va='top', fontsize=size, fontweight=weight,
             color=color, style=style, ha=ha, clip_on=False)

def _skip(h):
    global _y
    _y -= h

def _hline(c=RULE, lw=0.5, x0=None, x1=None):
    _ax.plot([x0 or LM, x1 or RM], [_y, _y], '-', color=c, lw=lw)

# ── title page ─────────────────────────────────────────────────────────────────
_new_page(title_page=True)

_ax.add_patch(plt.Rectangle((0, PH - 1.15), PW, 1.15, color=BLUE, zorder=2))
_ax.text(PW / 2, PH - 0.38, '20 m CW Transmitter  —  xmitter',
         ha='center', va='center', fontsize=16, fontweight='bold',
         color='white', zorder=3)
_ax.text(PW / 2, PH - 0.80, 'KiCad Symbol Library Reference',
         ha='center', va='center', fontsize=12, color='#aaccee', zorder=3)

_y = PH - 1.40

_skip(0.32)
for label, val in [
    ('Library file:', 'xmitter_prj/kicad/xmitter.kicad_sym'),
    ('Generated:',    '2026-06-04'),
    ('Symbols:',      f'{len(COMPS)} components defined'),
    ('Project:',      '20 m CW transmitter, solid-state VFO + digital keyer + vacuum-tube PA'),
]:
    _T(LM,        label, size=8, color=GRAY)
    _T(LM + 1.10, val,   size=8, weight='bold')
    _skip(0.22)

_skip(0.25)
_hline(c=BLUE, lw=1.2)
_skip(0.06)

# summary table header
COL = [LM, LM+1.55, LM+3.15, LM+5.05, LM+6.45]
for x, h in zip(COL, ['Symbol', 'Description', 'Package', 'Manufacturer', 'MPN']):
    _T(x, h, size=8, weight='bold', color=BLUE)
_skip(HDR_H)
_hline(c=BLUE, lw=0.7)
_skip(0.04)

for i, c in enumerate(COMPS):
    bg = LTBLUE if i % 2 == 0 else 'white'
    _ax.add_patch(plt.Rectangle((LM, _y - ROW_H + 0.01),
                                RM - LM, ROW_H - 0.01, color=bg, zorder=0))
    desc = c['desc'][:30] + '…' if len(c['desc']) > 31 else c['desc']
    for x, v in zip(COL, [c['name'], desc, c['package'], c['mfr'], c['mpn']]):
        _T(x, v, size=7.5)
    _skip(ROW_H)

_skip(0.30)
_hline(c=RULE, lw=0.4)
_skip(0.12)
_T(LM,
   'Note: Symbols are hand-created from datasheet pinouts. '
   'Verify footprint assignments before PCB layout.',
   size=7, color=GRAY, style='italic')

# ── content pages ──────────────────────────────────────────────────────────────
_new_page()

WRAP_W = 106   # chars per gotcha line

for comp in COMPS:
    pins   = comp['pins']
    ncols  = 2 if len(pins) > 6 else 1
    nrows  = (len(pins) + ncols - 1) // ncols
    BW     = (RM - LM) / ncols

    wrapped = []
    for g in comp['gotchas']:
        wrapped.append(textwrap.wrap(g, WRAP_W))

    total_got_lines = sum(len(wg) for wg in wrapped)

    h_est = (COMP_H + INFO_H + GAP
             + HDR_H + nrows * ROW_H + GAP
             + GOT_H + total_got_lines * GOT_H
             + SEP + 0.10)
    _need(h_est)

    # component name bar
    bar_h = COMP_H - 0.04
    _ax.add_patch(plt.Rectangle((LM, _y - bar_h), RM - LM, bar_h,
                                color=LTBLUE, zorder=1))
    _ax.plot([LM, LM], [_y, _y - bar_h], '-', color=BLUE, lw=3.5, zorder=2)
    _T(LM + 0.14, comp['name'], size=11, weight='bold', color=BLUE)
    _T(LM + 1.40, '— ' + comp['desc'], size=9, color='#333')
    _skip(COMP_H)

    # package / mfr / mpn
    _T(LM, (f"Package: {comp['package']}    "
            f"Manufacturer: {comp['mfr']}    "
            f"MPN: {comp['mpn']}"),
       size=7.5, color=GRAY)
    _skip(INFO_H)
    _skip(GAP)

    # pin table header
    # offsets within each block
    O_NUM  = 0.22
    O_NAME = 0.62
    O_FUNC = 1.55 if ncols == 2 else 1.85

    for bc in range(ncols):
        bx = LM + bc * BW
        _T(bx + O_NUM,  '#',        size=7, weight='bold', color='#444')
        _T(bx + O_NAME, 'Name',     size=7, weight='bold', color='#444')
        _T(bx + O_FUNC, 'Function', size=7, weight='bold', color='#444')
    _skip(HDR_H)
    _hline(c='#aaaaaa', lw=0.4)

    for ri in range(nrows):
        _skip(0.02)
        for ci in range(ncols):
            pi = ri + ci * nrows
            if pi >= len(pins):
                continue
            bx = LM + ci * BW
            bg = '#f5f5f5' if ri % 2 == 0 else 'white'
            _ax.add_patch(plt.Rectangle((bx + 0.01, _y - ROW_H + 0.02),
                                        BW - 0.08, ROW_H - 0.01,
                                        color=bg, zorder=0))
            pnum, pname, pfunc = pins[pi]
            # truncate function text for 2-col layout
            if ncols == 2 and len(pfunc) > 28:
                pfunc = pfunc[:26] + '…'
            _T(bx + O_NUM,  pnum,  size=7,   color='#333')
            _T(bx + O_NAME, pname, size=7,   weight='bold')
            _T(bx + O_FUNC, pfunc, size=6.8, color='#444')
        _skip(ROW_H)

    _skip(GAP)

    # gotchas
    _T(LM, 'Design notes & gotchas:', size=7.5, weight='bold', color='#8B1A1A')
    _skip(GOT_H)

    for wg in wrapped:
        is_warn = wg[0].startswith('⚠') or 'MUST' in wg[0]
        col    = WARN_RED if is_warn else '#1a1a1a'
        bullet = '⚠  ' if is_warn else '•  '
        for li, line in enumerate(wg):
            prefix = bullet if li == 0 else '      '
            _T(LM + 0.12, prefix + line, size=7.5, color=col)
            _skip(GOT_H)

    _skip(SEP)

# ── page footers ───────────────────────────────────────────────────────────────
total = len(_pages)
for i, fig in enumerate(_pages):
    ax = fig.axes[0]
    ax.plot([LM, RM], [0.42, 0.42], '-', color='#dddddd', lw=0.4)
    ax.text(PW / 2, 0.30, f'Page {i + 1} of {total}',
            ha='center', va='top', fontsize=7, color=LGRAY)
    ax.text(LM, 0.30, 'xmitter KiCad Symbol Library',
            ha='left', va='top', fontsize=7, color=LGRAY)
    ax.text(RM, 0.30, '2026-06-04',
            ha='right', va='top', fontsize=7, color=LGRAY)

# ── save ───────────────────────────────────────────────────────────────────────
with PdfPages(str(OUT)) as pdf:
    for fig in _pages:
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

print(f'Saved {total} pages to {OUT}')

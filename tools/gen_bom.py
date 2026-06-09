"""Generate xmitter BOM as a formatted Excel spreadsheet."""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
import os

OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'Documentation', 'BOM.xlsx')

# Row fill colors keyed by part type
FILL = {
    'Resistor':      'FFF2CC',
    'Capacitor':     'DDEEFF',
    'Inductor':      'E2EFDA',
    'Transformer':   'C6EFCE',
    'Semiconductor': 'FCE4D6',
    'Tube':          'EAD1FF',
    'IC':            'FFD9B3',
}

HEADERS = [
    'Part Type', 'Reference', 'Value', 'Notes',
    'Sheet(s)', 'Qty', 'Datasheet', 'Supplier', 'Obtained',
]

COL_WIDTHS = [14, 16, 14, 60, 14, 6, 28, 14, 10]

# (Part Type, Reference, Value, Notes, Sheet(s), Qty, Datasheet, Supplier, Obtained)
BOM = [
    # ── VFO ──────────────────────────────────────────────────────────────────
    # RS is NOT a discrete part — it models the Si5351A output impedance (~50Ω at 8mA drive)
    ('Resistor',     'RP1, RP3',    '150Ω',
     'Metal film 1%; pi-attenuator shunt (2 identical)',
     'VFO', 2, '', '', ''),
    ('Resistor',     'RP2',         '39Ω',
     'Metal film 1%; pi-attenuator series arm',
     'VFO', 1, '', '', ''),
    ('Resistor',     'RGL',         '1MΩ',
     'J310 gate bias',
     'VFO', 1, '', '', ''),
    ('Resistor',     'RS1',         '270Ω',
     'J310 source bias',
     'VFO', 1, '', '', ''),
    ('Capacitor',    'CF1, CF5',    '200pF',
     'NP0/C0G 1–2%; 5-pole LPF end caps (2 identical)',
     'VFO', 2, '', '', ''),
    ('Capacitor',    'CF3',         '360pF',
     'NP0/C0G 1–2%; 5-pole LPF centre cap',
     'VFO', 1, '', '', ''),
    ('Capacitor',    'CC1',         '10nF',
     'J310 gate coupling cap',
     'VFO', 1, '', '', ''),
    ('Inductor',     'LF2, LF4',    '624nH',
     'T-68-6 (Mix 6, yellow); ~12T #26AWG; 5-pole LPF series arms',
     'VFO', 2, '', 'Amidon / Kits&Parts', ''),
    ('Resistor',     'RT',          '50Ω',
     'Metal film 1%; 5-pole LPF load termination — IS a discrete resistor (not Si5351A impedance)',
     'VFO', 1, '', '', ''),
    ('Semiconductor','T1',          'J310',
     'N-ch JFET; source follower output stage; TO-92',
     'VFO', 1, '', '', ''),

    # ── BUFFER / KEYER ───────────────────────────────────────────────────────
    ('IC',           'U1',          'MC1496 / LM1496',
     'Gilbert cell balanced modulator used as VCA; DIP-14; key-up null eliminates RF leakage',
     'Buffer/Keyer', 1, '', '', ''),
    ('IC',           'A1',          'TL071',
     'Error amp / integrator; DIP-8. Library has TL072 — verify pinout if substituting (pin-compatible)',
     'Buffer/Keyer', 1, '', '', ''),
    ('IC',           'DAC',         'MCP4921',
     '12-bit SPI DAC; envelope control to MC1496 modulating port; dedicated SPI bus (NOT shared with I2C)',
     'Buffer/Keyer', 1, '', '', ''),
    ('Transformer',  'T1',          'FT37-43',
     'Broadband push-pull interstage; 10+10T primary bifilar, 10+10T secondary bifilar; #28AWG; Fair-Rite Mix 43',
     'Buffer/Keyer', 1, '', '', ''),
    ('Inductor',     'L_RFC',       '100µH',
     'Molded RFC; +12V to T1 primary CT; push-pull RF currents cancel — only DC flows; standard SRF OK',
     'Buffer/Keyer', 1, '', '', ''),
    ('Semiconductor','D1',          '1N5711',
     'Schottky; RF detector — samples one grid for AGC leveling loop',
     'Buffer/Keyer', 1, '', '', ''),
    ('Semiconductor','DZ1',         '1N4738A',
     '8.2V zener; generates −8.2V rail for MC1496 VEE and TL071 V− from grid bias rail',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_DROP',      '15kΩ 1W',
     'Dropping resistor from grid bias rail (−60 to −80V) to 1N4738A; ≤300mW at −80V',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_GL',        '22kΩ',
     'T1 secondary CT grid-leak (or return to fixed −bias supply for Class C)',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'RGS_A, RGS_B','100Ω',
     'Grid stopper resistors — one per 12HG7 grid',
     'Buffer/Keyer', 2, '', '', ''),
    ('Resistor',     'R_SCALE1',    '100kΩ',
     'AGC divider upper leg: TL071 output → MC1496 signal port',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_SCALE2',    '5.1kΩ',
     'AGC divider lower leg (4.85% ratio); sets MC1496 control range',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_SIG_P',     '10kΩ',
     'MC1496 signal port + reference to GND',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_INJ1',      '330kΩ',
     'Digital carrier null injection: DAC_NULL_P → MC1496 pin 1 (SIG_P); replaces mechanical null pot',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_INJ2',      '330kΩ',
     'Digital carrier null injection: DAC_NULL_N → MC1496 pin 4 (SIG_N); replaces mechanical null pot',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_BIAS',      '6.8kΩ',
     'MC1496 bias pin (pin 5) to GND; sets I5≈1mA per AN531/D (internal 500Ω + R_BIAS from pin 5 to GND)',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_RE',        '1kΩ',
     'MC1496 emitter degeneration between pins 2 and 3 (NOT to VEE); sets gain Av=RL/RE; may change to 500Ω at bring-up',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_INT',       '100kΩ',
     'TL071 inverting input resistor',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_FB',        '470kΩ',
     'TL071 anti-windup / DC gain feedback',
     'Buffer/Keyer', 1, '', '', ''),
    ('Resistor',     'R_DET',       '330kΩ',
     'Detector diode trickle bias from +12V; keeps 1N5711 linear at low signal levels',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_INT',       '1µF film',
     'TL071 integrator cap; film type for low leakage',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_DET',       '10nF film',
     'Detector smoothing cap',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_DET_IN',    '1000pF NP0',
     'Detector coupling from grid to 1N5711',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_GL',        '10nF NP0',
     'RF bypass across T1CTS grid-leak resistor',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_Z1',        '10µF electrolytic',
     '−8.2V rail bulk bypass',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_Z2',        '100nF ceramic',
     '−8.2V rail HF bypass',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_MC_CARR',   '100nF ceramic',
     'MC1496 carrier port − bypass (pin 8 to GND); keep lead short',
     'Buffer/Keyer', 1, '', '', ''),
    ('Capacitor',    'C_MC_VEE',    '100nF ceramic',
     'MC1496 VEE bypass (pin 7)',
     'Buffer/Keyer', 1, '', '', ''),

    # ── DRIVER ───────────────────────────────────────────────────────────────
    ('Tube',         '2× 12HG7',    '12HG7',
     'Push-pull driver; 150V B+; push-pull pair',
     'Driver', 2, '12HG7.pdf', '', ''),
    ('Resistor',     'R2, R6',      '1kΩ',
     'Screen resistors',
     'Driver', 2, '', '', ''),
    ('Resistor',     'R4, R7',      '47kΩ',
     'Grid bias resistors',
     'Driver', 2, '', '', ''),
    ('Resistor',     'R1, R3, R8, R9', '100Ω',
     '4 identical resistors',
     'Driver', 4, '', '', ''),
    ('Capacitor',    'C2, C4, C5',  '10nF',
     '2× 10nF in parallel per position (shown as 0.01001µF in schematic); 3 positions = 6 caps total',
     'Driver', 6, '', '', ''),
    ('Capacitor',    'C6, C7',      '10nF',
     'Bypass caps',
     'Driver', 2, '', '', ''),
    ('Inductor',     'L1, L3',      '1µH',
     'Plate RFC; commercial molded choke; >50mA',
     'Driver', 2, '', '', ''),

    # ── PA ───────────────────────────────────────────────────────────────────
    ('Tube',         '2× 6146B',    '6146B',
     '600V B+, 200V screen, −70V grid; push-pull pair',
     'PA', 2, '6146b_big.pdf', '', ''),
    ('Resistor',     'R1, R5',      '10Ω',
     'Cathode resistors; check power rating at operating current',
     'PA', 2, '', '', ''),
    ('Resistor',     'R3, R7',      '1kΩ',
     'Screen resistors',
     'PA', 2, '', '', ''),
    ('Resistor',     'R4, R8',      '22kΩ',
     'Grid bias resistors',
     'PA', 2, '', '', ''),
    ('Resistor',     'R2, R6',      '220Ω',
     '',
     'PA', 2, '', '', ''),
    ('Resistor',     'R14, R15',    '47Ω',
     '',
     'PA', 2, '', '', ''),
    ('Capacitor',    'C6, C7',      '0.24pF',
     'Cak compensation; verify availability — very low value',
     'PA', 2, '', '', ''),
    ('Capacitor',    'C8, C10',     '10nF',
     'Bypass; must be rated for HV (≥1kV)',
     'PA', 2, '', '', ''),
    ('Capacitor',    'C9, C11',     '100pF',
     'Bypass; must be rated for HV (≥1kV)',
     'PA', 2, '', '', ''),
    ('Capacitor',    'C12, C13',    '33pF',
     'Plate tank; ganged variable cap 8–100pF; user has these',
     'PA', 2, '', '', ''),
    ('Inductor',     'L4, L5',      '1.71µH ea',
     'T-106-6 (Mix 6); center-tapped tank halves wound on ONE core with L6; ~19T each half; see L6 row',
     'PA', 1, '', 'Amidon / Kits&Parts', ''),
    ('Inductor',     'L6',          '0.27µH',
     'Tank link/output winding; same T-106-6 core as L4/L5; ~8T',
     'PA', 1, '', 'Amidon / Kits&Parts', ''),
    ('Inductor',     'L10, L11',    '1µH',
     'Screen/supply decoupling choke; commercial molded; HV-rated',
     'PA', 2, '', '', ''),

    # ── BALUN ────────────────────────────────────────────────────────────────
    ('Transformer',  'LP / LS',     '14µH / 2.33µH',
     'FT-114-61 ferrite (AL=75); 15T primary : 6T secondary; 300Ω balanced → 50Ω unbal; 6.25:1 Z ratio; good through 10m',
     'Balun', 1, '', 'Amidon / Kits&Parts', ''),

    # ── OUTPUT LPF ───────────────────────────────────────────────────────────
    ('Capacitor',    'C1, C3',      '300pF',
     'NP0/C0G 1–2%; 5-pole 0.5dB Chebyshev LPF fc=18MHz; end caps',
     'LPF (50Ω)', 2, '', '', ''),
    ('Capacitor',    'C2',          '450pF',
     'NP0/C0G 1–2%; 5-pole Chebyshev LPF centre cap',
     'LPF (50Ω)', 1, '', '', ''),
    ('Inductor',     'L1, L2',      '540nH',
     'T-68-6 (Mix 6, yellow); ~11T #26AWG; 5-pole Chebyshev LPF series arms',
     'LPF (50Ω)', 2, '', 'Amidon / Kits&Parts', ''),
]


def thin_border():
    s = Side(style='thin', color='BBBBBB')
    return Border(left=s, right=s, top=s, bottom=s)


def build():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'BOM'

    # Header row
    header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill('solid', fgColor='2F5496')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for col, (hdr, width) in enumerate(zip(HEADERS, COL_WIDTHS), start=1):
        cell = ws.cell(row=1, column=col, value=hdr)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border()
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.row_dimensions[1].height = 20

    # Data rows
    data_align_wrap = Alignment(vertical='top', wrap_text=True)
    data_align_center = Alignment(horizontal='center', vertical='top')

    for row_idx, row in enumerate(BOM, start=2):
        part_type = row[0]
        color = FILL.get(part_type, 'FFFFFF')
        fill = PatternFill('solid', fgColor=color)

        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill = fill
            cell.border = thin_border()
            cell.font = Font(name='Calibri', size=10)
            if col_idx in (5, 6, 9):  # Sheet, Qty, Obtained — centre
                cell.alignment = data_align_center
            else:
                cell.alignment = data_align_wrap

        ws.row_dimensions[row_idx].height = 30

    # Auto-filter
    ws.auto_filter.ref = f'A1:{get_column_letter(len(HEADERS))}1'

    # Freeze header
    ws.freeze_panes = 'A2'

    # Data validation for Obtained column (col 9)
    dv = DataValidation(
        type='list',
        formula1='"Yes,Ordered,No"',
        allow_blank=True,
        showDropDown=False,
    )
    ws.add_data_validation(dv)
    dv.sqref = f'I2:I{len(BOM) + 1}'

    wb.save(OUT_PATH)
    print(f'Saved: {os.path.abspath(OUT_PATH)}')


if __name__ == '__main__':
    build()

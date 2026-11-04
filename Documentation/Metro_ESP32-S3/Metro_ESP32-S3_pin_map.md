# Adafruit Metro ESP32-S3 — pin map reference

Source: `Metro_ESP32-S3_Pinout.pdf` (Adafruit PrettyPins, from
`github.com/adafruit/Adafruit-Metro-ESP32-S3-PCB`).  Mechanical
footprint is Arduino Uno R3 shield standard — use KiCad stock
footprint `Module:Arduino_UNO_R3` (32 holes, 2.54 mm pitch, 48.26 mm
row-to-row, the classic 0.063" offset between D7 and D8, 1.0 mm drill
for 0.1" square male pin headers).

## POWER header (bottom-left, 8 pins)

- Pin 1  NC      — not connected
- Pin 2  IOREF   — tied to 3.3 V on Metro ESP32-S3
- Pin 3  RESET   — active-low reset
- Pin 4  3V3     — 3.3 V regulated out (400 mA max)
- Pin 5  5V (VHIGH) — 5 V when USB powered
- Pin 6  GND
- Pin 7  GND
- Pin 8  VIN     — higher of USB or DC jack

## ANALOG IN header (bottom-right, 6 pins)

- Pin 9   A0 — GPIO14 (ADC2_CH3, RTC, FSPIWP, Touch T14)
- Pin 10  A1 — GPIO15 (ADC2_CH4, RTC, U0RTS, XTAL_32K_P)
- Pin 11  A2 — GPIO16 (ADC2_CH5, RTC, U0CTS, XTAL_32K_N)
- Pin 12  A3 — GPIO17 (ADC2_CH6, RTC, U1TXD)
- Pin 13  A4 — GPIO18 (ADC2_CH7, RTC, U1RXD)
- Pin 14  A5 — GPIO1  (ADC1_CH0, RTC, Touch T1)

## DIGITAL 0-7 header (top-right, 8 pins)

- Pin 15  D0/RX — GPIO41 (CPU, MTDI)
- Pin 16  D1/TX — GPIO40 (CPU, MTDO)
- Pin 17  D2 — GPIO2 (ADC1_CH1, RTC, Touch T2)
- Pin 18  D3 — GPIO3 (ADC1_CH2, RTC, Touch T3) — **strapping pin**
- Pin 19  D4 — GPIO4 (ADC1_CH3, RTC, Touch T4)
- Pin 20  D5 — GPIO5 (ADC1_CH4, RTC, Touch T5)
- Pin 21  D6 — GPIO6 (ADC1_CH5, RTC, Touch T6)
- Pin 22  D7 — GPIO7 (ADC1_CH6, RTC, Touch T7)

## DIGITAL 8-13+ header (top-left, 10 pins, offset by 0.063" from D0-D7)

- Pin 23  D8  — GPIO8  (ADC1_CH7, RTC, Touch T8)
- Pin 24  D9  — GPIO9  (ADC1_CH8, RTC, FSPIHD, Touch T9)
- Pin 25  D10 — GPIO10 (ADC1_CH9, RTC, FSPICS0, Touch T10)
- Pin 26  D11 — GPIO11 (ADC2_CH0, RTC, FSPID, Touch T11) — **MOSI on FSPI**
- Pin 27  D12 — GPIO12 (ADC2_CH1, RTC, FSPICLK, Touch T12)
- Pin 28  D13 — GPIO13 (ADC2_CH2, RTC, FSPIQ, Touch T13)
- Pin 29  GND
- Pin 30  AREF — tied to 3.3 V on Metro
- Pin 31  SDA — GPIO47 (CPU, CLK_P_DIFF)
- Pin 32  SCL — GPIO48 (CPU, CLK_N_DIFF)

## Not brought to shield headers (but worth knowing)

Dedicated SPI header (ICSP-style, 6-pin):
- SCK  = GPIO39 (CPU, MTCK)
- MOSI = GPIO42 (CPU, MTMS) — same as D11/GPIO11 in pin naming
- MISO = GPIO21 (RTC)

On-board peripherals:
- SD_CS     = GPIO45 (CPU)
- NEOPIXEL  = GPIO46 (CPU)
- DEBUG_RX  = GPIO44 (U0RXD)
- DEBUG_TX  = GPIO43 (U0TXD)

## Firmware-side gotchas

- **GPIO3 (D3)** is a strapping pin on ESP32-S3.  Boot-time voltage
  selects JTAG signal source — keep boot behavior in mind when
  choosing what to put on D3.
- **GPIO45 / GPIO46 / GPIO47 / GPIO48** are CPU-domain only (not
  available as RTC GPIOs) — they can't wake the chip from deep sleep.
- **ADC2 channels** are shared with Wi-Fi; readings become unreliable
  while Wi-Fi is active.  Any pin that needs reliable ADC during Wi-Fi
  operation should land on an ADC1 channel (A5 and D2–D10 on this board).

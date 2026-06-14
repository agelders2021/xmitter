// =============================================================================
//  pin_map.h
//
//  Single source of truth for every GPIO and peripheral assignment on the
//  Adafruit Metro ESP32-S3 (Adafruit P/N 5500, rev B).  Each Arduino-header
//  silkscreen label is mapped to its underlying ESP32-S3 GPIO per the
//  Adafruit PrettyPins diagram in Documentation/adafruit-metro-esp32-s3.pdf
//  page 13.
//
//  Pins flagged TODO require the matching hardware on the final schematic
//  before flashing.  Edit here, rebuild, and a pin swap rolls everywhere.
// =============================================================================
#pragma once

#include "driver/gpio.h"
#include "driver/spi_common.h"
#include "driver/i2c_master.h"

namespace pins {

// ===========================================================================
//  Arduino-header → ESP32-S3 GPIO map (Metro ESP32-S3 rev B)
//
//  Digital  : D2..D13  -> GPIO 2..13
//             D0 (RX)  -> GPIO41
//             D1 (TX)  -> GPIO40
//  Analog   : A0..A4   -> GPIO 14..18
//             A5       -> GPIO 1
//  I2C      : SDA      -> GPIO47  (10 kΩ pullup on board)
//             SCL      -> GPIO48  (10 kΩ pullup on board)
//             shared with the STEMMA QT JST-SH connector and the on-board
//             MAX17048 battery monitor (addr 0x36 — avoid that address).
//  MicroSD  : MISO 21, MOSI 42, SCK 39, CS 45 (HS/QSPI peripheral)
//  Debug UART: RX0=GPIO44, TX0=GPIO43 (header pins, NOT the USB console)
//  NeoPixel : GPIO46  (on-board, not on a header)
//  L LED    : on-board, not broken out to a header
// ===========================================================================

// ---- I2C bus (monitoring + control) ---------------------------------------
//  Shared between: Si5351 (VFO, 0x60), MCP4728 (per-tube grid bias, alt addr),
//  ADS1115 (cathode ADC, 0x48), and the Metro's on-board MAX17048 fuel gauge.
constexpr i2c_port_num_t I2C_PORT = I2C_NUM_0;
constexpr gpio_num_t     I2C_SDA  = GPIO_NUM_47;   // Arduino "SDA" header pin
constexpr gpio_num_t     I2C_SCL  = GPIO_NUM_48;   // Arduino "SCL" header pin
constexpr uint32_t       I2C_HZ   = 400000;        // 400 kHz fast mode

// ---- SPI bus, dedicated to the envelope DAC --------------------------------
//  MCP4921 12-bit DAC, MOSI-only, manual CS (no hardware CS — playout task
//  owns the line timing).  Bus is FSPI on the S3.  MUST NOT share the
//  monitoring I2C bus (see Documentation/cw_envelope_keyer.md).
constexpr spi_host_device_t DAC_SPI_HOST = SPI2_HOST;     // = FSPI
constexpr gpio_num_t        ENV_DAC_SCK  = GPIO_NUM_12;   // Arduino D12
constexpr gpio_num_t        ENV_DAC_MOSI = GPIO_NUM_11;   // Arduino D11
constexpr gpio_num_t        ENV_DAC_CS   = GPIO_NUM_13;   // Arduino D13
constexpr int               ENV_DAC_HZ   = 20000000;      // MCP4921 max ~20 MHz

// ---------------------------------------------------------------------------
//  Peripheral I2C addresses
// ---------------------------------------------------------------------------
constexpr uint8_t I2C_ADDR_SI5351   = 0x60;   // Adafruit Si5351A breakout
constexpr uint8_t I2C_ADDR_ADS1115  = 0x48;   // ADDR pin tied to GND
constexpr uint8_t I2C_ADDR_MAX17048 = 0x36;   // on-board Metro battery monitor

// MCP4728 ships at 0x60 too — same as Si5351.  The grid-bias board must use
// a factory-programmed alternate address (e.g. 0x61) or sit on a second I2C
// peripheral.  Placeholder until resolved:
constexpr uint8_t I2C_ADDR_BIAS_DAC = 0x61;   // TODO confirm after MCP4728 program

// ---------------------------------------------------------------------------
//  Front-panel rotary encoders
//
//  Three encoders total, all wired so the COMMON terminal is GND and A/B
//  pull to GND when active.  The S3's internal pull-ups satisfy the "high"
//  state — no external resistors required for the mechanical PEC11s.
//
//  ENC_FREQ — optical, MBL-600-100P-5L (100 PPR → 400 quadrature counts
//  per revolution).  Per the spec sheet:
//    Vcc:    +5 V ± 5 % (the "5" in the model code)
//    Output: AM26LS31 differential line driver (the "L"), 6 wires:
//            pin1=A, pin2=B, pin3=0V, pin4=Vcc, pin5=Ā, pin6=B̄
//    High level ≥ 85 % × Vcc (≥ 4.25 V), low ≤ 0.3 V.
//  The output is NOT 3.3-V CMOS, so ENC_FREQ_A / ENC_FREQ_B must be driven
//  through a 5→3.3 V interface — RS-422 receiver (SN65HVD3082, DS26C32,
//  MAX3094) on the A/Ā and B/B̄ pairs is the clean choice; a 74LVC2G17
//  level shifter on just A & B works for short on-board wiring.  Do NOT
//  connect the encoder outputs straight to the GPIOs — the S3 is not
//  5 V tolerant.
//
//  ENC_STEP — mechanical Bourns PEC11-4 (24 detents / 24 pulses, push
//  momentary switch).  Selects the per-tick frequency step.
//
//  ENC_FUNC — mechanical Bourns PEC11-4 (same), reserved for future
//  function selection (mode, audio level, key memory slot, …).
// ---------------------------------------------------------------------------
constexpr gpio_num_t ENC_FREQ_A    = GPIO_NUM_2;    // Arduino D2
constexpr gpio_num_t ENC_FREQ_B    = GPIO_NUM_3;    // Arduino D3
constexpr gpio_num_t ENC_FREQ_SW   = GPIO_NUM_NC;   // optical encoder has no switch

constexpr gpio_num_t ENC_STEP_A    = GPIO_NUM_5;    // Arduino D5
constexpr gpio_num_t ENC_STEP_B    = GPIO_NUM_6;    // Arduino D6
constexpr gpio_num_t ENC_STEP_SW   = GPIO_NUM_7;    // Arduino D7

constexpr gpio_num_t ENC_FUNC_A    = GPIO_NUM_8;    // Arduino D8
constexpr gpio_num_t ENC_FUNC_B    = GPIO_NUM_9;    // Arduino D9
constexpr gpio_num_t ENC_FUNC_SW   = GPIO_NUM_10;   // Arduino D10

// ---------------------------------------------------------------------------
//  Fault / fail-safe — hardware screen-voltage gate
// ---------------------------------------------------------------------------
//  Active-low gate output drops the high-side MOSFET feeding the screen
//  supply, killing the tubes within ~100 µs.  Also fed from the LM393
//  comparator latch in hardware; the GPIO is the firmware-side path.
constexpr gpio_num_t FAULT_GATE_OUT     = GPIO_NUM_14;   // Arduino A0 — TODO confirm
constexpr gpio_num_t FAULT_LATCH_RESET  = GPIO_NUM_15;   // Arduino A1 — TODO (also XTAL_32K_P)
constexpr gpio_num_t FAULT_LATCH_STATUS = GPIO_NUM_16;   // Arduino A2 — TODO (also XTAL_32K_N)

// ---------------------------------------------------------------------------
//  Power-supply sequencing (supply not yet designed)
// ---------------------------------------------------------------------------
constexpr gpio_num_t PSU_MAIN_EN    = GPIO_NUM_17;   // Arduino A3 — TODO
constexpr gpio_num_t PSU_READY_IN   = GPIO_NUM_40;   // Arduino TX/D1 — TODO

// ---------------------------------------------------------------------------
//  Mains interlock — heartbeat to a 74HC4538 retriggerable monostable that
//  drives the K_MAIN relay coil.  Firmware MUST pulse this at ≥5 Hz once
//  boot is complete; the monostable's RC time-out (~200 ms) drops the relay
//  if heartbeat stops (firmware hang, crash, panic, brown-out).
//
//  Critical: this pin defaults LOW at hard reset and stays LOW until the
//  application explicitly opts in.  External 10 kΩ pull-down to GND on the
//  PCB makes "no MCU / no firmware" a guaranteed-off state — fail-safe by
//  default, not by code.
// ---------------------------------------------------------------------------
constexpr gpio_num_t MAINS_HEARTBEAT = GPIO_NUM_4;   // Arduino D4 — TODO confirm

// ---------------------------------------------------------------------------
//  WinKey paddle inputs (DIT / DAH closures, momentary key = GND)
// ---------------------------------------------------------------------------
constexpr gpio_num_t PADDLE_DIT     = GPIO_NUM_18;   // Arduino A4 — TODO
constexpr gpio_num_t PADDLE_DAH     = GPIO_NUM_1;    // Arduino A5 — TODO

// ---------------------------------------------------------------------------
//  On-board indicators (no hardware wiring needed)
// ---------------------------------------------------------------------------
constexpr gpio_num_t NEOPIXEL_LED   = GPIO_NUM_46;   // Metro on-board NeoPixel
constexpr gpio_num_t STATUS_LED     = GPIO_NUM_NC;   // L LED not broken out

// ---------------------------------------------------------------------------
//  Spares available on the Arduino headers
// ---------------------------------------------------------------------------
//  D0  = GPIO41  (RX, unused — UART debug runs on GPIO44 instead)
//  Total unused: GPIO 41.  D4 (GPIO4) now reserved for MAINS_HEARTBEAT
//  above.  All other Arduino-header pins are claimed.

// ---------------------------------------------------------------------------
//  RTOS core assignments
// ---------------------------------------------------------------------------
constexpr int CORE_MONITOR = 0;   // PRO_CPU — I2C traffic, encoders, faults
constexpr int CORE_KEYING  = 1;   // APP_CPU — envelope playout, WinKey

}  // namespace pins

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
//
//  Address plan for the Rev A analog control board (confirmed 2026-07-14):
//    0x20  PCF8575 (front panel, on vector board — factory default)
//    0x21  PCF8575 (main board — A0 jumper closed on breakout back)
//    0x36  I2C QT Rotary Encoder (STEP; factory default)
//    0x37  I2C QT Rotary Encoder (FUNC; A0 jumper closed on breakout back)
//    0x48  MAX17048 fuel gauge (on-board on the Metro; do not use)
//    0x60  Si5351A VFO (hardwired — no ADDR jumper accessible)
//    0x67  MCP4728 null DAC (reprogrammed from factory 0x60; see below)
//
//  Slot 0x62 / 0x63 are held in reserve for the two MCP4725 grid-bias DACs
//  that will live on the (not-yet-designed) separate bias board.  0x62 is
//  the MCP4725 factory default; 0x63 is its single-jumper option.  Do not
//  put anything else there.
// ---------------------------------------------------------------------------
constexpr uint8_t I2C_ADDR_SI5351            = 0x60;
constexpr uint8_t I2C_ADDR_MCP4728           = 0x67;  // post-reprogram target
constexpr uint8_t I2C_ADDR_MCP4728_FACTORY   = 0x60;  // out-of-box; must be moved
constexpr uint8_t I2C_ADDR_PCF8575_MAIN      = 0x20;  // A0 open (factory default) -- analog board, relay drives
constexpr uint8_t I2C_ADDR_PCF8575_PANEL     = 0x21;  // A0 jumper closed (pulled high) -- front-panel PCB
constexpr uint8_t I2C_ADDR_MAX17048          = 0x36;  // Metro on-board fuel gauge
constexpr uint8_t I2C_ADDR_ENC_STEP          = 0x37;  // NOTE: default 0x36
                                                      //  collides w/ MAX17048;
                                                      //  jumper STEP to 0x37
                                                      //  when the QT encoder
                                                      //  breakouts get built.
constexpr uint8_t I2C_ADDR_ENC_FUNC          = 0x38;  // FUNC: A1 jumper closed.

// ---------------------------------------------------------------------------
//  Front-panel rotary encoders
//
//  ENC_FREQ — optical MBL-600-100P-5L (100 PPR → 400 quadrature counts per
//  revolution), +5 V AM26LS31 differential line-driver output.  A per-board
//  AM26LS32ACN receiver + 2.2k/10k divider (Interface sheet) drops the
//  differential pair to 3.3 V single-ended before it reaches these GPIOs.
//  Do NOT connect the raw encoder outputs to the S3 — not 5 V tolerant.
//
//  ENC_STEP and ENC_FUNC — mechanical Bourns PEC11-4s that hang off the
//  Adafruit I2C QT Rotary Encoder breakouts (seesaw SAMD09 handles the
//  quadrature decode + button debounce on-board).  They are on the I2C
//  bus at ENC_STEP / ENC_FUNC addresses above — no dedicated GPIOs.
// ---------------------------------------------------------------------------
constexpr gpio_num_t ENC_FREQ_A    = GPIO_NUM_2;    // Arduino D2 (MBL600_A)
constexpr gpio_num_t ENC_FREQ_B    = GPIO_NUM_3;    // Arduino D3 (MBL600_B)
constexpr gpio_num_t ENC_FREQ_SW   = GPIO_NUM_NC;   // optical encoder has no switch

// STEP / FUNC now live on I2C QT breakouts.  These constants are kept as
// GPIO_NUM_NC so encoders.cpp (which still references them) compiles cleanly
// while the polling rewrite is pending.
constexpr gpio_num_t ENC_STEP_A    = GPIO_NUM_NC;
constexpr gpio_num_t ENC_STEP_B    = GPIO_NUM_NC;
constexpr gpio_num_t ENC_STEP_SW   = GPIO_NUM_NC;

constexpr gpio_num_t ENC_FUNC_A    = GPIO_NUM_NC;
constexpr gpio_num_t ENC_FUNC_B    = GPIO_NUM_NC;
constexpr gpio_num_t ENC_FUNC_SW   = GPIO_NUM_NC;

// ---------------------------------------------------------------------------
//  MCP4728 LDAC — needed for the one-time EEPROM address reprogram
//  (Microchip DS22187 §5.4.3).  Firmware normally drives this HIGH; the
//  reprogram sequence pulls it LOW around the write.  See mcp4728.cpp.
// ---------------------------------------------------------------------------
constexpr gpio_num_t MCP4728_LDAC  = GPIO_NUM_7;    // Arduino D7

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
//  Encoder interrupt — open-drain wired-OR from all seesaw I²C QT encoder
//  breakouts (STEP at 0x37, FUNC at 0x38).  Active-low; asserts when any
//  encoder has new count data.  De-asserts after all pending encoder
//  read_delta calls drain their count registers.
//
//  Hardware: R102 = 10 kΩ pull-up to +3.3 V on Rev A board (arduino sheet).
//  J5 = 2-pin 0.1" header (ENC_INT_CABLE) — leave unpopulated until the
//  front-panel INT cable is installed; R102 holds the pin idle-high.
// ---------------------------------------------------------------------------
constexpr gpio_num_t ENC_INT = GPIO_NUM_4;            // Arduino D4

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
//
//  TODO: pin table (bottom of this file) places MAINS_HEARTBEAT on one of
//  A0..A4 (GPIO14..18); assignment unresolved pending schematic trace.
//  GPIO_NUM_NC here until the A-pin assignment is confirmed.
// ---------------------------------------------------------------------------
constexpr gpio_num_t MAINS_HEARTBEAT = GPIO_NUM_NC;   // Arduino A? — TODO confirm

// ---------------------------------------------------------------------------
//  WinKey paddle inputs (DIT / DAH closures, momentary key = GND).
//  Rev A schematic (arduino.kicad_sch) wires PADDLE_A/B directly to D5/D6.
//  (Earlier plan had them on the front-panel PCF8575; that change was
//  reverted before the fab pass so the paddle latency is deterministic.)
// ---------------------------------------------------------------------------
constexpr gpio_num_t PADDLE_DIT     = GPIO_NUM_5;    // Arduino D5 (PADDLE_A)
constexpr gpio_num_t PADDLE_DAH     = GPIO_NUM_6;    // Arduino D6 (PADDLE_B)

// ---------------------------------------------------------------------------
//  On-board indicators (no hardware wiring needed)
// ---------------------------------------------------------------------------
constexpr gpio_num_t NEOPIXEL_LED   = GPIO_NUM_46;   // Metro on-board NeoPixel
constexpr gpio_num_t STATUS_LED     = GPIO_NUM_NC;   // L LED not broken out

// ---------------------------------------------------------------------------
//  Metro-pin usage on the Rev A analog control board (arduino.kicad_sch):
//    D0  = GPIO41  — RX (unused; UART debug runs on GPIO44)
//    D1  = GPIO40  — TX (unused)
//    D2  = GPIO2   — MBL600_A       (VFO tuning encoder, quadrature A)
//    D3  = GPIO3   — MBL600_B       (VFO tuning encoder, quadrature B)
//    D4  = GPIO4   — ENC_INT (reserved for future front-panel INT cable;
//                    J5 header unpopulated on Rev A build)
//    D5  = GPIO5   — PADDLE_A / DIT
//    D6  = GPIO6   — PADDLE_B / DAH
//    D7  = GPIO7   — LDAC_4728      (MCP4728 EEPROM reprogram; see above)
//    D8  = GPIO8   — I_CATHODE_A    (per-tube cathode current, ADC1)
//    D9  = GPIO9   — I_CATHODE_B    (per-tube cathode current, ADC1)
//    D10 = GPIO10  — CS_DAC         (SPI CS for envelope MCP4921)
//    D11 = GPIO11  — MOSI           (envelope DAC MOSI)
//    D12 = GPIO12  — GRID_BLOCK_CRASH (firmware bias-slam trigger)
//    D13 = GPIO13  — SCK            (envelope DAC clock)
//    A0..A4 = GPIO14..18 — TODO (relay drivers, MAINS_HEARTBEAT, PSU
//              sequencing; unresolved on the schematic — need to trace
//              A0/A1/A2/A3/A4 net labels before assuming assignments)
//    A5  = GPIO1   — TR_SENSE       (T/R relay contact confirmation)

// ---------------------------------------------------------------------------
//  RTOS core assignments
// ---------------------------------------------------------------------------
constexpr int CORE_MONITOR = 0;   // PRO_CPU — I2C traffic, encoders, faults
constexpr int CORE_KEYING  = 1;   // APP_CPU — envelope playout, WinKey

}  // namespace pins

// =============================================================================
//  pin_map.h
//
//  Single source of truth for every GPIO and peripheral assignment on the
//  Adafruit Metro ESP32-S3.  All values flagged TODO are placeholders that
//  must be confirmed against the final schematic before flashing real
//  hardware.  Keeping the assignments here (instead of scattered across the
//  modules) means a pin swap only needs one edit and a rebuild.
//
//  ESP-IDF v5.4.x.  Board: Metro ESP32-S3 (ESP32-S3-WROOM-1, 8 MB flash,
//  native USB on GPIO 19/20).
// =============================================================================
#pragma once

#include "driver/gpio.h"
#include "driver/spi_common.h"
#include "driver/i2c_master.h"

namespace pins {

// ---------------------------------------------------------------------------
//  Bus assignments.  See cw_envelope_keyer.md §"Bus discipline" — the
//  envelope DAC MUST be on its own SPI bus, never sharing the monitoring
//  I2C bus.
// ---------------------------------------------------------------------------

// ---- I2C bus (monitoring + control) ---------------------------------------
//  Shared between: Si5351 (VFO), MCP4728 (per-tube grid bias DACs), ADS1115
//  (cathode current ADC), any future small I2C peripherals.  GPIO 3/4 are
//  the Metro ESP32-S3 STEMMA QT pins and route to that connector as well.
constexpr i2c_port_num_t I2C_PORT      = I2C_NUM_0;
constexpr gpio_num_t     I2C_SDA       = GPIO_NUM_3;   // STEMMA QT SDA
constexpr gpio_num_t     I2C_SCL       = GPIO_NUM_4;   // STEMMA QT SCL
constexpr uint32_t       I2C_HZ        = 400000;       // 400 kHz fast-mode

// ---- SPI bus, dedicated to the envelope DAC --------------------------------
//  MCP4921, 12-bit, MOSI-only (MISO unused).  Bus is FSPI on the S3.  CS is
//  driven manually by the playout task — do NOT enable hardware CS.
constexpr spi_host_device_t DAC_SPI_HOST = SPI2_HOST;  // = FSPI
constexpr gpio_num_t     ENV_DAC_SCK   = GPIO_NUM_12;  // TODO: confirm w/ schematic
constexpr gpio_num_t     ENV_DAC_MOSI  = GPIO_NUM_11;  // TODO
constexpr gpio_num_t     ENV_DAC_CS    = GPIO_NUM_10;  // TODO
constexpr int            ENV_DAC_HZ    = 20000000;     // MCP4921 max ~20 MHz

// ---------------------------------------------------------------------------
//  Peripheral I2C addresses
// ---------------------------------------------------------------------------
constexpr uint8_t I2C_ADDR_SI5351   = 0x60;   // Adafruit Si5351A breakout
constexpr uint8_t I2C_ADDR_MCP4728  = 0x60;   // collides w/ Si5351 — see note below
constexpr uint8_t I2C_ADDR_ADS1115  = 0x48;   // default ADDR pin = GND

// NOTE on address collision: MCP4728 ships at 0x60 too.  The grid-bias board
// will use a factory-programmed alternate address (e.g. 0x61 or 0x62) or sit
// on a second I2C peripheral.  Resolve before populating the bias board.
// Placeholder until then:
constexpr uint8_t I2C_ADDR_BIAS_DAC = 0x61;   // TODO: confirm after MCP4728 program

// ---------------------------------------------------------------------------
//  Fault / fail-safe — hardware screen-voltage gate
// ---------------------------------------------------------------------------
//  Active-low gate output.  Drops the high-side MOSFET feeding the screen
//  supply, killing the tubes within ~100 µs.  Also fed from the LM393
//  comparator latch in hardware; the GPIO is the firmware path.
constexpr gpio_num_t FAULT_GATE_OUT     = GPIO_NUM_13;   // TODO
constexpr gpio_num_t FAULT_LATCH_RESET  = GPIO_NUM_14;   // TODO — pulse high to clear SR latch
constexpr gpio_num_t FAULT_LATCH_STATUS = GPIO_NUM_15;   // TODO — reads back the latch state

// ---------------------------------------------------------------------------
//  Front panel — rotary encoders + pushbuttons
// ---------------------------------------------------------------------------
//  Two quadrature encoders so far:
//    FREQ — tunes the VFO
//    POWER — single setpoint that fans out to (a) envelope DAC CODE_FULL and
//            (b) per-tube grid bias offset, per the leveled-buffer design
//
//  Pins are placeholders.  Use S3 GPIOs that route to PCNT-capable IO when
//  the encoder driver gets fleshed out (front_panel.cpp).
constexpr gpio_num_t ENC_FREQ_A     = GPIO_NUM_5;    // TODO
constexpr gpio_num_t ENC_FREQ_B     = GPIO_NUM_6;    // TODO
constexpr gpio_num_t ENC_FREQ_SW    = GPIO_NUM_7;    // TODO — push-in switch

constexpr gpio_num_t ENC_POWER_A    = GPIO_NUM_8;    // TODO
constexpr gpio_num_t ENC_POWER_B    = GPIO_NUM_9;    // TODO
constexpr gpio_num_t ENC_POWER_SW   = GPIO_NUM_16;   // TODO

// ---------------------------------------------------------------------------
//  Power-supply sequencing (TBD — supply not yet designed)
// ---------------------------------------------------------------------------
constexpr gpio_num_t PSU_MAIN_EN    = GPIO_NUM_17;   // TODO — turns on B+/screen/bias
constexpr gpio_num_t PSU_READY_IN   = GPIO_NUM_18;   // TODO — feedback from supply

// ---------------------------------------------------------------------------
//  WinKey paddle inputs (DIT / DAH closures)
// ---------------------------------------------------------------------------
constexpr gpio_num_t PADDLE_DIT     = GPIO_NUM_21;   // TODO — pull-up, key = GND
constexpr gpio_num_t PADDLE_DAH     = GPIO_NUM_47;   // TODO

// ---------------------------------------------------------------------------
//  Onboard LED (Metro ESP32-S3 has an onboard NeoPixel on GPIO 46, but we
//  use the red status LED on GPIO 13 of the original Metro — TODO to confirm
//  Adafruit Metro ESP32-S3 actually has a plain LED; if only NeoPixel, drop
//  status_blink() in fault_handler).
// ---------------------------------------------------------------------------
constexpr gpio_num_t STATUS_LED     = GPIO_NUM_NC;   // TODO — pick on real board

// ---------------------------------------------------------------------------
//  RTOS core assignments — referenced widely; keep them here so we never
//  hard-code a "1" in xTaskCreatePinnedToCore.
// ---------------------------------------------------------------------------
constexpr int CORE_MONITOR = 0;   // PRO_CPU — I2C traffic, encoders, faults
constexpr int CORE_KEYING  = 1;   // APP_CPU — envelope playout, WinKey

}  // namespace pins

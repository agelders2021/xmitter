// =============================================================================
//  mcp4728.cpp — MCP4728 driver.  See header.
// =============================================================================
#include "mcp4728.h"

#include <cstring>

#include "esp_log.h"
#include "esp_check.h"
#include "esp_rom_gpio.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "soc/gpio_sig_map.h"

#include "pin_map.h"

namespace mcp4728 {

namespace {

constexpr char TAG[] = "mcp4728";

// MCP4728 valid I2C address range: 0x60..0x67 (fixed high nibble 1100,
// three low bits programmable via EEPROM).
constexpr uint8_t ADDR_MIN = 0x60;
constexpr uint8_t ADDR_MAX = 0x67;

bool valid(uint8_t addr) { return addr >= ADDR_MIN && addr <= ADDR_MAX; }

// ---------------------------------------------------------------------------
//  Bit-bang I2C for the MCP4728 address reprogram.
//
//  The MCP4728 requires LDAC to transition HIGH -> LOW during the ACK bit
//  of the SLAVE ADDRESS byte to arm the "Write I2C Address" command
//  (DS22187 §4.5.3.3).  ESP-IDF v5.4's i2c_master driver gives us no way
//  to inject GPIO activity between address ACK and the following data
//  bytes, so hardware I2C either sends LDAC LOW too early (chip NAKs the
//  address) or LDAC never transitions (chip ACKs but ignores the
//  reprogram command).  Bit-banging lets us hit the ACK-window LDAC edge.
//
//  Timing target: 100 kHz.  Each SCL half-cycle is 5 us, plenty of margin
//  for even the slowest bench probe.  All delays are esp_rom_delay_us()
//  busy-waits since we're in a tight synchronous transaction.
// ---------------------------------------------------------------------------

constexpr int BB_HALF_US = 20;   // 25 kHz -- slow enough for weak pullups

inline void bb_delay() { esp_rom_delay_us(BB_HALF_US); }

// While bit-banging we route SDA/SCL from the I2C0 peripheral matrix
// signals to plain-GPIO output/input.  Restore them at the end so the
// hardware I2C peripheral gets its pins back.
void bb_take_pin(gpio_num_t pin) {
    // Force pin's output signal to plain GPIO_OUT (index 256 on ESP32-S3).
    esp_rom_gpio_connect_out_signal(pin, SIG_GPIO_OUT_IDX, false, false);
    // Enable both input and output; open-drain so pull-ups can hold HIGH.
    gpio_set_direction(pin, GPIO_MODE_INPUT_OUTPUT_OD);
    gpio_set_pull_mode(pin, GPIO_PULLUP_ONLY);
    gpio_set_level(pin, 1);          // idle HIGH
}

void bb_release_pin(gpio_num_t pin, uint32_t out_sig, uint32_t in_sig) {
    esp_rom_gpio_connect_out_signal(pin, out_sig, false, false);
    esp_rom_gpio_connect_in_signal(in_sig, pin, false);
}

inline void bb_scl_low(gpio_num_t scl)  { gpio_set_level(scl, 0); }
inline void bb_scl_high(gpio_num_t scl) { gpio_set_level(scl, 1); }
inline void bb_sda_low(gpio_num_t sda)  { gpio_set_level(sda, 0); }
inline void bb_sda_high(gpio_num_t sda) { gpio_set_level(sda, 1); }
inline int  bb_sda_read(gpio_num_t sda) { return gpio_get_level(sda); }

void bb_start(gpio_num_t sda, gpio_num_t scl) {
    bb_sda_high(sda); bb_scl_high(scl); bb_delay();
    bb_sda_low(sda);  bb_delay();
    bb_scl_low(scl);
}

void bb_stop(gpio_num_t sda, gpio_num_t scl) {
    bb_scl_low(scl); bb_sda_low(sda); bb_delay();
    bb_scl_high(scl); bb_delay();
    bb_sda_high(sda); bb_delay();
}

// Send one byte MSB-first, return true if slave ACKed.  Timing is
// generous: 2 us setup after SDA change before SCL rise, ~half-cycle
// during SCL HIGH, then wait for the pull-up to lift SDA before reading
// during the ACK bit.
//
// If drop_ldac_at_lsb_low_time is set, drives LDAC LOW during the
// SCL-LOW window after the 8th (LSB) data bit's SCL-HIGH sample -- this
// is the MCP4728 datasheet requirement for the "Write I2C Address"
// command: "LDAC pin makes a transition from High to Low at the low
// time of the last bit (8th clock) of the second byte" (DS22187 §5.6.8).
bool bb_write_byte(gpio_num_t sda, gpio_num_t scl, uint8_t byte,
                   bool drop_ldac_at_lsb_low_time, gpio_num_t ldac_pin) {
    for (int i = 7; i >= 0; --i) {
        if ((byte >> i) & 1) bb_sda_high(sda);
        else                 bb_sda_low(sda);
        esp_rom_delay_us(2);
        bb_scl_high(scl); bb_delay();
        bb_scl_low(scl);
        if (i == 0 && drop_ldac_at_lsb_low_time) {
            // We're now in the "low time of the 8th clock" -- SCL just went
            // LOW after the LSB was sampled, and we haven't started the
            // ACK bit yet.  Wait a moment for SCL to settle, drop LDAC.
            esp_rom_delay_us(2);
            gpio_set_level(ldac_pin, 0);
            esp_rom_delay_us(BB_HALF_US - 4);
        } else {
            esp_rom_delay_us(BB_HALF_US - 2);
        }
    }
    // ACK bit: release SDA, give the pull-up time, raise SCL, sample.
    bb_sda_high(sda);
    esp_rom_delay_us(3);
    bb_scl_high(scl);
    esp_rom_delay_us(BB_HALF_US / 2);
    const bool ack = (bb_sda_read(sda) == 0);
    esp_rom_delay_us(BB_HALF_US / 2);
    bb_scl_low(scl);
    esp_rom_delay_us(BB_HALF_US);
    return ack;
}

}  // namespace

esp_err_t plan_reprogram_bytes(uint8_t cur_addr,
                               uint8_t new_addr,
                               uint8_t out_bytes[3]) {
    if (!valid(cur_addr) || !valid(new_addr) || out_bytes == nullptr) {
        return ESP_ERR_INVALID_ARG;
    }

    const uint8_t cur_bits = cur_addr & 0x07;
    const uint8_t new_bits = new_addr & 0x07;

    // MCP4728 "Write I2C Address Bits" command -- correct bit layout per
    // jknipper's proven implementation and TrippyLighting's SoftI2cMaster
    // ldacwrite():
    //   Bits [7:5] = 011  (command family)
    //   Bits [4:2] = A2 A1 A0  (address bits, shifted LEFT by 2)
    //   Bits [1:0] = role code:
    //     01 = byte 2 (arm command with CURRENT addr)
    //     10 = byte 3 (data byte with NEW addr)
    //     11 = byte 4 (confirm with NEW addr)
    //
    // Previous rev of this file used address bits in [3:1] and only bit 0
    // as the role code -- that "Adafruit-style" encoding is a myth
    // (Adafruit_MCP4728 doesn't even have a setAddress method) and
    // consistently NAKed on real hardware.
    out_bytes[0] = (uint8_t)(0x61 | (cur_bits << 2));
    out_bytes[1] = (uint8_t)(0x62 | (new_bits << 2));
    out_bytes[2] = (uint8_t)(0x63 | (new_bits << 2));

    return ESP_OK;
}

esp_err_t reprogram_address(i2c_master_bus_handle_t bus,
                            uint8_t                 cur_addr,
                            uint8_t                 new_addr,
                            gpio_num_t              ldac_pin) {
    if (bus == nullptr)               return ESP_ERR_INVALID_ARG;
    if (!valid(cur_addr))             return ESP_ERR_INVALID_ARG;
    if (!valid(new_addr))             return ESP_ERR_INVALID_ARG;
    if (cur_addr == new_addr) {
        ESP_LOGW(TAG, "cur_addr == new_addr, nothing to do");
        return ESP_OK;
    }

    uint8_t bytes[3];
    esp_err_t e = plan_reprogram_bytes(cur_addr, new_addr, bytes);
    if (e != ESP_OK) return e;

    const gpio_num_t SDA = pins::I2C_SDA;
    const gpio_num_t SCL = pins::I2C_SCL;

    ESP_LOGI(TAG, "BIT-BANG reprogram: 0x%02X -> 0x%02X  (bytes: %02X %02X %02X)",
             cur_addr, new_addr, bytes[0], bytes[1], bytes[2]);
    ESP_LOGI(TAG, "  SDA=GPIO%d  SCL=GPIO%d  LDAC=GPIO%d",
             (int)SDA, (int)SCL, (int)ldac_pin);

    // Prep LDAC: clean pin, output, idle HIGH.
    gpio_reset_pin(ldac_pin);
    gpio_set_pull_mode(ldac_pin, GPIO_FLOATING);
    gpio_set_direction(ldac_pin, GPIO_MODE_OUTPUT);
    gpio_set_level(ldac_pin, 1);

    // Make sure the hardware I2C peripheral is quiescent before we hijack
    // its pins.
    (void)i2c_master_bus_wait_all_done(bus, 100);

    // Take pins from the peripheral.
    bb_take_pin(SDA);
    bb_take_pin(SCL);
    esp_rom_delay_us(50);   // let pull-ups settle after matrix swap

    // Datasheet-correct LDAC sequencing (DS22187 §5.6.8 "Write I2C Address
    // Bits Command"):
    //   * LDAC HIGH before START and through the address + first two
    //     command bytes.
    //   * LDAC transitions HIGH -> LOW during the SCL-LOW time of the LSB
    //     (8th clock) of the SECOND command byte (bytes[1] = new-address
    //     byte).  Chip samples this specific edge to arm the command.
    //   * LDAC stays LOW through the third command byte (bytes[2] =
    //     confirmation).
    //   * Address change takes effect on STOP.  LDAC can return HIGH
    //     after STOP.
    // Ensure HIGH.
    gpio_set_level(ldac_pin, 1);
    esp_rom_delay_us(50);

    // 7-bit address with W=0 in LSB
    const uint8_t addr_byte = (uint8_t)((cur_addr << 1) & 0xFE);

    // Datasheet + jknipper: LDAC drops LOW during the ACK bit of BYTE 2,
    // which in "bytes on the wire" counting is the FIRST DATA byte after
    // the address (bytes[0] here).  Earlier revs of this file put the
    // drop on bytes[1] -- wrong data byte.
    bb_start(SDA, SCL);
    const bool ack_addr = bb_write_byte(SDA, SCL, addr_byte,   false, ldac_pin);
    const bool ack1     = bb_write_byte(SDA, SCL, bytes[0],    true,  ldac_pin);
    const bool ack2     = bb_write_byte(SDA, SCL, bytes[1],    false, ldac_pin);
    const bool ack3     = bb_write_byte(SDA, SCL, bytes[2],    false, ldac_pin);
    bb_stop(SDA, SCL);

    // EEPROM burn (~50 ms per datasheet).  Keep LDAC LOW through it.
    vTaskDelay(pdMS_TO_TICKS(60));
    gpio_set_level(ldac_pin, 1);

    // Give SDA/SCL back to the hardware I2C peripheral.  ESP32-S3 I2C0
    // signals: SDA=I2CEXT0_SDA_OUT_IDX, SCL=I2CEXT0_SCL_OUT_IDX.
    bb_release_pin(SDA, I2CEXT0_SDA_OUT_IDX, I2CEXT0_SDA_IN_IDX);
    bb_release_pin(SCL, I2CEXT0_SCL_OUT_IDX, I2CEXT0_SCL_IN_IDX);

    ESP_LOGI(TAG, "  ACKs -- addr:%d byte1:%d byte2:%d byte3:%d",
             (int)ack_addr, (int)ack1, (int)ack2, (int)ack3);

    if (!ack_addr) {
        ESP_LOGE(TAG, "no ACK on slave address byte (chip not answering "
                      "bit-bang)");
        return ESP_ERR_NOT_FOUND;
    }
    if (!(ack1 && ack2 && ack3)) {
        ESP_LOGE(TAG, "chip NAK'd one of the reprogram command bytes");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "reprogram sequence acknowledged; caller should probe "
                  "0x%02X to verify", new_addr);
    return ESP_OK;
}

esp_err_t write_channel_dac(i2c_master_bus_handle_t bus,
                             uint8_t                 addr,
                             uint8_t                 channel,
                             uint16_t                code12) {
    if (!bus || channel > 3) return ESP_ERR_INVALID_ARG;
    if (code12 > 0x0FFFu) code12 = 0x0FFFu;

    // Multi-Write DAC Register (DS22187 §5.6.2).
    // Byte 0: 0b01000000 | (channel << 1) | UDAC(0)  [CMD=010, UDAC=0]
    // Byte 1: VREF=0(VDD) PD=00(normal) Gx=0(1×) D11:D8
    // Byte 2: D7:D0
    const uint8_t buf[3] = {
        (uint8_t)(0x40u | ((uint8_t)channel << 1u)),
        (uint8_t)((code12 >> 8u) & 0x0Fu),
        (uint8_t)(code12 & 0xFFu),
    };

    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = addr;
    cfg.scl_speed_hz    = 400000;

    i2c_master_dev_handle_t dev = nullptr;
    esp_err_t e = i2c_master_bus_add_device(bus, &cfg, &dev);
    if (e != ESP_OK) return e;
    e = i2c_master_transmit(dev, buf, sizeof(buf), 100);
    i2c_master_bus_rm_device(dev);

    if (e == ESP_OK) {
        ESP_LOGI(TAG, "ch %c -> %u (0x%03X)",
                 'A' + (char)channel, (unsigned)code12, (unsigned)code12);
    }
    return e;
}

}  // namespace mcp4728

// =============================================================================
//  vfo_si5351.cpp — Si5351A driver, CLK2 only.
//
//  CLK2 is the RF output routed to the analog board's buffer/keyer chain on
//  Rev A.  CLK0 and CLK1 are left disabled.
//
//  Frequency planning strategy (see AN619):
//    - CLK2 is driven by MS2 in INTEGER mode (best phase noise on a Si5351A).
//    - MS2 divider is the smallest even integer that puts the PLLA VCO in
//      the 600–900 MHz band specified by the datasheet.
//    - PLLA feedback divider (a + b/c) carries the fractional part, with
//      c = 1,048,575 (max 20-bit denominator) for sub-Hz resolution.
//
//  For 14.200 MHz on a 25 MHz xtal: MS2=50 → PLLA=710 MHz → fb = 28.4 →
//  a=28, b=419430, c=1048575.  Output is exact.
//
//  Register layout follows the Si5351A/B/C-B datasheet Rev. 1.0 and AN619.
// =============================================================================
#include "vfo_si5351.h"

#include <cstring>
#include "esp_log.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "pin_map.h"

namespace vfo {

namespace {

constexpr char TAG[] = "vfo";

// ---- Register addresses (Si5351 datasheet §10) -----------------------------
constexpr uint8_t REG_DEVICE_STATUS    = 0;
constexpr uint8_t REG_OUTPUT_ENABLE    = 3;     // bit n = 1 disables CLKn
constexpr uint8_t REG_CLK2_CTRL        = 18;    // CLK2 control byte
constexpr uint8_t REG_CLK_DISABLE_STATE = 24;   // state of CLKn when disabled
constexpr uint8_t REG_MSNA_BASE        = 26;    // PLLA Multisynth registers (8)
constexpr uint8_t REG_MS2_BASE         = 58;    // MS2 Multisynth registers  (8)
constexpr uint8_t REG_PLL_RESET        = 177;   // bit 5 = PLLA_RST, bit 7 = PLLB_RST
constexpr uint8_t REG_XTAL_CAP         = 183;   // bits[7:6] = XTAL load cap

// CLK2 control byte:
//   bit7 CLK2_PDN  = 0  (powered up)
//   bit6 MS2_INT   = 1  (integer-mode multisynth — quieter)
//   bit5 MS2_SRC   = 0  (PLLA)
//   bit4 CLK2_INV  = 0
//   bit3-2 CLK2_SRC = 11 (MS2 output)
//   bit1-0 CLK2_IDRV = 11 (8 mA)
constexpr uint8_t CLK2_CTRL_ON  = 0b01001111;   // 0x4F
constexpr uint8_t CLK2_CTRL_PDN = 0b10001100;   // PDN=1, drive irrelevant

// REG_OUTPUT_ENABLE masks (1 = disabled).  CLK2-only mode leaves bits 0,1
// set (CLK0/CLK1 disabled) and clears bit 2.
constexpr uint8_t OE_ALL_OFF     = 0xFF;
constexpr uint8_t OE_CLK2_ON     = 0xFB;   // 0b11111011

// XTAL load cap = 10 pF (Adafruit Si5351A breakout uses 10 pF crystal cap).
// Bits[7:6] = 11 (10 pF); bits[5:0] = 0b010010 (reserved, must be written).
constexpr uint8_t XTAL_CAP_10PF = 0b11010010;   // 0xD2

// PLLA VCO must stay between these (Si5351 datasheet §3.2).
constexpr uint64_t PLL_MIN_HZ = 600000000ULL;
constexpr uint64_t PLL_MAX_HZ = 900000000ULL;

// Denominator for the PLLA feedback fractional part — max 20-bit value gives
// the finest resolution the chip supports.
constexpr uint32_t FRAC_C = 1048575UL;

// ---- State -----------------------------------------------------------------
i2c_master_dev_handle_t s_dev = nullptr;
uint32_t                s_xtal_hz = XTAL_HZ_DEFAULT;
uint32_t                s_freq_hz = DEFAULT_FREQ_HZ;
bool                    s_on = false;

// ---- Low-level register access --------------------------------------------
esp_err_t write_reg(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg, val };
    return i2c_master_transmit(s_dev, buf, sizeof(buf), 100 /* ms */);
}

esp_err_t write_burst(uint8_t start_reg, const uint8_t *data, size_t n) {
    uint8_t buf[16];
    if (n + 1 > sizeof(buf)) return ESP_ERR_INVALID_ARG;
    buf[0] = start_reg;
    std::memcpy(buf + 1, data, n);
    return i2c_master_transmit(s_dev, buf, n + 1, 100 /* ms */);
}

// Pack the 8-byte block that programmes either a PLL or a MultiSynth
// (the two share the AN619 P1/P2/P3 layout).  See AN619 §3.2 Table 3.
void pack_msynth_block(uint8_t *out8,
                       uint32_t p1, uint32_t p2, uint32_t p3,
                       uint8_t  r_div = 0,        // CLK output divider (MS-only)
                       bool     divby4 = false)   // MS-only, for f>150 MHz
{
    out8[0] = (uint8_t)((p3 >> 8) & 0xFF);
    out8[1] = (uint8_t)( p3       & 0xFF);
    out8[2] = (uint8_t)(((r_div & 0x07) << 4) |
                        ((divby4 ? 0x3 : 0x0) << 2) |
                        ((p1 >> 16) & 0x03));
    out8[3] = (uint8_t)((p1 >> 8) & 0xFF);
    out8[4] = (uint8_t)( p1       & 0xFF);
    out8[5] = (uint8_t)(((p3 >> 12) & 0xF0) | ((p2 >> 16) & 0x0F));
    out8[6] = (uint8_t)((p2 >> 8) & 0xFF);
    out8[7] = (uint8_t)( p2       & 0xFF);
}

}  // namespace

// ---------------------------------------------------------------------------
//  Public API
// ---------------------------------------------------------------------------

esp_err_t init(i2c_master_bus_handle_t bus) {
    if (s_dev != nullptr) {
        // Already initialized; drop and re-add so a repeat init() recovers
        // cleanly after a bus or chip glitch.
        i2c_master_bus_rm_device(s_dev);
        s_dev = nullptr;
    }

    i2c_device_config_t cfg = {};
    cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    cfg.device_address  = pins::I2C_ADDR_SI5351;
    cfg.scl_speed_hz    = pins::I2C_HZ;
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus, &cfg, &s_dev),
                        TAG, "add Si5351 to I2C bus");

    // Wait for the chip's internal startup (SYS_INIT bit in DEVICE_STATUS to
    // clear).  Bounded poll — if it never clears, fall through and let the
    // first write fail loudly.
    for (int i = 0; i < 100; ++i) {
        uint8_t reg = REG_DEVICE_STATUS;
        uint8_t status = 0xFF;
        if (i2c_master_transmit_receive(s_dev, &reg, 1, &status, 1, 100) == ESP_OK) {
            if ((status & 0x80) == 0) break;   // SYS_INIT cleared
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }

    // Disable all CLK outputs while we (re)program.
    ESP_RETURN_ON_ERROR(write_reg(REG_OUTPUT_ENABLE, 0xFF), TAG, "disable outputs");

    // Power down all CLK control registers (CLK0..CLK7), known clean slate.
    for (uint8_t r = 16; r < 24; ++r) {
        ESP_RETURN_ON_ERROR(write_reg(r, 0x80), TAG, "powerdown CLKn");
    }

    // Set crystal load capacitance (10 pF on Adafruit breakout).
    ESP_RETURN_ON_ERROR(write_reg(REG_XTAL_CAP, XTAL_CAP_10PF), TAG, "xtal cap");

    s_on = false;
    ESP_LOGI(TAG, "Si5351A init OK (addr 0x%02X, xtal %lu Hz)",
             pins::I2C_ADDR_SI5351, (unsigned long)s_xtal_hz);
    return ESP_OK;
}

esp_err_t set_freq(uint32_t f_hz) {
    if (s_dev == nullptr) return ESP_ERR_INVALID_STATE;
    if (f_hz < 8000UL || f_hz > 160000000UL) return ESP_ERR_INVALID_ARG;
    s_freq_hz = f_hz;

    // ---- Pick an even-integer MS0 divider that puts PLLA inside the VCO band.
    uint32_t ms_div = (uint32_t)((PLL_MIN_HZ + f_hz - 1) / f_hz);   // ceil
    if (ms_div < 8) ms_div = 8;
    if (ms_div & 1) ms_div++;
    uint64_t pll_hz = (uint64_t)f_hz * ms_div;
    if (pll_hz > PLL_MAX_HZ) {
        ESP_LOGE(TAG, "freq %lu Hz out of PLL range (no even divider fits)",
                 (unsigned long)f_hz);
        return ESP_ERR_INVALID_ARG;
    }

    // ---- PLLA feedback divider = a + b/c
    uint32_t a   = (uint32_t)(pll_hz / s_xtal_hz);
    uint64_t rem = pll_hz - (uint64_t)a * s_xtal_hz;
    uint32_t b   = (uint32_t)((rem * FRAC_C) / s_xtal_hz);
    uint32_t c   = FRAC_C;

    // ---- AN619 P1/P2/P3 for the PLL (fractional path).
    uint64_t mul128_b_div_c = (128ULL * b) / c;
    uint32_t pll_p1 = (uint32_t)(128ULL * a + mul128_b_div_c - 512ULL);
    uint32_t pll_p2 = (uint32_t)(128ULL * b - (uint64_t)c * mul128_b_div_c);
    uint32_t pll_p3 = c;

    // ---- AN619 P1/P2/P3 for the MultiSynth (integer mode → b=0, c=1).
    uint32_t ms_p1 = 128UL * ms_div - 512UL;
    uint32_t ms_p2 = 0;
    uint32_t ms_p3 = 1;

    uint8_t buf[8];

    pack_msynth_block(buf, pll_p1, pll_p2, pll_p3);
    ESP_RETURN_ON_ERROR(write_burst(REG_MSNA_BASE, buf, 8), TAG, "PLLA write");

    pack_msynth_block(buf, ms_p1, ms_p2, ms_p3, /*r_div=*/0, /*divby4=*/false);
    ESP_RETURN_ON_ERROR(write_burst(REG_MS2_BASE, buf, 8), TAG, "MS2 write");

    // Reset PLLA so the new feedback divider takes effect from a known phase.
    ESP_RETURN_ON_ERROR(write_reg(REG_PLL_RESET, 0x20), TAG, "PLLA reset");

    // Apply CLK2 control (8 mA, PLLA src, integer multisynth) — does not yet
    // enable the output pin; that's vfo::on().
    ESP_RETURN_ON_ERROR(write_reg(REG_CLK2_CTRL, CLK2_CTRL_ON), TAG, "CLK2 ctrl");

    ESP_LOGI(TAG, "freq=%lu Hz  (MS=%lu, PLLA=%llu Hz, fb=%lu+%lu/%lu)",
             (unsigned long)f_hz, (unsigned long)ms_div,
             (unsigned long long)pll_hz,
             (unsigned long)a, (unsigned long)b, (unsigned long)c);
    return ESP_OK;
}

esp_err_t on() {
    if (s_dev == nullptr) return ESP_ERR_INVALID_STATE;
    // Make sure the CLK2 control byte is in the powered-up state, then drop
    // the output-disable bit for CLK2.
    ESP_RETURN_ON_ERROR(write_reg(REG_CLK2_CTRL,     CLK2_CTRL_ON), TAG, "clk2 ctrl");
    ESP_RETURN_ON_ERROR(write_reg(REG_OUTPUT_ENABLE, OE_CLK2_ON),   TAG, "clk2 enable");
    s_on = true;
    ESP_LOGI(TAG, "CLK2 on  (%lu Hz)", (unsigned long)s_freq_hz);
    return ESP_OK;
}

esp_err_t off() {
    if (s_dev == nullptr) return ESP_ERR_INVALID_STATE;
    ESP_RETURN_ON_ERROR(write_reg(REG_OUTPUT_ENABLE, OE_ALL_OFF),    TAG, "clk2 disable");
    ESP_RETURN_ON_ERROR(write_reg(REG_CLK2_CTRL,   CLK2_CTRL_PDN),   TAG, "clk2 powerdown");
    s_on = false;
    ESP_LOGI(TAG, "CLK2 off");
    return ESP_OK;
}

uint32_t current_freq() { return s_freq_hz; }
bool     is_on()        { return s_on; }

}  // namespace vfo

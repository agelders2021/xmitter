// =============================================================================
//  reprogram_mcp4728.ino
//
//  One-shot Arduino sketch to reprogram the MCP4728's I2C EEPROM address
//  from factory 0x60 to target 0x67.  Uses only the built-in Wire library
//  -- no external libraries needed.  Arduino ESP32's Wire runs on top of
//  the ESP-IDF I2C driver but through a different code path than what
//  our ESP-IDF firmware calls directly, so this is our last shot at
//  hardware I2C working when ESP-IDF's own driver stack won't do it.
//
//  BENCH SETUP:
//    * Metro on USB (COM11)
//    * MCP4728 breakout on STEMMA QT to Metro (3.3 V supply)
//    * MCP4728 LDAC pin wired to Metro D7 (GPIO 7)
//    * Nothing else on the I2C bus recommended
//
//  ARDUINO IDE SETUP (one-time, see step-by-step in chat):
//    1. Install Arduino IDE 2.x
//    2. Add ESP32 board support (Preferences URL)
//    3. Select "Adafruit Metro ESP32-S3" board, COM11 port
//    4. Open this sketch, click Upload, open Serial Monitor at 115200
// =============================================================================
#include <Wire.h>

// Adafruit Metro ESP32-S3 STEMMA QT / header I2C pins
constexpr int I2C_SDA = 47;
constexpr int I2C_SCL = 48;

// LDAC control -- MUST be wired from Metro D7 to breakout LDAC pin
constexpr int LDAC_PIN = 7;

constexpr uint8_t CUR_ADDR = 0x60;   // factory default
constexpr uint8_t NEW_ADDR = 0x67;   // xmitter project target

void setup() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    delay(2000);

    Serial.println();
    Serial.println("=== MCP4728 address reprogram (raw Wire) ===");
    Serial.printf(" cur addr: 0x%02X    new addr: 0x%02X    LDAC: GPIO %d\n",
                  CUR_ADDR, NEW_ADDR, LDAC_PIN);
    Serial.println();

    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);

    pinMode(LDAC_PIN, OUTPUT);
    digitalWrite(LDAC_PIN, HIGH);
    delay(10);

    // Check if already reprogrammed
    Wire.beginTransmission(NEW_ADDR);
    if (Wire.endTransmission() == 0) {
        Serial.println("INFO: 0x67 already ACKs -- chip already reprogrammed.");
        Serial.println("Nothing to do.  Reflash bringup.bat next.");
        while (true) delay(1000);
    }

    // Confirm chip at factory 0x60
    Wire.beginTransmission(CUR_ADDR);
    if (Wire.endTransmission() != 0) {
        Serial.println("FAIL: no chip at 0x60");
        Serial.println("  check STEMMA QT cable + 3.3V supply");
        while (true) delay(1000);
    }
    Serial.println("Found chip at 0x60.");

    // Prepare the 3 command bytes per DS22187 §5.6.8:
    //   byte 0: 0110_0AAA_1  (Write Addr cmd + CURRENT addr bits)
    //   byte 1: 0110_0AAA_0  (NEW addr bits)
    //   byte 2: 0110_0AAA_1  (confirm NEW addr bits)
    const uint8_t cur_bits = CUR_ADDR & 0x07;
    const uint8_t new_bits = NEW_ADDR & 0x07;
    const uint8_t b0 = 0x61 | (cur_bits << 1);
    const uint8_t b1 = 0x60 | (new_bits << 1);
    const uint8_t b2 = 0x61 | (new_bits << 1);
    Serial.printf("Sending bytes: %02X %02X %02X\n", b0, b1, b2);

    // Adafruit-style: LDAC HIGH -> LOW while bus is idle, BEFORE the START.
    digitalWrite(LDAC_PIN, LOW);
    delayMicroseconds(10);

    Wire.beginTransmission(CUR_ADDR);
    Wire.write(b0);
    Wire.write(b1);
    Wire.write(b2);
    uint8_t xfer_err = Wire.endTransmission();

    delay(100);   // EEPROM burn
    digitalWrite(LDAC_PIN, HIGH);

    Serial.printf("Wire.endTransmission returned: %u\n", xfer_err);
    if (xfer_err != 0) {
        Serial.println("  (0=OK, 1=data too long, 2=NAK on address, 3=NAK on data)");
    }

    // Verify
    delay(50);
    Wire.beginTransmission(NEW_ADDR);
    uint8_t verify_new = Wire.endTransmission();
    Wire.beginTransmission(CUR_ADDR);
    uint8_t verify_old = Wire.endTransmission();

    Serial.println();
    Serial.println("=================================================");
    if (verify_new == 0 && verify_old != 0) {
        Serial.printf(" SUCCESS: MCP4728 now responds at 0x%02X (0x%02X silent)\n",
                      NEW_ADDR, CUR_ADDR);
        Serial.println(" Reflash bringup.bat to return to normal.");
    } else if (verify_old == 0 && verify_new != 0) {
        Serial.printf(" FAIL: chip still at 0x%02X\n", CUR_ADDR);
        Serial.println(" LDAC wire from Metro D7 to breakout LDAC pin?");
    } else if (verify_new == 0 && verify_old == 0) {
        Serial.println(" WEIRD: both addresses ACK -- bus glitch?");
    } else {
        Serial.println(" WEIRD: neither address ACKs after reprogram.");
    }
    Serial.println("=================================================");
}

void loop() {
    // Nothing -- one-shot.  Reset the board to run again.
}

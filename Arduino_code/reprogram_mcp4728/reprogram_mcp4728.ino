// =============================================================================
//  reprogram_mcp4728.ino  --  MCP4728 address reprogram, bit-bang, JKnipper
//                             encoding + LDAC-during-byte-2-ACK timing.
//
//  Based on https://github.com/jknipper/mcp4728_program_address which uses
//  SoftI2cMaster's ldacwrite() -- the specific LDAC-drop-during-ACK-of-first-
//  data-byte trick that finally makes the "Write I2C Address" command work.
//  Inlined here so no external Arduino library install is needed.
//
//  Two things this fixes vs all our previous attempts (both Arduino-Wire
//  and ESP-IDF bit-bang / new / legacy drivers):
//
//    Encoding fix:
//      byte 2: 0x61 | (cur << 2)   -- NOT 0x61 | (cur << 1)
//      byte 3: 0x62 | (new << 2)   -- NOT 0x60 | (new << 1)
//      byte 4: 0x63 | (new << 2)   -- NOT 0x61 | (new << 1)
//      Address bits live in bit positions [4:2], role code in [1:0].
//
//    LDAC-timing fix:
//      LDAC transitions HIGH -> LOW during the SCL-LOW period of byte 2's
//      ACK bit (byte 2 = FIRST data byte after the address).  Previous
//      attempts dropped LDAC at every other point in the transaction --
//      before START, during address-byte ACK, during byte 3's LSB, etc.
//
//  BENCH SETUP:
//    * Metro on USB (COM11)
//    * MCP4728 breakout on STEMMA QT to Metro (3.3 V power via that cable)
//    * MCP4728 LDAC pin wired to Metro D7 (GPIO 7)
//    * Nothing else on the I2C bus recommended
// =============================================================================

#include <Arduino.h>

constexpr int SDA_PIN  = 47;   // Adafruit Metro ESP32-S3 STEMMA QT SDA
constexpr int SCL_PIN  = 48;   //                            STEMMA QT SCL
constexpr int LDAC_PIN = 7;    // Arduino D7 on Metro ESP32-S3

constexpr uint8_t CUR_ADDR = 0x60;
constexpr uint8_t NEW_ADDR = 0x67;

// I2C bit-bang timing.  25 kHz -- generous margin for weak/mixed pull-ups.
constexpr int I2C_HALF_US = 20;

inline void scl_high() { digitalWrite(SCL_PIN, HIGH); }
inline void scl_low()  { digitalWrite(SCL_PIN, LOW);  }
inline void sda_high() { digitalWrite(SDA_PIN, HIGH); }
inline void sda_low()  { digitalWrite(SDA_PIN, LOW);  }
inline int  sda_read() { return digitalRead(SDA_PIN); }

void i2c_init() {
    pinMode(SDA_PIN, OUTPUT);
    pinMode(SCL_PIN, OUTPUT);
    sda_high();
    scl_high();
    delayMicroseconds(50);
}

void i2c_start() {
    sda_high(); scl_high(); delayMicroseconds(I2C_HALF_US);
    sda_low();              delayMicroseconds(I2C_HALF_US);
    scl_low();
}

void i2c_stop() {
    scl_low(); sda_low(); delayMicroseconds(I2C_HALF_US);
    scl_high();           delayMicroseconds(I2C_HALF_US);
    sda_high();           delayMicroseconds(I2C_HALF_US);
}

// Standard 8-bit write with ACK read.  LDAC not touched.
bool i2c_write_byte(uint8_t b) {
    for (uint8_t m = 0x80; m != 0; m >>= 1) {
        if (m & b) sda_high(); else sda_low();
        scl_high();
        delayMicroseconds(I2C_HALF_US);
        scl_low();
        delayMicroseconds(I2C_HALF_US);
    }
    // ACK bit
    sda_high();
    pinMode(SDA_PIN, INPUT_PULLUP);
    scl_high();
    delayMicroseconds(I2C_HALF_US);
    const int nack = sda_read();
    scl_low();
    delayMicroseconds(I2C_HALF_US);
    pinMode(SDA_PIN, OUTPUT);
    sda_high();
    return nack == 0;
}

// Same as i2c_write_byte, but drops LDAC LOW during the SCL-LOW window of
// the ACK bit -- exactly the DS22187 §5.6.8 "at the low time of the last
// bit (8th clock)" trigger event.  Used on BYTE 2 of the reprogram
// sequence to arm the chip's "Write I2C Address" command decoder.
bool i2c_ldac_write_byte(uint8_t b) {
    for (uint8_t m = 0x80; m != 0; m >>= 1) {
        if (m & b) sda_high(); else sda_low();
        scl_high();
        delayMicroseconds(I2C_HALF_US);
        scl_low();
        delayMicroseconds(I2C_HALF_US);
    }
    // ACK bit -- LDAC drop happens HERE, while SCL is still LOW after the
    // 8th data bit and before we raise SCL for the ACK bit.
    digitalWrite(LDAC_PIN, LOW);
    sda_high();
    pinMode(SDA_PIN, INPUT_PULLUP);
    scl_high();
    delayMicroseconds(I2C_HALF_US);
    const int nack = sda_read();
    scl_low();
    delayMicroseconds(I2C_HALF_US);
    pinMode(SDA_PIN, OUTPUT);
    sda_high();
    return nack == 0;
}

bool i2c_probe(uint8_t addr) {
    i2c_start();
    const bool ack = i2c_write_byte((uint8_t)((addr << 1) | 0));
    i2c_stop();
    return ack;
}

void setup() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    delay(2000);

    Serial.println();
    Serial.println("=== MCP4728 address reprogram (bit-bang, jknipper encoding) ===");
    Serial.printf(" cur addr: 0x%02X    new addr: 0x%02X\n", CUR_ADDR, NEW_ADDR);
    Serial.printf(" SDA=GPIO%d  SCL=GPIO%d  LDAC=GPIO%d\n",
                  SDA_PIN, SCL_PIN, LDAC_PIN);
    Serial.println();

    pinMode(LDAC_PIN, OUTPUT);
    digitalWrite(LDAC_PIN, HIGH);        // LDAC HIGH before anything
    i2c_init();
    delay(10);

    if (i2c_probe(NEW_ADDR)) {
        Serial.println("INFO: 0x67 already ACKs -- chip already reprogrammed.");
        Serial.println("Nothing to do.  Reflash bringup.bat next.");
        while (true) delay(1000);
    }

    if (!i2c_probe(CUR_ADDR)) {
        Serial.println("FAIL: no chip at 0x60.");
        Serial.println("  Check STEMMA QT cable + 3.3V supply.");
        while (true) delay(1000);
    }
    Serial.println("Found chip at 0x60.");

    // JKnipper encoding: address bits shifted LEFT by 2 (bits [4:2]),
    // role code in bits [1:0]:  01=byte2, 10=byte3, 11=byte4.
    const uint8_t cur_bits = CUR_ADDR & 0x07;
    const uint8_t new_bits = NEW_ADDR & 0x07;
    const uint8_t b2 = 0x61 | (cur_bits << 2);   // byte 2, "arm with current"
    const uint8_t b3 = 0x62 | (new_bits << 2);   // byte 3, "new addr"
    const uint8_t b4 = 0x63 | (new_bits << 2);   // byte 4, "confirm new"
    Serial.printf("Sending bytes (after 0x%02X addr): %02X %02X %02X\n",
                  (CUR_ADDR << 1), b2, b3, b4);

    // LDAC starts HIGH (already set above).  Transaction:
    //   START -> addr byte -> byte2 (LDAC drops during ACK) -> byte3 -> byte4 -> STOP
    // LDAC stays LOW from byte-2 ACK all the way through STOP.
    digitalWrite(LDAC_PIN, HIGH);
    delayMicroseconds(10);

    i2c_start();
    const bool ack_addr = i2c_write_byte((uint8_t)((CUR_ADDR << 1) | 0));
    const bool ack_b2   = i2c_ldac_write_byte(b2);   // LDAC drops during THIS byte's ACK
    const bool ack_b3   = i2c_write_byte(b3);
    const bool ack_b4   = i2c_write_byte(b4);
    i2c_stop();

    // Hold LDAC LOW through the EEPROM burn window, then release.
    delay(100);
    digitalWrite(LDAC_PIN, HIGH);

    Serial.printf("ACKs -- addr:%d b2:%d b3:%d b4:%d\n",
                  (int)ack_addr, (int)ack_b2, (int)ack_b3, (int)ack_b4);

    // Verify
    delay(50);
    const bool at_new = i2c_probe(NEW_ADDR);
    const bool at_old = i2c_probe(CUR_ADDR);

    Serial.println();
    Serial.println("=================================================");
    if (at_new && !at_old) {
        Serial.printf(" SUCCESS: MCP4728 now responds at 0x%02X (0x%02X silent)\n",
                      NEW_ADDR, CUR_ADDR);
        Serial.println(" Reflash bringup.bat to return to normal.");
    } else if (at_old && !at_new) {
        Serial.printf(" FAIL: chip still at 0x%02X\n", CUR_ADDR);
    } else if (at_new && at_old) {
        Serial.println(" WEIRD: both addresses ACK -- bus glitch?");
    } else {
        Serial.println(" WEIRD: neither address ACKs after reprogram.");
    }
    Serial.println("=================================================");
}

void loop() { /* one-shot */ }

// =============================================================================
//  reprogram_mcp4728.ino
//
//  One-shot Arduino sketch to reprogram the MCP4728's I2C EEPROM address
//  from factory 0x60 to target 0x67, using Adafruit's known-working
//  MCP4728 library.  Flash this onto the Adafruit Metro ESP32-S3, watch
//  the serial monitor for "SUCCESS: chip now at 0x67", then reflash the
//  normal ESP-IDF bring-up (firmware/bringup.bat).
//
//  We fell back to this after every ESP-IDF variant we tried (new
//  i2c_master driver, bit-bang, legacy i2c driver) failed to make the
//  MCP4728 accept the "Write I2C Address" command.  The Adafruit Arduino
//  library uses the same underlying I2C hardware but via a driver stack
//  that empirically works on Adafruit-supplied breakouts.
//
//  BENCH SETUP:
//    * Metro on USB (COM11 per project memory)
//    * MCP4728 breakout on STEMMA QT to Metro
//    * MCP4728 LDAC pin wired to Metro D7 (GPIO 7)
//    * Nothing else on the I2C bus recommended (avoid Si5351 collision)
//
//  ARDUINO IDE SETUP (one-time):
//    1. File -> Preferences -> Additional boards manager URLs, add:
//       https://espressif.github.io/arduino-esp32/package_esp32_index.json
//    2. Tools -> Board -> Boards Manager, search "esp32", install
//       "esp32 by Espressif Systems" (any 3.x version).
//    3. Tools -> Board -> ESP32 Arduino -> "Adafruit Metro ESP32-S3".
//    4. Tools -> Manage Libraries, search "Adafruit MCP4728", install
//       the Adafruit_MCP4728 library (pulls Adafruit_BusIO as dependency).
//    5. Open this sketch, Tools -> Port -> COM11.
//    6. Upload (arrow icon).  Open serial monitor at 115200 baud.
// =============================================================================

#include <Wire.h>
#include <Adafruit_MCP4728.h>

// Adafruit Metro ESP32-S3 STEMMA QT / on-header I2C pins
constexpr int I2C_SDA = 47;
constexpr int I2C_SCL = 48;

// MCP4728 LDAC control -- MUST be wired from Metro D7 to breakout LDAC pin
constexpr int LDAC_PIN = 7;

constexpr uint8_t CUR_ADDR = 0x60;   // factory default
constexpr uint8_t NEW_ADDR = 0x67;   // xmitter project target

Adafruit_MCP4728 mcp;

void setup() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    delay(2000);

    Serial.println();
    Serial.println("=== MCP4728 address reprogram (Arduino / Adafruit lib) ===");
    Serial.printf(" cur addr: 0x%02X    new addr: 0x%02X    LDAC: GPIO %d\n",
                  CUR_ADDR, NEW_ADDR, LDAC_PIN);

    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);

    pinMode(LDAC_PIN, OUTPUT);
    digitalWrite(LDAC_PIN, HIGH);
    delay(10);

    // First check if chip is already reprogrammed.
    Wire.beginTransmission(NEW_ADDR);
    if (Wire.endTransmission() == 0) {
        Serial.println("INFO: 0x67 already ACKs -- chip already reprogrammed.");
        Serial.println("Nothing to do.  Reflash bringup.bat next.");
        while (true) delay(1000);
    }

    // Confirm chip is at factory 0x60.
    if (!mcp.begin(CUR_ADDR, &Wire)) {
        Serial.println("FAIL: no MCP4728 found at 0x60");
        Serial.println("      check STEMMA QT cable + 5V/3.3V supply");
        while (true) delay(1000);
    }
    Serial.println("Found MCP4728 at 0x60.");

    // Adafruit's setAddress() does the LDAC toggle timing internally.  We
    // just have to tell it which GPIO LDAC is wired to and what the new
    // address should be.
    Serial.println("Calling mcp.setAddress()...");
    bool ok = mcp.setAddress(NEW_ADDR, LDAC_PIN);
    Serial.printf("setAddress returned: %s\n", ok ? "true (success)" : "false (fail)");

    delay(100);

    // Verify the new address answers.
    Wire.beginTransmission(NEW_ADDR);
    uint8_t verify_err = Wire.endTransmission();
    if (verify_err == 0) {
        Serial.println();
        Serial.println("=================================================");
        Serial.printf(" SUCCESS: MCP4728 now responds at 0x%02X\n", NEW_ADDR);
        Serial.println(" You can now reflash bringup.bat.");
        Serial.println("=================================================");
    } else {
        Serial.println();
        Serial.printf(" FAIL: 0x%02X did not ACK after reprogram (err %d)\n",
                      NEW_ADDR, verify_err);
        Serial.println(" LDAC wire connection?  D7 -> LDAC breakout pin?");
    }
}

void loop() {
    // Nothing -- this sketch is one-shot.  Reset the board to run again.
}

idf_component_register(
    SRCS
        "main.cpp"
        "main_lcd_bringup.cpp"
        "vfo_si5351.cpp"
        "keyer_envelope.cpp"
        "keyer_winkey.cpp"
        "grid_bias_dac.cpp"
        "cathode_monitor.cpp"
        "fault_handler.cpp"
        "front_panel.cpp"
        "encoders.cpp"
        "power_supply.cpp"
        "console_shell.cpp"
        "i2c_scan.cpp"
        "mcp4728.cpp"
        "vfo_knob.cpp"
        "pcf8575.cpp"
        "lcd_hd44780.cpp"
        "display.cpp"
    INCLUDE_DIRS "."
    REQUIRES
        driver
        esp_timer
        esp_driver_i2c
        esp_driver_spi
        esp_driver_gpio
        esp_driver_pcnt
        nvs_flash
        console
        vfs
)

# Project-wide compile options: C++17, warnings up.
target_compile_options(${COMPONENT_LIB} PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:-std=gnu++17>
    -Wall
    -Wextra
    -Wno-unused-parameter
)

# LCD_BRINGUP swaps app_main() from main.cpp (full transmitter boot) to
# main_lcd_bringup.cpp (front-panel LCD-only bench test).  Build with:
#     idf.py -DLCD_BRINGUP=ON build flash monitor
# Leave it off (default) for the normal firmware.
option(LCD_BRINGUP "Build the front-panel LCD bring-up test entry point" OFF)
if(LCD_BRINGUP)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE LCD_BRINGUP=1)
endif()

# LDAC_SCOPE_ONLY skips the normal bring-up and just toggles the MCP4728
# LDAC line (GPIO 7) at 100 Hz forever, so a scope on the breakout's LDAC
# pin can confirm the D7 -> LDAC jumper is intact.  Requires LCD_BRINGUP.
#     idf.py -DLCD_BRINGUP=ON -DLDAC_SCOPE_ONLY=ON build flash monitor
option(LDAC_SCOPE_ONLY "LDAC continuity diagnostic (no MCP4728/Si5351 init)" OFF)
if(LDAC_SCOPE_ONLY)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE LDAC_SCOPE_ONLY=1)
endif()

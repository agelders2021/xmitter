# --------------------------------------------------------------------------
# REPROGRAM_ONLY is a completely-isolated build.  It compiles ONE source
# file (main_reprogram_only.cpp) and nothing else -- no new i2c_master.h
# users anywhere in the link, no chance of the two I2C driver stacks
# colliding.
#
#     idf.py -DREPROGRAM_ONLY=ON build flash monitor
#
# LCD_BRINGUP swaps to the front-panel bring-up entry point:
#     idf.py -DLCD_BRINGUP=ON build flash monitor
#
# LDAC_SCOPE_ONLY replaces the LCD bring-up app_main with a diagnostic
# that toggles GPIO 7 at 100 Hz forever.  Requires LCD_BRINGUP.
#     idf.py -DLCD_BRINGUP=ON -DLDAC_SCOPE_ONLY=ON build flash monitor
# --------------------------------------------------------------------------

option(LCD_BRINGUP        "Build the front-panel LCD bring-up test entry point" OFF)
option(LDAC_SCOPE_ONLY    "LDAC continuity diagnostic (no MCP4728/Si5351 init)" OFF)
option(REPROGRAM_ONLY     "Isolated legacy-driver MCP4728 reprogram build"      OFF)

if(REPROGRAM_ONLY)
    # Absolute minimum: just the one file.  Nothing else compiles or links,
    # so no i2c_master.h can possibly interfere with the legacy driver.
    set(app_srcs "main_reprogram_only.cpp")
else()
    set(app_srcs
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
    )
endif()

idf_component_register(
    SRCS
        ${app_srcs}
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

if(LCD_BRINGUP)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE LCD_BRINGUP=1)
endif()
if(LDAC_SCOPE_ONLY)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE LDAC_SCOPE_ONLY=1)
endif()
if(REPROGRAM_ONLY)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE REPROGRAM_ONLY=1)
endif()

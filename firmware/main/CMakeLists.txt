idf_component_register(
    SRCS
        "main.cpp"
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

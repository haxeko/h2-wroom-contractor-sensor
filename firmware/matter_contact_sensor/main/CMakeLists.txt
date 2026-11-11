idf_component_register(
    SRCS
        "app_main.cpp"
        "matter_endpoint.cpp"
        "sensor/hall_sensor.cpp"
        "power/power_manager.cpp"
        "power/uncommissioned_sleep.cpp"
        "button/button.cpp"
        "battery/battery_monitor.cpp"
        "led/status_led.cpp"
    INCLUDE_DIRS
        "."
    PRIV_REQUIRES
        esp_matter
        esp_driver_gpio
        esp_adc
        esp_pm
        esp_timer
        nvs_flash
        openthread
        ieee802154
)

# Same as the official esp-matter examples: CHIP headers need CHIP_HAVE_CONFIG_H
target_compile_options(${COMPONENT_LIB} PRIVATE "-DCHIP_HAVE_CONFIG_H")

# The 802.15.4 driver starts at +20 dBm (~140 mA): apply CONFIG_CS_THREAD_TX_POWER_DBM right after it
# initialises (power/power_manager.cpp), before OpenThread can send its first frame
target_link_libraries(${COMPONENT_LIB} INTERFACE "-Wl,--wrap=esp_ieee802154_enable")

/*
 * Power management for the battery powered Matter contact sensor (ESP32-H2).
 *
 *  - Automatic light sleep (esp_pm + FreeRTOS tickless idle). The Thread stack (OpenThread
 *    Sleepy End Device / Matter ICD) keeps its attachment to the parent while the chip is in
 *    light sleep; Deep-sleep is NOT used because it would drop the Thread/Matter state.
 *  - GPIO wake-up helpers. With CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP (TOP domain off,
 *    ~25 uA instead of ~85 uA in the datasheet) only LP IOs (GPIO7..14) can wake the chip,
 *    through EXT1 with a per-pin level.
 *  - 802.15.4 TX power (ESP-IDF default = maximum, 20 dBm).
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "esp_pm.h"
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Configure esp_pm (light sleep on) and park the unused GPIOs. Call first in app_main(). */
esp_err_t power_manager_init(void);

/** Install the shared GPIO ISR service (idempotent). */
esp_err_t power_manager_install_gpio_isr_service(void);

/**
 * Configure @p pin as a sleep wake-up capable input.
 * Validates that the pin can wake the chip with the selected sleep configuration and keeps
 * its pad configuration (input enable / pull) during sleep.
 */
esp_err_t power_manager_register_wakeup_gpio(gpio_num_t pin, bool pullup);

/**
 * (Re)arm the LEVEL wake-up and the LEVEL GPIO interrupt of @p pin on @p wake_level.
 * Also re-enables the GPIO interrupt (the ISRs disable it to avoid an interrupt storm).
 */
esp_err_t power_manager_arm_wakeup_gpio(gpio_num_t pin, int wake_level);

/**
 * Remove @p pin from the wake-up sources and mask its interrupt. Call it from the task that
 * handles the event (not from the ISR) before debouncing/polling: otherwise the level that just
 * woke the chip would keep waking it immediately from every light-sleep attempt.
 */
esp_err_t power_manager_disarm_wakeup_gpio(gpio_num_t pin);

/**
 * Set the same 802.15.4 TX power on all 16 channels (call after the Thread stack is up and after
 * every re-attach). The very first frames are covered by a linker wrap of esp_ieee802154_enable()
 * that applies CONFIG_CS_THREAD_TX_POWER_DBM as soon as the driver is initialised.
 */
esp_err_t power_manager_set_thread_tx_power(int8_t dbm);

/**
 * Weak-battery guard, call early in app_main() (before the radio starts).
 * @p loaded_mv is the battery voltage measured now, with the CPU running (0 = unknown; readings
 * below 1.5 V are treated as "no battery divider", e.g. on a development kit).
 * If the cell is too weak to start the radio (voltage below CONFIG_CS_BOOT_MIN_MV, or
 * CONFIG_CS_BROWNOUT_LIMIT brownout resets in a row) the chip goes to Deep-sleep for
 * CONFIG_CS_RECOVERY_SLEEP_S instead of resetting in a loop; the button wakes it earlier.
 */
void power_manager_boot_guard(uint32_t loaded_mv);

/**
 * Deep-sleep (~7 uA) until the button is pressed, or @p wake_after_s seconds have passed
 * (0 = button only). Every other wake-up source (Hall input) is disabled. Does not return:
 * the wake-up is a normal boot.
 */
void power_manager_deep_sleep(uint32_t wake_after_s) __attribute__((noreturn));

/** Create a lock that prevents automatic light sleep while held (ADC, LED patterns...). */
esp_pm_lock_handle_t power_manager_create_no_sleep_lock(const char *name);

/** Debug helper: print PM lock statistics (needs CONFIG_PM_PROFILING for timings). */
void power_manager_dump(void);

#ifdef __cplusplus
}
#endif

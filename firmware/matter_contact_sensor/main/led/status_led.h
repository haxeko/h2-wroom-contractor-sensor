/*
 * Status LED (single low-current red LED, ~1.3 mA when on).
 *
 * Normal operation: LED completely OFF (0 uA). It is only used for:
 *   - commissioning window open : 30 ms flash every 2 s ("base" pattern)
 *   - Identify (Matter)         : 0.5 s on / 0.5 s off
 *   - factory reset warning     : 5 Hz blink, then solid ON when release = reset
 *   - optional event flash      : one CONFIG_CS_LED_FLASH_MS flash per OPEN/CLOSED change
 *
 * The pin level is latched with gpio_hold_en() so that the LED keeps its state while the
 * chip is in light sleep (no PM lock needed -> no CPU current while the LED is lit).
 */
#pragma once

#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LED_PATTERN_NONE = 0,       /* overlay: none -> show the base pattern */
    LED_PATTERN_FLASH_ONCE,     /* one short flash */
    LED_PATTERN_IDENTIFY,       /* until status_led_show(LED_PATTERN_NONE) */
    LED_PATTERN_RESET_WARNING,  /* until replaced */
    LED_PATTERN_RESET_ARMED,    /* solid ON until replaced */
    LED_PATTERN_ERROR,          /* 3 quick flashes */
} led_pattern_t;

esp_err_t status_led_init(void);

/** Base pattern: commissioning window open (true) or off (false). */
void status_led_set_commissioning(bool on);

/** Temporary overlay pattern; LED_PATTERN_NONE returns to the base pattern. */
void status_led_show(led_pattern_t pattern);

#ifdef __cplusplus
}
#endif

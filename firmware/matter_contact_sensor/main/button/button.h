/*
 * Single push-button (commissioning / identify / factory reset).
 *
 *   short press  (< CONFIG_CS_BUTTON_LONG_PRESS_MS)        -> BUTTON_EVT_SHORT_PRESS
 *   hold >= CONFIG_CS_BUTTON_LONG_PRESS_MS                 -> BUTTON_EVT_RESET_WARNING (LED fast blink)
 *   hold >= CONFIG_CS_BUTTON_FACTORY_RESET_MS              -> BUTTON_EVT_RESET_ARMED  (release now)
 *   release after RESET_ARMED                              -> BUTTON_EVT_FACTORY_RESET
 *   release between LONG_PRESS and FACTORY_RESET           -> BUTTON_EVT_RESET_CANCELLED
 *
 * The factory reset is executed on RELEASE: GPIO9 is the BOOT strapping pin and a chip reset
 * while it is still LOW would enter the ROM download mode instead of the application.
 */
#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    BUTTON_EVT_SHORT_PRESS,
    BUTTON_EVT_RESET_WARNING,
    BUTTON_EVT_RESET_ARMED,
    BUTTON_EVT_RESET_CANCELLED,
    BUTTON_EVT_FACTORY_RESET,
} button_event_t;

typedef void (*button_cb_t)(button_event_t event, void *ctx);

esp_err_t button_init(button_cb_t cb, void *ctx);

#ifdef __cplusplus
}
#endif

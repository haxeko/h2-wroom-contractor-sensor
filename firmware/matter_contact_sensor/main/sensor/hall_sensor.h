/*
 * Hall-effect contact sensor driver (DRV5032FA omnipolar switch, push-pull output).
 *
 * Detection of BOTH transitions (OPEN->CLOSED and CLOSED->OPEN) while the SoC sleeps:
 *   - the Hall IC samples the field autonomously (5 Hz) and holds a LEVEL on its output;
 *   - ESP32-H2 light-sleep wake-up from GPIO is LEVEL triggered only, therefore the driver
 *     always arms the wake-up (and the GPIO interrupt) on the level OPPOSITE to the level
 *     that was just read. Any change of the output wakes the chip; because arming is done
 *     from the level read *now* (not from the last reported state) the scheme is race-free:
 *     a change that happens between the read and the arming triggers immediately.
 *   - with CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP the digital GPIO block is powered
 *     off, so the wake-up is routed through EXT1 (LP IO GPIO7..14, per-pin level on H2).
 */
#pragma once

#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Called from the Hall task (NOT from an ISR) after a debounced change.
 * @param magnet_present true = magnet detected (door/window CLOSED)
 */
typedef void (*hall_sensor_cb_t)(bool magnet_present, void *ctx);

/**
 * Configure the GPIO, read the initial state, arm the wake-up and start the Hall task.
 * The callback is NOT called for the initial state; use hall_sensor_is_magnet_present().
 */
esp_err_t hall_sensor_init(hall_sensor_cb_t cb, void *ctx);

/** Last debounced state (true = magnet present = CLOSED). */
bool hall_sensor_is_magnet_present(void);

/**
 * Re-read the pin and re-arm the wake-up. Used as a periodic sanity check
 * (e.g. together with the battery measurement) - a missed edge is then reported.
 */
void hall_sensor_resync(void);

#ifdef __cplusplus
}
#endif

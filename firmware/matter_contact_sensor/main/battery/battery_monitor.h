/*
 * Li-MnO2 battery monitor (CR123A, both boards).
 *
 * Hardware: VBAT -> 1 MOhm -> ADC node (GPIO1, 10 nF to GND) -> 1 MOhm -> VBAT_EN (GPIO22).
 * VBAT_EN is high impedance between measurements, so the divider draws 0 uA (only pad
 * leakage, <= 50 nA max per datasheet). During a measurement VBAT_EN is driven LOW for
 * CONFIG_CS_VBAT_SETTLE_MS + 8 ADC conversions (1.5 uA for ~50 ms every 12 h).
 *
 * The battery is measured on the INPUT of the buck-boost converter: the 3V2 rail is regulated
 * and says nothing about the remaining capacity.
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    BATTERY_LEVEL_OK = 0,        /* == Matter PowerSource BatChargeLevelEnum::kOk */
    BATTERY_LEVEL_WARNING = 1,   /* == kWarning */
    BATTERY_LEVEL_CRITICAL = 2,  /* == kCritical */
} battery_level_t;

typedef struct {
    uint32_t voltage_mv;      /* battery voltage (unloaded) */
    uint8_t percent_x2;       /* Matter BatPercentRemaining: 0..200 (0.5 % units) */
    battery_level_t level;
    bool replacement_needed;
} battery_status_t;

typedef void (*battery_cb_t)(const battery_status_t *status, void *ctx);

/** Start the monitor task; a first measurement is done immediately, then every
 *  CONFIG_CS_VBAT_PERIOD_MIN minutes. */
esp_err_t battery_monitor_init(battery_cb_t cb, void *ctx);

/**
 * Measure the battery voltage now, in the calling task (~50 ms). Usable before
 * battery_monitor_init(): the boot guard calls it with the CPU running, i.e. with the cell
 * loaded by ~15 mA, before the radio is started.
 */
esp_err_t battery_monitor_measure_now(uint32_t *out_mv);

/** Request an asynchronous measurement (e.g. after a button press). */
void battery_monitor_request(void);

/** Last result (valid after the first callback). */
bool battery_monitor_get_last(battery_status_t *out);

/** Percent (0..200, 0.5 % units) estimated from an unloaded Li-MnO2 voltage. */
uint8_t battery_monitor_percent_x2_from_mv(uint32_t mv);

#ifdef __cplusplus
}
#endif

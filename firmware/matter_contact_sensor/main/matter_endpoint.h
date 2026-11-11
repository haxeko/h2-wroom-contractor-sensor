/*
 * Matter data model of the contact sensor.
 *
 *  Endpoint 0 : Root Node (+ ICD Management when CONFIG_ENABLE_ICD_SERVER, OTA Requestor)
 *  Endpoint 1 : Contact Sensor (0x0015) + Power Source (0x0011) device types
 *               clusters: Descriptor, Identify, Boolean State (StateValue + StateChange event),
 *               Power Source (features BAT + REPLC)
 *
 * Boolean State semantics for the Contact Sensor device type:
 *    StateValue = TRUE  -> contact (magnet present, door/window CLOSED)
 *    StateValue = FALSE -> no contact (OPEN)
 *
 * All setters are thread-safe: they post work to the CHIP thread (PlatformMgr().ScheduleWork).
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "battery/battery_monitor.h"

typedef void (*matter_identify_cb_t)(bool start);

/** Create the node and the endpoints. Must be called before esp_matter::start(). */
esp_err_t matter_endpoint_create(matter_identify_cb_t identify_cb);

/** Endpoint id of the contact sensor. */
uint16_t matter_endpoint_contact_id(void);

/**
 * Publish the contact state. Can be called before the Matter server is ready: the value is
 * then cached and applied by matter_endpoint_on_server_ready().
 */
void matter_endpoint_set_contact(bool closed);

/** Publish battery attributes of the Power Source cluster (BatVoltage, BatPercentRemaining...). */
void matter_endpoint_set_battery(const battery_status_t *status);

/** Called from the CHIP event callback on kServerReady (CHIP thread). */
void matter_endpoint_on_server_ready(void);

/**
 * Fallback for kServerReady: call once after esp_matter::start() returned (the server init task
 * has completed at that point). Schedules matter_endpoint_on_server_ready() on the CHIP thread;
 * calling it twice is harmless.
 */
void matter_endpoint_sync_after_start(void);

/** ICD: switch to Active mode now (fast polling) so that pending reports leave immediately. */
void matter_endpoint_request_active_mode(void);

/** true if at least one fabric is configured. */
bool matter_endpoint_is_commissioned(void);

/** Open the BLE commissioning window (only meaningful while not commissioned). */
void matter_endpoint_open_commissioning_window(uint16_t timeout_s);

/** Erase fabrics, Thread credentials and NVS, then reboot. */
void matter_endpoint_factory_reset(void);

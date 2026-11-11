/*
 * Not commissioned and no commissioning window open: Deep-sleep until the button is pressed.
 *
 * esp-matter shuts the BLE controller down only once a fabric exists. While it is initialised,
 * its low-power clock keeps the main crystal running in light sleep (no 32 kHz crystal fitted:
 * CONFIG_BT_LE_LP_CLK_SRC_MAIN_XTAL): a few mA instead of ~25 uA (ESP-IDF nimble power_save
 * README, ESP32-H2). A sensor left unpaired - on the shelf with its battery, or after it was
 * removed from the home - would empty a CR123A in about two weeks.
 *
 * Once the window has closed without a commissioning (or a commissioning failed), after a grace
 * period that lets a PASE session in progress finish, the chip goes to Deep-sleep (~7 uA).
 * A press wakes it (EXT1, external pull-up R10) into a normal boot, which opens a new window.
 */
#pragma once

#include <platform/CHIPDeviceEvent.h>

/** Forward every esp-matter device event (CHIP task). No-op unless CONFIG_CS_UNCOMMISSIONED_DEEP_SLEEP. */
void uncommissioned_sleep_on_event(const chip::DeviceLayer::ChipDeviceEvent *event);

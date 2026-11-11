/*
 * Matter over Thread contact sensor - ESP32-H2 + DRV5032FA Hall switch + CR123A
 * (bare-chip board hardware/chip, or ESP32-H2-WROOM-02C module board hardware/wroom).
 *
 * Toolchain verified with: ESP-IDF v5.5.5 + esp-matter release/v1.6.
 *
 * Threads:
 *   hall / button / battery tasks  -> post app events (never touch Matter directly)
 *   app task                       -> application logic, calls matter_endpoint_*()
 *   CHIP task (esp-matter)         -> Matter stack; app_event_cb() runs here
 *   OpenThread task                -> Thread MTD / Sleepy End Device (ICD)
 * When every task is blocked FreeRTOS tickless idle lets esp_pm enter light sleep.
 */
#include <inttypes.h>
#include <string.h>

#include "sdkconfig.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nvs_flash.h"

#include <esp_matter.h>
#include <app/server/Server.h>
#include <platform/CHIPDeviceLayer.h>
#if CHIP_DEVICE_CONFIG_ENABLE_THREAD
#include <esp_openthread_types.h>
#include <platform/ESP32/OpenthreadLauncher.h>
#endif

#include "matter_endpoint.h"
#include "battery/battery_monitor.h"
#include "button/button.h"
#include "led/status_led.h"
#include "power/power_manager.h"
#include "power/uncommissioned_sleep.h"
#include "sensor/hall_sensor.h"

static const char *TAG = "app";

/* ------------------------------------------------------------------ app events */

typedef enum {
    APP_EVT_CONTACT,
    APP_EVT_BATTERY,
    APP_EVT_BUTTON,
    APP_EVT_THREAD_READY,
    APP_EVT_LAST_FABRIC_REMOVED,
} app_evt_type_t;

typedef struct {
    app_evt_type_t type;
    union {
        bool closed;
        battery_status_t battery;
        button_event_t button;
    };
} app_evt_t;

static QueueHandle_t s_app_queue;

static void post_event(const app_evt_t &evt)
{
    if (s_app_queue && xQueueSend(s_app_queue, &evt, 0) != pdTRUE) {
        ESP_LOGE(TAG, "app queue full, event %d dropped", (int)evt.type);
    }
}

/* ------------------------------------------------------------------ driver callbacks */

static void on_hall_change(bool magnet_present, void *ctx)
{
    app_evt_t evt = {};
    evt.type = APP_EVT_CONTACT;
    evt.closed = magnet_present;
    post_event(evt);
}

static void on_battery(const battery_status_t *status, void *ctx)
{
    app_evt_t evt = {};
    evt.type = APP_EVT_BATTERY;
    evt.battery = *status;
    post_event(evt);
}

static void on_button(button_event_t event, void *ctx)
{
    app_evt_t evt = {};
    evt.type = APP_EVT_BUTTON;
    evt.button = event;
    post_event(evt);
}

static void on_identify(bool start)
{
    status_led_show(start ? LED_PATTERN_IDENTIFY : LED_PATTERN_NONE);
}

/* ------------------------------------------------------------------ app logic */

static void handle_button(button_event_t event)
{
    switch (event) {
    case BUTTON_EVT_SHORT_PRESS:
        if (matter_endpoint_is_commissioned()) {
            /* User activity: go to ICD active mode, refresh battery, give feedback */
            matter_endpoint_request_active_mode();
            battery_monitor_request();
            hall_sensor_resync();
            status_led_show(LED_PATTERN_FLASH_ONCE);
        } else {
            ESP_LOGI(TAG, "opening BLE commissioning window (%d s)", CONFIG_CS_COMMISSIONING_WINDOW_SEC);
            matter_endpoint_open_commissioning_window(CONFIG_CS_COMMISSIONING_WINDOW_SEC);
        }
        break;
    case BUTTON_EVT_RESET_WARNING:
        status_led_show(LED_PATTERN_RESET_WARNING);
        break;
    case BUTTON_EVT_RESET_ARMED:
        status_led_show(LED_PATTERN_RESET_ARMED);
        break;
    case BUTTON_EVT_RESET_CANCELLED:
        status_led_show(LED_PATTERN_NONE);
        break;
    case BUTTON_EVT_FACTORY_RESET:
        status_led_show(LED_PATTERN_NONE);
        matter_endpoint_factory_reset();
        break;
    }
}

static void app_task(void *arg)
{
    app_evt_t evt;
    for (;;) {
        if (xQueueReceive(s_app_queue, &evt, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        switch (evt.type) {
        case APP_EVT_CONTACT:
            matter_endpoint_set_contact(evt.closed);
#if CONFIG_CS_LED_ON_CONTACT_EVENT
            status_led_show(LED_PATTERN_FLASH_ONCE);
#endif
            break;
        case APP_EVT_BATTERY:
            matter_endpoint_set_battery(&evt.battery);
            hall_sensor_resync(); /* periodic sanity check of the reported contact state */
            break;
        case APP_EVT_BUTTON:
            handle_button(evt.button);
            break;
        case APP_EVT_THREAD_READY:
            /* Needs the OpenThread lock -> done here, never from the CHIP callback */
            power_manager_set_thread_tx_power(CONFIG_CS_THREAD_TX_POWER_DBM);
            break;
        case APP_EVT_LAST_FABRIC_REMOVED:
            /* Let the RemoveFabric response and the MRP acks leave first */
            vTaskDelay(pdMS_TO_TICKS(3000));
            matter_endpoint_factory_reset();
            break;
        }
    }
}

/* ------------------------------------------------------------------ CHIP events (CHIP thread) */

static void app_event_cb(const ChipDeviceEvent *event, intptr_t arg)
{
    using namespace chip::DeviceLayer;
    uncommissioned_sleep_on_event(event);
    switch (event->Type) {
    case DeviceEventType::kServerReady:
        ESP_LOGI(TAG, "Matter server ready");
        matter_endpoint_on_server_ready();
        break;

    case DeviceEventType::kThreadConnectivityChange:
        if (event->ThreadConnectivityChange.Result == kConnectivity_Established) {
            app_evt_t evt = {};
            evt.type = APP_EVT_THREAD_READY;
            post_event(evt);
        }
        break;

    case DeviceEventType::kCommissioningWindowOpened:
        ESP_LOGI(TAG, "commissioning window opened");
        status_led_set_commissioning(true);
        break;

    case DeviceEventType::kCommissioningWindowClosed:
        ESP_LOGI(TAG, "commissioning window closed");
        status_led_set_commissioning(false);
        break;

    case DeviceEventType::kCommissioningComplete:
        ESP_LOGI(TAG, "commissioning complete (fabric index %u)",
                 static_cast<unsigned>(event->CommissioningComplete.fabricIndex));
        status_led_set_commissioning(false);
        break;

    case DeviceEventType::kBLEDeinitialized:
        ESP_LOGI(TAG, "BLE deinitialized (memory released)");
        break;

    case DeviceEventType::kFabricRemoved:
#if CONFIG_CS_FACTORY_RESET_ON_LAST_FABRIC_REMOVED
        if (chip::Server::GetInstance().GetFabricTable().FabricCount() == 0) {
            ESP_LOGW(TAG, "last fabric removed -> factory reset");
            app_evt_t evt = {};
            evt.type = APP_EVT_LAST_FABRIC_REMOVED;
            post_event(evt);
        }
#endif
        break;

    default:
        break;
    }
}

/* ------------------------------------------------------------------ entry point */

extern "C" void app_main(void)
{
    /* 1. NVS (fabrics, Thread dataset, counters) */
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS partition invalid - erasing (all pairings lost)");
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    ESP_LOGI(TAG, "reset reason %d", (int)esp_reset_reason());

    /* 2. Power management first: light sleep + parking of unused pins */
    ESP_ERROR_CHECK(power_manager_init());

    /* 2b. Weak-battery guard before anything starts the radio: the cell is loaded by the running
     *     CPU right now, so this voltage shows its internal resistance. Does not return if the
     *     battery cannot carry a boot (Deep-sleep, retried after CONFIG_CS_RECOVERY_SLEEP_S). */
    uint32_t boot_mv = 0;
    if (battery_monitor_measure_now(&boot_mv) != ESP_OK) {
        boot_mv = 0;
    }
    ESP_LOGI(TAG, "battery at boot (loaded): %" PRIu32 " mV", boot_mv);
    power_manager_boot_guard(boot_mv);

    s_app_queue = xQueueCreate(16, sizeof(app_evt_t));
    if (!s_app_queue || xTaskCreate(app_task, "app", 4096, nullptr, 5, nullptr) != pdPASS) {
        ESP_LOGE(TAG, "cannot create the app task");
        abort();
    }

    /* 3. Board peripherals */
    ESP_ERROR_CHECK(status_led_init());

    /* 4. Matter data model (must exist before esp_matter::start) */
    ESP_ERROR_CHECK(matter_endpoint_create(on_identify));

    /* 5. Sensors / inputs. The initial contact state is cached and pushed to the
     *    Boolean State cluster when the Matter server is ready (kServerReady). */
    ESP_ERROR_CHECK(hall_sensor_init(on_hall_change, nullptr));
    matter_endpoint_set_contact(hall_sensor_is_magnet_present());
    ESP_ERROR_CHECK(button_init(on_button, nullptr));
    ESP_ERROR_CHECK(battery_monitor_init(on_battery, nullptr));

#if CHIP_DEVICE_CONFIG_ENABLE_THREAD
    /* 6. OpenThread: native 802.15.4 radio, no RCP host */
    esp_openthread_platform_config_t ot_config = {};
    ot_config.radio_config.radio_mode = RADIO_MODE_NATIVE;
    ot_config.host_config.host_connection_mode = HOST_CONNECTION_MODE_NONE;
    ot_config.port_config.storage_partition_name = "nvs";
    ot_config.port_config.netif_queue_size = 10;
    ot_config.port_config.task_queue_size = 10;
    set_openthread_platform_config(&ot_config);
#endif

    /* 7. Start Matter (initialises OpenThread, BLE if not commissioned, the server...).
     *    esp_matter::start() returns after the server init task has completed. */
    ESP_ERROR_CHECK(esp_matter::start(app_event_cb));
    matter_endpoint_sync_after_start(); /* in case kServerReady was missed */

    /* 8. Per-channel TX power table (the first frames are already covered by the linker wrap of
     *    esp_ieee802154_enable(), see power_manager.cpp) */
    app_evt_t evt = {};
    evt.type = APP_EVT_THREAD_READY;
    post_event(evt);

    ESP_LOGI(TAG, "started: contact %s, commissioned %s",
             hall_sensor_is_magnet_present() ? "CLOSED" : "OPEN",
             matter_endpoint_is_commissioned() ? "yes" : "no");
}

/*
 * Deep-sleep while not commissioned - see uncommissioned_sleep.h
 * Same policy as the CR2032 Matter button firmware (verified there on ESP32-H2-WROOM-02C).
 */
#include "uncommissioned_sleep.h"

#include "sdkconfig.h"

#if CONFIG_CS_UNCOMMISSIONED_DEEP_SLEEP

#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <esp_matter.h>
#include <app/server/Server.h>
#include <lib/support/CodeUtils.h>
#include <platform/CHIPDeviceLayer.h>

#include "power_manager.h"

using namespace chip;
using namespace chip::DeviceLayer;

static const char *TAG = "unc_sleep";

static constexpr uint32_t kGraceS = CONFIG_CS_UNCOMMISSIONED_GRACE_S;
/* A PASE session was established this long ago at most: a commissioning is running even before
 * its fail-safe is armed; one that never arms it is abandoned after this */
static constexpr uint32_t kSessionStartGraceS = 300;
static System::Clock::Timestamp s_session_started = System::Clock::kZero; /* CHIP task only */

static void sleep_cb(System::Layer *, void *);

static void arm(void)
{
    SystemLayer().CancelTimer(sleep_cb, nullptr);
    LogErrorOnFailure(SystemLayer().StartTimer(System::Clock::Seconds32(kGraceS), sleep_cb, nullptr));
}

static void sleep_cb(System::Layer *, void *)
{
    Server &server = Server::GetInstance();
    if (server.GetFabricTable().FabricCount() > 0 ||
        server.GetCommissioningWindowManager().IsCommissioningWindowOpen()) {
        return; /* commissioned meanwhile, or a new window (its close arms the timer again) */
    }
    const System::Clock::Timestamp now = System::SystemClock().GetMonotonicTimestamp();
    const bool session_recent = s_session_started != System::Clock::kZero &&
                                now - s_session_started < System::Clock::Seconds32(kSessionStartGraceS);
    const bool button_down = gpio_get_level(static_cast<gpio_num_t>(CONFIG_CS_BUTTON_GPIO)) == 0;
    if (session_recent || server.GetFailSafeContext().IsFailSafeArmed() || button_down) {
        arm(); /* commissioning in progress, or the button held: look again later */
        return;
    }
    ESP_LOGW(TAG, "not commissioned, window closed: Deep-sleep, a button press opens a new window");
    vTaskDelay(pdMS_TO_TICKS(50)); /* the log line out of the UART */
    power_manager_deep_sleep(0);
}

void uncommissioned_sleep_on_event(const ChipDeviceEvent *event)
{
    switch (event->Type) {
    case DeviceEventType::kCommissioningSessionStarted: /* PASE up: the window closes, the fail-safe follows */
        s_session_started = System::SystemClock().GetMonotonicTimestamp();
        break;
    case DeviceEventType::kCommissioningSessionStopped:
    case DeviceEventType::kFailSafeTimerExpired:
        s_session_started = System::Clock::kZero;
        arm();
        break;
    case DeviceEventType::kCommissioningComplete:
        s_session_started = System::Clock::kZero;
        SystemLayer().CancelTimer(sleep_cb, nullptr);
        break;
    case DeviceEventType::kServerReady: /* in case no window opens at boot (BLE init failed) */
    case DeviceEventType::kCommissioningWindowClosed:
        if (Server::GetInstance().GetFabricTable().FabricCount() == 0) {
            arm();
        }
        break;
    default:
        break;
    }
}

#else /* !CONFIG_CS_UNCOMMISSIONED_DEEP_SLEEP */

void uncommissioned_sleep_on_event(const chip::DeviceLayer::ChipDeviceEvent *event)
{
    (void)event;
}

#endif

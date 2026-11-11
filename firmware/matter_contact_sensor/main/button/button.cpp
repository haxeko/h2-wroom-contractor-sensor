/*
 * Push-button driver - see button.h
 *
 * Idle: LOW-level wake-up (EXT1 on LP IO) + LOW-level interrupt -> zero CPU activity.
 * Pressed: the task polls the pin every kPollMs to time the press (the chip can still
 * light-sleep between polls), then re-arms the LOW-level wake-up after the release.
 */
#include "button.h"

#include <inttypes.h>
#include "sdkconfig.h"
#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "power/power_manager.h"

static const char *TAG = "button";

static constexpr gpio_num_t kPin = static_cast<gpio_num_t>(CONFIG_CS_BUTTON_GPIO);
static constexpr int kPressedLevel = 0;      /* active LOW, external 100 k pull-up */
static constexpr uint32_t kPollMs = 50;
static constexpr uint32_t kDebounceMs = 50;  /* minimum press length */
static constexpr uint32_t kLongMs = CONFIG_CS_BUTTON_LONG_PRESS_MS;
static constexpr uint32_t kResetMs = CONFIG_CS_BUTTON_FACTORY_RESET_MS;

static_assert(kResetMs > kLongMs, "factory reset time must be longer than the long press time");
#if CONFIG_CS_BUTTON_INTERNAL_PULLUP   /* bool Kconfig symbols set to 'n' are not defined */
static constexpr bool kPullup = true;
#else
static constexpr bool kPullup = false;
#endif

static TaskHandle_t s_task;
static button_cb_t s_cb;
static void *s_cb_ctx;

static void IRAM_ATTR button_isr(void *arg)
{
    gpio_intr_disable(kPin);
    BaseType_t higher_prio_woken = pdFALSE;
    vTaskNotifyGiveFromISR(s_task, &higher_prio_woken);
    if (higher_prio_woken) {
        portYIELD_FROM_ISR();
    }
}

static void emit(button_event_t evt)
{
    if (s_cb) {
        s_cb(evt, s_cb_ctx);
    }
}

static void handle_press(void)
{
    uint32_t held_ms = 0;
    bool warned = false;
    bool armed = false;

    while (gpio_get_level(kPin) == kPressedLevel) {
        vTaskDelay(pdMS_TO_TICKS(kPollMs));
        held_ms += kPollMs;
        if (!warned && held_ms >= kLongMs) {
            warned = true;
            ESP_LOGW(TAG, "held %" PRIu32 " ms: factory reset warning", held_ms);
            emit(BUTTON_EVT_RESET_WARNING);
        }
        if (!armed && held_ms >= kResetMs) {
            armed = true;
            ESP_LOGW(TAG, "held %" PRIu32 " ms: release to factory reset", held_ms);
            emit(BUTTON_EVT_RESET_ARMED);
        }
    }

    if (armed) {
        emit(BUTTON_EVT_FACTORY_RESET);
    } else if (warned) {
        emit(BUTTON_EVT_RESET_CANCELLED);
    } else if (held_ms >= kDebounceMs) {
        emit(BUTTON_EVT_SHORT_PRESS);
    } /* else: glitch shorter than kDebounceMs - ignored */
}

static void button_task(void *arg)
{
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        /* While the button is held LOW, a LOW-level wake-up would abort every light sleep:
         * disarm it during the press, poll the pin, re-arm after the release. */
        power_manager_disarm_wakeup_gpio(kPin);
        handle_press();
        /* Pin is released (HIGH) now -> wait for the next press */
        esp_err_t err = power_manager_arm_wakeup_gpio(kPin, kPressedLevel);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "re-arm failed: %s", esp_err_to_name(err));
        }
    }
}

esp_err_t button_init(button_cb_t cb, void *ctx)
{
    s_cb = cb;
    s_cb_ctx = ctx;

    ESP_RETURN_ON_ERROR(power_manager_register_wakeup_gpio(kPin, kPullup), TAG, "pin");
    ESP_RETURN_ON_ERROR(power_manager_install_gpio_isr_service(), TAG, "isr service");

    BaseType_t ok = xTaskCreate(button_task, "button", 3072, nullptr, 5, &s_task);
    ESP_RETURN_ON_FALSE(ok == pdPASS, ESP_ERR_NO_MEM, TAG, "task");

    ESP_RETURN_ON_ERROR(gpio_isr_handler_add(kPin, button_isr, nullptr), TAG, "isr add");
    /* If the button is already pressed at boot the LOW-level interrupt fires immediately. */
    return power_manager_arm_wakeup_gpio(kPin, kPressedLevel);
}

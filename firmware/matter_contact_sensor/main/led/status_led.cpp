/*
 * Status LED - see status_led.h
 * One esp_timer drives a small state machine; esp_timer alarms wake the chip from
 * automatic light sleep, so blinking does not require keeping the CPU awake.
 */
#include "status_led.h"

#include "sdkconfig.h"
#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "led";

#if CONFIG_CS_LED_GPIO >= 0

static constexpr gpio_num_t kPin = static_cast<gpio_num_t>(CONFIG_CS_LED_GPIO);
static constexpr int kOnLevel = CONFIG_CS_LED_ACTIVE_LEVEL;
static constexpr uint32_t kFlashMs = CONFIG_CS_LED_FLASH_MS;
static constexpr uint32_t kCommissioningPeriodMs = 2000;

static esp_timer_handle_t s_timer;
static SemaphoreHandle_t s_mutex;
static bool s_commissioning;              /* base pattern */
static led_pattern_t s_overlay = LED_PATTERN_NONE;
static uint32_t s_step;

static void led_write(bool on)
{
    gpio_hold_dis(kPin);
    gpio_set_level(kPin, on ? kOnLevel : !kOnLevel);
    gpio_hold_en(kPin); /* keep the level during light sleep */
}

static void schedule_ms(uint32_t ms)
{
    esp_timer_stop(s_timer); /* ESP_ERR_INVALID_STATE if not running - harmless */
    esp_timer_start_once(s_timer, (uint64_t)ms * 1000ULL);
}

/* Must be called with s_mutex held */
static void run_step(void)
{
    const uint32_t step = s_step++;
    switch (s_overlay) {
    case LED_PATTERN_FLASH_ONCE:
        if (step == 0) {
            led_write(true);
            schedule_ms(kFlashMs);
            return;
        }
        s_overlay = LED_PATTERN_NONE;
        break; /* fall back to the base pattern below */

    case LED_PATTERN_ERROR:
        if (step < 6) {
            led_write((step % 2) == 0);
            schedule_ms((step % 2) == 0 ? 100 : 150);
            return;
        }
        s_overlay = LED_PATTERN_NONE;
        break;

    case LED_PATTERN_IDENTIFY:
        led_write((step % 2) == 0);
        schedule_ms(500);
        return;

    case LED_PATTERN_RESET_WARNING:
        led_write((step % 2) == 0);
        schedule_ms(100);
        return;

    case LED_PATTERN_RESET_ARMED:
        esp_timer_stop(s_timer);
        led_write(true);
        return;

    case LED_PATTERN_NONE:
    default:
        break;
    }

    /* Base pattern */
    if (s_commissioning) {
        const bool on = (step % 2) == 0;
        led_write(on);
        schedule_ms(on ? kFlashMs : kCommissioningPeriodMs - kFlashMs);
    } else {
        esp_timer_stop(s_timer);
        led_write(false);
    }
}

static void timer_cb(void *arg)
{
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    run_step();
    xSemaphoreGive(s_mutex);
}

esp_err_t status_led_init(void)
{
    gpio_config_t io = {};
    io.pin_bit_mask = 1ULL << kPin;
    io.mode = GPIO_MODE_OUTPUT;
    io.pull_up_en = GPIO_PULLUP_DISABLE;
    io.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io.intr_type = GPIO_INTR_DISABLE;
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio_config");

    s_mutex = xSemaphoreCreateMutex();
    ESP_RETURN_ON_FALSE(s_mutex, ESP_ERR_NO_MEM, TAG, "mutex");

    esp_timer_create_args_t args = {};
    args.callback = timer_cb;
    args.name = "led";
    ESP_RETURN_ON_ERROR(esp_timer_create(&args, &s_timer), TAG, "timer");

    led_write(false);
    return ESP_OK;
}

void status_led_set_commissioning(bool on)
{
    if (!s_mutex) {
        return;
    }
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_commissioning = on;
    if (s_overlay == LED_PATTERN_NONE) {
        s_step = 0;
        run_step();
    }
    xSemaphoreGive(s_mutex);
}

void status_led_show(led_pattern_t pattern)
{
    if (!s_mutex) {
        return;
    }
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_overlay = pattern;
    s_step = 0;
    run_step();
    xSemaphoreGive(s_mutex);
}

#else /* no LED fitted */

esp_err_t status_led_init(void)
{
    ESP_LOGI(TAG, "no status LED configured");
    return ESP_OK;
}
void status_led_set_commissioning(bool on) {}
void status_led_show(led_pattern_t pattern) {}

#endif

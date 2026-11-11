/*
 * Hall-effect contact sensor driver - see hall_sensor.h for the wake-up strategy.
 *
 * Sequence on a door movement (MCU in light sleep):
 *   1. DRV5032FA samples the field (every ~50 ms, 20 Hz) and changes its output level.
 *   2. EXT1 (LP IO) wakes the ESP32-H2; the level GPIO interrupt fires -> ISR disables the
 *      interrupt (level interrupts would otherwise re-fire) and notifies the Hall task.
 *   3. The task confirms the level over CONFIG_CS_HALL_DEBOUNCE_MS (the task sleeps in
 *      vTaskDelay, so the chip can light-sleep during the debounce window).
 *   4. If the confirmed state differs from the last reported one -> callback (Matter update).
 *   5. Wake-up + interrupt are re-armed on the level opposite to the level read in step 3.
 */
#include "hall_sensor.h"

#include <inttypes.h>
#include "sdkconfig.h"
#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "power/power_manager.h"

static const char *TAG = "hall";

static constexpr gpio_num_t kPin = static_cast<gpio_num_t>(CONFIG_CS_HALL_GPIO);
static constexpr int kActiveLevel = CONFIG_CS_HALL_ACTIVE_LEVEL;
static constexpr uint32_t kDebounceMs = CONFIG_CS_HALL_DEBOUNCE_MS;
static constexpr int kMaxDebounceRounds = 10; /* door vibrating close to the threshold */
#if CONFIG_CS_HALL_PULLUP   /* bool Kconfig symbols set to 'n' are not defined at all */
static constexpr bool kPullup = true;
#else
static constexpr bool kPullup = false;
#endif

static TaskHandle_t s_task;
static hall_sensor_cb_t s_cb;
static void *s_cb_ctx;
static volatile bool s_magnet_present;

static void IRAM_ATTR hall_isr(void *arg)
{
    /* Level interrupt: mask it until the task has re-armed it on the opposite level */
    gpio_intr_disable(kPin);
    BaseType_t higher_prio_woken = pdFALSE;
    vTaskNotifyGiveFromISR(s_task, &higher_prio_woken);
    if (higher_prio_woken) {
        portYIELD_FROM_ISR();
    }
}

static inline bool level_to_present(int level)
{
    return level == kActiveLevel;
}

/* Wait until the pin keeps the same level for kDebounceMs and return that level. */
static int read_confirmed_level(void)
{
    int level = gpio_get_level(kPin);
    for (int round = 0; round < kMaxDebounceRounds; round++) {
        vTaskDelay(pdMS_TO_TICKS(kDebounceMs));
        const int again = gpio_get_level(kPin);
        if (again == level) {
            return level;
        }
        level = again; /* still moving - restart the window */
    }
    ESP_LOGW(TAG, "level not stable after %d windows, using %d", kMaxDebounceRounds, level);
    return level;
}

static void process_level(int level)
{
    const bool present = level_to_present(level);
    if (present != s_magnet_present) {
        s_magnet_present = present;
        ESP_LOGI(TAG, "%s (level %d)", present ? "CLOSED - magnet present" : "OPEN - magnet absent", level);
        if (s_cb) {
            s_cb(present, s_cb_ctx);
        }
    }
    /* Race-free re-arm: wake on the level opposite to what we just read. */
    esp_err_t err = power_manager_arm_wakeup_gpio(kPin, !level);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "re-arm failed: %s", esp_err_to_name(err));
    }
}

static void hall_task(void *arg)
{
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        /* The new level equals the armed wake level: disarm it so that the chip can really
         * light-sleep during the debounce window (re-armed in process_level()). */
        power_manager_disarm_wakeup_gpio(kPin);
        process_level(read_confirmed_level());
    }
}

esp_err_t hall_sensor_init(hall_sensor_cb_t cb, void *ctx)
{
    s_cb = cb;
    s_cb_ctx = ctx;

    ESP_RETURN_ON_ERROR(power_manager_register_wakeup_gpio(kPin, kPullup), TAG, "pin setup");
    ESP_RETURN_ON_ERROR(power_manager_install_gpio_isr_service(), TAG, "isr service");

    /* The DRV5032 output is valid tON (<=100 us) after power-up; the PCB powers it
     * permanently from the 3V2 rail, so the first read is already valid. */
    const int level = gpio_get_level(kPin);
    s_magnet_present = level_to_present(level);
    ESP_LOGI(TAG, "initial state: %s", s_magnet_present ? "CLOSED" : "OPEN");

    BaseType_t ok = xTaskCreate(hall_task, "hall", 3072, nullptr, 6, &s_task);
    ESP_RETURN_ON_FALSE(ok == pdPASS, ESP_ERR_NO_MEM, TAG, "task");

    ESP_RETURN_ON_ERROR(gpio_isr_handler_add(kPin, hall_isr, nullptr), TAG, "isr add");
    return power_manager_arm_wakeup_gpio(kPin, !level);
}

bool hall_sensor_is_magnet_present(void)
{
    return s_magnet_present;
}

void hall_sensor_resync(void)
{
    if (s_task) {
        /* Same path as an interrupt: debounce, report if needed, re-arm. */
        gpio_intr_disable(kPin);
        xTaskNotifyGive(s_task);
    }
}

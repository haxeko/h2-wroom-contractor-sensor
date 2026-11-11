/*
 * Li-MnO2 (CR123A) battery monitor - see battery_monitor.h
 *
 * APIs: esp_adc oneshot + curve-fitting calibration (ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
 * on ESP32-H2, ESP-IDF v5.5.5). ATTEN 6 dB: 0..1900 mV range, +-12 mV total error after
 * calibration (ESP32-H2 datasheet v1.3, table 5-5). Vbat/2 <= 1.7 V stays inside this range.
 */
#include "battery_monitor.h"

#include <inttypes.h>
#include <string.h>
#include "sdkconfig.h"
#include "driver/gpio.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "power/power_manager.h"

static const char *TAG = "battery";

static constexpr int kAdcGpio = CONFIG_CS_VBAT_ADC_GPIO;
static constexpr int kEnGpio = CONFIG_CS_VBAT_EN_GPIO;
static constexpr uint32_t kRatioX1000 = CONFIG_CS_VBAT_DIVIDER_RATIO_X1000;
static constexpr int kSamples = 8;

static TaskHandle_t s_task;
static esp_timer_handle_t s_timer;
static esp_pm_lock_handle_t s_pm_lock;
static battery_cb_t s_cb;
static void *s_cb_ctx;
static battery_status_t s_last;
static bool s_has_last;

/*
 * Unloaded voltage -> remaining capacity for a Li-MnO2 cell (CR123A) at ~20 degC and uA..mA loads.
 * Li-MnO2 has a very flat plateau, so the voltage only gives a coarse estimate; the table is
 * a STARTING POINT and must be re-fitted from discharge tests of the chosen battery brand
 * (docs/common/09_battery_life.md, test B-03).
 */
struct curve_point_t {
    uint16_t mv;
    uint8_t percent;
};
static const curve_point_t kCurve[] = {
    {3150, 100}, {3050, 90}, {3000, 80}, {2950, 65}, {2900, 50}, {2850, 35},
    {2800, 25},  {2700, 15}, {2600, 8},  {2500, 4},  {2400, 2},  {2300, 0},
};

uint8_t battery_monitor_percent_x2_from_mv(uint32_t mv)
{
    const size_t n = sizeof(kCurve) / sizeof(kCurve[0]);
    if (mv >= kCurve[0].mv) {
        return 200;
    }
    if (mv <= kCurve[n - 1].mv) {
        return 0;
    }
    for (size_t i = 1; i < n; i++) {
        if (mv >= kCurve[i].mv) {
            const uint32_t span_mv = kCurve[i - 1].mv - kCurve[i].mv;
            const uint32_t span_pct = kCurve[i - 1].percent - kCurve[i].percent;
            const uint32_t pct_x2 = 2 * kCurve[i].percent + (2 * span_pct * (mv - kCurve[i].mv)) / span_mv;
            return (uint8_t)(pct_x2 > 200 ? 200 : pct_x2);
        }
    }
    return 0;
}

static void divider_enable(bool on)
{
#if CONFIG_CS_VBAT_EN_GPIO >= 0
    const gpio_num_t pin = static_cast<gpio_num_t>(kEnGpio);
    if (on) {
        gpio_set_level(pin, 0);
        gpio_set_direction(pin, GPIO_MODE_OUTPUT);   /* sink the bottom resistor */
    } else {
        gpio_set_direction(pin, GPIO_MODE_DISABLE);  /* high-Z: no current path */
    }
#else
    (void)on; /* divider permanently connected (not recommended: ~1.5 uA continuous) */
#endif
}

/* @p cpu_busy: wait for the divider with the CPU running (boot guard: the cell must stay loaded,
 * a sleeping task would let its voltage recover) instead of letting the task sleep. */
static esp_err_t measure_mv(uint32_t *out_mv, bool cpu_busy)
{
    adc_unit_t unit;
    adc_channel_t channel;
    ESP_RETURN_ON_ERROR(adc_oneshot_io_to_channel(kAdcGpio, &unit, &channel), TAG, "GPIO%d is not an ADC pin", kAdcGpio);

    adc_oneshot_unit_handle_t adc = nullptr;
    adc_oneshot_unit_init_cfg_t unit_cfg = {};
    unit_cfg.unit_id = unit;
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&unit_cfg, &adc), TAG, "adc unit");

    adc_oneshot_chan_cfg_t chan_cfg = {};
    chan_cfg.atten = ADC_ATTEN_DB_6;
    chan_cfg.bitwidth = ADC_BITWIDTH_DEFAULT;
    esp_err_t err = adc_oneshot_config_channel(adc, channel, &chan_cfg);

    adc_cali_handle_t cali = nullptr;
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    if (err == ESP_OK) {
        adc_cali_curve_fitting_config_t cali_cfg = {};
        cali_cfg.unit_id = unit;
        cali_cfg.chan = channel;
        cali_cfg.atten = ADC_ATTEN_DB_6;
        cali_cfg.bitwidth = ADC_BITWIDTH_DEFAULT;
        if (adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali) != ESP_OK) {
            ESP_LOGW(TAG, "no ADC calibration in eFuse - raw conversion used");
            cali = nullptr;
        }
    }
#endif

    if (s_pm_lock) {
        esp_pm_lock_acquire(s_pm_lock); /* keep VBAT_EN driven LOW (digital pad) */
    }
    divider_enable(true);
    if (cpu_busy) {
        esp_rom_delay_us(CONFIG_CS_VBAT_SETTLE_MS * 1000);
    } else {
        vTaskDelay(pdMS_TO_TICKS(CONFIG_CS_VBAT_SETTLE_MS));
    }

    int sum_mv = 0;
    int valid = 0;
    for (int i = 0; err == ESP_OK && i < kSamples; i++) {
        int raw = 0;
        err = adc_oneshot_read(adc, channel, &raw);
        if (err != ESP_OK) {
            break;
        }
        int mv = 0;
        if (cali) {
            err = adc_cali_raw_to_voltage(cali, raw, &mv);
        } else {
            mv = raw * 1900 / 4095; /* approximate, uncalibrated */
        }
        if (err == ESP_OK) {
            sum_mv += mv;
            valid++;
        }
    }

    divider_enable(false);
    if (s_pm_lock) {
        esp_pm_lock_release(s_pm_lock);
    }

#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    if (cali) {
        adc_cali_delete_scheme_curve_fitting(cali);
    }
#endif
    adc_oneshot_del_unit(adc);

    ESP_RETURN_ON_ERROR(err, TAG, "adc read");
    ESP_RETURN_ON_FALSE(valid > 0, ESP_FAIL, TAG, "no sample");
    *out_mv = (uint32_t)(sum_mv / valid) * kRatioX1000 / 1000;
    return ESP_OK;
}

esp_err_t battery_monitor_measure_now(uint32_t *out_mv)
{
    ESP_RETURN_ON_FALSE(out_mv, ESP_ERR_INVALID_ARG, TAG, "null");
    if (!s_pm_lock) {
        s_pm_lock = power_manager_create_no_sleep_lock("vbat"); /* VBAT_EN is a digital pad */
    }
    return measure_mv(out_mv, true);
}

static void evaluate(uint32_t mv, battery_status_t *st)
{
    st->voltage_mv = mv;
    st->percent_x2 = battery_monitor_percent_x2_from_mv(mv);
    if (mv < CONFIG_CS_VBAT_CRITICAL_MV) {
        st->level = BATTERY_LEVEL_CRITICAL;
    } else if (mv < CONFIG_CS_VBAT_WARNING_MV) {
        st->level = BATTERY_LEVEL_WARNING;
    } else {
        st->level = BATTERY_LEVEL_OK;
    }
    st->replacement_needed = (st->level != BATTERY_LEVEL_OK);
}

static void battery_task(void *arg)
{
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        uint32_t mv = 0;
        if (measure_mv(&mv, false) != ESP_OK) {
            continue;
        }
        battery_status_t st;
        evaluate(mv, &st);
        ESP_LOGI(TAG, "Vbat %" PRIu32 " mV, %u.%u %%, level %d", st.voltage_mv, st.percent_x2 / 2,
                 (st.percent_x2 % 2) * 5, (int)st.level);

        /* Report only meaningful changes: every report wakes the radio (ICD active mode). */
        const bool changed = !s_has_last || st.level != s_last.level ||
                             (st.percent_x2 > s_last.percent_x2 + 2) || (s_last.percent_x2 > st.percent_x2 + 2);
        if (changed) {
            s_last = st;
            s_has_last = true;
            if (s_cb) {
                s_cb(&st, s_cb_ctx);
            }
        }
    }
}

static void timer_cb(void *arg)
{
    battery_monitor_request();
}

esp_err_t battery_monitor_init(battery_cb_t cb, void *ctx)
{
    s_cb = cb;
    s_cb_ctx = ctx;

#if CONFIG_CS_VBAT_EN_GPIO >= 0
    gpio_config_t io = {};
    io.pin_bit_mask = 1ULL << kEnGpio;
    io.mode = GPIO_MODE_DISABLE;
    io.pull_up_en = GPIO_PULLUP_DISABLE;
    io.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io.intr_type = GPIO_INTR_DISABLE;
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "VBAT_EN");
#endif
    if (!s_pm_lock) {
        s_pm_lock = power_manager_create_no_sleep_lock("vbat");
    }

    BaseType_t ok = xTaskCreate(battery_task, "battery", 3072, nullptr, 2, &s_task);
    ESP_RETURN_ON_FALSE(ok == pdPASS, ESP_ERR_NO_MEM, TAG, "task");

    esp_timer_create_args_t args = {};
    args.callback = timer_cb;
    args.name = "vbat";
    ESP_RETURN_ON_ERROR(esp_timer_create(&args, &s_timer), TAG, "timer");
    ESP_RETURN_ON_ERROR(esp_timer_start_periodic(s_timer, (uint64_t)CONFIG_CS_VBAT_PERIOD_MIN * 60ULL * 1000000ULL),
                        TAG, "timer start");

    battery_monitor_request(); /* first measurement at boot */
    return ESP_OK;
}

void battery_monitor_request(void)
{
    if (s_task) {
        xTaskNotifyGive(s_task);
    }
}

bool battery_monitor_get_last(battery_status_t *out)
{
    if (!s_has_last || !out) {
        return false;
    }
    *out = s_last;
    return true;
}

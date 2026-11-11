/*
 * Power management - see power_manager.h
 *
 * Verified against ESP-IDF v5.5.5 sources:
 *  - esp_sleep_enable_gpio_wakeup() logs "GPIO wakeup source is not available if the peripheral
 *    power domain is powered down in sleep" when CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP=y
 *    (components/esp_hw_support/sleep_modes.c) -> EXT1 is used instead.
 *  - ESP32-H2 supports a per-pin EXT1 level (SOC_PM_SUPPORT_EXT1_WAKEUP_MODE_PER_PIN) on
 *    GPIO7..14 (rtc_io_periph.c), so the Hall input and the button can have different levels.
 *  - ieee802154_pib_init() sets every channel to the maximum TX power (20 dBm on H2).
 *  - A provisioned device sends a Child Update Request to its former parent 0..25 ms after Thread
 *    starts (OpenThread PrevRoleRestorer), usually before app_main() gets the OpenThread lock:
 *    at +20 dBm that frame draws ~180 mA from the cell. esp_ieee802154_enable() is therefore
 *    wrapped at link time (main/CMakeLists.txt) to lower the power before the first frame.
 */
#include "power_manager.h"

#include <inttypes.h>
#include "sdkconfig.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_attr.h"
#include "esp_ieee802154.h"
#include "esp_openthread_lock.h"
#include "esp_system.h"
#include "esp_timer.h"

static const char *TAG = "power";

/* Pins that are not connected on PCB rev A (see docs/05_schematic.md, GPIO table).
 * Floating inputs waste current; gpio_reset_pin() disables the input buffer and enables the
 * weak pull-up, as recommended by the ESP32-H2 hardware design guidelines. */
static const gpio_num_t kUnusedPins[] = {
    GPIO_NUM_0, GPIO_NUM_2, GPIO_NUM_3, GPIO_NUM_4, GPIO_NUM_5, GPIO_NUM_12, GPIO_NUM_25,
#if !CONFIG_RTC_CLK_SRC_EXT_CRYS
    GPIO_NUM_13, GPIO_NUM_14, /* 32.768 kHz crystal footprint not populated */
#endif
#if !CONFIG_USJ_ENABLE_USB_SERIAL_JTAG
    GPIO_NUM_26, GPIO_NUM_27, /* USB D-/D+ only used for development */
#endif
};

static bool s_isr_service_installed;

static bool pin_is_used_by_app(gpio_num_t pin)
{
    const int used[] = {CONFIG_CS_HALL_GPIO, CONFIG_CS_BUTTON_GPIO, CONFIG_CS_LED_GPIO,
                        CONFIG_CS_VBAT_ADC_GPIO, CONFIG_CS_VBAT_EN_GPIO};
    for (int u : used) {
        if (u == (int)pin) {
            return true;
        }
    }
    return false;
}

esp_err_t power_manager_init(void)
{
#if CONFIG_PM_ENABLE
    esp_pm_config_t pm_config = {};
    /* Fixed CPU clock, exactly like the esp-matter ICD example: the radio drivers hold
     * the max frequency anyway while active, and a fast CPU shortens the awake time. */
    pm_config.max_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ;
    pm_config.min_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ;
#if CONFIG_FREERTOS_USE_TICKLESS_IDLE
    pm_config.light_sleep_enable = true;
#endif
    ESP_RETURN_ON_ERROR(esp_pm_configure(&pm_config), TAG, "esp_pm_configure failed");
    ESP_LOGI(TAG, "PM: %d MHz, light sleep %s", pm_config.max_freq_mhz,
             pm_config.light_sleep_enable ? "enabled" : "disabled");
#else
    ESP_LOGW(TAG, "CONFIG_PM_ENABLE is off: the device will NOT reach its battery life target");
#endif

    for (gpio_num_t pin : kUnusedPins) {
        if (!pin_is_used_by_app(pin)) {
            gpio_reset_pin(pin);
        }
    }
    return ESP_OK;
}

esp_err_t power_manager_install_gpio_isr_service(void)
{
    if (s_isr_service_installed) {
        return ESP_OK;
    }
    /* IRAM ISR: the handlers only use IRAM-safe calls (CONFIG_GPIO_CTRL_FUNC_IN_IRAM=y) */
    esp_err_t err = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    if (err == ESP_ERR_INVALID_STATE) {
        err = ESP_OK; /* already installed by another component */
    }
    s_isr_service_installed = (err == ESP_OK);
    return err;
}

esp_err_t power_manager_register_wakeup_gpio(gpio_num_t pin, bool pullup)
{
#if CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP
    ESP_RETURN_ON_FALSE(esp_sleep_is_valid_wakeup_gpio(pin), ESP_ERR_INVALID_ARG, TAG,
                        "GPIO%d cannot wake the chip when the peripheral domain is powered down "
                        "(use an LP IO: GPIO7..14)", (int)pin);
#endif
    gpio_config_t io = {};
    io.pin_bit_mask = 1ULL << pin;
    io.mode = GPIO_MODE_INPUT;
    io.pull_up_en = pullup ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE;
    io.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io.intr_type = GPIO_INTR_DISABLE;
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio_config GPIO%d", (int)pin);

#if CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP
    /* The IO MUX registers are lost when the TOP domain is off: hold the pad configuration
     * (input enabled, pull) during sleep. Same approach as espressif/button (button_gpio.c). */
    ESP_RETURN_ON_ERROR(gpio_hold_en(pin), TAG, "gpio_hold_en GPIO%d", (int)pin);
#else
    static bool s_gpio_wakeup_enabled;
    if (!s_gpio_wakeup_enabled) {
        ESP_RETURN_ON_ERROR(esp_sleep_enable_gpio_wakeup(), TAG, "esp_sleep_enable_gpio_wakeup");
        s_gpio_wakeup_enabled = true;
    }
#endif
    return ESP_OK;
}

esp_err_t power_manager_arm_wakeup_gpio(gpio_num_t pin, int wake_level)
{
    const gpio_int_type_t type = wake_level ? GPIO_INTR_HIGH_LEVEL : GPIO_INTR_LOW_LEVEL;
    /* gpio_wakeup_enable() also programs the (level) interrupt type of the pin */
    ESP_RETURN_ON_ERROR(gpio_wakeup_enable(pin, type), TAG, "gpio_wakeup_enable GPIO%d", (int)pin);
#if CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP
    ESP_RETURN_ON_ERROR(esp_sleep_enable_ext1_wakeup_io(1ULL << pin,
                                                        wake_level ? ESP_EXT1_WAKEUP_ANY_HIGH
                                                                   : ESP_EXT1_WAKEUP_ANY_LOW),
                        TAG, "ext1 GPIO%d", (int)pin);
#endif
    return gpio_intr_enable(pin);
}

esp_err_t power_manager_disarm_wakeup_gpio(gpio_num_t pin)
{
    gpio_intr_disable(pin);
    esp_err_t err = gpio_wakeup_disable(pin);
#if CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP
    /* Clears EXT1_TRIG_EN as well when no EXT1 pin is left (sleep_modes.c) */
    const esp_err_t err_ext1 = esp_sleep_disable_ext1_wakeup_io(1ULL << pin);
    if (err == ESP_OK) {
        err = err_ext1;
    }
#endif
    return err;
}

esp_err_t power_manager_set_thread_tx_power(int8_t dbm)
{
    esp_ieee802154_txpower_table_t table;
    for (int8_t &ch : table.channel) {
        ch = dbm;
    }
    esp_openthread_lock_acquire(portMAX_DELAY);
    esp_err_t err = esp_ieee802154_set_power_table(table);
    esp_openthread_lock_release();
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "802.15.4 TX power set to %d dBm on channels 11..26", dbm);
    }
    return err;
}

/* ------------------------------------------------------------------ TX power, first frame */

extern "C" esp_err_t __real_esp_ieee802154_enable(void);

extern "C" esp_err_t __wrap_esp_ieee802154_enable(void)
{
    const esp_err_t err = __real_esp_ieee802154_enable();
    esp_ieee802154_set_txpower(CONFIG_CS_THREAD_TX_POWER_DBM);
    return err;
}

/* ------------------------------------------------------------------ Deep-sleep / weak battery */

/* Survive software, panic, brownout and Deep-sleep resets, not a power-on reset */
static RTC_NOINIT_ATTR uint32_t s_rtc_magic;
static RTC_NOINIT_ATTR uint32_t s_rtc_brownouts;
static constexpr uint32_t kRtcMagic = 0x43534247; /* "CSBG" */
static constexpr uint64_t kStableRunUs = 10ULL * 60ULL * 1000000ULL;
static constexpr uint32_t kBootMinMv = CONFIG_CS_BOOT_MIN_MV; /* 0 = voltage check disabled */

void power_manager_deep_sleep(uint32_t wake_after_s)
{
    /* The Hall input is an EXT1 source for light sleep: it must not wake a sleeping, unusable device */
    esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);
    if (wake_after_s > 0) {
        esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(wake_after_s) * 1000000ULL);
    }
    const gpio_num_t button = static_cast<gpio_num_t>(CONFIG_CS_BUTTON_GPIO);
    /* Release the light-sleep pad hold so that the sleep code can set the pad up for EXT1 */
    gpio_hold_dis(button);
    gpio_set_direction(button, GPIO_MODE_INPUT);
    gpio_pullup_en(button);
    /* A button held down now would wake the chip at once, again and again: timer only in that case */
    if (gpio_get_level(button) != 0 || wake_after_s == 0) {
        esp_sleep_enable_ext1_wakeup_io(1ULL << button, ESP_EXT1_WAKEUP_ANY_LOW);
    }
    esp_deep_sleep_start();
}

static void stable_run_cb(void *arg)
{
    s_rtc_brownouts = 0;
}

void power_manager_boot_guard(uint32_t loaded_mv)
{
    const esp_reset_reason_t reason = esp_reset_reason();
    if (s_rtc_magic != kRtcMagic || reason == ESP_RST_POWERON) {
        s_rtc_magic = kRtcMagic;
        s_rtc_brownouts = 0;
    }
    if (reason == ESP_RST_BROWNOUT) {
        s_rtc_brownouts++;
        ESP_LOGW(TAG, "brownout reset (%" PRIu32 " in a row)", s_rtc_brownouts);
    }

    /* Below 1.5 V the converter could not run at all: such a reading means "no battery divider"
     * (development kit, unpopulated R8/R9), not a weak cell */
    const bool weak = kBootMinMv > 0 && loaded_mv >= 1500 && loaded_mv < kBootMinMv;
    const bool looping = s_rtc_brownouts >= CONFIG_CS_BROWNOUT_LIMIT;
    if (!weak && !looping) {
        /* A run this long without a brownout clears the counter */
        static esp_timer_handle_t s_stable_timer;
        esp_timer_create_args_t args = {};
        args.callback = stable_run_cb;
        args.name = "stable";
        if (!s_stable_timer && esp_timer_create(&args, &s_stable_timer) == ESP_OK) {
            esp_timer_start_once(s_stable_timer, kStableRunUs);
        }
        return;
    }
    ESP_LOGW(TAG, "battery too weak (%" PRIu32 " mV loaded, %" PRIu32 " brownouts): Deep-sleep %d s",
             loaded_mv, s_rtc_brownouts, CONFIG_CS_RECOVERY_SLEEP_S);
    if (looping) {
        s_rtc_brownouts = CONFIG_CS_BROWNOUT_LIMIT - 1; /* one more try after the rest */
    }
    power_manager_deep_sleep(CONFIG_CS_RECOVERY_SLEEP_S);
}

esp_pm_lock_handle_t power_manager_create_no_sleep_lock(const char *name)
{
    esp_pm_lock_handle_t handle = nullptr;
#if CONFIG_PM_ENABLE
    if (esp_pm_lock_create(ESP_PM_NO_LIGHT_SLEEP, 0, name, &handle) != ESP_OK) {
        ESP_LOGE(TAG, "esp_pm_lock_create(%s) failed", name);
        handle = nullptr;
    }
#endif
    return handle;
}

void power_manager_dump(void)
{
#if CONFIG_PM_ENABLE
    esp_pm_dump_locks(stdout);
#endif
}

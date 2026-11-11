/*
 * Matter data model of the contact sensor - see matter_endpoint.h
 *
 * Verified against esp-matter release/v1.6 (legacy data model, the default) and its
 * connectedhomeip submodule (commit 75902a0c6):
 *
 *  - endpoint::contact_sensor::create() adds Identify + Boolean State and the StateChange event
 *    (components/esp_matter/data_model/legacy/esp_matter_endpoint.cpp).
 *  - Boolean State is served by the code-driven chip::app::Clusters::BooleanStateCluster
 *    (data_model_provider/clusters/boolean_state/integration.cpp). Its StateValue is NOT stored
 *    in the esp-matter attribute table: esp_matter::attribute::update() returns
 *    ESP_ERR_NOT_SUPPORTED for this read-only, SCI-served attribute (esp_matter_data_model.cpp,
 *    set_val()). The value must be changed with BooleanStateCluster::SetStateValue(), which also
 *    generates the StateChange event. esp-matter does not export a FindClusterOnEndpoint() for
 *    this cluster, so the instance is fetched from the provider's ServerClusterInterfaceRegistry.
 *  - Power Source is still served through an AttributeAccessInterface for a few attributes only;
 *    BatVoltage / BatPercentRemaining / BatChargeLevel / BatReplacementNeeded live in the
 *    esp-matter attribute table, so esp_matter::attribute::update() is the correct API.
 */
#include "matter_endpoint.h"

#include <atomic>
#include <optional>
#include <string.h>

#include "sdkconfig.h"
#include "esp_check.h"
#include "esp_log.h"

#include <esp_matter.h>
#include <data_model_provider/esp_matter_data_model_provider.h>

#include <app/clusters/boolean-state-server/BooleanStateCluster.h>
#include <app/server/CommissioningWindowManager.h>
#include <app/server/Server.h>
#include <platform/CHIPDeviceLayer.h>
#if CONFIG_ENABLE_ICD_SERVER
#include <app/icd/server/ICDNotifier.h>
#endif

static const char *TAG = "matter_ep";

using namespace esp_matter;
using namespace chip::app::Clusters;

static uint16_t s_contact_ep_id = chip::kInvalidEndpointId;
static std::atomic<bool> s_contact_closed{false};
static std::atomic<bool> s_server_ready{false};
static matter_identify_cb_t s_identify_cb;

/* ------------------------------------------------------------------ callbacks */

static esp_err_t attribute_update_cb(attribute::callback_type_t type, uint16_t endpoint_id, uint32_t cluster_id,
                                     uint32_t attribute_id, esp_matter_attr_val_t *val, void *priv_data)
{
    /* A contact sensor has no writable application attributes (no actuator). */
    return ESP_OK;
}

static esp_err_t identification_cb(identification::callback_type_t type, uint16_t endpoint_id, uint8_t effect_id,
                                   uint8_t effect_variant, void *priv_data)
{
    ESP_LOGI(TAG, "identify: type %u, effect %u", static_cast<unsigned>(type), static_cast<unsigned>(effect_id));
    if (s_identify_cb) {
        s_identify_cb(type != identification::callback_type_t::STOP);
    }
    return ESP_OK;
}

/* ------------------------------------------------------------- creation */

esp_err_t matter_endpoint_create(matter_identify_cb_t identify_cb)
{
    s_identify_cb = identify_cb;

    node::config_t node_config;
    node_t *node = node::create(&node_config, attribute_update_cb, identification_cb);
    ESP_RETURN_ON_FALSE(node, ESP_FAIL, TAG, "node::create failed");

    endpoint::contact_sensor::config_t cs_config;
    endpoint_t *ep = endpoint::contact_sensor::create(node, &cs_config, ENDPOINT_FLAG_NONE, nullptr);
    ESP_RETURN_ON_FALSE(ep, ESP_FAIL, TAG, "contact_sensor::create failed");
    s_contact_ep_id = endpoint::get_id(ep);

    /* Power Source on the same endpoint (same layout as the upstream smoke-co-alarm-app):
     * one replaceable primary battery. An empty EndpointList means "powers the whole node". */
    endpoint::power_source::config_t ps_config;
    cluster::power_source::config_t &ps = ps_config.power_source;
    ps.status = chip::to_underlying(PowerSource::PowerSourceStatusEnum::kActive);
    ps.order = 0;
    strlcpy(ps.description, "Primary battery", sizeof(ps.description));
    ps.feature_flags = cluster::power_source::feature::battery::get_id() |
                       cluster::power_source::feature::replaceable::get_id();
    ps.features.battery.bat_charge_level = chip::to_underlying(PowerSource::BatChargeLevelEnum::kOk);
    ps.features.battery.bat_replacement_needed = false;
    ps.features.battery.bat_replaceability = chip::to_underlying(PowerSource::BatReplaceabilityEnum::kUserReplaceable);
    strlcpy(ps.features.replaceable.bat_replacement_description, "CR123A 3V lithium",
            sizeof(ps.features.replaceable.bat_replacement_description));
    ps.features.replaceable.bat_quantity = 1;
    ESP_RETURN_ON_ERROR(endpoint::power_source::add(ep, &ps_config), TAG, "power_source::add failed");

    cluster_t *ps_cluster = cluster::get(ep, PowerSource::Id);
    ESP_RETURN_ON_FALSE(ps_cluster, ESP_FAIL, TAG, "no Power Source cluster");
    /* Optional attributes (null until the first measurement) */
    cluster::power_source::attribute::create_bat_voltage(ps_cluster, nullable<uint32_t>(), nullable<uint32_t>(0),
                                                         nullable<uint32_t>(4000));
    cluster::power_source::attribute::create_bat_percent_remaining(ps_cluster, nullable<uint8_t>(), nullable<uint8_t>(0),
                                                                   nullable<uint8_t>(200));
    cluster::power_source::attribute::create_bat_present(ps_cluster, true);
    cluster::power_source::attribute::create_bat_common_designation(
        ps_cluster, chip::to_underlying(PowerSource::BatCommonDesignationEnum::kCr123a), 0, 80);
    cluster::power_source::attribute::create_bat_approved_chemistry(
        ps_cluster, chip::to_underlying(PowerSource::BatApprovedChemistryEnum::kLithiumManganeseDioxide), 0, 32);

    ESP_LOGI(TAG, "Contact Sensor + Power Source on endpoint %u", s_contact_ep_id);
    return ESP_OK;
}

uint16_t matter_endpoint_contact_id(void)
{
    return s_contact_ep_id;
}

/* ------------------------------------------------------------- contact state */

static BooleanStateCluster *find_boolean_state_cluster(void)
{
    chip::app::ServerClusterInterface *iface = data_model::provider::get_instance().registry().Get(
        chip::app::ConcreteClusterPath(s_contact_ep_id, BooleanState::Id));
    /* esp-matter registers a LazyRegisteredServerCluster<BooleanStateCluster> for this path
     * (boolean_state/integration.cpp) -> static_cast is valid (RTTI is disabled in ESP-IDF). */
    return static_cast<BooleanStateCluster *>(iface);
}

/* Runs on the CHIP thread */
static void apply_contact_state(intptr_t)
{
    BooleanStateCluster *cluster = find_boolean_state_cluster();
    if (!cluster) {
        ESP_LOGW(TAG, "Boolean State not registered yet - value cached");
        return;
    }
    const bool closed = s_contact_closed.load();
    if (cluster->GetStateValue() == closed) {
        return;
    }
    std::optional<chip::EventNumber> evt = cluster->SetStateValue(closed);
    ESP_LOGI(TAG, "StateValue=%s (%s)%s", closed ? "true" : "false", closed ? "CLOSED" : "OPEN",
             evt.has_value() ? ", StateChange event logged" : "");
}

void matter_endpoint_set_contact(bool closed)
{
    s_contact_closed.store(closed);
    if (!s_server_ready.load()) {
        return; /* applied by matter_endpoint_on_server_ready() */
    }
    LogErrorOnFailure(chip::DeviceLayer::PlatformMgr().ScheduleWork(apply_contact_state, 0));
    matter_endpoint_request_active_mode();
}

void matter_endpoint_on_server_ready(void)
{
    s_server_ready.store(true);
    apply_contact_state(0); /* already on the CHIP thread */
}

void matter_endpoint_sync_after_start(void)
{
    LogErrorOnFailure(
        chip::DeviceLayer::PlatformMgr().ScheduleWork([](intptr_t) { matter_endpoint_on_server_ready(); }));
}

/* ------------------------------------------------------------- battery */

void matter_endpoint_set_battery(const battery_status_t *st)
{
    if (!st || s_contact_ep_id == chip::kInvalidEndpointId) {
        return;
    }
    /* attribute::update() takes the CHIP stack lock itself (ScopedChipStackLock) */
    esp_matter_attr_val_t v = esp_matter_nullable_uint32(nullable<uint32_t>(st->voltage_mv));
    attribute::update(s_contact_ep_id, PowerSource::Id, PowerSource::Attributes::BatVoltage::Id, &v);

    v = esp_matter_nullable_uint8(nullable<uint8_t>(st->percent_x2));
    attribute::update(s_contact_ep_id, PowerSource::Id, PowerSource::Attributes::BatPercentRemaining::Id, &v);

    v = esp_matter_enum8(static_cast<uint8_t>(st->level));
    attribute::update(s_contact_ep_id, PowerSource::Id, PowerSource::Attributes::BatChargeLevel::Id, &v);

    v = esp_matter_bool(st->replacement_needed);
    attribute::update(s_contact_ep_id, PowerSource::Id, PowerSource::Attributes::BatReplacementNeeded::Id, &v);
}

/* ------------------------------------------------------------- ICD / commissioning */

void matter_endpoint_request_active_mode(void)
{
#if CONFIG_ENABLE_ICD_SERVER
    /* Same call as the esp-matter icd_app user-active-mode button: keeps the ICD in Active
     * mode (fast polling) for at least ActiveModeThreshold so reports/acks are exchanged fast. */
    LogErrorOnFailure(chip::DeviceLayer::PlatformMgr().ScheduleWork(
        [](intptr_t) { chip::app::ICDNotifier::GetInstance().NotifyNetworkActivityNotification(); }));
#endif
}

bool matter_endpoint_is_commissioned(void)
{
    lock::ScopedChipStackLock lock(portMAX_DELAY);
    return chip::Server::GetInstance().GetFabricTable().FabricCount() > 0;
}

static void open_window_work(intptr_t timeout_s)
{
    chip::CommissioningWindowManager &mgr = chip::Server::GetInstance().GetCommissioningWindowManager();
    if (chip::Server::GetInstance().GetFabricTable().FabricCount() > 0) {
        /* Multi-admin must use the Enhanced Commissioning window opened by an existing
         * administrator (Apple/Google/HA "share / pairing mode"), not a physical button. */
        ESP_LOGI(TAG, "already commissioned: use the ecosystem's 'pairing mode' to add an admin");
        return;
    }
    if (mgr.IsCommissioningWindowOpen()) {
        return;
    }
    CHIP_ERROR err = mgr.OpenBasicCommissioningWindow(chip::System::Clock::Seconds32(static_cast<uint32_t>(timeout_s)),
                                                      chip::CommissioningWindowAdvertisement::kAllSupported);
    if (err != CHIP_NO_ERROR) {
        ESP_LOGE(TAG, "OpenBasicCommissioningWindow failed: %" CHIP_ERROR_FORMAT, err.Format());
    }
}

void matter_endpoint_open_commissioning_window(uint16_t timeout_s)
{
    LogErrorOnFailure(
        chip::DeviceLayer::PlatformMgr().ScheduleWork(open_window_work, static_cast<intptr_t>(timeout_s)));
}

void matter_endpoint_factory_reset(void)
{
    ESP_LOGW(TAG, "factory reset");
    esp_matter::factory_reset(); /* erases esp-matter NVS + ScheduleFactoryReset() -> reboot */
}

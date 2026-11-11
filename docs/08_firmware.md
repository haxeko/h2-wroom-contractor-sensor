# 08 – Firmware (ESP-IDF + ESP-Matter + OpenThread)

Mã nguồn: `firmware/matter_contact_sensor/` (cấu trúc đúng yêu cầu). **Đã build thành công** cho `esp32h2` (không còn warning trong mã ứng dụng):

| Hạng mục | Giá trị |
|---|---|
| ESP-IDF | **v5.5.5** (phiên bản esp-matter khuyến nghị cho nhánh v1.6) |
| esp-matter | nhánh **`release/v1.6`** (Matter 1.6), connectedhomeip commit `75902a0c6` |
| Data model | esp-matter "legacy" (mặc định; `CONFIG_ESP_MATTER_ENABLE_GENERATED_DATA_MODEL=n`) |
| Binary | 1 572 032 B (0x17FCC0); slot OTA 0x1E0000 còn trống 20 % (§8.1) |
| RAM tĩnh | DIRAM 190 376 / 258 000 B |

Lý do chọn nhánh: tại thời điểm thiết kế, các nhánh phát hành là `release/v1.5` (IDF v5.5.5), `release/v1.6` (IDF v5.5.5) và `release/v1.6.1` (IDF **v6.0.2**). Chọn v1.6 + IDF 5.5.5: Matter mới, dòng IDF 5.5 đã ổn định; chuyển sang v1.6.1/IDF 6.0 là bước nâng cấp sau (các API dùng trong repo đều tồn tại ở IDF 6.0, nhưng phải build lại và chạy lại toàn bộ test).

## 1. Kiến trúc

```
 ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
 │ hall_sensor  │  │ button       │  │ battery_monitor│   driver: không gọi Matter trực tiếp
 │ (GPIO10 EXT1)│  │ (GPIO9 EXT1) │  │ (ADC, GPIO22)  │
 └──────┬───────┘  └──────┬───────┘  └───────┬────────┘
        │ callback        │ callback          │ callback
        ▼                 ▼                   ▼
 ┌────────────────────────────────────────────────────┐      ┌──────────────┐
 │ app_main.cpp : app_task + hàng đợi sự kiện          │─────►│ status_led   │
 └──────────────────────────┬─────────────────────────┘      └──────────────┘
                            │ matter_endpoint_*() (thread-safe, ScheduleWork)
                            ▼
 ┌────────────────────────────────────────────────────┐      ┌──────────────┐
 │ matter_endpoint.cpp : node, endpoint, cluster, ICD  │      │ power_manager│ esp_pm, EXT1,
 └──────────────────────────┬─────────────────────────┘      │ TX power     │ GPIO hold
                            ▼                                └──────────────┘
           esp-matter / connectedhomeip (CHIP task) ── OpenThread (MTD/SED) ── 802.15.4
```

| File | Vai trò |
|---|---|
| `main/app_main.cpp` | khởi tạo NVS, PM, driver, data model, OpenThread, `esp_matter::start()`; app task xử lý sự kiện; callback sự kiện CHIP |
| `main/matter_endpoint.cpp/.h` | Root Node + Contact Sensor + Power Source; cập nhật BooleanState, pin; ICD active; commissioning window; factory reset |
| `main/sensor/hall_sensor.cpp/.h` | Hall: ISR mức, debounce, đảo mức đánh thức EXT1 |
| `main/button/button.cpp/.h` | nút: nhấn ngắn / cảnh báo / reset khi thả |
| `main/battery/battery_monitor.cpp/.h` | đo pin định kỳ, chuyển % và mức sạc |
| `main/power/power_manager.cpp/.h` | `esp_pm_configure`, EXT1/GPIO wake, `gpio_hold`, TX power 802.15.4, khóa PM |
| `main/led/status_led.cpp/.h` | các mẫu nháy LED bằng esp_timer + `gpio_hold` |
| `main/Kconfig.projbuild` | cấu hình chân, ngưỡng, thời gian (menu "Contact Sensor (board) configuration") |
| `sdkconfig.defaults` | cấu hình SDK (mục 7) |
| `partitions.csv` | 2 slot OTA trên 4 MB |

## 2. Data model Matter ✅

| Endpoint | Device type | Cluster |
|---|---|---|
| 0 | Root Node (0x0016) + OTA Requestor (0x0012) | Descriptor, Access Control, Basic Information, General Commissioning, Network Commissioning (Thread), General Diagnostics, Administrator Commissioning, Operational Credentials, **ICD Management** (do `node::create()` + Kconfig); OTA Software Update Requestor được `esp_matter_ota_requestor_init()` tự thêm vào endpoint 0 trong `esp_matter::start()` (`esp_matter_ota.cpp`) |
| 1 | **Contact Sensor (0x0015, rev 2)** + **Power Source (0x0011)** | Descriptor, Identify, **Boolean State** (StateValue + sự kiện StateChange), **Power Source** (feature BAT + REPLC; BatVoltage, BatPercentRemaining, BatChargeLevel, BatReplacementNeeded, BatReplaceability, BatReplacementDescription "CR123A 3V lithium", BatQuantity 1, BatPresent, BatCommonDesignation **CR123A**, BatApprovedChemistry **LithiumManganeseDioxide**) |

Ngữ nghĩa: **StateValue = TRUE ⇔ có tiếp xúc (nam châm gần, cửa ĐÓNG)**; FALSE ⇔ cửa MỞ. Không có cluster/thuộc tính tự định nghĩa. Bố trí Power Source cùng endpoint với ứng dụng giống `smoke-co-alarm-app` của connectedhomeip; EndpointList rỗng = nguồn cấp cho toàn node.

## 3. Ngủ và Thread: SED, ICD và những gì KHÔNG làm được

### 3.1 SED truyền thống vs Matter ICD ✅

| | Thread SED (OpenThread) | Matter ICD (Intermittently Connected Device) |
|---|---|---|
| Tầng | MAC/Thread: child "rx-off-when-idle", định kỳ gửi *Data Poll* tới parent | Ứng dụng Matter: quản lý **khi nào** thiết bị Active/Idle và chu kỳ poll tương ứng |
| Tham số | poll period | SlowPollingInterval (Idle), FastPollingInterval (Active), IdleModeDuration, ActiveModeDuration, ActiveModeThreshold |
| Controller biết gì | không | thuộc tính ICD Management + khóa DNS-SD `SII/SAI/SAT` ⇒ controller chỉnh thời gian chờ MRP |
| Báo cáo/subscription | — | MaxInterval của subscription được kéo dài theo IdleModeDuration ⇒ thiết bị ít phải thức |

ICD **dùng** SED ở tầng Thread; esp-matter bật ICD bằng `CONFIG_ENABLE_ICD_SERVER` (phụ thuộc `CONFIG_OPENTHREAD_MTD`).

### 3.2 SIT vs LIT ✅ / 🧪
- **SIT** (Short Idle Time): slow poll ≤ 15 s – connectedhomeip cưỡng chế bằng `static_assert` ("Spec requires the maximum slow poll interval for the SIT device to be smaller or equal than 15 s"). Không cần controller đăng ký. → **cấu hình mặc định**.
- **LIT** (Long Idle Time): slow poll > 15 s, cần **Check-In Protocol** và **đăng ký client** (`RegisterClient`) từ controller. Theo spec (ghi chú trong `icd_app` README): *"A LIT ICD SHALL operate as a SIT ICD if it doesn't have at least one registration"*. DSLS (Dynamic SIT/LIT) cho phép tự chuyển. Kconfig có sẵn: `CONFIG_ENABLE_ICD_LIT`, `CONFIG_ENABLE_ICD_CIP`, `CONFIG_ENABLE_ICD_DSLS`, `CONFIG_ICD_CLIENTS_SUPPORTED_PER_FABRIC`.
- 🧪 Mức hỗ trợ đăng ký LIT của Apple Home, Google Home, Home Assistant (python-matter-server) và Aqara thay đổi theo phiên bản — **phải thử**. Nếu ≥ 1 hệ sinh thái chính đăng ký được, bật LIT + DSLS (+0.7 năm tuổi thọ theo `tools/battery_life.py`, slow poll 60 s).

### 3.3 Tham số ICD đã chọn 💡

| Kconfig | Giá trị | Lý do |
|---|---|---|
| `CONFIG_ICD_SLOW_POLL_INTERVAL_MS` | **15000** | mức tối đa của SIT; poll là thành phần động lớn nhất (~15.6 µA ở 15 s) |
| `CONFIG_ICD_FAST_POLL_INTERVAL_MS` | 500 | như `icd_app`; nhận ACK/response nhanh khi Active |
| `CONFIG_ICD_IDLE_MODE_INTERVAL_SEC` | **3600** | subscription keep-alive mỗi giờ thay vì 10 phút: bớt ~4 µA (8 % ngân sách). Controller phát hiện cảm biến "offline" sau khoảng 1 giờ; sự kiện đóng/mở vẫn gửi ngay |
| `CONFIG_ICD_ACTIVE_MODE_INTERVAL_MS` | 1000 | thời gian Active tối thiểu |
| `CONFIG_ICD_ACTIVE_MODE_THRESHOLD_MS` | 1000 | giữ Active sau hoạt động mạng |
| `CONFIG_ENABLE_ICD_USER_ACTIVE_MODE_TRIGGER` | y | nhấn nút = UAT (`NotifyNetworkActivityNotification()`) |

Check-In interval: với SIT không có Check-In; khi bật LIT, `MaximumCheckInBackOff` mặc định = IdleModeDuration (`CHIPConfig.h`).

### 3.4 Chế độ ngủ được hỗ trợ ✅
- **Light sleep tự động** (esp_pm + FreeRTOS tickless idle): OpenThread vẫn giữ trạng thái child, đánh thức theo timer để poll; radio 802.15.4 tắt giữa các lần (`CONFIG_IEEE802154_SLEEP_ENABLE`). Đây là cơ chế Espressif dùng trong `icd_app` và `ot_sleepy_device`.
- **TOP power-down** (`CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP`): sàn ~25–27 µA thay vì ~85 µA; IDF 5.5 đánh dấu **EXPERIMENTAL** (Espressif vẫn dùng cho H2 trong `icd_app`). Hệ quả: đánh thức GPIO chỉ qua **EXT1** trên LP IO 7–14; các thanh ghi GPIO/IO MUX được REGDMA lưu/khôi phục.
- **Deep sleep: KHÔNG dùng khi đang hoạt động bình thường** (chỉ dùng khi chưa ghép nối hoặc pin quá yếu, §3.6). Deep sleep reset CPU và HP SRAM ⇒ mất trạng thái OpenThread (phải attach lại làm child: vài giây RX liên tục), mất CASE session/subscription (controller thấy "Không phản hồi" và phải thiết lập lại – tốn vài chục–trăm mC mỗi lần). Parent cũng xóa child sau child-timeout. ⇒ không tương thích hành vi ICD/SED chuẩn.

### 3.5 Tối ưu năng lượng trong firmware
- Hall/nút dùng ngắt mức + EXT1, **không polling**; debounce bằng `vTaskDelay` (chip ngủ trong lúc chờ).
- LED tắt hoàn toàn khi hoạt động bình thường; mức LED được giữ bằng `gpio_hold_en` ⇒ không cần khóa PM khi LED sáng.
- TX 802.15.4: hạ từ mặc định **20 dBm** (ESP-IDF `ieee802154_pib_init()` đặt mọi kênh ở mức tối đa) xuống **10 dBm**, **ngay từ khung đầu tiên** (§3.6), rồi đặt lại bằng `esp_ieee802154_set_power_table()` dưới khóa OpenThread sau mỗi lần kết nối.
- Đo pin 12 h/lần, chỉ báo cáo khi thay đổi ≥ 1 % hoặc đổi mức sạc (mỗi báo cáo đánh thức radio).
- BLE chỉ dùng khi commissioning (`CONFIG_USE_BLE_ONLY_FOR_COMMISSIONING`); USB-Serial-JTAG tắt (`CONFIG_USJ_ENABLE_USB_SERIAL_JTAG=n`); **log mặc định ở mức sản xuất** (WARN / CHIP ERROR), bản dev thêm `sdkconfig.defaults.debug` (§3.6, §8).
- Chân không dùng được `gpio_reset_pin()` (tắt input buffer, bật pull-up) theo khuyến nghị Espressif.

### 3.6 Cơ chế bảo vệ pin ✅ (mã, build) / 🧪 (phần cứng)

Bổ sung sau đợt rà soát firmware. Ba cơ chế đầu lấy từ firmware nút bấm CR2032 (cùng module, cùng SDK).

| Cơ chế | Vấn đề nếu không có | Cách làm | File |
|---|---|---|---|
| **TX đúng công suất từ khung đầu tiên** | Driver 802.15.4 khởi động ở +20 dBm (~140 mA). Thiết bị đã ghép nối gửi Child Update Request 0–25 ms sau khi Thread chạy, trước khi `app_main()` kịp hạ công suất. Một khung như vậy rút ~180 mA từ pin: phí pin, và làm sụt áp mạnh khi pin yếu hoặc lạnh | bọc `esp_ieee802154_enable()` bằng linker wrap (`-Wl,--wrap=esp_ieee802154_enable`), đặt `CONFIG_CS_THREAD_TX_POWER_DBM` ngay sau khi driver khởi tạo | `main/CMakeLists.txt`, `power/power_manager.cpp` |
| **Deep-sleep khi chưa ghép nối** (`CONFIG_CS_UNCOMMISSIONED_DEEP_SLEEP`) | esp-matter chỉ tắt BLE khi đã có fabric. BLE còn bật thì thạch anh chính chạy suốt trong light sleep (không có 32 kHz): **vài mA thay vì ~25 µA**. Cảm biến để chưa ghép nối (tồn kho có pin, hoặc sau khi xóa khỏi nhà) làm cạn CR123A trong khoảng 2 tuần | khi cửa sổ commissioning đóng mà chưa có fabric: chờ 60 s (không ngủ nếu đang có phiên PASE hoặc fail-safe), rồi Deep-sleep ~7 µA. Nhấn nút đánh thức (EXT1, R10) → khởi động bình thường → mở cửa sổ mới. Ngõ Hall bị tắt khỏi nguồn đánh thức | `power/uncommissioned_sleep.cpp` |
| **Bộ bảo vệ khởi động** (`CONFIG_CS_BOOT_MIN_MV` 2200, `CONFIG_CS_BROWNOUT_LIMIT` 3, `CONFIG_CS_RECOVERY_SLEEP_S` 3600) | pin gần hết: mỗi lần bật radio rail sập, chip reset rồi thử lại liên tục, rút nốt phần pin còn lại | đo áp pin ngay đầu `app_main()`, giữ CPU chạy trong lúc đo để pin có tải. Dưới 2.2 V, hoặc 3 lần brownout liên tiếp (bộ đếm trong RTC RAM): Deep-sleep 1 giờ rồi thử lại; nút đánh thức sớm. Chạy ổn 10 phút thì xóa bộ đếm. Giá trị đo dưới 1.5 V coi như không có mạch phân áp (devkit); `CONFIG_CS_BOOT_MIN_MV=0` tắt phép kiểm tra | `power/power_manager.cpp`, `app_main.cpp` |
| **Brownout mức 7 (2.94 V)** | rail 3.2 V tụt mà chip vẫn chạy flash/radio dưới điện áp tối thiểu | `CONFIG_ESP_BROWNOUT_DET_LVL_SEL_7` | `sdkconfig.defaults` |
| **Log mức sản xuất** | mỗi dòng log giữ CPU thức tới khi UART gửi xong (87 µs/ký tự ở 115200 baud). Log INFO/PROGRESS của một báo cáo Matter (1–2 kB) tốn 1–2 mC, nhiều hơn chính báo cáo đó (~1.2 mC) | `sdkconfig.defaults`: `LOG_DEFAULT_LEVEL_WARN`, `BOOTLOADER_LOG_LEVEL_WARN`, `CHIP_LOG_DEFAULT_LEVEL_ERROR`, `OPENTHREAD_LOG_LEVEL_WARN`. Bản dev: thêm `sdkconfig.defaults.debug` | `sdkconfig.defaults*` |
| **Keep-alive 1 giờ** | báo cáo rỗng mỗi 10 phút cho từng subscriber | `CONFIG_ICD_IDLE_MODE_INTERVAL_SEC=3600` (§3.3) | `sdkconfig.defaults` |

🧪 Phải thử trên phần cứng:
- Nút là GPIO9 (chân strap BOOT). Chân strap chỉ được chốt khi reset nguồn/brownout/watchdog, không phải khi thức dậy từ Deep-sleep, nên nhấn nút để đánh thức phải vào ứng dụng bình thường. **Kiểm tra: nhấn giữ nút 3 s để đánh thức, chip không được vào chế độ download.** Nếu có vấn đề, tắt `CONFIG_CS_UNCOMMISSIONED_DEEP_SLEEP`.
- Dòng khi chưa ghép nối: trong cửa sổ commissioning (mA), sau khi Deep-sleep (kỳ vọng ~7 µA + 1.6 µA Hall + rò).
- Bộ đếm brownout trong RTC RAM có thể mất nếu TPS63900 cắt hẳn rail; khi đó phép đo áp có tải lúc khởi động là lớp bảo vệ chính.

**Chưa làm (đề xuất):**
- **Mức pin.** `BatPercentRemaining` tính từ điện áp không tải. Pin Li-MnO2 giữ khoảng 2.95 V gần suốt đời nên con số % chỉ là ước lượng thô; bảng quy đổi phải hiệu chỉnh bằng thử xả (docs/10 B-03). Firmware nút bấm có cách ước lượng theo thời gian và nội trở, có thể mang sang.
- **Tạm dừng Thread khi mất mạng lâu.** OpenThread tự thử kết nối lại với chu kỳ tăng dần tới 20 phút, mỗi lần thu khoảng 2 s ở 26 mA: khoảng 50 µA thêm, tức dòng tăng gấp đôi suốt thời gian Border Router tắt. Firmware nút bấm đã có chính sách này (`CONFIG_THREAD_PAUSE_WHEN_DETACHED`); với cảm biến cửa có thể thử lại ngay khi cửa đổi trạng thái.

## 4. Luồng xử lý khi cửa thay đổi ✅ (mã) / 🧪 (thời gian)

1. DRV5032FA lấy mẫu (≤ 75 ms) → đổi mức OUT.
2. EXT1 đánh thức ESP32-H2; ISR mức tắt ngắt GPIO10, notify `hall_task`.
3. `hall_task` đọc mức, chờ `CONFIG_CS_HALL_DEBOUNCE_MS` (300 ms), đọc lại (lặp tới khi ổn định).
4. Nếu khác trạng thái đã báo → callback → `app_task`.
5. `matter_endpoint_set_contact()` → `PlatformMgr().ScheduleWork()` → trên CHIP thread: `BooleanStateCluster::SetStateValue()` (đánh dấu thuộc tính thay đổi + sinh sự kiện StateChange) và `ICDNotifier::NotifyNetworkActivityNotification()` (vào Active mode, fast poll).
6. Reporting engine gửi ReportData tới mọi subscriber; ICD giữ Active tới khi exchange đóng + ActiveModeThreshold.
7. Re-arm EXT1/ngắt ở mức ngược với mức vừa đọc → chip quay lại light sleep.

## 5. Commissioning, factory reset, khôi phục trạng thái ✅

| Tình huống | Hành vi |
|---|---|
| Lần đầu cấp pin, chưa commission | `CONFIG_CHIP_ENABLE_PAIRING_AUTOSTART` (mặc định y) mở cửa sổ commissioning BLE (tối đa `CHIP_DISCOVERY_TIMEOUT_SECS` = 900 s); LED nháy 30 ms/2 s |
| Cửa sổ đóng mà chưa commission | sau 60 s: **Deep-sleep** (§3.6). Nhấn nút = khởi động lại + mở cửa sổ mới |
| Commission | BLE (PASE) → cấp Thread dataset (Network Commissioning) → CASE qua Thread; fabric + dataset lưu NVS; `kCommissioningComplete` → LED tắt; BLE được giải phóng |
| Nhấn ngắn khi chưa commission (chip còn thức) | mở lại cửa sổ BLE `CONFIG_CS_COMMISSIONING_WINDOW_SEC` (300 s) |
| Nhấn ngắn khi đã commission | UAT (Active mode), đo pin, resync Hall, nháy LED 1 lần |
| Thêm hệ sinh thái thứ 2 (multi-admin) | dùng tính năng "chia sẻ/pairing mode" của hệ sinh thái đang quản lý (Enhanced Commissioning Window qua Administrator Commissioning cluster); firmware **không** mở BCM bằng nút khi đã có fabric |
| Giữ nút ≥ 5 s | LED nháy 5 Hz (cảnh báo) |
| Giữ ≥ 10 s rồi **thả** | `esp_matter::factory_reset()` (xóa NVS esp-matter + `Server::ScheduleFactoryReset()` → khởi động lại). Thực hiện **khi thả** vì GPIO9 là chân strap BOOT |
| Thả trong khoảng 5–10 s | hủy |
| Fabric cuối cùng bị xóa | (`CONFIG_CS_FACTORY_RESET_ON_LAST_FABRIC_REMOVED=y`) chờ 3 s cho phản hồi đi xong → factory reset → quảng bá BLE lại |
| Mất nguồn / thay pin | fabric, Thread dataset, bộ đếm lưu NVS; khởi động lại attach Thread; **subscription được thiết bị tự khôi phục** (`CONFIG_ENABLE_PERSIST_SUBSCRIPTIONS=y`); trạng thái cửa đọc lại từ Hall và đẩy vào cluster khi `kServerReady` |
| Reset do brownout/watchdog | như mất nguồn; `esp_reset_reason()` được log. 3 lần brownout liên tiếp hoặc pin < 2.2 V lúc khởi động: Deep-sleep 1 giờ (§3.6) |

## 6. OTA ✅ / 🧪

- Matter OTA Requestor bật (`CONFIG_ENABLE_OTA_REQUESTOR=y`); esp-matter tự khởi tạo requestor trong `esp_matter::start()` khi dùng data model.
- Flash 4 MB: bootloader + bảng phân vùng 48 KB, NVS 48 KB, **2 slot 1.92 MB**; image hiện tại 1.50 MB ⇒ dư 20 %/slot.
- Rollback: bật `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` ở cấu hình sản xuất và xác nhận ảnh mới (`esp_ota_mark_app_valid_cancel_rollback()`) sau khi Thread + Matter khởi động thành công — 🧪 thêm vào firmware sản xuất.
- Năng lượng OTA trên Thread: ~1.6 MB qua 802.15.4 (~100–150 kbit/s hiệu dụng trong điều kiện tốt) ⇒ vài phút ở chế độ Active liên tục (~10–20 mA) ⇒ ~0.5–1 mAh/lần. 🧪 Chỉ cho phép OTA khi `BatChargeLevel = OK`; kiểm tra controller (Apple/Google/HA) thực sự cung cấp OTA cho thiết bị chưa có trong DCL production.
- Không có phương án flash ngoài trên H2 (chân flash không đưa ra); nếu buộc dùng H2FH2S 2 MB thì bỏ OTA dual-bank.

## 7. Giải thích `sdkconfig.defaults` ✅ (mọi khóa tồn tại trong Kconfig của IDF 5.5.5 / esp-matter v1.6)

| Nhóm | Khóa | Giá trị | Giải thích |
|---|---|---|---|
| Flash | `CONFIG_ESPTOOLPY_FLASHSIZE_4MB` | y | ESP32-H2FH4S |
| | `CONFIG_PARTITION_TABLE_CUSTOM`, `_FILENAME`, `_OFFSET=0xC000` | | bảng `partitions.csv` |
| | `CONFIG_COMPILER_OPTIMIZATION_SIZE` | y | giảm kích thước |
| BLE | `CONFIG_BT_ENABLED`, `CONFIG_BT_NIMBLE_ENABLED` | y | BLE commissioning |
| | `CONFIG_USE_BLE_ONLY_FOR_COMMISSIONING` | y | giải phóng BLE sau commissioning, không khởi động BLE khi đã provisioned |
| | `CONFIG_BT_LE_SLEEP_ENABLE`, `CONFIG_BT_LE_LP_CLK_SRC_MAIN_XTAL` | y | controller BLE ngủ giữa các sự kiện; đồng hồ LP lấy từ XTAL chính (không có 32 kHz) |
| | `CONFIG_BT_LE_DFT_TX_POWER_LEVEL_N0` | y | BLE 0 dBm thay vì +9 dBm mặc định: điện thoại ở sát cảm biến khi ghép nối |
| Mạng | `CONFIG_ENABLE_WIFI_STATION=n`, `CONFIG_LWIP_IPV4=n`, `CONFIG_DISABLE_IPV4=y`… | | chỉ IPv6/Thread |
| Thread | `CONFIG_OPENTHREAD_ENABLED`, `CONFIG_OPENTHREAD_MTD` | y | thiết bị con, không định tuyến |
| | `CONFIG_OPENTHREAD_SRP_CLIENT`, `_MAX_SERVICES=6` | | quảng bá dịch vụ Matter qua SRP: 1/fabric (tối đa 5) + commissionable |
| | `CONFIG_OPENTHREAD_DNS_CLIENT` | y | phân giải địa chỉ khi tự khôi phục subscription |
| | `CONFIG_IEEE802154_SLEEP_ENABLE` | y | radio ngủ |
| Matter | `CONFIG_ENABLE_OTA_REQUESTOR` | y | OTA |
| | `CONFIG_ENABLE_PERSIST_SUBSCRIPTIONS` | y | khôi phục subscription sau reboot |
| | `CONFIG_SUPPORT_GROUPCAST_CLUSTER=n` | | như `icd_app` |
| ICD | xem §3.3 | | SIT |
| PM | `CONFIG_PM_ENABLE`, `CONFIG_FREERTOS_USE_TICKLESS_IDLE`, `CONFIG_FREERTOS_HZ=1000` | y | light sleep tự động |
| | `CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP` | y | tắt miền TOP (EXPERIMENTAL) |
| | `CONFIG_ESP_SLEEP_POWER_DOWN_FLASH` | y | tắt flash khi ngủ (thức lâu hơn chút) |
| | `CONFIG_ESP_PHY_MAC_BB_PD` | y | tắt baseband khi ngủ |
| | `CONFIG_PM_SLP_IRAM_OPT`, `CONFIG_PM_RTOS_IDLE_OPT` | y | mã vào/ra light sleep nằm trong RAM: mỗi lần thức ngắn hơn |
| | `CONFIG_GPIO_CTRL_FUNC_IN_IRAM` | y | ISR IRAM-safe |
| | `CONFIG_RTC_CLK_SRC_INT_RC` | y | RTC slow clock RC 136 kHz (32.768 kHz DNP) |
| Console | `CONFIG_ESP_CONSOLE_UART_DEFAULT`, `CONFIG_ESP_CONSOLE_SECONDARY_NONE` | y | log qua pad UART |
| | `CONFIG_USJ_ENABLE_USB_SERIAL_JTAG=n` | | tắt clock USB-Serial-JTAG để giảm dòng |
| Log | `CONFIG_LOG_DEFAULT_LEVEL_WARN`, `CONFIG_BOOTLOADER_LOG_LEVEL_WARN`, `CONFIG_CHIP_LOG_DEFAULT_LEVEL_ERROR`, `CONFIG_OPENTHREAD_LOG_LEVEL_WARN`, `CONFIG_CHIP_CONFIG_IM_PRETTY_PRINT=n` | | mức sản xuất (§3.6) |
| Nguồn | `CONFIG_ESP_BROWNOUT_DET`, `CONFIG_ESP_BROWNOUT_DET_LVL_SEL_7` | y | brownout 2.94 V |

Không có cấu hình xung đột: ví dụ không bật đồng thời `esp_sleep_enable_gpio_wakeup()` với TOP PD (firmware dùng EXT1 khi TOP PD, chỉ dùng GPIO wake khi TOP PD tắt – `power_manager.cpp`).

## 8. Các lớp cấu hình

| File | Dùng cho |
|---|---|
| `sdkconfig.defaults` | **bản sản xuất** cho cả hai board (chip rời và module), pin CR123A: TX 10 dBm, CPU 96 MHz, log tối thiểu |
| `+ sdkconfig.defaults.debug` | phát triển: log INFO / CHIP PROGRESS / OpenThread NOTE trên UART0. **Không dùng khi đo dòng** |

Còn phải làm cho sản phẩm thật 💡:
- Dữ liệu nhà máy: `CONFIG_ENABLE_ESP32_FACTORY_DATA_PROVIDER=y` + DAC/PAI/CD lưu trong `esp_secure_cert` (`CONFIG_SEC_CERT_DAC_PROVIDER`) – sinh bằng `esp-matter-mfg-tool` (đã có trong requirements esp-matter); VID/PID chính thức của công ty (không dùng VID test 0xFFF1).
- Bảo mật: Secure Boot v2 + Flash Encryption (release mode) + NVS encryption (phân vùng `nvs_keys` đã có).
- `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`.

### 8.1 Kết quả build ✅
ESP-IDF v5.5.5 + esp-matter release/v1.6, không có cảnh báo trong `main/`. Cùng một file dùng cho cả bản chip rời và bản module:

| Bản | Lệnh | `matter_contact_sensor.bin` | Slot OTA 0x1E0000 | DIRAM tĩnh |
|---|---|---|---|---|
| Mặc định (CR123A, 10 dBm, 96 MHz) | `idf.py build` | 0x17FCC0 B (1 572 032 B) | còn 20 % | 190 376 / 258 000 B |

Image nhỏ hơn bản đầu (0x192FE0 B) khoảng 79 kB vì mức log sản xuất. Đã kiểm tra trong file ELF: hàm khởi tạo radio của OpenThread gọi `__wrap_esp_ieee802154_enable`, hàm này gọi driver thật rồi `esp_ieee802154_set_txpower()`.

## 9. Build & thử nhanh

```bash
# 1. SDK (đúng phiên bản)
git clone -b v5.5.5 --recursive --shallow-submodules https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32h2 && . ./export.sh && cd ..
git clone -b release/v1.6 --depth 1 https://github.com/espressif/esp-matter.git
cd esp-matter && git submodule update --init --depth 1
cd connectedhomeip/connectedhomeip && ./scripts/checkout_submodules.py --platform esp32 linux --shallow && cd ../..
./install.sh && . ./export.sh && cd ..
# 2. Build
cd matter_contact_sensor && idf.py set-target esp32h2 && idf.py build
# 3. Nạp (giữ nút BOOT/GPIO9 khi cấp nguồn nếu flash đã có app chặn UART)
idf.py -p /dev/ttyUSB0 flash monitor
# 4. Commission thử bằng chip-tool (Thread BR có sẵn dataset):
chip-tool pairing ble-thread 1 hex:<active_dataset> 20202021 3840
chip-tool booleanstate read state-value 1 1
chip-tool booleanstate subscribe state-value 1 600 1 1
chip-tool powersource read bat-percent-remaining 1 1
```
(Mã setup 20202021/discriminator 3840 là giá trị TEST mặc định của SDK – sản phẩm thật dùng dữ liệu nhà máy.)

## 10. Bảng đối chiếu API (không dùng API giả định) ✅

| API | Kiểm chứng tại |
|---|---|
| `esp_matter::node::create(config, attr_cb, identify_cb)` | `components/esp_matter/data_model/legacy/esp_matter_endpoint_impl.h` |
| `endpoint::contact_sensor::create()` (Identify + Boolean State + StateChange event) | `data_model/legacy/esp_matter_endpoint.cpp` |
| `endpoint::power_source::add()`, `cluster::power_source::config_t.feature_flags`, `feature::battery/replaceable` | `esp_matter_endpoint.cpp`, `esp_matter_cluster.cpp`, `esp_matter_feature_impl.h` |
| `cluster::power_source::attribute::create_bat_voltage/percent_remaining/present/common_designation/approved_chemistry` | `data_model/legacy/esp_matter_attribute.cpp` |
| `esp_matter::attribute::update()` (tự lấy CHIP lock; **không** dùng cho thuộc tính do SCI quản lý) | `data_model/esp_matter_attribute_utils.cpp`, `esp_matter_data_model.cpp::set_val()` |
| `data_model::provider::get_instance().registry().Get(ConcreteClusterPath)` | `data_model_provider/esp_matter_data_model_provider.h` |
| `chip::app::Clusters::BooleanStateCluster::SetStateValue()/GetStateValue()` | connectedhomeip `src/app/clusters/boolean-state-server/BooleanStateCluster.h` |
| `chip::app::ICDNotifier::GetInstance().NotifyNetworkActivityNotification()` | connectedhomeip `src/app/icd/server/ICDNotifier.h`; dùng y hệt trong `examples/icd_app/main/app_driver.cpp` |
| `CommissioningWindowManager::OpenBasicCommissioningWindow(Seconds32, CommissioningWindowAdvertisement)` | connectedhomeip `src/app/server/CommissioningWindowManager.h` |
| `esp_matter::factory_reset()` | `components/esp_matter/esp_matter_core.cpp` |
| `set_openthread_platform_config()` | connectedhomeip `src/platform/ESP32/OpenthreadLauncher.h` |
| `esp_pm_configure()`, `esp_pm_lock_*` | ESP-IDF `components/esp_pm` |
| `gpio_wakeup_enable()`, `esp_sleep_enable_ext1_wakeup_io()`, `esp_sleep_is_valid_wakeup_gpio()`, `gpio_hold_en()` | ESP-IDF `esp_driver_gpio/src/gpio.c`, `esp_hw_support/sleep_modes.c` |
| `esp_ieee802154_set_power_table()`, `esp_ieee802154_set_txpower()`, `esp_ieee802154_enable()` (bọc bằng linker wrap), `esp_openthread_lock_acquire()` | ESP-IDF `components/ieee802154/include/esp_ieee802154.h`, `components/openthread/include/esp_openthread_lock.h` |
| `esp_sleep_disable_wakeup_source()`, `esp_sleep_enable_timer_wakeup()`, `esp_deep_sleep_start()`, `RTC_NOINIT_ATTR`, `esp_reset_reason()` | ESP-IDF `esp_hw_support/include/esp_sleep.h`, `esp_common/include/esp_attr.h`, `esp_system` |
| `DeviceEventType::kCommissioningSessionStarted/Stopped`, `kCommissioningWindowClosed`, `kFailSafeTimerExpired`, `Server::GetFailSafeContext().IsFailSafeArmed()`, `SystemLayer().StartTimer()` | esp-matter `components/esp_matter/esp_matter.h` (sự kiện commissioning), connectedhomeip `src/include/platform/CHIPDeviceEvent.h`, `src/app/server/Server.h`, `src/system/SystemLayer.h` |
| `adc_oneshot_*`, `adc_cali_create_scheme_curve_fitting()` (`ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED` trên H2) | ESP-IDF `components/esp_adc` |

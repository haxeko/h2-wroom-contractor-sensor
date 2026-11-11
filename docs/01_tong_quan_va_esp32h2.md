# 01 – Tổng quan kiến trúc và phân tích ESP32-H2

Quy ước trạng thái dùng trong toàn bộ tài liệu:

| Ký hiệu | Ý nghĩa |
|---|---|
| ✅ **ĐÃ KIỂM CHỨNG** | Đối chiếu trực tiếp với datasheet/tài liệu nhà sản xuất, mã nguồn SDK, hoặc đã build thành công |
| 🧪 **CẦN THỬ NGHIỆM** | Hợp lý về lý thuyết nhưng chỉ khẳng định được bằng đo đạc trên PCB/vỏ thật |
| 💡 **ĐỀ XUẤT** | Lựa chọn thiết kế của tài liệu này; có thể thay đổi sau EVT |

Nguồn tham chiếu chính: ESP32-H2 Series Datasheet v1.3, ESP32-H2 Hardware Design Guidelines (bản HTML hiện hành), mã nguồn ESP-IDF v5.5.5 và esp-matter `release/v1.6` (connectedhomeip commit `75902a0c6`), datasheet TI DRV5032 (SLVSDC7H), DRV5012 (SLVSDD5), TPS63900 (SLVSET3D), TPS3839 (SBVS193D), TI AN043 (SWRA117D).

---

## 1. Kiến trúc tổng thể

```
                 ┌──────────────────────────────────────────────────────────────┐
 CR123A 3 V ──►  │ Q1 PMOS chống ngược cực ─► C bulk 2×22 µF ─► U2 TPS63900      │
 (Li-MnO2)       │ (AO3401A)                  (VBAT)            buck-boost 3.2 V │
                 └───────────────┬─────────────────────────────────────┬────────┘
                                 │ VBAT (đo bằng ADC qua phân áp     │ 3V2 (rail hệ thống)
                                 │  1M/1M đóng-ngắt bằng GPIO22)     │
                                 ▼                                   ▼
 ┌──────────┐ HALL_OUT  ┌───────────────────────────────────────────────────┐   LNA_IN   ┌────────┐  50 Ω  ┌──────┐  ┌──────────┐
 │ U3       ├──────────►│ GPIO10 (LP IO, EXT1 wake)        ANT (pin 32) ────┼──►CLC(CL) ─┤ J2 SWF ├────────┤ π ant├─►│ ANT1     │
 │ DRV5032FA│           │ GPIO9  ◄── SW1 (BOOT/commission/reset)            │   chip     │ (EVT)  │        │      │  │ MIFA     │
 └──────────┘           │ GPIO11 ──► D1 LED (giữ mức bằng gpio_hold)        │            └────────┘        └──────┘  │ AN043    │
                        │ GPIO1  ◄── VBAT/2 (ADC)  GPIO22 ── VBAT_EN         │                                       └──────────┘
 U4 TPS3839K33 ─RESET──►│ CHIP_EN                                           │
                        │ XTAL 32 MHz ±10 ppm (+ 32.768 kHz tùy chọn, DNP)  │
                        │ UART0 (GPIO23/24) ─► pad test / jig sản xuất       │
                        └───────────────────────────────────────────────────┘
                                          ESP32-H2FH4S (QFN32 4×4, 4 MB flash in-package)
```

Luồng hoạt động: thiết bị là **Matter Contact Sensor (0x0015)**, chạy **Thread MTD – Sleepy End Device** với cơ chế **ICD SIT** (Short Idle Time). Giữa các lần poll, SoC ở **light sleep** (miền TOP tắt, ~25–27 µA). Hall sensor tự lấy mẫu 5 Hz và giữ mức đầu ra; mọi thay đổi mức đánh thức SoC qua **EXT1** (LP IO). BLE chỉ dùng khi commissioning rồi bị giải phóng.

---

## 2. Chọn chip: ESP32-H2 dạng IC rời

### 2.1 Biến thể và phiên bản chip ✅

| Mã đặt hàng | Flash in-package | Nhiệt độ | Điện áp SPI |
|---|---|---|---|
| ESP32-H2FH2S | 2 MB (Quad SPI) | –40 ~ 105 °C | 3.3 V |
| **ESP32-H2FH4S** | **4 MB (Quad SPI)** | –40 ~ 105 °C | 3.3 V |

(Datasheet v1.3, bảng 1-1). Datasheet v1.3 được cập nhật theo **chip revision v1.2**; chân flash trong package không đưa ra ngoài.

**Kết luận: dùng ESP32-H2FH4S.** Lý do định lượng ở mục 2.3 (OTA cần 2 slot ≥ 1.6 MB).

> 🧪 Khi nhận hàng: đọc revision và kích thước flash thực tế bằng `esptool.py --chip esp32h2 chip_id` và `esptool.py flash_id`, ghi vào hồ sơ lô. ESP-IDF v5.5.5 có lựa chọn `CONFIG_ESP32H2_REV_MIN` = v0.0 / v0.1 / v0.2 / **v1.2** (`ESP32H2_REV_MIN_102`); firmware giữ mặc định v0.0 để chạy mọi revision. Khi xác nhận toàn bộ lô sản xuất là v1.2 có thể nâng `REV_MIN` lên v1.2 để bootloader từ chối chip cũ.

### 2.2 RAM có đủ cho Matter Contact Sensor? ✅ (số liệu build thực tế)

ESP32-H2 có 320 KB HP SRAM + 4 KB LP SRAM (datasheet §4.1). Kết quả `idf.py size` của firmware trong repo (ESP-IDF v5.5.5 + esp-matter release/v1.6, cấu hình ICD + BLE + OTA):

| Vùng | Dùng | Tổng khả dụng | Còn lại |
|---|---|---|---|
| DIRAM (.text IRAM + .data + .bss) | 189 954 B (73.6 %) | 258 000 B | **68 046 B** cho heap lúc khởi động |
| LP SRAM | 124 B | 4 096 B | 3 972 B |
| Flash code (.text + .rodata) | 1 540 150 B | — | — |

- Heap còn ~66 KB trước khi khởi động stack; BLE (NimBLE) chỉ được cấp khi commissioning và **được giải phóng sau khi commissioning** (`CONFIG_USE_BLE_ONLY_FOR_COMMISSIONING=y`, mặc định của connectedhomeip ESP32), Espressif chạy chính ví dụ `icd_app` trên H2 với cấu hình tương tự.
- 🧪 Bắt buộc đo `heap_caps_get_free_size()` và `heap_caps_get_minimum_free_size()` ở 3 thời điểm: trong commissioning BLE, sau commissioning, sau 24 h với 4 fabric. Ngưỡng chấp nhận đề xuất: minimum free heap ≥ 15 KB.

### 2.3 Flash, phân vùng, OTA ✅

Binary ứng dụng thực tế (bản sản xuất, log tối thiểu): **0x17FCC0 = 1 572 032 B (~1.50 MB)**; bản debug có log INFO lớn hơn khoảng 80 kB. Bảng phân vùng (giống `examples/icd_app` của Espressif):

| Phân vùng | Offset | Kích thước | Ghi chú |
|---|---|---|---|
| bootloader + partition table | 0x0 | 0xC000 | |
| esp_secure_cert | 0xD000 | 8 KB | DAC/PAI chứng thư (sản xuất) |
| nvs | 0x10000 | 48 KB | fabric, Thread dataset, bộ đếm |
| nvs_keys | — | 4 KB | khóa NVS encryption |
| otadata | — | 8 KB | |
| phy_init | — | 4 KB | |
| **ota_0** | 0x20000 | **1 920 KB** | ứng dụng |
| **ota_1** | 0x200000 | **1 920 KB** | ứng dụng (OTA) |
| fctry | 0x3E0000 | 24 KB | dữ liệu commissionable/device info |

- Mỗi slot còn trống **20 % (0x60340 ≈ 385 KB)** cho tính năng tương lai.
- Với **H2FH2S (2 MB)**: 2 slot × 1.50 MB = 3.0 MB > 2 MB ⇒ **không thể OTA dual-bank**. Phương án nếu buộc dùng 2 MB: (a) bỏ OTA (`CONFIG_ENABLE_OTA_REQUESTOR=n`, 1 slot 1.9 MB) – không khuyến nghị cho sản phẩm thương mại; (b) thêm flash SPI ngoài – **không khả thi trên H2FH2S** vì các chân SPI flash không đưa ra ngoài và H2 không có bộ điều khiển flash ngoài thứ hai cho XIP.
- **Kết luận:** không cần flash ngoài; dùng **ESP32-H2FH4S** là đủ cho Matter + OTA dual-bank.

### 2.4 Matter ICD trên ESP32-H2 ✅ / 🧪

- ✅ Mã nguồn connectedhomeip (`config/esp32/components/chip/Kconfig`) có `CONFIG_ENABLE_ICD_SERVER` (phụ thuộc `OPENTHREAD_MTD`), các thông số poll/idle/active, LIT, CIP, DSLS, UAT.
- ✅ esp-matter có ví dụ chính thức `examples/icd_app` "available for ESP32-H2 and ESP32-C6", với đo dòng ESP32-H2 DevKit: **sàn sleep 27.04 µA**, chu kỳ SIT poll 5 s trung bình 88 µA (TX 20 dBm).
- ✅ Ràng buộc chuẩn: SIT slow-poll ≤ 15 s được connectedhomeip **cưỡng chế bằng static_assert** (`ICDConfigurationData.h`, spec 9.16.1.5).
- 🧪 Khả năng **LIT** (Long Idle Time) chỉ có ích khi controller đăng ký ICD client (Check-In). Mức hỗ trợ thực tế của Apple Home / Google Home / Home Assistant / Aqara thay đổi theo phiên bản phần mềm — **không giả định**; thiết kế mặc định dùng **SIT**, LIT để dành cho thử nghiệm (xem `docs/08_firmware.md` §4).

### 2.5 Điện áp hoạt động ✅ (quyết định kiến trúc nguồn)

Datasheet bảng 5-2: **VDD3P3, VBAT, VDDA_PMU, VDDPST1, VDDPST2 = 3.0 V (min) / 3.3 V (typ) / 3.6 V (max)**; tuyệt đối max 3.6 V. Pin CR123A (Li-MnO2) có điện áp làm việc ~2.8–3.0 V khi có tải và sụt xuống tới 2.0 V cuối đời ⇒ **cấp trực tiếp từ pin vi phạm mức tối thiểu 3.0 V trong phần lớn tuổi thọ pin**. Phân tích đầy đủ và so sánh DC-DC ở `docs/02_nguon_pin.md`.

### 2.6 Dòng tiêu thụ theo datasheet ✅

| Chế độ | Dòng (datasheet v1.3) |
|---|---|
| 802.15.4 TX 20 dBm / 9 dBm / 0 dBm | 140 / 60 / 36 mA (peak) |
| 802.15.4 RX | 25 mA |
| BLE TX 0 dBm / RX | 36 / 24 mA |
| Modem-sleep 96 MHz CPU idle | 6 mA |
| Light-sleep, CPU + radio + **ngoại vi tắt** | **25 µA** |
| Light-sleep, CPU + radio tắt, ngoại vi còn điện | 85 µA |
| Deep-sleep | 7 µA |
| Power off (CHIP_EN = 0) | 1 µA |

Không dùng **Deep-sleep** vì deep-sleep reset CPU và làm mất trạng thái OpenThread/Matter (child phải attach lại, CASE session và subscription mất) — xem `docs/08_firmware.md` §3.

---

## 3. Bảng tổng hợp quyết định thiết kế

| # | Hạng mục | Quyết định | Trạng thái |
|---|---|---|---|
| 1 | SoC | ESP32-H2FH4S (4 MB) IC rời, QFN32 | ✅ |
| 2 | SDK | ESP-IDF v5.5.5 + esp-matter `release/v1.6` | ✅ build OK |
| 3 | Chế độ Thread/Matter | MTD + ICD SIT, slow poll 15 s, idle 3600 s | ✅ cấu hình / 🧪 tuổi thọ |
| 4 | Ngủ | Light sleep, TOP power-down (`PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP`, EXPERIMENTAL trong IDF 5.5) | ✅ API / 🧪 ổn định dài hạn |
| 5 | Nguồn | TPS63900 buck-boost 3.2 V, Iq 75 nA | ✅ datasheet / 🧪 hiệu suất thực |
| 6 | Chống ngược cực | PMOS AO3401A (thay được bằng DMG2305UX-7) + đế pin có định hướng | 💡 |
| 7 | Reset | TPS3839K33 (2.93 V, 150 nA) → CHIP_EN | 💡 |
| 8 | Hall | **A: DRV5032FADBZR** (omnipolar, push-pull, 20 Hz, 1.6 µA; FB 5 Hz 0.69 µA nếu giá cho phép) | ✅ datasheet / 🧪 khoảng cách |
| 9 | Anten | MIFA TI AN043 (15.2 × 5.7 mm) + π tuning + CLC phía chip | ✅ hình học / 🧪 hiệu suất trong vỏ |
| 10 | PCB | 4 lớp 1.0 mm, 36 × 18 mm, pin CR123A rời nối dây vào J1 (KiCad 10, `hardware/kicad/`) | 💡 |
| 11 | Công suất phát | 10 dBm mặc định (IDF mặc định 20 dBm) | 💡 / 🧪 tầm phủ |
| 12 | OTA | Matter OTA Requestor, 2 slot 1.92 MB | ✅ |
| 13 | Tuổi thọ pin | ~2.3–2.6 năm (thực tế, 10–20 lần/ngày, 1500–1700 mAh) | 🧪 phải đo |

---

## 4. Những điều KHÔNG được giả định

1. **Không** giả định cấp nguồn trực tiếp từ CR123A là hợp lệ (vi phạm 3.0 V min).
2. **Không** giả định deep-sleep giữ được kết nối Thread/Matter.
3. **Không** giả định LIT/Check-In được mọi controller hỗ trợ.
4. **Không** giả định anten đạt hiệu suất chỉ dựa vào mô phỏng hay vào app note: hình học AN043 được đo trên dongle CC2511 trong không khí; PCB 17 mm + vỏ nhựa + pin kim loại sẽ làm lệch cộng hưởng ⇒ bắt buộc quy trình VNA + đo bức xạ (docs/04).
5. **Không** giả định `esp_matter::attribute::update()` dùng được cho mọi cluster: với esp-matter v1.6, `BooleanState::StateValue` do `BooleanStateCluster` (code-driven) quản lý và `attribute::update()` trả về `ESP_ERR_NOT_SUPPORTED` (đã kiểm tra mã nguồn `esp_matter_data_model.cpp::set_val()`); firmware dùng `BooleanStateCluster::SetStateValue()`.
6. **Không** giả định số liệu dòng tiêu thụ: mọi con số trong docs/09 có nguồn và có tham số để thay bằng số đo.

# matter_contact_sensor – firmware ESP32-H2 (Matter over Thread, ICD)

Firmware cho cảm biến cửa: **ESP32-H2FH4S + DRV5032FA (Hall) + TPS63900 + CR123A** (bản chip rời `hardware/kicad`) và bản module ESP32-H2-WROOM-02C (`hardware/kicad_wroom`, cùng pin CR123A, cùng firmware).
Thiết kế chi tiết: [`../../docs/08_firmware.md`](../../docs/08_firmware.md).

## Phiên bản SDK đã kiểm chứng

| Thành phần | Phiên bản |
|---|---|
| ESP-IDF | **v5.5.5** |
| esp-matter | **release/v1.6** (connectedhomeip `75902a0c6`) |
| Target | `esp32h2` |

Kết quả build: `matter_contact_sensor.bin` = 0x17FCC0 B (1 572 032 B), slot OTA 0x1E0000 còn trống 20 %; DIRAM tĩnh 190 376 / 258 000 B.

## Cấu trúc

```
matter_contact_sensor/
├── CMakeLists.txt
├── sdkconfig.defaults          # BẢN SẢN XUẤT: ICD SIT, light sleep (TOP PD), BLE chỉ để commissioning, OTA, log tối thiểu
├── sdkconfig.defaults.debug    # lớp thêm khi phát triển: log INFO / CHIP PROGRESS (không dùng khi đo dòng)
├── partitions.csv              # 4 MB: 2 × 1.92 MB OTA
├── README.md
└── main/
    ├── CMakeLists.txt
    ├── Kconfig.projbuild       # chân GPIO, ngưỡng, thời gian, TX power
    ├── app_main.cpp            # khởi tạo + app task + sự kiện CHIP
    ├── matter_endpoint.cpp/.h  # Contact Sensor + Power Source, ICD, commissioning, factory reset
    ├── sensor/hall_sensor.cpp/.h
    ├── power/power_manager.cpp/.h          # light sleep, EXT1, TX power từ khung đầu, Deep-sleep, bảo vệ khởi động
    ├── power/uncommissioned_sleep.cpp/.h   # Deep-sleep khi chưa ghép nối và cửa sổ commissioning đã đóng
    ├── button/button.cpp/.h
    ├── battery/battery_monitor.cpp/.h
    └── led/status_led.cpp/.h
```

## Build / nạp

```bash
. $IDF_PATH/export.sh            # ESP-IDF v5.5.5
. $ESP_MATTER_PATH/export.sh     # esp-matter release/v1.6
idf.py set-target esp32h2
idf.py build                     # bản sản xuất: gần như không có log
idf.py -p /dev/ttyUSB0 flash monitor

# Bản phát triển có log (không dùng để đo dòng: UART giữ CPU thức)
idf.py -B build_debug -D SDKCONFIG=build_debug/sdkconfig \
       -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.debug" set-target esp32h2 build

# Bản module ESP32-H2-WROOM-02C (hardware/kicad_wroom): dùng đúng bản build mặc định ở trên
```

Vào chế độ nạp trên PCB: giữ nút (GPIO9 = BOOT) hoặc kéo TP5 xuống GND trong lúc reset (TP4) / cấp nguồn. GPIO8 đã có điện trở kéo lên R11 (bắt buộc cho Joint Download Boot).

## Sơ đồ chân mặc định (PCB rev A)

| Chức năng | GPIO | Kconfig |
|---|---|---|
| Hall OUT (DRV5032FA, push-pull, LOW = có nam châm) | 10 (LP IO, EXT1) | `CONFIG_CS_HALL_GPIO` |
| Nút commissioning/reset (active LOW) | 9 (LP IO, EXT1, strap BOOT) | `CONFIG_CS_BUTTON_GPIO` |
| LED đỏ (active HIGH) | 11 | `CONFIG_CS_LED_GPIO` (-1 = không có) |
| ADC đo pin (VBAT/2) | 1 (ADC1_CH0) | `CONFIG_CS_VBAT_ADC_GPIO` |
| Đóng/ngắt phân áp | 22 | `CONFIG_CS_VBAT_EN_GPIO` |
| UART0 TX / RX | 24 / 23 | — |

Với `CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP=y`, Hall và nút **phải** nằm trên GPIO7–14 (Kconfig ép dải này).

## Hành vi

| Thao tác | Kết quả |
|---|---|
| Cấp pin lần đầu | quảng bá BLE (tối đa 15 phút), LED nháy 30 ms/2 s |
| Hết 15 phút mà chưa commission | sau 60 s: **Deep-sleep** (~7 µA). Nhấn nút để thức dậy và mở cửa sổ mới (docs/08 §3.6) |
| Nhấn ngắn (chưa commission, còn thức) | mở lại cửa sổ BLE 300 s |
| Pin quá yếu lúc khởi động (< 2.2 V có tải, hoặc 3 lần brownout liên tiếp) | Deep-sleep 1 giờ rồi thử lại; nút đánh thức sớm |
| Nhấn ngắn (đã commission) | ICD Active mode, đo pin, kiểm tra lại Hall, LED nháy 1 lần |
| Giữ 5 s | LED nháy nhanh (cảnh báo reset) |
| Giữ ≥ 10 s rồi thả | factory reset |
| Identify từ app | LED nháy 1 Hz |
| Cửa đóng/mở | BooleanState.StateValue = true/false + sự kiện StateChange |

## Thử nhanh với chip-tool

```bash
chip-tool pairing ble-thread 1 hex:<operational_dataset> 20202021 3840
chip-tool booleanstate read state-value 1 1
chip-tool booleanstate subscribe state-value 1 600 1 1
chip-tool booleanstate read-event state-change 1 1
chip-tool powersource read bat-voltage 1 1
chip-tool icdmanagement read idle-mode-duration 1 0
```
`20202021` / `3840` là dữ liệu commissioning **thử nghiệm** của SDK; sản phẩm dùng dữ liệu nhà máy (`esp-matter-mfg-tool`, `esp_secure_cert`).

## Thử trên ESP32-H2-DevKitM-1

Devkit không có mạch phân áp đo pin: đặt `CONFIG_CS_BOOT_MIN_MV=0` (chân ADC thả nổi có thể đọc ra giá trị "pin yếu" làm chip Deep-sleep ngay lúc khởi động). Nút BOOT của devkit nối GPIO9 nên dùng được ngay; gắn module Hall DRV5032 vào GPIO10/3V3/GND. LED RGB địa chỉ hóa trên devkit không phải LED đơn ⇒ đặt `CONFIG_CS_LED_GPIO=-1` hoặc gắn LED + điện trở ngoài vào GPIO11. Khi đo dòng trên devkit cần tách mạch USB-UART/LED nguồn của devkit (chúng tiêu thụ mA).

## Ghi chú quan trọng về API (esp-matter v1.6)

`BooleanState::StateValue` do `chip::app::Clusters::BooleanStateCluster` (code-driven) quản lý: `esp_matter::attribute::update()` trả về `ESP_ERR_NOT_SUPPORTED` cho thuộc tính này. Firmware lấy cluster từ `data_model::provider::get_instance().registry()` và gọi `SetStateValue()` (tự sinh sự kiện StateChange). Thuộc tính Power Source vẫn cập nhật bằng `attribute::update()`.

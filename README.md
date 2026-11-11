# h2-wroom-contractor-sensor

**Cảm biến cửa Matter over Thread dùng module ESP32-H2-WROOM-02C, cảm biến Hall DRV5032FA, pin CR123A rời.**
PCB 32 × 20 mm **2 lớp**, anten của module nhô ra 6 mm ngoài mép board. Repo gồm thiết kế KiCad 10 đầy đủ (sơ đồ, PCB, file sản xuất) và firmware ESP-IDF / esp-matter.

Repo này tách từ [`haxeko/matter-thread-contractor`](https://github.com/haxeko/matter-thread-contractor) (commit `2f9c032` trên `main`). Repo gốc có thêm bản dùng chip ESP32-H2 rời với anten in trên PCB, 4 lớp. Mạch ngoài module (nguồn, chống ngược cực, reset, nút, Hall, LED, đo pin) và firmware của hai bản giống hệt nhau.

Quy ước trạng thái: ✅ **đã kiểm chứng** (datasheet / mã nguồn SDK / đã build) · 🧪 **cần thử nghiệm** trên phần cứng thật · 💡 **đề xuất** thiết kế.

## Nội dung

| Thư mục / file | Nội dung |
|---|---|
| [`docs/12_ban_module_wroom.md`](docs/12_ban_module_wroom.md) | **Tài liệu chính của board này**: ánh xạ chân, PCB 2 lớp, bảng pad test cho jig, file sản xuất, pin CR123A và vỏ, vì sao không dùng pin cúc áo CR2450 |
| [`hardware/kicad_wroom/`](hardware/kicad_wroom/) | Dự án KiCad 10: sơ đồ, PCB, luật thiết kế, báo cáo DRC |
| [`hardware/kicad_wroom/fab/`](hardware/kicad_wroom/fab/) | **File đặt hàng**: `matter_contact_sensor_wroom-gerber.zip`, `assembly/…-bom.csv`, `assembly/…-cpl.csv`, PDF sơ đồ / lắp ráp / từng lớp, ảnh render |
| [`hardware/kicad/mcs.*`](hardware/kicad/) | Thư viện symbol/footprint riêng của dự án (module WROOM, pad dây pin…), dùng qua `../kicad/mcs.*` |
| [`firmware/matter_contact_sensor/`](firmware/matter_contact_sensor/) | Firmware ESP-IDF v5.5.5 + esp-matter release/v1.6 (C++), build thành công cho esp32h2 |
| [`docs/01`](docs/01_tong_quan_va_esp32h2.md), [`02`](docs/02_nguon_pin.md), [`03`](docs/03_hall_sensor.md) | Tổng quan và ESP32-H2, nguồn pin (TPS63900, chống ngược cực), cảm biến Hall và nam châm |
| [`docs/08`](docs/08_firmware.md), [`09`](docs/09_battery_life.md), [`10`](docs/10_test_plan.md), [`11`](docs/11_lo_trinh_trien_khai.md) | Firmware, tuổi thọ pin, kế hoạch thử, lộ trình |
| [`tools/`](tools/) | Script sinh thiết kế (`design_data*.py`, `tools/kicad/`) và tính toán (tuổi thọ pin, nam châm, pin cúc áo) |

**Tài liệu của bản chip rời** (docs/04 anten, 05 sơ đồ, 06 PCB, 07 BOM, `hardware/bom/bom.csv`, `hardware/antenna/`, `tools/cpwg_impedance.py`) được giữ lại để tham khảo, vì phần mạch ngoài module giống nhau. Các tọa độ, kích thước board và số lớp trong đó là của **bản chip rời**, không phải board này. File PCB của bản chip rời không có trong repo này.

## Thông số chính

| Hạng mục | Giá trị |
|---|---|
| Module | **ESP32-H2-WROOM-02C-H4S** (4 MB flash, anten PCB): đủ chỗ cho OTA 2 slot |
| PCB | **32 × 20 mm, 2 lớp**, dày 1.0 mm, linh kiện một mặt; via 0.6 / 0.3 mm, không có lỗ nhỏ hơn 0.3 mm (không bị JLCPCB tính phí 4-Wire Kelvin Test); đường / khe nhỏ nhất 0.15 / 0.17 mm. ✅ ERC 0, DRC 0 vi phạm / 0 kết nối hở / 0 lệch sơ đồ |
| BOM lắp ráp | 18 dòng / 27 linh kiện, nhỏ nhất 0402 |
| Nguồn | CR123A rời, hàn 2 dây vào J1 (pad vuông = +) → PMOS AO3401A chống ngược cực → **TPS63900** buck-boost 3.2 V (Iq 75 nA), không cần tụ lớn |
| Hall | **DRV5032FADBZR**, GPIO10 (LP IO, đánh thức EXT1) |
| Matter | Contact Sensor + Power Source trên endpoint 1; ICD **SIT** (slow poll 15 s, idle 3600 s) |
| Firmware | image 1.50 MB (slot OTA còn 20 %); TX 802.15.4 10 dBm ngay từ khung đầu, Deep-sleep khi chưa ghép nối, bảo vệ khi pin yếu, log mức sản xuất |
| Tuổi thọ pin (ước tính) | **~2.3–2.6 năm** ở 10–20 lần đóng/mở mỗi ngày (CR123A 1500–1700 mAh) – 🧪 phải đo dòng ngủ thật của module |

## Đặt PCB / lắp ráp

1. Tải `hardware/kicad_wroom/fab/matter_contact_sensor_wroom-gerber.zip` lên nhà sản xuất: **2 lớp, 1.0 mm** (0.8–1.6 mm đều được, không cần kiểm soát trở kháng), đồng 1 oz, khuyên dùng ENIG.
2. Lắp ráp SMT: `assembly/matter_contact_sensor_wroom-bom.csv` + `assembly/matter_contact_sensor_wroom-cpl.csv`. Kiểm tra góc xoay trên ảnh xem trước, nhất là module U1 (anten hướng ra mép trái).
3. Pin, tiếp điểm pin và dây không có trong BOM lắp ráp: lắp tay sau khi test (docs/12 §7).
4. Jig nạp / test: bảng pad test ở docs/12 §3.

## Sinh lại thiết kế

```bash
# KiCad 10 + kicad-cli; pcbnew Python = /usr/bin/python3.12 trên Ubuntu
python3 tools/kicad/gen_libs.py                          # thư viện mcs.*
python3 tools/kicad/gen_schematic.py --variant wroom     # sơ đồ từ tools/design_data_wroom.py
/usr/bin/python3.12 tools/kicad/build_pcb_wroom.py       # đặt linh kiện, đi dây, đổ đồng, DRC
python3 tools/kicad/export_fab.py --variant wroom        # Gerber, khoan, BOM, CPL, PDF, ảnh -> hardware/kicad_wroom/fab/
python3 tools/battery_life.py                            # tuổi thọ pin (thay số đo thật bằng tham số)
python3 tools/magnet_field.py                            # chọn nam châm
```
Luôn dùng `--variant wroom`: không có tham số này các script nhắm vào bản chip rời, mà file của bản đó không có trong repo. `build_pcb_wroom.py` cho ra đúng PCB đang có trong repo (đã kiểm tra: cùng 285 đoạn đường và via).

## Build firmware

```bash
. $IDF_PATH/export.sh            # ESP-IDF v5.5.5
. $ESP_MATTER_PATH/export.sh     # esp-matter release/v1.6
cd firmware/matter_contact_sensor
idf.py set-target esp32h2 && idf.py build
```
Bản phát triển có log: thêm `-D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.debug"` (xem `firmware/matter_contact_sensor/README.md`).

## Phạm vi và giới hạn

- Chưa có phép đo phần cứng nào: mọi con số "thực tế" là ước tính có nguồn, đánh dấu 🧪, kèm quy trình đo.
- Việc cần làm trên mạch mẫu: docs/12 §6 và docs/10 (B-04 … B-09), đặc biệt đánh thức từ Deep-sleep bằng nút trên chân strap BOOT (GPIO9), gợn nguồn 3V2 khi phát và tầm phủ sóng của board 2 lớp.
- Dữ liệu commissioning trong firmware là dữ liệu **TEST** của SDK; sản phẩm thật cần VID/PID, DAC, dữ liệu nhà máy và chứng nhận CSA.

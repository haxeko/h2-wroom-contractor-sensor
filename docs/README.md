# Tài liệu

Số thứ tự giữ nguyên như khi viết (các tài liệu tham chiếu nhau bằng số, ví dụ "docs/common/08 §3.6").

## Chung cho cả hai board – [`common/`](common/)

| # | Tài liệu | Nội dung |
|---|---|---|
| 01 | [Tổng quan và ESP32-H2](common/01_tong_quan_va_esp32h2.md) | kiến trúc, chọn chip, RAM/Flash/OTA, ICD, bảng quyết định |
| 02 | [Nguồn pin](common/02_nguon_pin.md) | CR123A và dải 3.0–3.6 V, TPS63900, chống ngược cực, giám sát nguồn, đo pin |
| 03 | [Cảm biến Hall](common/03_hall_sensor.md) | DRV5032FA, phát hiện 2 trạng thái khi ngủ, tính nam châm |
| 08 | [Firmware](common/08_firmware.md) | kiến trúc, SED / ICD, chế độ ngủ, bảo vệ pin (§3.6), commissioning, OTA, sdkconfig |
| 09 | [Tuổi thọ pin](common/09_battery_life.md) | ngân sách dòng, 3 kịch bản, cách đo |
| 10 | [Kế hoạch thử](common/10_test_plan.md) | Apple / Google / HA / Aqara, test sản xuất, chứng nhận |
| 11 | [Lộ trình](common/11_lo_trinh_trien_khai.md) | 10 giai đoạn, cổng nghiệm thu, rủi ro |

## Bản module ESP32-H2-WROOM-02C – [`wroom/`](wroom/)

| # | Tài liệu | Nội dung |
|---|---|---|
| 12 | [Bản module](wroom/12_ban_module_wroom.md) | ánh xạ chân, PCB 2 lớp, pad test, file sản xuất, pin CR123A và vỏ, vì sao không dùng CR2450 |

## Bản chip ESP32-H2 rời – [`chip/`](chip/)

| # | Tài liệu | Nội dung |
|---|---|---|
| 04 | [Anten và RF](chip/04_antenna_rf.md) | MIFA TI AN043, matching, GCPW 50 Ω, quy trình VNA |
| 05 | [Sơ đồ nguyên lý](chip/05_schematic.md) | sơ đồ theo khối, bảng chân, bảng GPIO, test point (phần ngoài MCU dùng chung với bản module) |
| 06 | [PCB](chip/06_pcb_layout.md) | stack-up 4 lớp, bố trí, quy tắc RF, pad test, lắp vỏ |
| 07 | [BOM](chip/07_bom.md) | hãng, mã, mã thay thế, giá; rà soát giá (§5) |

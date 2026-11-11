# 11 – Lộ trình triển khai 10 giai đoạn

Thời lượng là ước lượng cho một nhóm nhỏ (1 HW, 1 FW, 1 ME, hỗ trợ RF/test bên ngoài); các giai đoạn 6–9 chạy song song một phần.

| GĐ | Mục tiêu | Công việc chính | Đầu ra | Cổng nghiệm thu (exit criteria) | Thời gian |
|---|---|---|---|---|---|
| 1 | Kiểm tra khả năng triển khai Matter trên ESP32-H2 bare chip | Dựng SDK (IDF v5.5.5 + esp-matter release/v1.6); build `firmware/matter_contact_sensor` ✅ (đã làm); chạy trên ESP32-H2-DevKitM-1 (Hall gắn ngoài, nút BOOT = GPIO9): commission 4 hệ sinh thái; đo sàn sleep & điện tích poll bằng PPK2 | log commission, số đo dòng, heap tối thiểu | Commission OK trên Apple/Google/HA; sàn sleep ≤ 30 µA trên devkit; free heap tối thiểu ≥ 15 KB | 2–3 tuần |
| 2 | Chốt Hall sensor và mạch nguồn | Board thử nhỏ: DRV5032FA + nam châm theo `tools/magnet_field.py`; đo khoảng cách đóng/mở 30 mẫu; board TPS63900 + PMOS: đo hiệu suất 10 µA–150 mA, droop khi TX 20 dBm, UVLO, lắp ngược | báo cáo Hall + nguồn; chọn nam châm | khe đóng chắc chắn ≥ 10 mm; droop VDD3P3 ≤ 100 mV; hiệu suất ≥ 85 % @ 30 µA | 2 tuần (song song GĐ1) |
| 3 | Schematic hoàn chỉnh | Schematic KiCad đã sinh (`hardware/kicad/`, từ `tools/design_data.py`, ERC 0 lỗi); review chéo với checklist Espressif | schematic rev A, BOM rev A | ERC sạch; review checklist Espressif đủ mục (nguồn, reset, XTAL, RF, strap, UART, ADC) | 1 tuần |
| 4 | Anten PCB và RF matching | Footprint `Texas_SWRA117D_2.4GHz_Right` + 3 biến thể L1 (đã đặt trong PCB rev A); mô phỏng EM (tùy chọn: openEMS/Sonnet/HFSS) cho PCB 18 mm + vỏ; stub, GCPW, J2 đã có trong layout | layout khối RF, kế hoạch tuning | mô phỏng (nếu có) cho f_res trong vỏ 2.40–2.50 GHz – **chỉ để định hướng**; quyết định cuối theo đo GĐ8 | 1–2 tuần |
| 5 | PCB và DRC | PCB rev A đã sinh bằng `tools/kicad/build_pcb.py` (docs/06); kỹ sư layout rà soát; impedance control; DFM với nhà sản xuất; panel EVT gồm 3 biến thể anten | Gerber/ODB++, pick&place, stencil | DRC/DFM sạch; nhà sản xuất xác nhận stack-up/trở kháng; review layout RF/nguồn/XTAL | 2 tuần |
| 6 | Firmware Matter over Thread | Chạy firmware trên PCB EVT; hoàn thiện chế độ test sản xuất (UART); cấu hình sản xuất (log, factory data, secure boot, flash encryption, rollback); thử LIT/DSLS | firmware v0.9 + công cụ sản xuất | toàn bộ test C-*, R-*, F-*, M-* đạt trên EVT | 3–4 tuần |
| 7 | Dòng tiêu thụ và tối ưu pin | Đo theo docs/09 §6; tối ưu slow poll/idle mode/TX power; cân nhắc 32.768 kHz (Y2); cập nhật mô hình | báo cáo năng lượng; tham số ICD chốt | ước tính thực tế ≥ 2 năm (kịch bản bình thường, 1500 mAh) với số đo thật | 2 tuần |
| 8 | RF, anten, ổn định Thread | VNA trong vỏ (docs/04 §5), chọn biến thể L1 và giá trị π; đo dẫn qua J2; OTA/TRP hoặc phép so sánh nội bộ; test RF-01..03, N-*, AQ-*; tiền kiểm FCC/CE | BOM RF chốt, báo cáo RF | S11 ≤ –10 dB trong vỏ; TRP ≥ P_cond – 4 dB; lệch tần ≤ ±10 ppm; tiền kiểm phát xạ đạt biên ≥ 3 dB | 3–4 tuần |
| 9 | Vỏ và tích hợp nam châm | Thiết kế vỏ (PCB 36 × 18 mm + ngăn pin CR123A riêng, nối dây) theo docs/06 §9; vỏ nam châm cùng độ cao die Hall; khuôn mẫu in 3D → khuôn thật; thử rơi, tháo lắp pin, ESD tiếp điểm | file CAD, mẫu vỏ | test H-01/H-02 đạt với vỏ thật; RF-03 đạt với vật liệu vỏ cuối | 4–6 tuần (song song GĐ6–8) |
| 10 | Kiểm tra trước sản xuất hàng loạt | DVT (≥ 50 máy): toàn bộ ma trận docs/10; chứng nhận Matter/Thread/BT/FCC/CE; PVT (≥ 300 máy) trên dây chuyền với jig FCT; L-01 90 ngày; báo cáo yield | hồ sơ chứng nhận, jig FCT, quy trình sản xuất | yield FCT ≥ 98 %; không lỗi nghiêm trọng mở; chứng nhận đạt | 8–12 tuần |

## Rủi ro chính và biện pháp

| Rủi ro | Mức | Biện pháp |
|---|---|---|
| Anten lệch cộng hưởng mạnh trong vỏ / gần pin | Cao | 3 biến thể L1 trên panel EVT; π tuning; giữ ≥ 25 mm tới pin; J2 cho đo dẫn |
| Sàn sleep ESP32-H2 cao hơn kỳ vọng trên board thật (rò PCB, cấu hình) | Trung bình | đo sớm ở GĐ1 trên devkit; kiểm tra từng nguồn rò; `gpio_reset_pin` chân thừa; tắt USJ/console |
| `PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP` là EXPERIMENTAL trong IDF 5.5 | Trung bình | test dài hạn L-01; phương án dự phòng: tắt TOP PD (+~60 µA, tuổi thọ ~1 năm) – không chấp nhận được ⇒ theo dõi bản sửa IDF |
| Controller không hỗ trợ LIT | Thấp (đã thiết kế SIT) | LIT chỉ là tối ưu thêm |
| Thread networks tách rời giữa Apple/Aqara | Trung bình | hướng dẫn người dùng; test AQ-* |
| Lead-time linh kiện RF 0201 / đầu nối RF J2 | Trung bình | đặt sớm; linh kiện tương đương đã liệt kê |
| Chứng nhận vô tuyến cho thiết kế chip rời | Trung bình | tiền kiểm ở GĐ8; khóa công suất TX trong firmware |

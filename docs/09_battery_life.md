# 09 – Ước tính tuổi thọ pin CR123A

Công cụ: `tools/battery_life.py` (mọi tham số có nguồn ghi trong mã; tham số "ESTIMATE" phải thay bằng số đo). Chạy lại với số đo thật, ví dụ:
`python3 tools/battery_life.py --sleep-ua 24.5 --q-poll-mc 0.27 --subscribers 3`

## 1. Mô hình

**Định nghĩa kịch bản:** 1 "lần đóng/mở" = 1 chu kỳ MỞ + ĐÓNG = **2 báo cáo** Matter.

| Thành phần (trên rail 3V2) | Mô hình | Nguồn số liệu |
|---|---|---|
| Sàn sleep ESP32-H2 (light sleep, TOP PD) | 27.0 µA | ✅ đo của Espressif trong `esp-matter/examples/icd_app` (H2 SIT: 27.04 µA); datasheet: 25 µA typ |
| DRV5032FA (20 Hz) | 1.6 µA | ✅ datasheet (3.5 µA max); bản FB 5 Hz: 0.69 µA |
| TPS3839K33 | 0.15 µA | ✅ datasheet |
| Rò PCB/tụ/pad | 0.3 µA | ESTIMATE |
| Một lần Thread poll | 0.30 mC @ 20 dBm → **0.235 mC @ 10 dBm** | ✅ suy ra từ hình đo `icd_app` (1.769 mC/20 s – sàn 27 µA, 4 poll); hiệu chỉnh TX theo bảng 5-7 datasheet (120 → 65 mA trong 1.2 ms) |
| Poll định kỳ | Q_poll / 15 s | Kconfig |
| Chu kỳ ICD Idle→Active (3600 s) | 2 fast poll + mỗi subscriber 1 báo cáo keep-alive (1.2 mC) | báo cáo: ESTIMATE |
| Mỗi sự kiện cửa | 0.1 mC (đánh thức + debounce) + subscriber × 1.2 mC + 2 fast poll | ESTIMATE |
| Đo pin | 2 lần/ngày × 0.3 mC | ước tính |
| DC-DC | I_pin = I_rail·3.2 V /(0.90 · 2.95 V) + 75 nA | ✅ datasheet TPS63900 (η ~90 % ở 10 µA–10 mA, Fig. 8-7) |
| Commissioning | 1.0 mAh một lần | ESTIMATE |

**Lý thuyết** = 100 % dung lượng danh định, dòng danh định.
**Thực tế dự kiến** = 85 % dung lượng khả dụng (xung tải, nhiệt độ, lão hóa, chênh lệch nhãn pin) + tự xả 1.5 %/năm + 20 % biên cho mọi dòng động (truyền lại, đổi parent, nhiễu Wi-Fi, controller đọc thêm…).

## 2. Kết quả – cấu hình mặc định (TX 10 dBm, slow poll 15 s, idle 3600 s, 2 subscriber)

### Phân bổ dòng trung bình trên rail 3V2 (uA)

| Kịch bản | Lần đóng/mở/ngày | sleep+always-on | thread polls | ICD keep-alive | door events | battery meas. | Tổng rail |
|---|---|---|---|---|---|---|---|
| Bình thường | 10 | 29.05 | 15.64 | 0.80 | 0.69 | 0.01 | 46.2 |
| Bình thường | 20 | 29.05 | 15.64 | 0.80 | 1.37 | 0.01 | 46.9 |
| Sử dụng nhiều | 50 | 29.05 | 15.64 | 0.80 | 3.44 | 0.01 | 48.9 |
| Sử dụng nhiều | 100 | 29.05 | 15.64 | 0.80 | 6.87 | 0.01 | 52.4 |
| Rất nhiều | 200 | 29.05 | 15.64 | 0.80 | 13.75 | 0.01 | 59.2 |

### Tuổi thọ pin (năm)

| Kịch bản | Lần đóng/mở/ngày | I pin lý thuyết (uA) | Lý thuyết 1500 mAh | Lý thuyết 1700 mAh | I pin thực tế (uA) | Thực tế 1500 mAh | Thực tế 1700 mAh |
|---|---|---|---|---|---|---|---|
| Bình thường | 10 | 55.7 | 3.07 | 3.48 | 62.4 | 2.33 | 2.63 |
| Bình thường | 20 | 56.6 | 3.03 | 3.43 | 63.4 | 2.29 | 2.59 |
| Sử dụng nhiều | 50 | 59.0 | 2.90 | 3.28 | 66.4 | 2.19 | 2.47 |
| Sử dụng nhiều | 100 | 63.2 | 2.71 | 3.07 | 71.4 | 2.04 | 2.30 |
| Rất nhiều | 200 | 71.5 | 2.39 | 2.71 | 81.3 | 1.79 | 2.02 |

### Độ nhạy (kịch bản 20 lần/ngày, 1500 mAh, thực tế)

| Thay đổi | I pin (uA) | Tuổi thọ (năm) |
|---|---|---|
| Mặc định | 63.4 | 2.29 |
| TX 20 dBm (mặc định ESP-IDF) | 69.9 | 2.08 |
| TX 0 dBm | 59.9 | 2.43 |
| Slow poll 5 s | 108.7 | 1.34 |
| Slow poll 10 s | 74.7 | 1.95 |
| Idle mode 600 s (cấu hình cũ) | 69.2 | 2.10 |
| Idle mode 1800 s | 64.6 | 2.25 |
| 1 subscriber | 62.1 | 2.34 |
| 4 subscriber (Apple+Google+HA+Aqara) | 66.0 | 2.20 |
| LIT 60 s (nếu controller đăng ký ICD) | 46.5 | 3.13 |
| Sleep floor 20 uA (nếu đo được thấp hơn) | 55.0 | 2.64 |
| Sleep floor 35 uA (board kém) | 73.1 | 1.99 |
| Vout 3.3 V | 65.3 | 2.23 |
| Hiệu suất DC-DC 85 % | 67.0 | 2.17 |

Trường hợp xấu (TX 20 dBm như mặc định ESP-IDF + 4 subscriber Apple/Google/HA/Aqara):

| Kịch bản | Lần đóng/mở/ngày | Lý thuyết 1500 mAh | Thực tế 1500 mAh | Thực tế 1700 mAh |
|---|---|---|---|---|
| Bình thường | 10–20 | 2.67–2.74 năm | 2.01–2.06 năm | 2.26–2.32 năm |
| Sử dụng nhiều | 50–100 | 2.24–2.49 năm | 1.67–1.87 năm | 1.88–2.10 năm |
| Rất nhiều | 200 | 1.87 năm | 1.38 năm | 1.56 năm |

## 3. Tóm tắt cho 3 kịch bản yêu cầu

| Kịch bản | Dòng pin trung bình (thực tế) | Tuổi thọ lý thuyết | **Tuổi thọ thực tế dự kiến** (1500–1700 mAh) |
|---|---|---|---|
| Bình thường 10–20 lần/ngày | ~62–63 µA | 3.0–3.5 năm | **~2.3–2.6 năm** |
| Nhiều 50–100 lần/ngày | ~66–71 µA | 2.7–3.3 năm | **~2.0–2.5 năm** |
| Rất nhiều 200 lần/ngày | ~81 µA | 2.4–2.7 năm | **~1.8–2.0 năm** |

**Dòng standby mục tiêu** (đo trên rail 3V2 giữa hai poll, cửa không đổi): **≤ 30 µA** (chip 27 µA + Hall + giám sát + rò). Dòng trung bình mục tiêu ở pin, kịch bản bình thường: **≤ 65 µA**.

**Bản module** (docs/12) dùng cùng pin CR123A và cùng firmware nên dùng chung các bảng trên; 🧪 dòng ngủ thật của module phải đo lại. Pin cúc áo CR2450 đã bị loại: ESP32-H2 chỉ dùng được khoảng 40 % dung lượng của nó, tức khoảng 0.5 năm (docs/12 §8, `python3 tools/coin_cell_buffer.py`).

**Các con số trên giả định firmware bản sản xuất** (docs/08 §3.6): log tối thiểu, keep-alive 1 giờ, TX đúng công suất từ khung đầu, thiết bị đã ghép nối. Bản debug (log INFO) và thiết bị chưa ghép nối tiêu thụ nhiều hơn đáng kể.

## 4. Nhận xét kỹ thuật (trung thực về giới hạn)

1. **Sàn light-sleep ~25–27 µA của ESP32-H2 chiếm ~55 % ngân sách**; các SoC Thread chuyên pin (sàn 1–5 µA) đạt 5+ năm với cùng pin. Với ESP32-H2, 2–3 năm là mức thực tế; đây là hệ quả của lựa chọn chip bắt buộc, không phải của thiết kế board.
2. Poll Thread là thành phần động lớn nhất (~15.6 µA @ 15 s). Mỗi poll trên H2 tốn ~0.24–0.3 mC (đánh thức từ TOP PD, khôi phục ngữ cảnh, radio) – lớn hơn nhiều so với thời gian truyền thuần.
3. Đòn bẩy giảm tiêu thụ còn lại, theo thứ tự hiệu quả: **LIT 60 s (+0.8 năm, phụ thuộc controller)** > sàn sleep thấp hơn (board sạch rò) > TX 0 dBm (+0.14 năm, đánh đổi tầm phủ) > ít subscriber. Idle mode 3600 s (+0.19 năm so với 600 s) đã được áp dụng.
4. Không có phương án deep-sleep hợp lệ với Matter ICD khi đang hoạt động (docs/08 §3.4); deep-sleep chỉ dùng khi chưa ghép nối hoặc pin quá yếu (docs/08 §3.6).
6. **Thiết bị chưa ghép nối** mà không có cơ chế Deep-sleep sẽ tốn vài mA liên tục (BLE giữ thạch anh chính chạy): cạn CR123A trong khoảng 2 tuần. Firmware đã xử lý (docs/08 §3.6); phải đo lại trên phần cứng.
5. Cấp trực tiếp từ pin (ngoài spec 3.0 V) chỉ cho ~3.65 năm lý thuyết **nếu** chip chạy được tới cuối pin – không phải phương án hợp lệ.

## 5. Các yếu tố làm giảm tuổi thọ

- Nhiệt độ thấp (< 0 °C): dung lượng khả dụng và điện áp dưới tải giảm; DC-DC phải kéo dòng lớn hơn.
- Vị trí xa parent: truyền lại MAC/MRP, poll thất bại, đổi parent; công suất TX phải tăng.
- Nhiều hệ sinh thái (subscriber) và controller đọc/subscribe dày; IdleModeDuration ngắn.
- Mạng Thread bất ổn (border router khởi động lại, phân mảnh mạng) ⇒ attach lại, khôi phục subscription.
- LED dùng nhiều (commissioning lặp lại, cấu hình nháy theo sự kiện).
- OTA thường xuyên (~0.5–1 mAh/lần).
- Rò rỉ do bẩn flux/độ ẩm trên PCB (phân áp 1 MΩ nhạy với rò) – cần rửa sạch và phủ (conformal coating nếu cần).
- Pin kém chất lượng/hàng giả; pin đã lưu kho lâu.

## 6. Đo dòng thực tế bằng thiết bị đo dòng siêu thấp 🧪

Thiết bị phù hợp: **Nordic Power Profiler Kit II** (0.2 µA–1 A, 100 kS/s), **Qoitech Otii Arc/Ace**, **Joulescope JS220** (dải động nA–A, 1 MS/s) hoặc Keysight N6705C + N6781A. Đồng hồ vạn năng **không** đo đúng được dạng xung ms này.

Quy trình:
1. **Điểm đo**: (a) ở **pin** (thay pin bằng nguồn của thiết bị đo đặt 3.0 V, nối vào TP3/VBAT – đo cả DC-DC); (b) ở **rail 3V2** (cắt R5 hoặc dùng jumper tùy chọn ở đầu ra DC-DC) để tách tổn hao DC-DC.
2. Tắt console UART trong firmware đo (hoặc tháo dây UART – dòng rò qua bộ chuyển đổi USB-UART làm sai số chục µA).
3. Commission vào mạng Thread thật (Apple TV/HomePod hoặc OTBR), chờ 10 phút cho trạng thái ổn định.
4. Ghi liên tục **≥ 1 giờ** (≥ 24 h cho số liệu cuối) ở ≥ 100 kS/s; đánh dấu: sàn sleep, từng poll (đo điện tích tích phân mỗi xung), chu kỳ Idle→Active, một sự kiện mở/đóng, đo pin.
5. Thay các tham số `--sleep-ua`, `--q-poll-mc` và các ESTIMATE trong `tools/battery_life.py` bằng số đo; lặp lại với 1, 2, 4 subscriber; TX 0/10/20 dBm; khoảng cách gần/xa parent.
6. Kiểm chứng dài hạn: 5 thiết bị × 3 tháng ở tốc độ đóng/mở tự động 200 lần/ngày (jig servo nam châm) + đo điện áp pin hằng tuần ⇒ ngoại suy, so với mô hình.

# 10 – Kế hoạch kiểm thử và tương thích

Mọi mục ở đây là 🧪 **CẦN THỬ NGHIỆM**. Mỗi test có ID để truy vết kết quả trong báo cáo EVT/DVT/PVT.

## 1. Môi trường thử

| Hệ sinh thái | Controller | Thread Border Router | Ghi chú |
|---|---|---|---|
| Apple Home | iPhone (iOS bản mới nhất + bản trước) | Apple TV 4K / HomePod mini / HomePod (2nd gen) | |
| Google Home | Android + app Google Home | Nest Hub (2nd gen) / Nest Hub Max / Nest Wifi Pro / Google TV Streamer | |
| Home Assistant | Matter Server (python-matter-server) | OpenThread Border Router add-on + radio Thread (ví dụ Home Assistant Connect ZBT-1) | dễ đọc log, thuộc tính, Thread diagnostics |
| Aqara | app Aqara Home | **Aqara Hub M3** (Thread BR + Matter controller) | |
| Công cụ dev | chip-tool (connectedhomeip), ot-ctl (OTBR) | OTBR trên Raspberry Pi + RCP ESP32-H2 | sniffer 802.15.4 (ESP32-H2 RCP + Wireshark), sniffer BLE |

Thiết bị đo: PPK2/Otii/Joulescope, VNA, máy phân tích phổ, hộp chống nhiễu, nguồn lập trình được (mô phỏng pin), buồng nhiệt –10…+50 °C, gaussmeter, jig servo đóng/mở cửa tự động.

## 2. Ma trận chức năng

| ID | Hạng mục | Quy trình | Tiêu chí đạt |
|---|---|---|---|
| C-01 | Commissioning BLE | Quét QR trên 4 hệ sinh thái, mỗi hệ 20 lần (factory reset giữa các lần) | ≥ 19/20 thành công; thời gian < 60 s; LED nháy đúng trạng thái |
| C-02 | Cửa sổ commissioning hết hạn | Không quét trong 15 phút; nhấn nút ngắn | BLE ngừng quảng bá khi hết hạn; nhấn ngắn mở lại 300 s |
| C-03 | BLE giải phóng | Sau commissioning đọc log `kBLEDeinitialized`, heap tăng | heap tự do tăng (≥ 15 KB) |
| R-01 | Báo OPEN/CLOSED | 500 chu kỳ đóng/mở bằng jig servo, 1/3/10 s mỗi trạng thái | 100 % sự kiện có trên controller; thứ tự đúng; trễ trung vị < 1 s, P99 < 3 s |
| R-02 | Rung cửa | Rung nam châm quanh ngưỡng | không có trạng thái "nhấp nháy" lặp; trạng thái cuối đúng |
| R-03 | Sự kiện StateChange | Đọc event log Boolean State (chip-tool `booleanstate read-event state-change`) | mỗi thay đổi có 1 event |
| R-04 | Trạng thái sau reboot | Reset khi cửa mở/đóng | StateValue đúng sau khởi động, controller cập nhật |
| N-01 | Reconnect BR | Tắt BR (parent) 1 min / 10 min / 2 h rồi bật | thiết bị tự attach parent khác/cũ, báo cáo trở lại ≤ 2 chu kỳ IdleMode; không cần thao tác người dùng |
| N-02 | Khởi động lại toàn mạng | Mất điện toàn bộ nhà (BR + router Wi-Fi) | thiết bị hồi phục khi mạng trở lại |
| N-03 | Đổi kênh Thread / dataset (pending dataset) | Thay đổi kênh từ OTBR | thiết bị theo mạng mới |
| P-01 | Thay pin | Rút pin 5 s / 1 h / 1 tuần, lắp lại | giữ fabric + dataset; subscription tự khôi phục; trạng thái cửa đúng |
| P-02 | Lắp ngược pin | Lắp ngược 1 min | không hỏng, không nóng; lắp đúng chạy bình thường |
| P-03 | Pin yếu | Nguồn lập trình quét 3.3 → 1.6 V (bước 50 mV, 10 min/bước) + xung TX | BatChargeLevel: Warning < 2.7 V, Critical < 2.5 V; không reset ngẫu nhiên trên 1.8 V; UVLO tắt sạch, không hỏng NVS |
| P-04 | Nhiệt độ | –10 / 0 / 25 / 45 °C, pin thật | hoạt động, báo cáo đúng; ghi dòng sleep |
| F-01 | Factory reset bằng nút | Giữ 10 s rồi thả | xóa fabric, quảng bá BLE lại; giữ 5–10 s rồi thả = hủy |
| F-02 | Xóa fabric cuối từ app | "Remove accessory" | thiết bị tự factory reset, quảng bá BLE |
| F-03 | Reset trong lúc OTA/ghi NVS | Rút pin ngẫu nhiên 50 lần | không brick, không mất fabric quá 1 lần |
| M-01 | Multi-admin | Commission Apple → chia sẻ sang Google, HA, Aqara (4 fabric) | cả 4 nhận sự kiện; xóa 1 fabric không ảnh hưởng các fabric khác |
| M-02 | Thứ tự khác | Bắt đầu từ HA / Aqara / Google | như trên |
| I-01 | ICD SIT | sniffer 802.15.4 + PPK2 | slow poll 15 s ±5 %; Active khi sự kiện/nhấn nút; thuộc tính ICD Management đúng Kconfig |
| I-02 | Truy cập từ controller khi Idle | Gửi Identify/đọc thuộc tính | phản hồi ≤ slow poll + 2 s |
| I-03 | LIT (thử nghiệm) | Firmware LIT + DSLS, kiểm tra controller nào gửi RegisterClient | ghi nhận hệ sinh thái hỗ trợ; check-in đúng |
| O-01 | OTA | chip-tool `ota-provider-app` + từng hệ sinh thái nếu hỗ trợ | cập nhật thành công, rollback khi image lỗi, pin tiêu hao ghi nhận |
| B-01 | Dòng sleep | PPK2 tại rail 3V2 và tại pin | ≤ 30 µA rail; số liệu đưa vào `tools/battery_life.py` |
| B-02 | Điện tích mỗi poll/sự kiện | tích phân xung | cập nhật mô hình |
| B-03 | Thử xả pin | 5 thiết bị, tăng tốc 200 chu kỳ/ngày, 3 tháng | đường V(t) để hiệu chỉnh bảng % |
| B-04 | Chưa ghép nối: Deep-sleep | Cấp pin, không quét QR; đo dòng tại pin trong 20 phút | trong cửa sổ BLE: cỡ mA; sau khi cửa sổ đóng + 60 s: ≤ 12 µA (Deep-sleep 7 µA + Hall + rò); nhấn nút → mở cửa sổ mới |
| B-05 | Đánh thức bằng nút strap BOOT | Khi đang Deep-sleep: nhấn nhanh, nhấn giữ 3 s, nhấn giữ 15 s; lặp 20 lần | luôn khởi động vào ứng dụng, **không bao giờ vào chế độ download**; nếu lỗi: tắt `CONFIG_CS_UNCOMMISSIONED_DEEP_SLEEP` |
| B-06 | TX khung đầu tiên | PPK2/máy hiện sóng tại pin lúc khởi động thiết bị đã ghép nối | không có xung > 80 mA trong 2 s đầu (TX 10 dBm) |
| B-07 | Bộ bảo vệ khởi động | Nguồn lập trình + điện trở nối tiếp 47 Ω (giả pin yếu); pin thật gần hết | chip Deep-sleep 1 giờ thay vì reset lặp; nút đánh thức; không ghi nhầm khi pin tốt |
| B-08 | Kết nối lại Thread khi pin yếu | Pin CR123A gần hết (hoặc nguồn 2.5 V + 2 Ω nối tiếp); tắt BR 10 phút rồi bật; máy hiện sóng tại TP3 | VBAT ≥ 1.8 V, không reset |
| B-09 | Log bản sản xuất | So sánh điện tích một báo cáo đóng/mở giữa bản mặc định và bản `sdkconfig.defaults.debug` | ghi chênh lệch; số đo tuổi thọ pin chỉ lấy từ bản mặc định |
| RF-01 | Nhiễu Wi-Fi | AP 2.4 GHz kênh 1/6/11 tải nặng sát thiết bị; lò vi sóng | tỉ lệ mất báo cáo < 0.1 % (nhờ MRP) |
| RF-02 | Tầm phủ | khoảng cách tới parent LOS/qua tường, cửa gỗ/nhôm/thép | RSSI/LQI, PER; xác định giới hạn lắp đặt khuyến nghị |
| RF-03 | Anten trong vỏ | docs/chip/04 §5–6 | S11 ≤ –10 dB 2405–2480 MHz trong vỏ; TRP ≥ P_cond – 4 dB |
| H-01 | Khoảng cách nam châm | jig + gaussmeter, 30 mẫu | đóng chắc chắn ≤ 10 mm; mở ≥ 35 mm (worst case) |
| H-02 | Ảnh hưởng pin thép / cửa thép | 3 nhãn pin, cửa thép | ngưỡng lệch < 20 % |
| L-01 | Độ ổn định dài hạn | 20 thiết bị, 4 hệ sinh thái, 90 ngày, jig tự động | không treo; không mất kết nối > 1 IdleMode mà không tự hồi phục; heap tối thiểu ổn định |

## 3. Apple TV và Aqara Hub M3 cùng tham gia mạng Thread (yêu cầu đặc biệt)

Điểm cần hiểu (✅ kiến thức chuẩn Thread/Matter, 🧪 hành vi cụ thể của từng hãng):

- Một thiết bị Thread chỉ thuộc **một** mạng Thread (một bộ dataset) — mạng được cấp ở lần commissioning đầu tiên.
- Các BR của các hãng **có thể tạo các mạng Thread riêng** nếu không chia sẻ credential; chúng chỉ chung mạng khi BR này gia nhập bằng credential của BR kia (Thread credential sharing, tùy hãng/ứng dụng hỗ trợ).
- Multi-admin vẫn hoạt động giữa các mạng khác nhau vì Matter chạy trên IPv6: controller của hệ sinh thái B tới thiết bị qua LAN → **BR của mạng chứa thiết bị** (route OMR prefix + SRP/advertising proxy). Do đó nếu chỉ còn BR của hệ sinh thái B (khác mạng) mà BR của mạng thiết bị tắt hết, thiết bị **mất liên lạc** dù BR B vẫn chạy.

| ID | Kịch bản | Kiểm tra | Tiêu chí |
|---|---|---|---|
| AQ-01 | Commission bằng Apple (thiết bị vào mạng Apple), chia sẻ sang Aqara M3 | Extended PAN ID / tên mạng của Apple TV và M3 (OTBR scan, app Thread network viewer); sự kiện đến cả 2 app | sự kiện đến cả hai ≤ 2 s |
| AQ-02 | Commission bằng Aqara M3 trước, chia sẻ sang Apple | như trên | như trên |
| AQ-03 | M3 và Apple TV **cùng** mạng (nếu M3 hỗ trợ gia nhập mạng hiện có) | thiết bị có thể chọn parent là M3 hoặc Apple TV; ép đổi parent bằng tắt từng BR | không mất sự kiện khi đổi parent; thời gian hồi phục ≤ 2 × slow poll + attach |
| AQ-04 | M3 và Apple TV **khác** mạng | tắt Apple TV (giả sử thiết bị trong mạng Apple) | ghi nhận: thiết bị mất liên lạc với cả hai (hành vi chuẩn) ⇒ đưa vào hướng dẫn người dùng; bật lại → tự hồi phục |
| AQ-05 | Ổn định 7 ngày với cả hai BR hoạt động | log parent changes, mất báo cáo, phân mảnh/hợp nhất partition | không phân mảnh kéo dài; mất báo cáo 0 |
| AQ-06 | Cập nhật firmware BR (Apple tvOS / Aqara) trong lúc thử | | thiết bị hồi phục không cần can thiệp |

## 4. Kiểm thử sản xuất (FCT) – mỗi sản phẩm

| Bước | Nội dung | Thời gian ước tính |
|---|---|---|
| 1 | Đặt PCB lên jig pogo (TP1–TP10 + 2 pad dây pin J1, cấp nguồn qua J1), kiểm tra ngắn mạch 3V2/VBAT–GND | 2 s |
| 2 | Cấp 3.0 V vào J1 (qua Q1 như pin thật; thử thêm cực ngược –3 V: dòng ≈ 0), đo dòng khởi động và rail 3V2 (3.15–3.25 V) | 3 s |
| 3 | Vào download mode (kéo TP5 khi reset TP4), nạp bootloader + firmware + `esp_secure_cert` (DAC/PAI riêng từng máy) + `fctry` (passcode, discriminator, serial) bằng `esp-matter-mfg-tool`; in nhãn QR/manual code | 20–30 s |
| 4 | Firmware tự kiểm tra (chế độ test qua UART): đọc Hall với nam châm jig ở vị trí gần/xa, nút (jig nhấn), LED (cảm biến quang), ADC VBAT (so với nguồn jig ±50 mV) | 5 s |
| 5 | RF: TX tone kênh 18 – đo công suất và lệch tần (≤ ±10 ppm) qua J2 hoặc coupler bức xạ trong hộp chống nhiễu; RX: PER với gói chuẩn | 5–10 s |
| 6 | Dòng sleep: firmware vào light sleep, đo ≤ 35 µA (giới hạn sản xuất) | 5 s |
| 7 | Ghi kết quả + MAC/serial vào MES | — |
| 8 | Hàn 2 dây pin vào J1 (đỏ → pad 1 vuông "+", đen → pad 2 "–"), cố định dây; lắp PCB + tiếp điểm pin vào vỏ, lắp pin; kiểm tra LED nháy khi khởi động | 30–60 s |
| 9 | Kiểm tra cuối: lấy mẫu (AQL) commission vào mạng Thread chuẩn | — |

## 5. Chứng nhận (lập kế hoạch sớm vì dùng chip rời) 💡
- **Matter (CSA)** tại ATL: device type Contact Sensor, ICD, OTA requestor; cần VID/PID chính thức, DAC từ PAA được CSA công nhận, Certification Declaration; mục DCL.
- **Thread Group**: chứng nhận Thread (thiết bị MTD/SED) – có thể kế thừa chứng nhận stack OpenThread/Espressif tùy chương trình hiện hành.
- **Bluetooth SIG**: Qualified Design Listing (kế thừa QDID controller/host của Espressif nếu đủ điều kiện).
- **Vô tuyến**: FCC Part 15 (DTS 15.247 + 15.109), ISED RSS-247, CE RED (EN 300 328, EN 301 489-1/-17, EN 62368-1, EN 62311), các thị trường khác (VN: QCVN – kiểm tra yêu cầu hợp quy thiết bị vô tuyến cự ly ngắn).
- An toàn pin & vận chuyển: pin Li-MnO2 kim loại lithium (UN3091 khi đóng gói cùng thiết bị); RoHS/REACH.

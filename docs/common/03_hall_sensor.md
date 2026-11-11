# 03 – Cảm biến Hall và nam châm

## 1. So sánh các loại cảm biến Hall ✅

| Loại | Đầu ra | Đáp ứng từ | Hành vi khi không có từ trường | Dòng tiêu thụ điển hình (họ micropower) | Phù hợp cảm biến cửa? |
|---|---|---|---|---|---|
| **Hall switch unipolar** | số (on/off) | chỉ 1 cực (thường S) | trở về OFF | 0.5–5 µA (lấy mẫu chu kỳ) | Có, nhưng nam châm phải đúng cực |
| **Hall switch omnipolar** | số | cả N và S (|B| > BOP) | trở về OFF | **0.54–1.6 µA** (DRV5032) | **Tốt nhất**: lắp nam châm chiều nào cũng được |
| **Hall latch (bipolar)** | số, *chốt* | S → ON, N → OFF | **giữ trạng thái cũ** | 1.3–1.6 µA (DRV5012 @ 20 Hz) | Chỉ được khi có cả 2 cực (cần nam châm phụ) |
| **Hall analog (ratiometric)** | điện áp tỉ lệ B | tuyến tính | điện áp giữa | cỡ mA liên tục (cảm biến tuyến tính luôn cấp điện) | ✗ – phải để MCU đọc ADC (polling) |
| Cảm biến 3D số (I²C) | thanh ghi | 3 trục | — | µA ở chế độ wake-on-threshold, mA khi đo | Thừa tính năng, đắt, phức tạp |

Theo yêu cầu (không polling ADC, dòng µA), **loại analog bị loại**; chọn giữa **switch omnipolar (A)** và **latch (B)**.

## 2. Phương án A (đang dùng): TI DRV5032FA – omnipolar switch, push-pull ✅

| Thông số (datasheet SLVSDC7H, Rev. H 12/2024) | DRV5032**FB** (dòng thấp nhất, giá cao hơn) | DRV5032**FA** (**đang dùng**) |
|---|---|---|
| Mã đặt hàng (SOT-23, Active) | DRV5032FBDBZR | **DRV5032FADBZR** |
| Đáp ứng | omnipolar | omnipolar |
| Đầu ra | push-pull | push-pull |
| Tần số lấy mẫu | 5 Hz (chu kỳ 117 / 200 / 286 ms min/typ/max) | 20 Hz (27 / 50 / 75 ms) |
| I_CC trung bình @ 3 V | 0.69 µA typ / 1.8 µA max | **1.6 µA typ / 3.5 µA max** |
| BOP (đóng) | ±1.5 / ±3.0 / **±4.8 mT** | như FB |
| BRP (nhả) | **±0.5** / ±1.5 / ±3.0 mT | như FB |
| Trễ từ BHYS | 0.8 / 1.5 / 3.0 mT | như FB |
| VCC | 1.65 – 5.5 V | |
| Hướng nhạy | trường **vuông góc mặt trên** vỏ SOT-23 (trục Z của PCB) | |
| Vỏ khác | X2SON 1.4 × 1.1 mm (DRV5032FADMRR...), TO-92 (DRV5032FBLPG) | |

Logic: |B| > BOP ⇒ OUT = LOW (có nam châm = **cửa đóng**); |B| < BRP ⇒ OUT = HIGH (**cửa mở**). Push-pull ⇒ không cần điện trở kéo (một pull-up 45 kΩ đánh nhau với mức LOW sẽ tốn ~70 µA – firmware **tắt** pull-up nội, `CONFIG_CS_HALL_PULLUP=n`).

Lựa chọn biến thể:
- **FA (20 Hz) – đang dùng**: giá thấp hơn FB (theo báo giá); trễ phát hiện tối đa 75 ms. Đổi lại tốn thêm khoảng 0.9 µA so với FB (~1.7 % dòng pin trung bình: tuổi thọ CR123A khoảng 2.33 → 2.29 năm, docs/common/09).
- FB (5 Hz): dòng thấp nhất (0.69 µA), trễ tối đa 286 ms; cùng footprint, chân và ngưỡng nên lắp thẳng thay FA được nếu giá chấp nhận được.
- DU (dual unipolar, 2 đầu ra N/S, 20 Hz): dùng khi muốn **chống giả mạo bằng nam châm lạ** (nam châm chính có cực định trước; đầu ra cực ngược = báo động). Tốn 1 GPIO LP IO nữa.

## 3. Phương án B: Hall latch DRV5012 + nam châm phân cực ✅ (linh kiện) / 💡 (cấu hình)

DRV5012 (mã **DRV5012AEDMRR**, X2SON 1.1 × 1.4 mm): BOP +0.6 / +2 / +3.3 mT (cực S), BRP –3.3 / –2 / –0.6 mT (cực N), trễ 4 mT typ, 20 Hz: 1.6 µA typ @ 3 V (3.3 µA max), chân SEL chọn 20 Hz / 2.5 kHz.

**Vấn đề:** latch **giữ nguyên** trạng thái khi từ trường về 0. Với 1 nam châm cửa: đóng → S → OUT LOW; mở → B ≈ 0 → OUT **vẫn LOW** ⇒ không phát hiện được cửa mở.

**Cấu hình đúng:** đặt **một nam châm phụ nhỏ cố định trong vỏ cảm biến**, tạo trường nền B_bias ≈ –4.5 mT (cực N, > |BRP max| = 3.3 mT) tại cảm biến:

| Trạng thái | Trường tại cảm biến | Đầu ra latch |
|---|---|---|
| Cửa mở | B_bias = –4.5 mT < BRP min (–3.3 mT) | HIGH (OPEN) – chắc chắn |
| Cửa đóng | B_door(+S) + B_bias ≥ BOP max (+3.3 mT) ⇒ **B_door ≥ 7.8 mT** | LOW (CLOSED) |

Kết quả tính (`tools/magnet_field.py`, nam châm cửa N35 15×5×3 mm): khe đóng tối đa đảm bảo **7.3 mm** (so với **9.9 mm** của phương án A cùng nam châm).

| | A: DRV5032FA omnipolar | B: DRV5012 latch + bias |
|---|---|---|
| Dòng | 1.6 µA (FB: 0.69 µA) | 1.6 µA |
| Linh kiện cơ khí | 1 nam châm | 2 nam châm (1 cố định trong thân) |
| Chiều lắp nam châm | tùy ý | **bắt buộc đúng cực** |
| Khe đóng đảm bảo (cùng nam châm) | 9.9 mm | 7.3 mm |
| Nhạy với từ trường lạ / thép gần | trung bình | cao hơn (bias bị lệch bởi thép cửa) |
| Ưu điểm riêng | đơn giản, rẻ | trạng thái được "chốt" cứng; có thể dùng cho cửa trượt với nam châm 2 cực xen kẽ |

⇒ **Chọn Phương án A**. Phương án B chỉ hợp lý cho các cơ cấu có cả hai cực đi qua cảm biến (cửa trượt, encoder).

## 4. Giữ khả năng phát hiện CẢ HAI trạng thái khi MCU ngủ ✅

### 4.1 Ràng buộc phần cứng ESP32-H2 (đã kiểm tra mã nguồn ESP-IDF v5.5.5)

1. Đánh thức light-sleep bằng GPIO chỉ hỗ trợ **mức** (LOW/HIGH), không hỗ trợ cạnh (`gpio_wakeup_enable` trả lỗi với kiểu edge).
2. Khi bật `CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP` (tắt miền TOP để đạt ~25 µA), khối GPIO số mất điện: `esp_sleep_enable_gpio_wakeup()` in cảnh báo "GPIO wakeup source is not available…". Nguồn đánh thức hợp lệ là **EXT1** trên **LP IO GPIO7–GPIO14** (`rtc_io_periph.c`), ESP32-H2 hỗ trợ **mức riêng cho từng chân** (`SOC_PM_SUPPORT_EXT1_WAKEUP_MODE_PER_PIN`).
3. Thanh ghi GPIO/IO MUX được REGDMA lưu–khôi phục quanh lần ngủ (`port/esp32h2/system_periph_retention.c`) ⇒ ngắt mức cấu hình trước khi ngủ vẫn kích hoạt sau khi thức.

⇒ Hall OUT nối **GPIO10** (LP IO), nút nhấn **GPIO9** (LP IO). Đây cũng là cách thư viện `espressif/button` (chế độ power-save) và ví dụ `icd_app` của Espressif làm trên H2 (Kconfig ví dụ giới hạn chân nút 9–14 cho H2).

### 4.2 Thuật toán "đảo mức đánh thức" (firmware `sensor/hall_sensor.cpp`)

```
          ┌───────────────────────────── ngủ (light sleep) ─────────────────────────────┐
          │  EXT1 + ngắt GPIO10 được đặt ở mức = NOT(mức vừa đọc)                        │
          └───────┬──────────────────────────────────────────────────────────────────────┘
                  │ Hall đổi mức (cửa đóng/mở) → EXT1 đánh thức → ISR mức
                  ▼
   ISR: gpio_intr_disable(GPIO10); notify hall_task           (tránh ngắt lặp vô hạn)
                  ▼
   hall_task: L0 = đọc; chờ 300 ms (chip vẫn ngủ trong lúc chờ); L1 = đọc
              nếu L1 ≠ L0 → lặp lại (tối đa 10 cửa sổ) ⇒ mức đã xác nhận L
                  ▼
   nếu (L == 0) ≠ trạng thái đã báo → callback → app task → Matter BooleanState
                  ▼
   arm(GPIO10, mức đánh thức = NOT L)   ← dựa trên mức VỪA ĐỌC, không dựa trên trạng thái đã báo
```

Tính đúng đắn:
- **Không mất sự kiện do race**: vì đánh thức theo *mức*, nếu cửa đổi trạng thái ngay giữa lúc đọc L và lúc arm, mức chân đã khác L = trùng mức đánh thức ⇒ ngắt kích hoạt ngay lập tức.
- **Rung cửa**: DRV5032FA cập nhật đầu ra mỗi 27–75 ms (FB: 117–286 ms); cửa sổ xác nhận 300 ms phủ ≥ 4 chu kỳ lấy mẫu (≥ 1 với FB). Đóng–mở nhanh hơn 300 ms chỉ báo trạng thái cuối (đúng nghĩa vật lý).
- **Kiểm tra định kỳ**: mỗi lần đo pin (12 h) và mỗi lần nhấn nút, firmware gọi `hall_sensor_resync()` để đọc lại và báo nếu lệch.
- **Khởi động / thay pin**: đọc mức ngay sau khi cấu hình chân, giá trị được đẩy vào cluster khi server Matter sẵn sàng (`kServerReady`).

### 4.3 Độ trễ từ cửa → báo cáo 🧪

| Giai đoạn | Thời gian |
|---|---|
| Hall lấy mẫu | 0 – 75 ms (FB: 0 – 286 ms) |
| Đánh thức light sleep (TOP PD, khôi phục ngữ cảnh) | ~1–2 ms (🧪) |
| Cửa sổ xác nhận | 300 ms |
| Matter: SetStateValue + báo cáo, ICD chuyển Active (fast poll 500 ms) | 10–50 ms để gửi; ACK ≤ 500 ms |
| **Tổng tới khi bản tin rời thiết bị** | **≈ 0.3–0.45 s** (FB: 0.3–0.65 s) |

## 5. Nam châm và hình học lắp đặt

### 5.1 Hướng đặt

- SOT-23 cảm nhận **Bz** (vuông góc PCB). PCB đặt **song song mặt lắp** (sát đáy vỏ) ⇒ Bz là trường *vuông góc mặt cửa*.
- Nam châm từ hóa **theo trục Z** (vuông góc mặt lắp), đặt **cùng độ cao** với die Hall: cảm biến nằm trên mặt phẳng xích đạo của lưỡng cực ⇒ |Bz| lớn nhất. Lệch độ cao làm giảm Bz và có điểm triệt tiêu khi góc nhìn ≈ 54.7° so với trục từ ⇒ thiết kế vỏ để tâm nam châm cao ≈ độ cao die (≈ 4 mm trên mặt lắp).
- Omnipolar ⇒ nam châm có thể lật N/S.
- Nếu cơ khí bắt buộc từ trường nằm ngang: dùng bản TO-92 (**DRV5032FBLPG**, 5 Hz – kiểm tra TI có bản FA TO-92 hay không) đứng vuông góc PCB, nam châm từ hóa ngang hướng vào cảm biến (trường trục ≈ 2 lần trường xích đạo) – 💡 phương án dự phòng.

### 5.2 Kết quả tính (`tools/magnet_field.py`, mô hình nam châm khối, đã kiểm chứng với công thức trục dạng đóng sai số < 1 %) ✅ tính toán / 🧪 đo

Giả định: die Hall cách mặt ngoài vỏ 2.5 mm; vách vỏ nam châm 1.2 mm; die ngang tâm nam châm.

| Nam châm (từ hóa trục Z) | Đóng chắc chắn (|B| ≥ 4.8 mT) | Đóng điển hình (3.0 mT) | Nhả điển hình (1.5 mT) | Mở chắc chắn (|B| ≤ 0.5 mT) |
|---|---|---|---|---|
| N35 10×5×3 mm | ≤ 8.1 mm | 10.5 mm | 14.9 mm | ≥ 24.3 mm |
| N35 15×5×3 mm | ≤ 9.9 mm | 12.7 mm | 17.8 mm | ≥ 28.5 mm |
| **N35 20×6×3 mm** | **≤ 11.9 mm** | **15.3 mm** | **21.2 mm** | **≥ 33.9 mm** |
| N52 15×5×3 mm | ≤ 11.0 mm | 14.0 mm | 19.4 mm | ≥ 30.9 mm |

(khoảng cách = khe hở giữa hai vỏ). Dung sai lắp với N35 15×5×3 tại khe 10 mm: lệch dọc cạnh 5 mm → |B| giảm 4.68 → 4.24 mT; lệch cao ±4 mm → 3.57 mT.

**💡 Đề xuất:** NdFeB **N35 (hoặc N42) 20 × 6 × 3 mm, từ hóa qua chiều 3 mm**, mạ Ni-Cu-Ni, dán trong vỏ nam châm (kích thước vỏ ~35 × 12 × 12 mm). Hướng dẫn lắp cho người dùng: khe ≤ 10 mm, vạch căn chỉnh trên hai vỏ thẳng hàng (±5 mm). Ngưỡng "mở" thực tế với linh kiện điển hình ≈ 21 mm.

### 5.3 Các yếu tố phải đo 🧪

- **Vỏ thép của pin CR123A** (thép mạ Ni, sắt từ) nằm cách Hall ~9 mm: làm lệch/tập trung từ thông ⇒ đo |B| tại vị trí Hall với ít nhất 3 nhãn pin.
- Khung cửa thép/nhôm: nhôm không ảnh hưởng tĩnh; thép làm lệch đường sức ⇒ test trên cửa thép.
- Nhiệt độ: Br của NdFeB giảm ~0.1 %/°C; ngưỡng DRV5032 thay đổi theo nhiệt (datasheet Fig. 6-4/6-5).
- Cuộn cảm DC-DC (đặt cách Hall ≥ 10 mm, loại có che chắn) – xác nhận không gây chuyển trạng thái giả khi TX 20 dBm.
- Đo bằng gaussmeter + jig khoảng cách để lập đường cong "khoảng cách đóng/mở" cho 30 mẫu DRV5032 (phân bố BOP/BRP).

## 6. Bố trí trên PCB 💡

- U3 (SOT-23) sát **cạnh dài "mặt A"** (hướng về nam châm): thân cách mép PCB 0.1 mm, tâm (die) tại **x = 26.7 mm từ đầu anten, cách mép 1.8 mm** (PCB KiCad `hardware/chip/`, docs/chip/06 §4); in vạch căn chỉnh trên vỏ đúng tọa độ này.
- Tụ C24 0.1 µF sát chân VCC.
- Không đặt linh kiện sắt từ (lò xo pin, vít thép, cuộn cảm) trong bán kính 10 mm.
- Đường HALL_OUT ngắn, có test point TP9 để jig sản xuất kiểm tra bằng nam châm điện/nam châm cố định.

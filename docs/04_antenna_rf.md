# 04 – Anten PCB 2.4 GHz và mạch RF

Yêu cầu: một anten PCB tự thiết kế phục vụ **BLE commissioning (2402–2480 MHz)** và **Thread/802.15.4 (kênh 11–26, 2405–2480 MHz)**, không dùng module/anten rời. Tiêu chí: |S11| ≤ –10 dB trên 2400–2483.5 MHz **khi đã lắp trong vỏ, có pin**.

## 1. Chọn cấu trúc anten ✅ (tài liệu) / 🧪 (hiệu năng thực)

| Ứng viên | Kích thước | Vừa PCB 16–18 mm? | Ghi chú |
|---|---|---|---|
| TI DN007 IFA | 25.7 × 7.5 mm | ✗ (quá rộng) | |
| **TI AN043 (SWRA117D) – meandered IFA** | **15.2 × 5.7 mm** | ✅ | thiết kế 50 Ω ở 2.45 GHz, VSWR < 2 trên băng ISM khi đo trên dongle CC2511; băng thông ~250 MHz trong không khí |
| Anten chip ceramic | 3–5 mm | ✅ | ✗ trái yêu cầu (phải là anten PCB) |

**Chọn MIFA AN043.** TI nhấn mạnh: "*small changes of the antenna dimensions may have large impact on the performance… strongly recommended to make an exact copy*"; vỏ nhựa **dời cộng hưởng xuống thấp** (bù bằng cách rút ngắn anten); kích thước mặt phẳng GND cũng ảnh hưởng. Vì vậy:

- Dùng **nguyên footprint chuẩn KiCad `RF_Antenna:Texas_SWRA117D_2.4GHz_Right`** (ảnh gương của bản `_Left`; bản sao tại `hardware/antenna/`), không vẽ tay.
- Sinh sẵn 3 biến thể rút ngắn nhánh hở L1 (3.64 / 3.34 / 3.04 mm) bằng `tools/gen_antenna_variants.py` để đặt cạnh nhau trên panel EVT và chọn theo phép đo trong vỏ.

### 1.1 Kích thước (SWRA117D bảng 1) ✅

| Ký hiệu | mm | Ý nghĩa (theo hình 3 AN043) |
|---|---|---|
| L1 | 3.94 | nhánh hở cuối cùng (điểm tuning) |
| L2 | 2.70 | thanh ngang trên của mỗi khúc uốn |
| L3 | 5.00 | thanh ngang trên nối stub ngắn mạch – feed – khúc uốn 1 |
| L4 | 2.64 | chân dọc khúc uốn |
| L5 | 2.00 | khe giữa hai chân khúc uốn |
| L6 | 4.90 | chiều dài stub ngắn mạch / stub feed (gồm 0.5 mm đi vào vùng GND) |
| W1 | 0.90 | bề rộng stub ngắn mạch |
| W2 | 0.50 | bề rộng vệt anten |
| D1 / D3 | 0.50 / 0.30 | khoảng cách tới mép PCB trái/phải |
| D2 | 0.30 | khoảng cách tới mép PCB đầu |
| D4 | 0.50 | phần stub đi vào vùng GND (via GND ở cuối stub ngắn mạch) |
| D5 / D6 | 1.40 / 1.70 | khe stub ngắn mạch–feed / feed–khúc uốn |

Footprint KiCad: pad 1 = feed (0.5 × 0.5 mm, F.Cu), pad 2 = GND (lỗ 0.3 mm), `net_tie_pad_groups "1,2"`; vùng keep-out 15.2 × 5.2 mm phía trên mép GND.

### 1.2 Đặt anten trên PCB 36 × 18 mm 💡 (đã thực hiện trong `hardware/kicad/`)

- Anten nằm ở **một đầu** PCB, trải ngang 15.2 mm trong bề rộng 18 mm; vùng anten (kể cả D1/D3) **trùng mép "mặt A"** (y = 18) – giống mép PCB của thiết kế tham chiếu ở phía đó; phía còn lại thừa 2.8 mm FR4 không đồng. Điểm feed ở y = 14.95, nên chuỗi RF chạy thẳng dọc mép mặt A tới chip.
- **Keep-out x = 0 → 5.2 mm, toàn bộ bề rộng, MỌI lớp đồng** (rule area KiCad: không đường, không via, không đổ đồng; L1 chỉ có đồng anten). Mép mặt phẳng GND trên mọi lớp **thẳng hàng** tại x = 5.2 mm.
- Mặt phẳng GND còn lại 18 × 30.8 mm (≈ λ/4 ≈ 31 mm theo chiều dài) – vẫn đủ cho IFA, nhưng mặt GND ngắn hơn bản 72 mm ⇒ băng thông/hiệu suất và tần số cộng hưởng thay đổi; 🧪 bắt buộc đo S11 trong vỏ và chọn biến thể L1/π ở §5. Dây pin là vật dẫn dài nối vào GND: cho ra ở đầu xa anten (J1, x = 34.2 mm) và không vòng qua vùng anten.
- 🧪 FR4 thừa 2.8 mm ở một bên + PCB dày 1.0 mm so với dongle tham chiếu ⇒ cộng hưởng có thể lệch vài chục MHz ⇒ xử lý ở bước tuning §5 (biến thể L1, π anten).

## 2. Sơ đồ RF từ chân chip tới anten ✅ (cấu trúc theo Espressif) / 🧪 (giá trị)

```
 ESP32-H2                 MATCHING PHÍA CHIP (sát chân, 0201, zigzag)            TEST         MATCHING PHÍA ANTEN     ANTEN
 pin 32 ANT ─LNA_IN─┬─ L4 ──┬── C21 ──┬───── RF_M1 ── J2 SWF ── RF_50R (GCPW) ──┬─ L6 ──┬── RF_ANT ── ANT1 feed (pad 1)
                    │ 2.7nH │ 0 Ω*   │             (MS-156C3)                  │ 0 Ω   │              ANT1 short (pad 2) ─ GND
                   C19     C20       L5                                        C22     C23
                  1.5pF   1.5pF     DNP                                        DNP     DNP
                    │       │        │                                          │       │
                   GND(+stub) GND   GND                                        GND     GND
 (*) C21 = 0 Ω mặc định (cấu trúc CLC); lắp 10 pF C0G nếu cần chặn DC/dùng cấu trúc CLCCL đầy đủ.
```

| Ký hiệu | Vai trò (tên trong sơ đồ tham chiếu Espressif) | Giá trị bắt đầu | Dải theo Espressif | Mã gợi ý |
|---|---|---|---|---|
| C19 | tụ shunt phía chip (C12) | 1.5 pF | 1.2–1.8 pF | GRM0335C1H1R5BA01D (0201 C0G ±0.1 pF) |
| L4 | cuộn nối tiếp (L2) | 2.7 nH | 2.0–3.0 nH | LQP03TN2N7B02D (0201 ±0.1 nH) |
| C20 | tụ shunt phía anten (C11) | 1.5 pF | 1.2–1.8 pF | GRM0335C1H1R5BA01D |
| C21 / L5 | phần CL của CLCCL (C3/L1) | 0 Ω / DNP | — | chỉ cần khi có nguồn nhiễu AC-DC |
| J2 | cổng đo dẫn có công tắc | Hirose MS-156C3 (EVT/DVT, có thể giữ ở MP) | | DC–11 GHz, cao 1.35 mm, footprint thư viện KiCad; Murata MM8130 là phương án khác footprint |
| C22 / L6 / C23 | π tuning anten | DNP / 0 Ω / DNP | | 0201, chọn sau đo VNA |

Quy tắc Espressif bắt buộc ✅:
- Linh kiện matching **0201**, đặt sát chân ANT, **zigzag** (hai tụ không cùng hướng).
- **Stub trên pad GND của tụ shunt sát chip (C19)**: dài 15 mil (0.38 mm), trở kháng 100 Ω ± 10 %, tham chiếu lớp L3 ⇒ khoét đồng L2 dưới stub — để triệt hài bậc 2.
- Tiêu chí chỉnh mạng phía chip: nhìn từ cổng 1 (phía chip) **S11 ≈ 35 + j0 Ω** (liên hợp trở kháng chip) và **S21 < –35 dB tại 4.8 GHz và 7.2 GHz**.
- Thêm mạng CLC gần anten để tuning anten.

## 3. Đường truyền 50 Ω ✅ (tham chiếu Espressif) / 🧪 (đo TDR)

Stack-up tham chiếu Espressif (4 lớp, L1–L2 prepreg 7628 dày 8.22 mil, Dk 4.6): **GCPW 50 Ω: rộng 12.6 mil (0.32 mm), khe 12.2 mil (0.31 mm)**.
Kiểm tra chéo bằng `tools/cpwg_impedance.py` (công thức tựa tĩnh, hiệu chỉnh theo điểm tham chiếu trên):

| Stack-up | khe 0.20 mm | khe 0.25 mm | khe 0.30 mm |
|---|---|---|---|
| 4 lớp, prepreg 7628 ~0.21 mm, εr 4.4 | w = 0.31 mm | 0.32 mm | 0.33 mm |
| 4 lớp, prepreg 3313 ~0.10 mm, εr 4.1 | 0.17 mm | 0.17 mm | 0.18 mm |
| 2 lớp 0.8 mm, εr 4.5 | 0.70 mm | 0.79 mm | — |

Quy tắc: đường RF trên L1, **không via, không rẽ nhánh**, cong 135° hoặc cung tròn, dài ≤ 8 mm, hàng via GND hai bên bước ≤ 1 mm, L2 dưới đường RF liền, không có đường tín hiệu nào chạy dưới. Đặt hàng **kiểm soát trở kháng** với nhà sản xuất PCB và xác nhận bằng coupon TDR.

## 4. Vùng keep-out trong vỏ 💡 / 🧪

| Vật thể | Khoảng cách tới anten | Ghi chú |
|---|---|---|
| Đồng PCB các lớp | 0 trong vùng 17 × 5.2 mm | bắt buộc |
| Pin CR123A (vỏ thép) | **≥ 25 mm** (pin nằm ngoài PCB: ngăn pin đặt sau đầu J1 ⇒ ≥ 32 mm) | vỏ thép là vật dẫn lớn nhất trong sản phẩm |
| Lò xo/tiếp điểm pin, dây pin, vít kim loại | ≥ 20 mm | dây pin đi ra từ đầu xa anten |
| Thạch anh 32 MHz, cuộn cảm DC-DC, UART | càng xa càng tốt (Espressif) | XTAL/UART đặt phía sau chip so với anten |
| Thành vỏ nhựa | ≥ 1 mm, dày ≤ 1.5 mm, ABS/PC không độn sợi thủy tinh, không sơn kim loại | gây dịch tần xuống |
| Light-pipe LED, keo dán 2 mặt | không phủ lên vùng anten | |
| Mặt lắp (khung cửa) | Espressif khuyến nghị khoảng trống 15 mm mọi hướng – không đạt được về phía mặt lắp ⇒ **đo trên cửa gỗ, nhôm và thép** | thép làm lệch cộng hưởng mạnh nhất |

## 5. Quy trình tuning bằng VNA 🧪

Thiết bị: VNA 2–8 GHz (Keysight/R&S/Copper Mountain; NanoVNA chỉ dùng tham khảo), cáp semi-rigid Ø1.2 mm (UT-047) làm pigtail, ferrite sleeve trên cáp (giảm dòng mặt ngoài vỏ cáp), bộ hiệu chuẩn SOL hoặc kéo dài cổng (port extension) tới đầu pigtail, phần mềm Smith chart.

1. **Chuẩn bị mẫu**: PCB EVT có J2 (Hirose MS-156C3). Với phép đo anten: tháo L6 (0 Ω) nếu cần cô lập; hàn lõi pigtail vào pad phía anten của L6, vỏ pigtail vào pad GND sát cạnh. Hiệu chuẩn tới đầu pigtail.
2. **Đo anten trần** (PCB không vỏ, không pin) – đối chiếu với AN043 (cộng hưởng ~2.45 GHz, |S11| < –10 dB).
3. **Đo trong các cấu hình thực tế**: vỏ đóng + pin; + đặt trên tấm gỗ; + trên khung nhôm; + trên khung thép; với cả 3 biến thể L1. Ghi f_res, |S11| tại 2405/2440/2480 MHz.
4. **Chọn biến thể L1** có f_res trong vỏ ≈ 2440–2450 MHz (thường biến thể ngắn hơn do vỏ kéo tần xuống).
5. **Tinh chỉnh π anten** (C22/L6/C23) trên Smith chart để đưa trở kháng về gần 50 Ω trong toàn băng (ưu tiên cấu hình chỉ 1–2 linh kiện để giảm tổn hao).
6. **Chỉnh mạng phía chip**: đo hai cổng giữa pad ANT (chip chưa hàn, hoặc trên board test riêng) và J2, chỉnh C19/L4/C20 trong dải Espressif tới S11 ≈ 35 + j0 Ω, S21(4.8/7.2 GHz) < –35 dB.
7. **Chốt BOM RF**, lặp lại trên 5 board từ 2 lô PCB để kiểm tra độ lặp (dung sai εr/độ dày prepreg).

## 6. Đo công suất phát / độ nhạy thu 🧪

### 6.1 Đo dẫn (conducted) qua J2
- Phần mềm: Espressif "Certification and Test Tool"/RF test firmware (hỗ trợ qua **UART** – Espressif khuyến nghị giữ cổng UART tải firmware vì công cụ RF hiện chỉ hỗ trợ UART).
- Máy phân tích phổ / máy test 802.15.4–BLE: công suất ra kênh 11/18/26 ở cài đặt 10 và 20 dBm, hài bậc 2/3, phát xạ giả, EVM (802.15.4 O-QPSK), lệch tần.
- **Lệch tần thạch anh**: chế độ TX tone, chỉnh C15/C16 tới lệch ≤ ±10 ppm (lệch dương ⇒ tăng tụ tải, lệch âm ⇒ giảm), theo quy trình Espressif.
- Độ nhạy thu: PER < 1 % với máy phát tín hiệu 802.15.4/BLE và suy hao bước.

### 6.2 Đo bức xạ khi lắp trong vỏ
1. **Phòng đo OTA (khuyến nghị cho DVT)**: TRP/TIS 3D tại phòng thí nghiệm; mục tiêu đề xuất 💡 TRP ≥ P_conducted – 4 dB (hiệu suất anten ≳ 40 %), không có "lỗ" sâu > 15 dB theo phương lắp đặt thực tế.
2. **Phương pháp nội bộ so sánh**: hộp chống nhiễu/buồng bán phản xạ, sniffer 802.15.4 cố định (ví dụ ESP32-H2-DevKitM-1 chạy `ot_rcp` + Wireshark, hoặc dongle nRF52840 sniffer), DUT trên bàn xoay; so RSSI trung bình/thấp nhất với **mẫu tham chiếu ESP32-H2-MINI-1** cùng công suất phát. Sai khác ≤ 3 dB ⇒ đạt.
3. **Link budget**: DUT trong hộp chống nhiễu, ăng ten ghép + suy hao bước tới thiết bị đối tác ⇒ tìm suy hao tại PER 1 % cho cả TX và RX, so với mẫu tham chiếu.
4. **Thực địa**: khoảng cách tới parent Thread trong nhà (LOS 10/20/30 m, qua 1–2 tường), lấy RSSI/LQI từ Thread Network Diagnostics cluster của Matter và OpenThread, đếm số lần đổi parent và tỉ lệ mất báo cáo trong 72 h.

## 7. Thạch anh 32 MHz ✅
- Firmware ESP32-H2 **chỉ hỗ trợ 32 MHz**, sai số ≤ ±10 ppm, biên độ > 500 mV.
- Linh kiện nối tiếp trên XTAL_P: **24 nH** ban đầu (L3) để giảm hài thạch anh ảnh hưởng RF; chỉnh sau test tổng thể.
- Tụ tải: C_L = C15·C16/(C15+C16) + C_stray ⇒ thạch anh C_L = 10 pF, C_stray ≈ 2.5 pF ⇒ **C15 = C16 = 15 pF** khởi điểm.
- Layout: thạch anh cách chân clock ≥ 1.8 mm, không via trên đường clock, không đường tín hiệu dưới thạch anh, vành GND + via quanh đường clock, không đặt cuộn cảm gần (DC-DC đặt xa).

## 8. Hệ quả pháp lý khi dùng chip rời 💡
Không có chứng nhận module (FCC modular grant/CE của module) ⇒ **sản phẩm phải tự chứng nhận bộ phát vô tuyến**: FCC Part 15.247 (DTS) + 15.109/15.209, CE RED (EN 300 328, EN 301 489-1/-17, EN 62368-1/62311), IC (RSS-247), cùng chứng nhận Bluetooth SIG (Qualified Design), Thread Group và CSA Matter. Ngân sách và thời gian cho các phép thử này phải nằm trong kế hoạch (docs/11). Công suất phát cấu hình trong firmware (`CONFIG_CS_THREAD_TX_POWER_DBM`) phải khớp với giá trị khai báo khi chứng nhận.

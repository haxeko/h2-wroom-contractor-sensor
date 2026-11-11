# 02 – Mạch nguồn CR123A

## 1. Đặc tính pin CR123A (Li-MnO2) ✅

| Thông số | Energizer EL123AP | Panasonic CR123A |
|---|---|---|
| Hóa học | Li / MnO2 | Li / MnO2 |
| Điện áp danh định | 3.0 V | 3.0 V |
| Dung lượng | **1500 mAh** (xả 100 Ω tới 2.0 V, 21 °C) | **1550 mAh** |
| Dòng xả tối đa | 1500 mA liên tục, 3500 mA xung | — |
| Nhiệt độ làm việc | –40 ~ 60 °C | –40 ~ 70 °C |
| Thời gian lưu kho | ~10 năm | — |

Đặc điểm quan trọng cho thiết kế:

- Điện áp hở mạch pin mới ≈ 3.2–3.3 V, nhưng **điện áp làm việc khi có tải mA nằm khoảng 2.7–3.0 V trong phần lớn quá trình xả**, và giảm dần về 2.0 V cuối đời (đường xả của nhà sản xuất) 🧪 *đo lại với nhãn pin được chọn*.
- Đường xả rất phẳng ⇒ đo điện áp lúc nghỉ chỉ phát hiện pin yếu ở ~10–15 % cuối (ảnh hưởng tới thuật toán BatPercentRemaining, xem §7).
- Ở nhiệt độ thấp nội trở tăng mạnh ⇒ sụt áp xung TX lớn hơn.

## 2. Yêu cầu nguồn của ESP32-H2 ✅

- VDD3P3, VBAT, VDDA_PMU, VDDPST1, VDDPST2: **3.0 V min / 3.3 V typ / 3.6 V max** (datasheet v1.3, bảng 5-2); tuyệt đối max 3.6 V.
- Khuyến nghị nguồn đơn ≥ 350 mA (đủ cho TX 20 dBm 140 mA + CPU).
- Định thời bật nguồn: các rail phải ổn định ≥ 50 µs trước khi CHIP_EN lên mức cao (tSTBL), giữ CHIP_EN thấp ≥ 50 µs để reset (tRST). Hardware Design Guidelines: với nguồn tăng/giảm chậm hoặc không ổn định, **nên dùng IC giám sát nguồn ngưỡng ~3.0 V**.
- Ghi eFuse: VDDPST2 không vượt 3.3 V.

## 3. Có cấp trực tiếp từ CR123A được không? → **Không** ✅

| Tiêu chí | Cấp trực tiếp | Kết luận |
|---|---|---|
| Điện áp tối thiểu 3.0 V | Pin làm việc 2.7–3.0 V dưới tải, cuối đời 2.0 V | **Vi phạm datasheet phần lớn tuổi thọ pin** |
| Sụt áp khi TX (60–140 mA) | ΔV = I·R_int + phân cực ≈ 0.05–0.3 V, lớn hơn khi lạnh/pin cũ | Rơi sâu dưới 3.0 V |
| Brownout nội (IDF: 2.57–2.94 V, "ước lượng") | Reset ngẫu nhiên khi TX ở 10–20 % dung lượng cuối | Thiết bị "mất kết nối" trong khi pin còn năng lượng |
| Hiệu năng RF | PA/LDO nội không được đặc tả dưới 3.0 V | Không đảm bảo công suất phát/EVM |
| Năng lượng | Không tổn hao chuyển đổi | Ưu điểm duy nhất |

Một con số tham khảo từ `tools/battery_life.py`: nếu chip *chạy được* tới cuối pin khi cấp trực tiếp thì tuổi thọ lý thuyết ~3.4 năm, so với ~2.8 năm qua DC-DC (cùng kịch bản 20 lần/ngày, 1500 mAh). Khoảng chênh ~17 % này là "giá" của việc vận hành **trong** thông số datasheet; với sản phẩm thương mại cần chứng nhận Matter/FCC/CE và độ tin cậy, đây là lựa chọn bắt buộc.

> Ghi chú: LDO không giải quyết được vấn đề (LDO chỉ hạ áp, mà pin đã thấp hơn 3.0 V). Buck thuần cũng không. Chỉ boost hoặc buck-boost giữ được ≥ 3.0 V.

## 4. Chọn DC-DC: TI TPS63900 buck-boost ✅

| Thông số (datasheet SLVSET3D) | Giá trị |
|---|---|
| Dải vào | 1.8 – 5.5 V (UVLO lên 1.75 V, trễ 100 mV → tắt ở ~1.65 V) |
| Dải ra | 1.8 – 5 V, 32 mức bước 100 mV bằng điện trở cấu hình (R2D) |
| Dòng tĩnh | **75 nA** typ (1 µA max), tắt 60 nA |
| Dòng ra | > 400 mA khi VI ≥ 2.0 V, VO = 3.3 V |
| Hiệu suất | > 90 % ở 10 µA (Fig. 8-7: ~90 % từ 10 µA tới 10 mA với VI 2.5–3.0 V) |
| Độ chính xác DC đầu ra | ±1.5 % |
| Chế độ | Single-mode (không chuyển buck/boost giật cục), có DVS, giới hạn dòng vào 1–100 mA hoặc unlimited |
| Kiểu vỏ | WSON-10 2.5 × 2.5 mm, **TPS63900DSKR** (Active) |

So sánh với các lựa chọn khác:

| Phương án | Ưu | Nhược | Đánh giá |
|---|---|---|---|
| Trực tiếp | 0 tổn hao | Vi phạm 3.0 V min | ✗ |
| LDO | Đơn giản | Không tăng áp được | ✗ |
| Boost thông thường (Iq ~1 µA) | Rẻ | Khi pin mới > Vout cần chế độ pass-through; Iq cao hơn 13 lần | Có thể, kém hơn |
| **Buck-boost TPS63900** | Iq 75 nA, ~90 % ở µA, chạy tới 1.65 V | Thêm cuộn cảm 2.5 × 2 mm, giá ~0.9–1.2 USD | ✅ chọn |

### 4.1 Cấu hình TPS63900 ✅ (bảng 7-2/7-3 datasheet)

| Chân | Nối | Ý nghĩa |
|---|---|---|
| EN (1) | VBAT | luôn bật (không được để hở) |
| SEL (2) | VBAT | chọn VO(2) (không được để hở) |
| CFG1 (3) | **R2 = 30.1 kΩ ±1 %** → GND | VO(2) = **3.2 V** |
| CFG2 (4) | **R3 = 0 Ω** → GND | giới hạn dòng vào = **Unlimited** |
| CFG3 (5) | R4 = 0 Ω → GND | VO(1) = 1.8 V (không dùng vì SEL luôn cao) |
| LX1 (9) – LX2 (7) | L2 = 2.2 µH **Murata DFE252010F-2R2M** (Isat 3.1 A, DCR 97 mΩ) | cuộn cảm khuyến nghị bảng 8-2 |
| VIN (10) | C1 22 µF sát chân + C2 22 µF bulk | |
| VOUT (6) | C3 22 µF sát chân | |
| GND (8) + thermal pad | GND, ≥ 4 via | |

Điện trở cấu hình phải ±1 %, tempco ≤ ±200 ppm/°C; chân CFG chỉ được đọc lúc khởi động (sau đó tắt, không tốn dòng). Tụ trên chân CFG ≤ 10 pF ⇒ không đặt test point dài trên các chân này.

**Vì sao 3.2 V chứ không 3.0 hay 3.3 V?** 3.0 V – 1.5 % = 2.955 V < 3.0 V ⇒ vi phạm min. 3.1 V – 1.5 % = 3.05 V, còn biên ~50 mV cho đáp ứng quá độ tải. **3.2 V** cho biên ~150 mV. 3.3 V tăng ~3 % năng lượng (chip dùng LDO nội: dòng gần như không đổi theo điện áp ⇒ công suất ∝ V). 🧪 Có thể hạ xuống 3.1 V nếu đo droop VDD3P3 khi TX 20 dBm < 40 mV.

### 4.2 Kiểm tra dòng đỉnh ✅ (công thức 4–5 datasheet)

Tải xấu nhất: TX 20 dBm 140 mA + CPU ~10 mA = 150 mA ở 3.2 V; VI min thiết kế 2.0 V; η = 0.9:

- D = (3.2 – 2.0)/3.2 = 0.375; I_vào trung bình ≈ 3.2·0.15/(0.9·2.0) ≈ **0.27 A**
- I_PEAK ≈ I_out/(η(1–D)) + V_in·D/(2fL) ≈ 0.267 + 0.114 (f ≈ 1.5 MHz) ≈ **0.38 A** < giới hạn dòng đỉnh Q1 (1.33 A min) và < Isat cuộn cảm (3.1 A) ✓
- Với TX 10 dBm (cấu hình mặc định ~65 mA) dòng vào chỉ ~0.13 A.

## 5. Chống ngược cực ✅ (linh kiện) / 💡 (cấu hình)

| Cách | Sụt áp/Tổn hao | Dòng tĩnh | Đánh giá |
|---|---|---|---|
| Diode Schottky nối tiếp | 0.2–0.35 V ở 0.1–0.3 A ⇒ mất ~10 % năng lượng, làm UVLO đến sớm | rò ngược µA | ✗ |
| **PMOS "ideal diode"** | R_DS(on) ≤ 100 mΩ @ 2.5 V ⇒ ~27 mV ở 0.27 A | chỉ rò cổng (nA) | ✅ chọn |
| Cơ khí (đế pin có định hướng) | 0 | 0 | ✅ kết hợp |

Mạch: **Q1 = AO3401A** (P-MOSFET SOT-23, chân 1 G / 2 S / 3 D; chọn vì rẻ và dễ mua, cùng mã với bản nút bấm). Thay thế cắm thẳng: Diodes DMG2305UX-7 (20 V, 4.2 A, V_GS(th) ≤ 0.9 V, R_DS(on) 52 mΩ @ 4.5 V / 100 mΩ @ 2.5 V, V_GS ±8 V), Si2301CDS. Điều kiện: kênh P, V_GS(th) tối đa ≤ ~1.3 V, có R_DS(on) tại V_GS = −2.5 V. 🧪 Đối chiếu thông số AO3401A với datasheet hãng trước khi chốt.

```
 J1.1(+) ── VBAT_RAW ──┬── D(3) Q1 S(2) ─── VBAT ──► TPS63900 VIN
                       │        G(1)
                    D2 ESD       │
              (PESD5V0U1BL,     R1 100 kΩ
               2 chiều)          │
 J1.2(–) ── GND ─────────────────┴──────────
```

- Lắp đúng: diode thân (anode = D, cathode = S) dẫn trước, V_GS ≈ –V_pin ⇒ kênh mở hoàn toàn từ V_pin ≥ ~1.8 V (V_GS(th) max 0.9 V, R_DS(on) đặc tả tới 1.8 V).
- Lắp ngược: D = –3 V, diode thân phân cực ngược, V_GS = 0 ⇒ Q1 khóa; mạch không nhận điện áp âm.
- **D2 phải là loại 2 chiều** (PESD5V0U1BL,315, 5 V, rò cỡ nA; hoặc PESD3V3S1BL nếu mua được): một TVS 1 chiều sẽ dẫn thuận và **ngắn mạch pin** khi lắp ngược. D2 bảo vệ ESD khi người dùng chạm tiếp điểm lúc thay pin.
- 💡 Pin nằm **ngoài PCB**, trong ngăn pin của vỏ: tiếp điểm Keystone 1087-1 (+, tấm có núm lõm chỉ chạm được núm dương) và 1087-2 (–, lò xo) gài vào khe vỏ; 2 dây 0.15 mm² hàn từ đuôi tiếp điểm vào J1 (pad 1 vuông = +). Vỏ có biểu tượng cực ±. Q1 vẫn cần: lắp ngược pin hoặc hàn đảo dây đều được chặn.
- 🧪 Dây pin ≤ ~60 mm, xoắn đôi, đi ra từ đầu PCB **xa anten** (J1 ở x = 34.2 mm, anten ở x = 0–5.2 mm); điện trở dây (~0.12 Ω/m với 0.15 mm²) không đáng kể ở dòng đỉnh vài chục mA.
- 🧪 Kiểm tra sơ đồ chân SOT-23 của MOSFET thực mua (1 = G, 2 = S, 3 = D) với datasheet: sai chân thì mạch chống ngược cực mất tác dụng.

## 6. Tụ bulk, decoupling và sụt áp khi phát RF

### 6.1 Bố trí tụ (theo sơ đồ tham chiếu Espressif) ✅

| Vị trí | Tụ | Mã |
|---|---|---|
| VBAT (vào DC-DC) | C1, C2: 2 × 22 µF X5R 6.3 V 0603 | GRM188R60J226MEA0D |
| VOUT DC-DC | C3: 22 µF | GRM188R60J226MEA0D |
| VDD3P3 chân 1/2 | C4 22 µF (≥ 10 µF theo Espressif) + C5 1 µF + C6 0.1 µF | |
| VDD3P3 chân 31 (gần ANT) | C7 10 nF | GRM155R71H103KA88D |
| VDD3P3 chân 27/30 (gần XTAL) | C8 1 µF + C9 0.1 µF | |
| VDDPST2 chân 20 | C10 0.1 µF | |
| VBAT/VDDA_PMU chân 18/19 (R5 = 0 Ω như tham chiếu) | C11 0.1 µF | |
| VDDPST1 chân 9 | C12 0.1 µF | |
| DRV5032 VCC | C24 0.1 µF (TI khuyến nghị ≥ 0.1 µF) | |

Tổng điện dung trên 3V2 ≈ 70 µF danh định (≈ 35–50 µF sau suy giảm DC-bias) – nằm trong ma trận cho phép của TPS63900 (bảng 8-1: 10…≥ 300 µF với 2.2 µH).

### 6.2 Ngân sách sụt áp ✅ (tính) / 🧪 (đo)

**Phía 3V2 (chip):** 3.2 V × (1 – 1.5 %) = 3.152 V. Đáp ứng quá độ tải 0 → 100 mA của TPS63900 (Fig. 8-22…8-24, thang 20 mV/div) chỉ vài chục mV. Mục tiêu thiết kế: droop ≤ 100 mV ⇒ VDD3P3 ≥ **3.05 V > 3.0 V** ✓.

**Phía pin:** dòng vào xung ≤ 0.27 A (TX 20 dBm, pin 2.0 V). Với nội trở pin 0.3 Ω (mới, 20 °C) → 1 Ω (cũ/lạnh, *ước lượng*): ΔV = 0.08–0.27 V. Pin cuối đời 2.0 V – 0.27 V = 1.73 V > UVLO tắt 1.65 V ✓ (biên mỏng ⇒ firmware cảnh báo pin yếu từ 2.7 V/2.5 V; khi lạnh sâu nên giảm công suất TX).
Bulk 44 µF ở VIN chỉ đỡ được các đỉnh < ~100 µs (ΔV = I·t/C = 0.27 A·100 µs/44 µF ≈ 0.6 V) – phần còn lại do pin cấp; vì thế tụ lớn hơn (tantalum polymer 100–220 µF) **không** được thêm mặc định (rò µA của tantalum ăn pin), chỉ để footprint DNP.

🧪 Phép đo bắt buộc ở EVT: oscilloscope 2 kênh tại VBAT và VDD3P3 khi phát liên tục ở 20 dBm và 10 dBm, pin mới / pin còn 10 % / ở –10 °C.

## 7. Giám sát nguồn và reset 💡

- **U4 = TI TPS3839K33DBZR** (SOT-23: 1 GND, 2 RESET push-pull, 3 VDD): V_IT– = 2.857 / **2.93** / 2.974 V, trễ 29 mV, giữ reset 200 ms sau khi nguồn ổn định, dòng tĩnh **150 nA**.
- RESET → **R6 = 1 kΩ** → CHIP_EN, **C13 = 100 nF** tại CHIP_EN (lọc nhiễu, τ = 0.1 ms). R6 cho phép jig sản xuất kéo CHIP_EN xuống để reset mà không đánh nhau với đầu ra push-pull (dòng ≤ 3.2 mA).
- Bảo đảm tSTBL ≥ 50 µs và chống hỏng flash khi pin sụt/được tháo – đúng khuyến nghị "power monitor ~3.0 V" của Espressif.
- Phương án dự phòng (DNP): R7 10 kΩ lên 3V2 + C14 1 µF (mạch RC tham chiếu của Espressif) khi bỏ U4.
- BOD nội ESP32-H2 giữ mặc định (mức 0 ≈ 2.57 V theo Kconfig, IDF ghi chú là ước lượng).

## 8. Đo điện áp pin bằng ADC, không tiêu hao liên tục ✅ (firmware) / 🧪 (sai số)

```
 VBAT ── R8 1 MΩ ──┬── GPIO1 (ADC1_CH0) ── C25 10 nF ── GND
                   │
                   R9 1 MΩ
                   │
                GPIO22 (VBAT_EN): high-Z khi nghỉ / output LOW khi đo
```

- Khi nghỉ GPIO22 ở high-Z (`GPIO_MODE_DISABLE`) ⇒ **không có đường DC xuống GND ⇒ 0 µA** (chỉ còn rò pad ≤ 50 nA max theo datasheet, thường nhỏ hơn nhiều). Nút ADC nổi lên VBAT qua 1 MΩ; vì VBAT ≤ 3.3 V ≈ 3V2, diode ESD của pad không dẫn.
- Khi đo: GPIO22 = LOW, dòng phân áp 1.5 µA trong ~50 ms mỗi 12 h (~1.7 nA trung bình).
- τ = (R8‖R9)·C25 = 0.5 MΩ × 10 nF = 5 ms; firmware chờ 40 ms (8 τ) rồi lấy trung bình 8 mẫu.
- ADC: suy hao 6 dB (ATTEN2, 0–1900 mV, sai số tổng ±12 mV sau hiệu chuẩn – datasheet bảng 5-5); VBAT/2 ≤ 1.7 V. Sai số tổng (ADC ×2 + điện trở 1 % + rò pad × 0.5 MΩ) ≈ ±40–60 mV ⇒ đủ cho ngưỡng Warning 2.7 V / Critical 2.5 V.
- Đo ở **đầu vào DC-DC** (VBAT) vì rail 3V2 luôn được ổn áp.
- 🧪 Li-MnO2 phẳng ⇒ cân nhắc đo **ngay sau một burst TX** (điện áp dưới tải phản ánh nội trở/độ cạn pin tốt hơn). Bảng chuyển đổi mV → % trong `battery_monitor.cpp` là điểm xuất phát, phải hiệu chỉnh bằng thử xả thực tế (docs/common/10, test B-03).

## 9. Tóm tắt dòng tĩnh của khối nguồn ✅

| Thành phần | Dòng | Nguồn số liệu |
|---|---|---|
| TPS63900 Iq (vào VIN) | 0.075 µA typ | datasheet |
| TPS3839K33 | 0.15 µA typ | datasheet |
| Q1 rò cổng + D2 rò | < 0.01 µA | datasheet (D2 rò cỡ nA) |
| Phân áp đo pin | 0 (chỉ khi đo) | thiết kế |
| **Tổng khối nguồn** | **≈ 0.23 µA** | so với ~27 µA sàn sleep của ESP32-H2 |

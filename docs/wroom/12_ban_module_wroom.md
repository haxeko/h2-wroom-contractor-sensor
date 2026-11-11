# 12 – Bản dùng module ESP32-H2-WROOM-02C (KiCad 10)

Bản thứ hai của cảm biến cửa, song song với bản dùng chip ESP32-H2 rời (docs/chip/05–06). Mạch ngoài module (nguồn, chống ngược cực, reset, nút, Hall, LED, đo pin, pad test, dây pin) **giống hệt** bản chip rời, và dùng **cùng pin CR123A rời, nối 2 dây vào J1**. Phần RF (thạch anh 32 MHz, mạng phối hợp, anten, tụ 3V3, RC trên EN) nằm trong module.

> **Bản hiện tại: PCB 2 lớp** (thay cho bản 4 lớp, còn trong lịch sử git ở commit `3d4bf9c`). Phần RF nằm trọn trong module nên board nền không có đường nào cần kiểm soát trở kháng (§3).
>
> **Lịch sử.** Bản module từng được thử với pin cúc áo CR2450 nằm cạnh board (rev A: giới hạn dòng 25 mA + 6 tụ 220 µF trên rail; rev B: 2 tụ 220 µF phía pin). Cả hai đã bị bỏ: ESP32-H2 chỉ dùng được khoảng 40 % dung lượng CR2450, tức khoảng nửa năm (§8). Bản hiện tại dùng CR123A: khoảng 2.3–2.6 năm, không cần tụ lớn.

| | Bản chip rời (`hardware/chip/`) | **Bản module (`hardware/wroom/`)** |
|---|---|---|
| SoC | ESP32-H2FH4S (QFN32) | ESP32-H2-WROOM-02C-H4S (4 MB flash, anten PCB) |
| PCB | 36 × 18 mm, 4 lớp | **32 × 20 mm, 2 lớp**, 1.0 mm; anten của module **nhô ra 6 mm** ngoài mép trái ⇒ dài tổng 38 mm |
| Pin | CR123A rời, 2 dây vào J1 | **giống hệt: CR123A rời, 2 dây vào J1** |
| Nguồn | TPS63900 3.2 V, không giới hạn dòng vào | **giống hệt** |
| BOM lắp ráp | 27 dòng / 46 linh kiện, có linh kiện 0201 | **18 dòng / 27 linh kiện**, nhỏ nhất 0402 |
| RF | tự thiết kế: GCPW 50 Ω, stub, tuning VNA, J2 đo dẫn | của module – không cần tuning mạng phối hợp, không có cổng đo dẫn |
| Chứng nhận vô tuyến | phải tự làm toàn bộ | 🧪 có thể tận dụng chứng nhận của module (kiểm tra danh sách chứng nhận Espressif cho từng thị trường) |
| Firmware | `firmware/` (`sdkconfig.defaults`) | **dùng nguyên, cùng file build**: cùng GPIO, cùng 4 MB flash, cùng pin |
| Tuổi thọ pin (ước tính) | ~2.3–2.6 năm | **~2.3–2.6 năm** (docs/common/09; 🧪 đo dòng ngủ thật của module) |

## 1. Nguồn tham chiếu (datasheet ESP32-H2-WROOM-02C v1.2, 2025-10-13) ✅
- 29 chân, 20.0 × 18.0 × 3.2 mm, –40…105 °C; mã đặt hàng -H2S (2 MB) / **-H4S (4 MB, dùng ở đây)**.
- VDD33 3.0 / 3.3 / 3.6 V (min/typ/max), tuyệt đối tối đa 3.6 V ⇒ TPS63900 đặt **3.2 V** như bản chip rời (thấp hơn 3.3 V để tiết kiệm ~3 % năng lượng; còn 0.2 V trên mức tối thiểu).
- Bảng 2 chân (dùng trong thiết kế): 1 3V3, 2 EN, 5 IO10, 6 IO11, 7 IO8, 8 IO9, 9/13/29 GND, 14 VBAT, 15 IO22, 21 RXD0 (GPIO23), 22 TXD0 (GPIO24), 27 IO1.
- VBAT (chân 14): "nối với 3V3 bên trong (mặc định) hoặc pin ngoài 3.0–3.6 V" ⇒ để trống.
- EN: datasheet nêu RC 10 kΩ / 1 µF đã có trong module (sơ đồ module ghi R9 "10K(NC)" + C5 1 µF) – bên ngoài vẫn dùng TPS3839 + R6 1 kΩ (push-pull, không để EN thả nổi).
- Strapping: GPIO9 = 0 + GPIO8 = 1 ⇒ Joint Download Boot (giống bản chip: SW1/TP5, R11).
- Land pattern (hình 7): pad 1.5 × 0.9 mm, bước 1.5 mm, nhô 0.5 mm ra ngoài thân module; pad GND 29 = dải 2.8 × 0.55 + khối 2.8 × 1.6 mm có via; vùng anten = 6 mm đầu module.
- Dòng: thu 802.15.4 **26 mA**, phát 36 mA @ 0 dBm, 60 mA @ 9 dBm, 140 mA @ 20 dBm (bảng 13); CPU chạy 13 mA @ 64 MHz, 17 mA @ 96 MHz (bảng 14); deep-sleep 7 µA, light-sleep 85 µA (ngoại vi tắt hết: 25 µA) (bảng 15). Firmware phát 10 dBm ⇒ đỉnh khoảng 60–65 mA trên rail, CR123A và TPS63900 đáp ứng thoải mái.

## 2. Ánh xạ chân (firmware không đổi)

| Chức năng | GPIO | Chân module | Net |
|---|---|---|---|
| Đo pin (ADC) | GPIO1 | 27 | VBAT_ADC |
| Strap download | GPIO8 | 7 | IO8_STRAP (R11 100 k lên 3V2) |
| Nút / BOOT | GPIO9 | 8 | BTN (R10 100 k, SW1) |
| Hall | GPIO10 | 5 | HALL_OUT |
| LED | GPIO11 | 6 | LED_DRV → R12 → D1 |
| Bật phân áp pin | GPIO22 | 15 | VBAT_EN |
| UART0 | GPIO23 / GPIO24 | 21 / 22 | U0RXD / U0TXD_CHIP → R13 510 Ω |
| Reset | EN | 2 | CHIP_EN ← R6 ← TPS3839 |

Chân không dùng (IO0, IO2–IO5, IO12–IO14, IO25–IO27, NC 16–19, VBAT) có cờ no-connect. Thạch anh 32.768 kHz tùy chọn của bản chip (Y2) **không** đưa vào bản module (có thể nối vào IO13/IO14 = chân 11/12 nếu cần).

## 3. PCB 2 lớp 💡 (đã làm trong `hardware/wroom/`)

**Vì sao 2 lớp là đủ.** Thạch anh, mạng phối hợp RF và anten đều nằm trong module. Board nền chỉ có nguồn, vài tín hiệu chậm và pad test, không có đường nào cần trở kháng 50 Ω. Bản chip rời thì vẫn phải 4 lớp vì có đường RF trên board.

- Module ở đầu trái, xoay để **vùng anten 6 mm nằm ngoài mép board** (không có đồng ở bất kỳ lớp nào dưới anten; Espressif: xem *ESP32-H2 Hardware Design Guidelines → Positioning a Module on a Base Board*). Pad 1 ở (1.1; 18.75), hàng pad 1–9 dọc mép dưới (mặt A), 20–28 dọc mép trên, 10–19 hướng vào trong board.
- Board **32 × 20 mm**: cao 20 mm = module 18 mm + pad nhô 0.5 mm mỗi bên + khe tới mép 0.5 mm.
- **GND:** đổ đồng cả hai mặt, nối với nhau bằng 84 via GND (via ở từng pad GND, hàng via quanh mép, lưới 2 mm; cả board có 121 via). Mặt trên dưới thân module chỉ có GND. Sau khi đổ đồng, script kiểm tra mọi pad GND còn nối với phần GND chính (`repair_gnd()`), nếu có vùng bị các đường dây cô lập ở cả hai mặt thì tự thêm via hoặc đường GND.
- **3V2:** không còn mặt nguồn, đi bằng dây. Đường trục rộng 0.4 mm, dài 26.5 mm (khoảng 33 mΩ, sụt dưới 5 mV ở 140 mA): C3 (tụ ra TPS63900) → C4 → C6 → via → mặt dưới → chân 1 của module. Các nhánh 0.3 mm tới U4, R10, R11, U3/C24, TP1.
- **Bố trí theo đường trục 3V2.** Đường trục chạy chéo ở mặt dưới và chia board làm hai nửa, mỗi tín hiệu ở yên một nửa nên không phải cắt qua nhau:
  - nửa trên: hàng chân trên của module (UART, VBAT_ADC) và VBAT_EN ⇒ TPS63900, mạch phân áp đo pin R8/R9/C25 (dải trên cùng giữa module và C1), R13;
  - nửa dưới: hàng chân dưới (EN, Hall, LED, strap, nút) ⇒ TPS3839 U4 + R6, nút SW1, LED, Hall U3 sát mép mặt A.
- Các chân tín hiệu ở hai hàng bên của module có đoạn thoát 1.5 mm vào trong + via, đi tiếp ở mặt dưới. Pad 29 nối đặc vào GND qua 3 via của footprint.
- **Via 0.6 / 0.3 mm cho toàn board, không có lỗ nào nhỏ hơn 0.3 mm** (mức tối thiểu của mạch 1–2 lớp ở JLCPCB). Vì vậy U2 dùng footprint WSON không có via tản nhiệt 0.2 mm; pad giữa của U2 nối với chân GND 8 ở mặt trên.
- **J1 = 2 pad xuyên lỗ hàn dây pin** (lỗ 0.7 mm, pad 1.7 mm, bước 2.54 mm) ở đầu phải, tâm (30.24; 7.98) và (30.24; 10.52): **pad 1 vuông = +**, pad 2 tròn = –; có dấu "+" và "–" trên lớp in.
- 2 lỗ định vị (26.3; 1.55) và (28.97; 18.55), 2 fiducial (20.3; 19.0) và (31.1; 1.0).
- ✅ KiCad 10.0.8: **ERC 0, DRC 0 vi phạm / 0 kết nối hở / 0 lệch sơ đồ** (`hardware/wroom/drc_report.json`). 164 đoạn đường (mặt trên 166 mm, mặt dưới 119 mm), đường nhỏ nhất 0.15 mm, khe hở nhỏ nhất 0.17 mm.

**Pad test** (mặt dưới, Ø1.0 mm, lưới 2 × 6 bước 2.54 mm ở đầu phải; **vị trí khác bản 4 lớp**, jig phải làm theo bảng này):

| y (mm) | Cột x = 27.7 | Cột x = 30.24 |
|---|---|---|
| 2.90 | TP7 U0TXD | TP10 VBAT_ADC |
| 5.44 | TP8 U0RXD | TP1 3V2 |
| 7.98 | TP3 VBAT | **J1.1 pin +** |
| 10.52 | TP5 BTN (GPIO9) | **J1.2 pin –** |
| 13.06 | TP6 IO8_STRAP | TP2 GND |
| 15.60 | TP9 HALL_OUT | TP4 CHIP_EN |

Jig cấp nguồn qua J1 như bản chip rời.

**Đánh đổi so với 4 lớp** 🧪: không còn mặt GND liền riêng, nên khả năng chống nhiễu và phát xạ kém hơn một chút. Tín hiệu trên board đều chậm nên rủi ro thấp, nhưng phải đo trên mẫu: dòng ngủ, gợn trên 3V2 khi phát, tầm phủ sóng.

## 4. File sản xuất (`hardware/wroom/fab/`)
- `matter_contact_sensor_wroom-gerber.zip` (Gerber 2 lớp đồng + khoan), `assembly/…-bom.csv`, `assembly/…-cpl.csv`, PDF sơ đồ / lắp ráp / từng lớp, ảnh render (không có thân 3D của module), thống kê.
- **Thông số đặt PCB: 32 × 20 mm, 2 lớp, dày 1.0 mm** (0.8–1.6 mm đều được vì không có đường kiểm soát trở kháng), đồng 1 oz, đường/khe nhỏ nhất 0.15 / 0.17 mm, via 0.6 / 0.3 mm, lỗ nhỏ nhất 0.3 mm. Phủ ENIG nên dùng cho WSON bước 0.5 mm và pad module; HASL không chì rẻ hơn, 🧪 thử trước nếu muốn dùng.
- Linh kiện chỉ ở mặt trên (lắp ráp một mặt). Pin, tiếp điểm pin và dây không có trong BOM/CPL lắp ráp (lắp tay sau khi test); xem §7 và dòng 33–34 của `hardware/chip/bom.csv`.
- 🧪 Góc xoay CPL theo quy ước KiCad – kiểm tra trên ảnh xem trước của nhà lắp ráp, đặc biệt module U1 (pad 1 ở góc dưới-trái, anten hướng ra mép trái), SOT-23, WSON, LED.
- Module MSL 3 (datasheet): hàn trong 168 h sau khi mở túi, hoặc sấy.

## 5. Sinh lại
```
python3 tools/kicad/gen_libs.py                              # thêm symbol/footprint ESP32-H2-WROOM-02C vào mcs.*
python3 tools/kicad/gen_schematic.py --variant wroom         # sơ đồ từ tools/design_data_wroom.py
/usr/bin/python3.12 tools/kicad/build_pcb_wroom.py           # đặt linh kiện, đi dây, đổ đồng, DRC
python3 tools/kicad/export_fab.py --variant wroom            # Gerber/BOM/CPL/PDF/ảnh
```

## 6. Cần kiểm tra trước khi đặt hàng 🧪
1. Đối chiếu footprint `mcs:ESP32-H2-WROOM-02C` với hình 6/7 của datasheet (in 1:1 đặt module thật lên).
2. Vỏ: chừa khoảng trống cho 6 mm anten nhô ra, không kim loại/pin/dây gần anten theo hướng dẫn Espressif; đo RSSI/tầm phủ trong vỏ.
3. Đo dòng ngủ thực tế của module (flash và linh kiện trong module có thể khác bản chip rời) rồi cập nhật docs/common/09.
4. Board 2 lớp: đo gợn và sụt áp tại chân 3V3 của module khi phát, và so tầm phủ với devkit.
5. Kỹ sư layout rà đường do router sinh (nhiều đoạn 45° ngắn).

## 7. Pin CR123A và vỏ 💡

```
 Nhìn từ trên (mm)
        ┌───────── PCB 32 × 20 ─────────┐  dây +/–   ┌──────── ngăn pin ────────┐
  ┌───┐ │                            J1 │────────────│ (+)      CR123A      (–) │
  │ANT│ │  module WROOM   nguồn / UI /  │            │        Ø17 × 34.5        │
  └───┘ │  (18 × 20)      Hall          │            │  tiếp điểm 1087-1/1087-2 │
   6 mm └───────────────────────────────┘            └──────────────────────────┘
        anten ở đầu xa pin nhất              khoảng 42 mm
```

- **Pin:** CR123A Li-MnO2 3 V, 1500–1700 mAh, Ø17 × 34.5 mm. Nội trở dưới 1 Ω nên cấp được trực tiếp các xung 60–200 mA của radio qua TPS63900: **không cần tụ lớn, không cần giới hạn dòng**.
- **Lắp pin:** giống bản chip rời (docs/common/02, docs/chip/06 §9): pin nằm trong ngăn pin của vỏ, giữa tiếp điểm Keystone 1087-1 (+, núm lõm chỉ chạm được cực dương) và 1087-2 (–, lò xo). Hai dây 0.15 mm² (26 AWG), dài ≤ 60 mm, đỏ/đen, hàn từ đuôi tiếp điểm vào J1 (đỏ vào pad 1 vuông). Q1 chặn cả trường hợp lắp ngược pin lẫn hàn đảo dây.
- **Vỏ tham chiếu (ước lượng, chưa có bản vẽ):** dáng thon như bản chip rời, PCB ở đầu anten, ngăn pin phía sau. Bên trong: 6 (anten) + 32 (PCB) + khoảng 42 (ngăn pin) ≈ 80 mm dài, rộng 20 mm, cao khoảng 18 mm (pin Ø17). Vỏ ngoài khoảng **84 × 24 × 22 mm**.
- Đi dây pin dọc mép board phía xa anten; không để dây hoặc pin nằm trong vùng 6 mm anten và phần kéo dài của nó.
- Hall U3 nằm sát mép mặt A (y = 20): nam châm gắn ở phía mép đó của vỏ (docs/common/03).

## 8. Vì sao không dùng pin cúc áo CR2450 ✅ (tính toán) / 🧪 (chưa đo)

Module rút 26 mA khi thu và 36 mA khi phát 0 dBm. Qua TPS63900, pin phải cấp khoảng 45–60 mA. CR2450 có nội trở lớn và tăng dần khi dùng (datasheet Energizer CR2450, xung 2 s, 21 °C):

| Dung lượng đã dùng | 0–200 mAh | 250 mAh | 300 mAh | 350 mAh | 400 mAh | 450 mAh |
|---|---|---|---|---|---|---|
| Nội trở | 10–12 Ω | 20 Ω | 30 Ω | 40 Ω | 60 Ω | 90 Ω |

Datasheet Jauch CR2450 cho kết quả tương tự (xung 200 Ω trong 5 s: khoảng 18 Ω khi mới, 35 Ω ở 300 mAh) và ghi dòng xung tối đa 15 mA.

`python3 tools/coin_cell_buffer.py` mô phỏng pin + tụ + TPS63900. Ô ghi dung lượng đã dùng (mAh) mà sự kiện còn chạy được:

| Sự kiện | Không có tụ lớn | 2 × 220 µF phía pin | 6 × 220 µF phía pin | Rev A (giới hạn 25 mA + 6 tụ trên rail) |
|---|---|---|---|---|
| Poll Thread (mỗi 15 s) | 220 | 520 | 520 | 520 |
| Đóng/mở cửa: 2 báo cáo + 2 poll nhanh | 220 | 260 | 520 | 350 |
| **Thread kết nối lại (thu liên tục 0.75 s)** | 220 | **250** | **250** | **không đạt** |

- **Giới hạn là lần thu liên tục khi Thread kết nối lại.** Pin phải tự cấp khoảng 50 mA trong 1–2 giây, không tụ gốm nào gánh nổi. Việc này cần nội trở pin ≤ khoảng 20 Ω, tức chỉ **khoảng 250 mAh đầu (40 %)** của CR2450.
- Tuổi thọ tương ứng: **khoảng 0.5 năm** (`python3 tools/battery_life.py --capacity-mah 600 620 --usable-fraction 0.40 --tx-dbm 0`), so với khoảng 2.3–2.6 năm của CR123A.
- Rev A (giới hạn dòng vào 25 mA) còn tệ hơn: 25 mA từ pin chỉ ra khoảng 18 mA trên rail, ít hơn dòng thu 26 mA, nên reset ở mọi lần kết nối lại, kể cả với pin mới.
- Kết luận: ESP32-H2 không hợp với pin cúc áo (dòng thu cao gấp khoảng 4–5 lần các SoC Thread chuyên cho pin cúc áo). Hai thiết kế CR2450 còn trong lịch sử git (commit `b48dd7d` rev A, `f882acb` rev B) để tham khảo.

## 9. Firmware ✅ (build thử thành công)
- **Dùng đúng bản build mặc định của bản chip rời** (`sdkconfig.defaults`): cùng GPIO, cùng pin CR123A, TX 10 dBm, CPU 96 MHz. Không còn lớp cấu hình riêng cho bản module.
- Các cơ chế bảo vệ pin (docs/common/08 §3.6) áp dụng cho cả hai board: TX đúng công suất từ khung đầu tiên, Deep-sleep khi chưa ghép nối, bộ bảo vệ khởi động khi pin yếu, log mức sản xuất.
- Kết quả build: docs/common/08 §8.1.

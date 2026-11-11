# 07 – BOM (Bill of Materials) rev A

Nguồn dữ liệu duy nhất: `hardware/chip/bom.csv` (bảng dưới được sinh tự động từ CSV). Tham chiếu ký hiệu khớp 100 % với `hardware/chip/netlist.csv` (kiểm tra bằng script khi tạo tài liệu).

Quy ước cột "Lắp": **Mandatory** = bắt buộc; **Recommended** = khuyến nghị (có phương án thay thế trên PCB); **DNP** = có footprint, không hàn mặc định; **EVT/DVT only** = chỉ lắp ở mẫu thử.

## 1. Danh sách linh kiện

| # | Ref | SL | Linh kiện | Hãng | Mã (MPN) | Lắp | Thay thế | Giá tham khảo (USD @1k) |
|---|---|---|---|---|---|---|---|---|
| 1 | U1 | 1 | ESP32-H2 SoC, RISC-V 96 MHz, 802.15.4 + BLE 5, 4 MB in-package flash | Espressif | `ESP32-H2FH4S` | Mandatory | ESP32-H2FH2S (2 MB: no OTA - not recommended) | 1.40-1.90 |
| 2 | U3 | 1 | Hall switch omnipolar, push-pull, 20 Hz, 1.6 uA typ @3 V, BOP 4.8 mT max | Texas Instruments | `DRV5032FADBZR` | Mandatory | DRV5032FBDBZR (5 Hz 0.69 uA – dòng thấp hơn, giá cao hơn); DRV5032FBLPG (TO-92 option) | 0.35-0.55 |
| 3 | U2 | 1 | Buck-boost 1.8-5.5 V in, 75 nA Iq, set to 3.2 V | Texas Instruments | `TPS63900DSKR` | Mandatory | TPS63900DSKRG4 | 0.95-1.40 |
| 4 | L2 | 1 | Inductor 2.2 uH, Isat 3.1 A, DCR 97 mOhm | Murata | `DFE252010F-2R2M` | Mandatory | DFE201612E-2R2M; Coilcraft XFL4020-222ME | 0.10-0.20 |
| 5 | U4 | 1 | Supply supervisor 2.93 V, push-pull RESET, 150 nA | Texas Instruments | `TPS3839K33DBZR` | Recommended | TPS3831K33DQNR (X2SON with MR); RC network R7/C14 | 0.25-0.40 |
| 6 | Q1 | 1 | P-MOSFET reverse polarity protection, SOT-23 (1 G, 2 S, 3 D), -30 V, logic level (Rds specified at Vgs -2.5 V) | Alpha & Omega | `AO3401A` | Mandatory | Diodes DMG2305UX-7; Vishay Si2301CDS; Infineon IRLML6402 (verify pinout 1 G / 2 S / 3 D) | 0.02-0.05 |
| 7 | D2, D3 | 2 | ESD diode BIDIRECTIONAL 5 V, nA leakage (must be bidirectional: sits in front of Q1) | Nexperia | `PESD5V0U1BL,315` | D2 Mandatory, D3 DNP | PESD3V3S1BL (original choice); any bidirectional SOD-882 ESD diode >= 3.6 V | 0.03-0.06 |
| 8 | Y1 | 1 | Crystal 32 MHz, +-10 ppm, CL 10 pF, ESR 50 Ohm | ECS Inc. | `ECS-320-10-37B2-CKY-TR` | Mandatory | Murata XRCGB32M000F1H00R0; YXC X201632MOB4SI (verify stability) | 0.15-0.30 |
| 9 | Y2 | 1 | Crystal 32.768 kHz, CL 12.5 pF, ESR 70 kOhm, +-20 ppm | Abracon | `ABS07-32.768KHZ-T` | DNP (option) | Epson FC-135 (verify ESR <= 70k) | 0.20-0.35 |
| 10 | C19, C20 | 2 | 0201 C0G 1.5 pF +-0.1 pF 50 V (tune 1.2-1.8 pF) | Murata | `GRM0335C1H1R5BA01D` | Mandatory (value tuned) | GRM0335C1H1R2BA01D / GRM0335C1H1R8BA01D | 0.01-0.03 |
| 11 | L4 | 1 | 0201 thin-film inductor 2.7 nH +-0.1 nH (tune 2.0-3.0 nH) | Murata | `LQP03TN2N7B02D` | Mandatory (value tuned) | LQP03TN2N0B02D ... LQP03TN3N0B02D (Espressif series LQP03TN2NXB02D) | 0.02-0.05 |
| 12 | C21, L6 | 2 | 0201 0 Ohm jumper (C21 may become 10 pF C0G DC-block) | Yageo | `RC0201JR-070RL` | Mandatory | any 0201 0 Ohm | 0.002 |
| 13 | L5, C22, C23 | 3 | Tuning footprints (0201) | — | `DNP` | DNP | values from VNA tuning | — |
| 14 | J2 | 1 | RF coaxial switch connector 50 Ohm DC-11 GHz, 1.35 mm high (conducted test port, normally closed) | Hirose | `MS-156C3` | EVT/DVT (MP: may stay populated - switch is closed without probe) | Murata MM8130-2600RB8 (different footprint - not drop-in) | 0.40-0.90 |
| 15 | ANT1 | 1 | PCB meandered IFA (TI SWRA117D), 15.2 x 5.7 mm copper | — | `PCB copper (footprint Texas_SWRA117D_2.4GHz_Right[_L1_x])` | Mandatory | — | 0 |
| 16 | L3 | 1 | Inductor 24 nH 0402 (series on XTAL_P, Espressif initial value) | Murata | `LQW15AN24NG00D` | Mandatory (value tuned) | LQG15WH24NJ02D; 0 Ohm/resistor per Espressif | 0.02-0.05 |
| 17 | C15, C16 | 2 | 0402 C0G 15 pF 50 V (crystal load; tune) | Murata | `GRM1555C1H150JA01D` | Mandatory | any C0G 15 pF | 0.003 |
| 18 | C17, C18 | 2 | 0402 C0G 22 pF (32 kHz load) | Murata | `GRM1555C1H220JA01D` | DNP | any C0G | 0.003 |
| 19 | C1, C2, C3, C4 | 4 | 22 uF 6.3 V X5R +-20 % 0603 | Murata | `GRM188R60J226MEA0D` | Mandatory | Samsung CL10A226MQ8NRNC (verify) | 0.02-0.05 |
| 20 | C5, C8, C14 | 3 | 1 uF 10 V X5R 0402 | Murata | `GRM155R61A105KE15D` | C5, C8 Mandatory; C14 DNP | any X5R 1 uF | 0.004 |
| 21 | C6, C9, C10, C11, C12, C13, C24 | 7 | 100 nF 16 V X7R 0402 | Murata | `GRM155R71C104KA88D` | Mandatory | any X7R 100 nF | 0.002 |
| 22 | C7, C25 | 2 | 10 nF 50 V X7R 0402 | Murata | `GRM155R71H103KA88D` | Mandatory | any X7R 10 nF | 0.002 |
| 23 | R2 | 1 | 30.1 kOhm 1 % 100 ppm 0402 (TPS63900 CFG1 = 3.2 V) | Yageo | `RC0402FR-0730K1L` | Mandatory | any 1 % <= 200 ppm | 0.002 |
| 24 | R3, R4, R5 | 3 | 0 Ohm 0402 | Yageo | `RC0402JR-070RL` | Mandatory | any | 0.002 |
| 25 | R1, R10, R11 | 3 | 100 kOhm 1 % 0402 | Yageo | `RC0402FR-07100KL` | Mandatory | any | 0.002 |
| 26 | R8, R9 | 2 | 1 MOhm 1 % 0402 | Yageo | `RC0402FR-071ML` | Mandatory | any 1 % | 0.002 |
| 27 | R6, R12 | 2 | 1 kOhm 1 % 0402 | Yageo | `RC0402FR-071KL` | Mandatory | any | 0.002 |
| 28 | R7 | 1 | 10 kOhm 1 % 0402 (RC reset fallback) | Yageo | `RC0402FR-0710KL` | DNP | any | 0.002 |
| 29 | R13 | 1 | 510 Ohm 5 % 0402 (U0TXD series, 470-560 Ohm) | Yageo | `RC0402JR-07510RL` | Mandatory | any | 0.002 |
| 31 | D1 | 1 | LED red 630 nm 0603, Vf 1.75 V @ 2 mA | Kingbright | `APTD1608LSURCK` | Mandatory | Kingbright APHD1608LSURCK | 0.03-0.08 |
| 32 | SW1 | 1 | Tactile switch SPST-NO 3.0 x 2.5 mm, top actuated, 153 gf | Omron | `B3U-1000P` | Mandatory | B3U-1000P-B (with boss); side actuated B3U-3000P (verify) | 0.15-0.30 |
| 33 | BT1 (trong vỏ) | 1+1 | CR123A contacts OFF the PCB, in the housing battery compartment: + button contact 1087-1, - coil spring 1087-2 (L outside = 39.8 mm for 2/3A cells); housing slots hold the plates; 2 wires 0.15 mm² (26 AWG), ≤ 60 mm, red/black, soldered from the contact tails to J1 (+ = square pad 1) | Keystone | `1087-1 + 1087-2` | Mandatory | Keystone 1017-1 (leaf) for the - end; SMT pairs need >= 43 mm (Keystone 254 x2) - Keystone 1128 holder is 18.3 mm wide / 52.3 mm long: does not fit | 0.15-0.40 (pair) |
| 34 | — | 1 | CR123A Li-MnO2 3 V, 1500 mAh | Energizer | `EL123AP` | Ship with product | Panasonic CR123A (1550 mAh); Duracell DL123A | 1.00-2.00 (OEM bulk) |
| 35 | — | 1 | Magnet NdFeB N35 20 x 6 x 3 mm, magnetized through 3 mm, Ni-Cu-Ni | Generic (sintered NdFeB) | `Spec: N35/N42, 20x6x3 mm, axial-3mm` | Mandatory | N52 15x5x3 mm | 0.05-0.15 |
| 36 | PCB | 1 | 4-layer FR4 1.0 mm, 36 x 18 mm, impedance control 50 Ohm GCPW on L1/L2, ENIG | PCB fab | `rev A` | Mandatory | 2-layer 0.8 mm variant (see docs/chip/06) | 0.30-0.60 |
| 37 | TP1-TP10 + J1 | 10 + 2 | Test pads 1.0 mm on BOTTOM + 2 THT battery-wire pads J1 (drill 0.7 / pad 1.7 mm), one 2 × 6 pogo grid of 2.54 mm at the far end; the jig powers the board through J1 | — | `PCB pad` | Mandatory | — | 0 |
Datasheet/nguồn xác minh của từng dòng nằm ở cột `Datasheet/Source` và `Verified` của CSV.

## 2. Mức độ xác minh mã linh kiện

| Nhóm | Cách xác minh |
|---|---|
| ESP32-H2FH4S, DRV5032FBDBZR, DRV5032FADBZR, DRV5012AEDMRR, TPS63900DSKR, TPS3839K33DBZR | ✅ đọc trực tiếp datasheet và *Package Option Addendum* (trạng thái **Active**) của Espressif/TI |
| DFE252010F-2R2M, XFL4020-222ME, DFE201612E-2R2M | ✅ bảng 8-2 datasheet TPS63900 |
| PESD5V0U1BL (trang Nexperia: ESD 2 chiều, SOD882), DMG2305UX-7, ECS-320-10-37B2-CKY-TR, ABS07-32.768KHZ-T, GRM0335C1H1R5BA01D, LQP03TN2N7B02D, LQW15AN24NG00D, GRM188R60J226MEA0D, Hirose MS-156C3, APTD1608LSURCK, B3U-1000P, Keystone 1087-1/1087-2 (catalog K75 p.15/p.41), Energizer EL123AP, Panasonic CR123A | ✅ tra cứu trang nhà sản xuất / nhà phân phối (DigiKey, LCSC, Octopart, Arrow…) – thông số chính ghi trong CSV |
| Tụ/điện trở tiêu chuẩn (Murata GRM155/GRM1555, Yageo RC0402/RC0201) | mã theo quy tắc đặt tên chuẩn của hãng; **được phép thay bằng linh kiện tương đương** cùng thông số |
| Nam châm | đặc tả theo kích thước/cấp từ (không phụ thuộc nhà cung cấp); 🧪 xác nhận bằng gaussmeter |

> 🧪 Trước khi chốt BOM sản xuất: kiểm tra tồn kho/lead-time thực tế (ví dụ GRM0335C1H1R5BA01D được ghi nhận lead-time 17–24 tuần ở một số nhà phân phối; đầu nối RF ~12 tuần), dòng đời sản phẩm (NRND/EOL), xác nhận sơ đồ chân và thông số SOT-23 của Q1 (AO3401A: mã lấy theo BOM bản nút bấm, LCSC C15127, 🧪 chưa đối chiếu datasheet hãng trong repo này), và **kích thước lỗ chân tiếp điểm Keystone 1087-1/1087-2 trên mẫu thật** (catalog ghi "mounting dimensions for reference only"). Đế Keystone 1128 (52.3 × 18.3 mm) và cặp kẹp SMT 254 (43.1 mm) đã bị loại vì không vừa PCB 72 × 18 mm.

## 3. Chi phí ước tính (tham khảo, phải báo giá lại)

| Hạng mục | USD / bộ @1k |
|---|---|
| Linh kiện điện tử + PCB (không gồm pin, không gồm J2) | **≈ 4.8 – 8.0** |
| Pin CR123A (OEM) | ≈ 1.0 – 2.0 |
| J2 (chỉ EVT/DVT) | ≈ 0.3 – 0.6 |
| Lắp ráp SMT, test, vỏ nhựa, nam châm, bao bì, chứng nhận (phân bổ) | ngoài phạm vi BOM |

Giá trong bảng là **ước lượng theo mức giá phân phối phổ biến ở thời điểm viết**, không phải báo giá; cần RFQ với nhà phân phối/EMS.

## 4. Linh kiện bắt buộc vs tùy chọn

- **Bắt buộc**: U1, U2, L2, U3, Q1, D2, Y1, L3, C15/C16, mạng RF C19/L4/C20/C21/L6, ANT1, toàn bộ tụ decoupling, R2–R5, R8–R13, D1, SW1, BT1, PCB.
- **Khuyến nghị**: U4 (có thể thay bằng RC R7/C14 – không khuyến nghị cho sản phẩm dùng pin).
- **Tùy chọn/tuning (DNP)**: Y2/C17/C18 (32.768 kHz), L5, C22, C23, D3, R7, C14.
- **Chỉ mẫu thử**: J2 (Hirose MS-156C3; có thể giữ ở MP vì công tắc đóng khi không cắm đầu đo).

## 5. Rà soát giá 💡

Đã áp dụng:

| Thay đổi | Tác động |
|---|---|
| Bản module: bỏ pin cúc áo CR2450, dùng **CR123A rời như bản chip rời** (docs/wroom/12 §7–8) | bỏ toàn bộ tụ 220 µF 1210 (rev A cần 6 tụ, rev B cần 2). Giá tham khảo LCSC (ảnh chụp cũ, không phải báo giá): 0.42–0.89 USD/tụ ⇒ bớt khoảng **2.5–5.3 USD/board** so với rev A. Pin dùng khoảng 2.3 năm thay vì khoảng 6 tháng |
| Bản module: board 36 × 24 → **32 × 20 mm** | board nhỏ hơn; BOM lắp ráp còn 18 dòng / 27 linh kiện |
| Bản module: PCB **4 lớp → 2 lớp**, via 0.6 / 0.3 mm, không có lỗ dưới 0.3 mm (docs/wroom/12 §3) | thuộc loại mạch 2 lớp tiêu chuẩn, rẻ nhất ở mọi nhà sản xuất; lấy báo giá thật để biết mức chênh |
| Hai board dùng chung mọi linh kiện ngoài U1 | R2/R3 (30.1 kΩ / 0 Ω), pin, tiếp điểm pin, firmware giống nhau: gom đơn, một file build |
| Q1 → **AO3401A** | rẻ hơn, có sẵn ở mọi nơi; cùng chân với DMG2305UX-7 |
| D2/D3 → **PESD5V0U1BL,315** | mã cũ PESD3V3S1BL khó mua lẻ |
| R13 499 Ω (E96) → **510 Ω** (E24) | giá trị phổ thông |
| Thêm mã LCSC cho Q1, U2 trong `fab/assembly/*-bom.csv` | trùng mã với BOM bản nút bấm |

Có thể làm tiếp, **sau khi thử trên mẫu** (chưa áp dụng):

| Hạng mục | Tiết kiệm (USD/board) | Điều kiện |
|---|---|---|
| U4 TPS3839 (0.25–0.40) → kéo EN lên bằng 10 kΩ (bản module đã có tụ 1 µF trên EN trong module; bản chip rời có sẵn chỗ R7/C14) | ~0.25–0.40 | cần thêm 1 chỗ điện trở trên board module; thử lắp/tháo pin chậm, pin yếu, brownout. Espressif khuyên dùng IC giám sát khi nguồn lên/xuống chậm |
| D1 Kingbright → LED đỏ 0603 phổ thông; SW1 Omron B3U → nút tương đương 3.0 × 2.5 mm | ~0.1–0.3 | kiểm tra độ sáng ở 1.4 mA và lực nhấn |
| J2 (cổng đo RF, chỉ bản chip rời) | 0.3–0.6 | chỉ lắp ở mẫu thử |

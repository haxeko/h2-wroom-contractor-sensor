# 06 – Thiết kế PCB rev A (KiCad 10)

File thiết kế: `hardware/chip/matter_contact_sensor.kicad_pro` (+ `.kicad_sch`, `.kicad_pcb`, `.kicad_dru`, thư viện dự án `mcs.kicad_sym` / `mcs.pretty`). File sản xuất: `hardware/chip/fab/` (Gerber, khoan, pick & place, IPC-D-356, PDF sơ đồ/lắp ráp, ảnh render).

Toàn bộ được **sinh lại được** từ một nguồn dữ liệu duy nhất `tools/design_data.py`:

```
python3 tools/netlist.py                     # netlist.csv + ERC đơn giản
python3 tools/kicad/gen_libs.py              # symbol/footprint dự án (ESP32-H2FH4S, tiếp điểm pin, anten…)
python3 tools/kicad/gen_schematic.py         # sơ đồ KiCad  -> kicad-cli sch erc: 0 vi phạm
/usr/bin/python3.12 tools/kicad/build_pcb.py # đặt linh kiện, đi dây, đổ đồng, DRC + schematic parity
python3 tools/kicad/export_fab.py            # Gerber/khoan/pos/PDF/ảnh
```

`build_pcb.py` lấy netlist do chính KiCad xuất từ sơ đồ, nên PCB luôn khớp sơ đồ (DRC kiểm tra *schematic parity*). Đường RF, vòng nguồn DC-DC, ba net clock 32 MHz và các via 3V2 cạnh chân RF được **vẽ tay theo tọa độ** trong script; các net còn lại do `tools/kicad/pcb_router.py` (router lưới A* 0.05 mm, viết riêng cho dự án) đi dây với các vùng cấm: anten, chuỗi RF, dưới thạch anh. Kết quả là bản rev A cho EVT: một kỹ sư layout cần rà soát lại trong KiCad trước khi đặt hàng (xem §10).

## 1. Thông số tấm mạch ✅ (trong file) / 💡 (lựa chọn)

| Thông số | Giá trị |
|---|---|
| Kích thước | **36 × 18 mm**, bo góc R0.5. Pin CR123A **không nằm trên PCB**: nằm trong ngăn pin của vỏ, 2 dây hàn vào J1 ở đầu xa anten (bản trước 72 mm có tiếp điểm pin trên board) |
| Số lớp / độ dày | **4 lớp, 1.0 mm** (stack-up §3, đã ghi vào file PCB) |
| Hoàn thiện | ENIG (QFN 0.4 mm, linh kiện 0201) |
| Đường / khe | thiết kế 0.15 / 0.15 mm; tối thiểu cho phép 0.1 / 0.1 mm (ràng buộc board) |
| Via | tín hiệu/plane 0.4 / 0.2 mm; nguồn VBAT 0.5 / 0.25 mm; EPAD U1: 9 via 0.2 mm, U2: 6 via |
| Net class | Default 0.15/0.15; RF 0.32 mm (GCPW); PWR 0.4 mm (thực tế 0.3 mm qua chân 0.5 mm của TPS63900); PLANE |
| Luật riêng (`.kicad_dru`) | đổ đồng cách đường RF **0.31 mm** (khe GCPW); khe pad nội bộ 0201 |
| Kiểm soát trở kháng | GCPW 50 Ω trên L1 tham chiếu L2 – đặt hàng có coupon TDR |
| Linh kiện | chỉ mặt TOP (1 lần reflow); 2 lỗ hàn dây pin J1 (THT, hàn tay sau khi test); mặt BOTTOM chỉ có pad test |

## 2. Vì sao 4 lớp thay vì 2 lớp ✅ (lý do) / 💡 (quyết định)

| Tiêu chí | 2 lớp 0.8 mm | **4 lớp 1.0 mm** |
|---|---|---|
| Khuyến nghị Espressif | được phép | **khuyến nghị** (L2 GND liền, L3 nguồn + GND dưới RF/thạch anh) |
| Đường 50 Ω GCPW | rộng ~0.70–0.79 mm – rộng hơn pad 0201 và chân ANT | **0.32 mm / khe 0.31 mm** – khớp pad 0201 |
| Stub 15 mil 100 Ω tham chiếu L3 (triệt hài bậc 2) | không làm đúng được | làm đúng hướng dẫn (§5.2) |
| Mặt phẳng GND dưới QFN/RF/thạch anh | bị cắt bởi đường lớp dưới | L2 liền khối hoàn toàn |
| Nguồn | đi dây chung lớp tín hiệu | L3: mặt 3V2 dưới MCU/nguồn, GND dưới RF/thạch anh |
| Chi phí (tham khảo) | thấp nhất | +0.1–0.3 USD/board ở số lượng lớn |

## 3. Stack-up (ghi trong file PCB) 💡 – xác nhận lại với nhà sản xuất 🧪

| Lớp | Vật liệu | Độ dày | Dùng cho |
|---|---|---|---|
| F.Mask | solder mask | 0.01 mm | |
| L1 F.Cu | đồng | 0.035 mm | linh kiện, RF, tín hiệu ngắn, đổ GND |
| PP | FR4 7628, εr 4.4 | 0.21 mm | |
| L2 In1.Cu | đồng | 0.035 mm | **GND liền khối, không có đường đi dây** (chỉ khoét dưới stub RF) |
| Core | FR4, εr 4.5 | 0.42 mm | |
| L3 In2.Cu | đồng | 0.035 mm | **3V2** dưới MCU/nguồn/UI; **GND** dưới chuỗi RF, thạch anh, mép anten, pin |
| PP | FR4 7628, εr 4.4 | 0.21 mm | |
| L4 B.Cu | đồng | 0.035 mm | đổ GND, đường tín hiệu tới pad test, 10 pad test |
| B.Mask | solder mask | 0.01 mm | |

Đường 50 Ω: GCPW L1/L2 **w = 0.32 mm, khe 0.31 mm** (tham chiếu stack-up Espressif, kiểm tra chéo `tools/cpwg_impedance.py`). Stub 100 Ω trên L1 tham chiếu L3 (L2 khoét): **0.29 mm** (Hammerstad, h = 0.665 mm, εr 4.4). 🧪 Xác nhận cả hai bằng bộ tính trở kháng của nhà sản xuất cho đúng stack-up đặt hàng.

## 4. Bố trí thực tế (tọa độ tính từ góc trên-trái, x = 0 ở đầu anten, y = 18 là mép "mặt A" hướng nam châm)

| Vùng | Vị trí | Nội dung |
|---|---|---|
| Anten | x 0 – 5.2 (toàn bề rộng) | MIFA TI AN043 bản `Right`, feed tại (5.45; 14.95), cạnh vùng anten trùng mép mặt A; **rule area mọi lớp**: không đường, không via, không đổ đồng |
| Chuỗi RF | dọc y = 14.95, x 5.8 – 15.6 | anten → L6 (π: C23 dưới, C22 trên) → J2 Hirose MS-156C3 → C21 (L5 dưới) → L4 (C20 dưới) → C19 (ngay chân ANT) → U1 chân 32 |
| MCU | U1 tâm (17.6; 12.95), xoay 90° | chân ANT (32) ở góc dưới-trái hướng về anten; cạnh trái: VDD3P3 27/30/31, XTAL 28/29; cạnh phải: GPIO8–13 (UI); cạnh trên: CHIP_EN, nguồn, UART |
| Thạch anh 32 MHz | Y1 (10.7; 11.4) | phía trên-trái chip, trên chuỗi RF; L3 24 nH sát chip, C15/C16 ở hai phía thạch anh |
| Nguồn | dải trên x 14.6 – 23.5 | U2 TPS63900 (18.6; 3.9), L2 (22.05; 4.1), C1/C2 (VIN), C3 (VOUT), R2–R4 (CFG) |
| Chống ngược cực | Q1 (28.2; 9.0), D2, R1 | sát J1 (dây pin) |
| Reset | U4 (26.0; 3.0), R6; C13 sát chân CHIP_EN | R7/C14 (DNP) cạnh mép phải |
| UI | SW1 (11.6; 3.5) góc trên-trái; D1 + R12 phải chip | nút cách khúc uốn anten > 6 mm |
| Hall | U3 DRV5032 (26.7; 16.2) | thân cách mép mặt A 0.1 mm (die cách mép ~1.8 mm) |
| RTC (DNP) | Y2 (23.75; 9.8), C17, C18 | cạnh phải-trên chip (chân 15/16) |
| Dây pin J1 | pad 1 (+) (34.24; 6.98), pad 2 (–) (34.24; 9.52) | 2 lỗ khoan 0.7 / pad 1.7 mm cho dây 0.15 mm²; pad 1 vuông; ký hiệu +/– trên silk mặt trên |
| Pad test | mặt BOTTOM, cuối board x 31.7 / 34.24 | 10 pad Ø1 mm + 2 pad J1 trên cùng lưới 2 × 6, bước 2.54 mm (§6) |

Khoảng cách kiểm tra (đo trên file):

| Cặp | Khoảng cách | Yêu cầu |
|---|---|---|
| L2 (cuộn DC-DC) ↔ thạch anh Y1 | ≈ 13.5 mm | ≥ 10 mm (docs/common/02, Espressif "không đặt linh kiện từ tính gần thạch anh") ✅ |
| L2 ↔ Hall U3 | ≈ 13 mm | ≥ 10 mm ✅ |
| L2 ↔ mép GND anten | ≈ 16.8 mm | xa ✅ |
| Pin (vỏ thép) ↔ vùng anten | do vỏ quyết định: ngăn pin đặt sau đầu J1 ⇒ ≥ 31 mm | ≥ 25 mm (docs/chip/04 §4) 💡 |
| Thạch anh ↔ chân clock | ≈ 3 mm | ≥ 1.8 mm (Espressif) ✅ |
| Thạch anh ↔ mép GND anten | ≈ 4 mm | "càng xa càng tốt" – 🧪 kiểm tra spur 32 MHz × n trên phổ khi đo dẫn |

## 5. Các quy tắc đã áp dụng trong layout

### 5.1 RF ✅ (Espressif ESP32-H2 PCB layout guide)
- Mạng phối hợp 0201 sát chân ANT, sắp xếp zigzag (tụ shunt luân phiên trên/dưới đường); C19 nằm **thẳng trên đường** ngay chân 32.
- Đường RF trên L1, **một bề rộng 0.32 mm, không via, không rẽ nhánh dài**, gấp 45°; 0.4 mm cuối vào chân ANT thu về 0.2 mm (bằng chiều rộng pad, tránh chạm chân VDD3P3 31).
- Đổ đồng cách đường RF 0.31 mm (luật `RF GCPW gap to pour`), hàng via GND hai bên đường bước 0.5 mm; L2 liền bên dưới; không có đường tín hiệu nào dưới chuỗi RF ở mọi lớp (vùng cấm của router).
- 💡 Sai khác so với hình mẫu Espressif: các tụ shunt C20/C22/C23/L5 đặt **cạnh** pad linh kiện nối tiếp với đoạn nối ~0.4 mm (để chuỗi 9 linh kiện + J2 vừa 9.8 mm). Giá trị chốt bằng VNA nên ký sinh này được bù khi tuning 🧪.

### 5.2 Stub triệt hài bậc 2 ✅ (Espressif)
"Add a stub on the ground pad of the grounding capacitor near the chip side… keep the stub length 15 mil… characteristic impedance 100 Ω ± 10 %… reference plane is the third layer, so the area under the trace on the second layer should be cleared." Thực hiện: pad GND của C19 → đường 0.29 mm dài 0.38 mm → via GND; rule area *STUB L2 CUT* khoét L2 dưới stub; rule area *STUB L1 CLEAR* giữ đồng L1 tránh xa stub (pad GND của C19 chỉ xuống đất qua stub).

### 5.3 Thạch anh ✅ (Espressif)
- Cách chân clock ≥ 1.8 mm; **không via trên XTAL_P/XTAL_N**; L3 (24 nH) đặt phía chip; C15/C16 ở hai phía thạch anh, nối ở cuối đường clock (sau chân thạch anh), không nối thẳng vào L3.
- Không có đường tín hiệu dưới thạch anh (vùng cấm L1/L3/L4); L3 (In2) dưới thạch anh là GND; vành via GND quanh thạch anh.
- Ba net clock vẽ tay: XTAL_P (chân 29 → L3), XTAL_P_X (L3 → Y1.1 → C15), XTAL_N (chân 28 → đi lên giữa L3 và via 3V2 → vòng trên thạch anh → Y1.3 → C16).

### 5.4 Nguồn ✅ (Espressif + TI)
- TPS63900: vòng VIN–C1, VOUT–C3, LX1/LX2–L2 vẽ tay, vết 0.3 mm (chân 0.5 mm), dài < 2 mm; chân GND 8 nối thẳng EPAD; EPAD 6 via, nối đặc.
- 3V2 phân phối bằng mặt L3; **mỗi chân nguồn và mỗi tụ có via riêng** sát pad (router tự đặt, cách pad ≤ 1.6 mm); VDD3P3 27 và 30/31 (kẹp giữa chân thạch anh/RF) có đường thoát + via cố định trước khi đi các net khác.
- EPAD ESP32-H2: 9 via (footprint ThermalVias), nối đặc.
- VBAT 0.3 mm (pin → Q1 → C1/C2/VIN, R8, TP3).
- 🧪 Lệch so với hướng dẫn "VDD3P3 pin 1/2 trace ≥ 15 mil": pin 1/2 nối mặt 3V2 bằng đường 0.2 mm (bằng bề rộng pad QFN) dài < 0.6 mm tới via; tụ C4/C5/C6 ngay bên dưới.

### 5.5 Tín hiệu
- Các chân tín hiệu của U1 có **đoạn thoát cố định 0.85 mm** để net đi trước không bịt lối của net đi sau.
- Đường tới pad test đi trên L1 rồi xuống L4 bằng via gần lưới pad test (dài nhất: BTN ≈ 34 mm tổng, U0TXD ≈ 17 mm); L3 không có đường tín hiệu nào. Pad test GND (TP2) có via riêng xuống các lớp GND.
- VBAT_RAW từ J1.1 tới D2/Q1 chỉ 6 mm trên L1.
- Via thoát cố định không dùng tới (chân 21/22 khi net đi tiếp trên L1) và đoạn đường thừa phía sau được script tự xóa ở bước dọn dẹp.
- USB D–/D+ (chân 25/26) **không đưa ra** (firmware tắt USB-Serial-JTAG; nạp/log qua UART0). Lý do: giải phóng lối thoát bên trái chip cho clock 32 MHz và VDD3P3 27.

## 6. Pad test và jig

| Pad | Net | Vị trí (x; y) mặt dưới |
|---|---|---|
Lưới 2 cột × 6 hàng, bước 2.54 mm, nhìn từ mặt dưới (y = 1.9 / 4.44 / 6.98 / 9.52 / 12.06 / 14.6):

| y | Cột x = 31.7 | Cột x = 34.24 |
|---|---|---|
| 1.9 | TP4 CHIP_EN | TP5 BTN (GPIO9) |
| 4.44 | TP7 U0TXD | TP1 3V2 |
| 6.98 | TP8 U0RXD | **J1.1 + (VBAT_RAW)**, lỗ THT |
| 9.52 | TP3 VBAT | **J1.2 – (GND)**, lỗ THT |
| 12.06 | TP6 IO8_STRAP | TP2 GND |
| 14.6 | TP9 HALL_OUT | TP10 VBAT_ADC |

- Bỏ TP11 (GND thứ hai): GND đã có ở TP2 và J1.2.
- 2 lỗ định vị NPTH Ø1.5 mm: H1 (7.2; 6.2) ở đầu anten (ngoài keep-out) và H2 (32.97; 16.55) cạnh lưới pad test – hai đầu board để jig định vị chắc; 2 fiducial Ø0.5/mask 1 mm tại (7.2; 1.3) và (29.4; 1.3).
- Jig: **cấp nguồn qua 2 pad J1** (pogo vào lỗ THT từ mặt dưới, trước khi hàn dây pin – đi qua Q1 như pin thật), nạp qua UART (TP7/TP8, kéo BOOT TP5), đo dòng ngủ, Hall bằng nam châm trên nắp jig, LED bằng cảm biến quang, RF qua J2 (EVT/DVT). Hàn dây pin sau khi test đạt.

## 7. Footprint dự phòng để tuning

| Footprint | Mặc định | Mục đích |
|---|---|---|
| C22 / L6 / C23 (π anten) | DNP / 0 Ω / DNP | tuning anten trong vỏ |
| C21 / L5 | 0 Ω / DNP | chặn DC / hoàn thiện CLCCL |
| ANT1 biến thể L1 3.94 → 3.04 mm | chọn sau EVT | bù dịch tần do vỏ (`mcs:Texas_SWRA117D_2.4GHz_Right_L1_x`) |
| J2 Hirose MS-156C3 | lắp (EVT/DVT) | đo dẫn; công tắc đóng khi không cắm đầu đo |
| L3, C15/C16 | 24 nH, 15 pF | chỉnh lệch tần thạch anh |
| Y2, C17/C18 | DNP | thử RTC 32.768 kHz |
| R7/C14 | DNP | reset RC thay U4 |
| D3 | DNP | ESD cho nút nếu nút lộ ra ngoài vỏ |

## 8. DRC / DFM

- Ràng buộc board: khe 0.1 mm, đường 0.1 mm, via 0.4/0.2 mm, vành khuyên 0.1 mm, lỗ–lỗ 0.25 mm, đồng–mép 0.3 mm, `min_resolved_spokes` = 1 (mỗi pad GND còn có via riêng).
- Rule area anten (mọi lớp); keep-out của footprint J2 được router tôn trọng.
- ✅ Kết quả DRC của bản trong repo (KiCad 10.0.8, `kicad-cli pcb drc --refill-zones --schematic-parity --severity-all`): **0 vi phạm (lỗi + cảnh báo), 0 kết nối hở, 0 lệch sơ đồ** – `hardware/chip/drc_report.json`. ERC sơ đồ: 0 vi phạm.
- Kiểm tra bị bỏ qua: 5 mục mặc định của KiCad (courtyard thiếu, đầu đường lệch tâm via, tuning profile, footprint filter, loại linh kiện) và `lib_footprint_mismatch`: J2 được bật "cho phép cầu solder mask giữa các pad" nên khác bản thư viện. Kiểm tra "footprint không có trong thư viện" **được bật** (0 vi phạm).
- Thống kê: 258 đoạn đường (L1 176 mm, L4 97 mm, L3 không có), 130 via xuyên (127 × 0.4/0.2 mm, 3 × 0.5/0.25 mm), 71 footprint (61 mặt trên gồm J1/fiducial/lỗ định vị, 10 pad test mặt dưới); khe hở nhỏ nhất giữa các đường 0.161 mm.
- File sản xuất (`fab/`): gốc tọa độ khoan/pick & place = **góc dưới-trái board** (X sang phải, Y lên); Gerber X2 + Excellon PTH/NPTH tách riêng + drill map + job file; pick & place mặt trên (48 linh kiện) đã loại linh kiện DNP, anten (đồng in trên PCB), J1 và pad test; fiducial FID1/FID2 có trong file.
- Gói đặt hàng: `fab/matter_contact_sensor-gerber.zip` (Gerber + khoan, tải thẳng lên nhà sản xuất PCB), `fab/assembly/matter_contact_sensor-bom.csv` (27 dòng / 46 linh kiện, cột Comment, Designator, Footprint, Quantity, Manufacturer, MPN, LCSC Part #) và `fab/assembly/matter_contact_sensor-cpl.csv` (Designator, Mid X, Mid Y, Layer, Rotation). Chỉ 3 mã LCSC đã kiểm chứng được điền sẵn; các dòng khác nhà lắp ráp chọn theo MPN. 🧪 Góc xoay trong CPL theo quy ước KiCad: kiểm tra lại trên ảnh xem trước của nhà lắp ráp (đặc biệt SOT-23, QFN/WSON, LED, J2).
- Panel: tab + mouse-bite cách vùng anten ≥ 3 mm; không V-cut ngang qua anten; fiducial panel + 2 fiducial cục bộ.
- Stencil 0.1 mm; EPAD có ô kem chia nhỏ theo footprint KiCad.

## 9. Lắp trong vỏ – pin rời nối dây 💡

PCB 36 × 18 mm không còn quyết định chiều dài vỏ; pin CR123A (Ø17 × 34.5 mm) nằm trong ngăn riêng giữa hai tiếp điểm Keystone 1087-1 (+) / 1087-2 (–) gài vào khe vỏ, hai dây 0.15 mm² hàn từ đuôi tiếp điểm vào J1. Phương án tham chiếu (dáng thon, vỏ ~80 × 22 × 22 mm):

```
 Mặt cắt dọc
 ┌────────────────────────────── ~80 ──────────────────────────────┐
 │ │anten│ RF + MCU + nguồn + UI │pad│~~ dây ~~┐ │+│   PIN CR123A    │–│ │
 │ │ 5.2 │      (x 5.2 – 30)     │J1 │          └─┤ │  Ø17 × 34.5 mm  │ │ │
 │ ├─────┴───────────────────────┴───┤            └─┴─────────────────┴─┘ │
 │ │        PCB 36 × 18 × 1.0         │      ngăn pin (tiếp điểm 39.8 mm)   │
 └─┴──────────────────────────────────┴────────────────────────────────────┘
   ◄ mặt A (Hall, y = 18) hướng về nam châm
```

- Đầu anten sát vách đầu vỏ (≥ 1 mm không khí), vách ≤ 1.5 mm, nhựa ABS/PC không độn sợi thủy tinh, không kim loại trong 20 mm đầu. Pin và dây ở đầu xa anten ⇒ vỏ thép pin cách vùng anten ≥ 31 mm.
- Dây pin ngắn (≤ ~60 mm), xoắn đôi, cố định bằng gân/keo trong vỏ (pad THT chịu lực kéo kém); không cho dây vòng ngược về phía anten.
- Có thể đặt pin song song cạnh PCB để vỏ ngắn hơn, nhưng đầu pin gần anten phải cách vùng anten ≥ 25 mm ⇒ vỏ vẫn dài ≥ ~60 mm; phương án nối tiếp ở trên đơn giản hơn cho RF.
- Vạch căn chỉnh nam châm trên vỏ tại tọa độ Hall: **x = 26.7 mm từ đầu anten của PCB** (+ khe hở đầu vỏ + thành vỏ).
- Light-pipe cho D1 tại (25.6; 12.4), cần nhấn cho SW1 tại (11.6; 3.5) – cả hai ngoài vùng anten.
- 🧪 Tiếp điểm Keystone 1087 là loại PC-mount: kiểm tra hàn dây vào đuôi tiếp điểm và khe giữ trong vỏ trên mẫu thật.

## 10. Việc còn phải làm trước khi đặt PCB 🧪

1. Kỹ sư layout rà toàn bộ trong KiCad: đường do router sinh có nhiều đoạn 45° ngắn – có thể làm gọn.
2. Xác nhận stack-up và độ rộng 50 Ω / 100 Ω với nhà sản xuất; đặt coupon TDR.
3. Chốt ngăn pin trong vỏ (khe giữ tiếp điểm Keystone, đường đi và cố định dây pin) và đo lại S11 khi có pin + dây trong vỏ.
4. Mặt GND rút từ 66.8 xuống 30.8 mm: cộng hưởng/hiệu suất anten thay đổi so với bản 72 mm – bắt buộc tuning trên mẫu (biến thể L1, π anten).
5. Mô phỏng EM (tùy chọn) và chuẩn bị 3 biến thể L1 của anten trên panel EVT.
6. Đo VNA/OTA theo docs/chip/04 §5–6 rồi chốt giá trị C19/L4/C20, π anten, biến thể L1.

# 05 – Sơ đồ nguyên lý (schematic) rev A

Tài liệu này là **đặc tả schematic đầy đủ** để vẽ lại trong KiCad/Altium: mọi linh kiện, giá trị, chân và net. Bản máy đọc được: `hardware/netlist/netlist.csv` (mỗi dòng = 1 chân linh kiện → net) và `hardware/bom/bom.csv`.

Ký hiệu net nguồn: `VBAT_RAW` (cực + pin, trước PMOS), `VBAT` (sau PMOS, vào DC-DC), `3V2` (rail hệ thống), `GND`.

## 1. Khối nguồn

```
 Pin CR123A NGOÀI PCB (tiếp điểm Keystone 1087-1/1087-2 trong vỏ) ── 2 dây 0.15 mm² ── J1
 J1.1 (+) ───────── VBAT_RAW ────┬──────────────┐
                                 │              │ 3 D
                           D2 PESD5V0U1BL     Q1 AO3401A (P-MOS)
                           (2 chiều)            │ 2 S ───────────── VBAT ──┬────────┬──────┬──────────┐
                                 │            1 G                           │        │      │          │
 J1.2 (–) ── GND ────────────────┴──── R1 100k ─┘                      C1 22µ  C2 22µ   R8 1M      U2 TPS63900DSKR
                                                                         │        │      │       10 VIN   VOUT 6 ── 3V2 ──┬── C3 22µ ── GND
                                                                        GND      GND   (khối đo  1 EN ─┐  LX1 9 ──┐       │
                                                                                        pin)     2 SEL ┴─ VBAT    L2 2.2µH (DFE252010F-2R2M)
                                                                                                 3 CFG1 ── R2 30.1k 1% ── GND
                                                                                                 4 CFG2 ── R3 0 Ω ── GND   LX2 7 ┘
                                                                                                 5 CFG3 ── R4 0 Ω ── GND   GND 8 + EP ── GND
```

| Ref | Linh kiện | Giá trị | Chân → Net |
|---|---|---|---|
| J1 | 2 lỗ hàn dây pin (THT, khoan 0.7 / pad 1.7 mm, bước 2.54 mm; pad 1 vuông = +) | dây đơn 0.15 mm² (26 AWG), cách điện ≤ Ø1.5 mm | 1 → VBAT_RAW; 2 → GND |
| — (ngoài PCB) | Pin CR123A + tiếp điểm trong vỏ | Keystone 1087-1 (+, tiếp điểm nút) + 1087-2 (–, lò xo) gài vào khe vỏ, hàn dây vào đuôi tiếp điểm; L ngoài 39.8 mm | dây + → J1.1; dây – → J1.2 |
| D2 | ESD 2 chiều | Nexperia PESD5V0U1BL,315 (SOD-882) | 1 → VBAT_RAW; 2 → GND |
| Q1 | P-MOSFET chống ngược cực | AO3401A (thay thế: DMG2305UX-7) | 1 G → Q1_G; 2 S → VBAT; 3 D → VBAT_RAW |
| R1 | Điện trở cổng | 100 kΩ 1 % 0402 | Q1_G – GND |
| C1, C2 | Bulk vào DC-DC | 22 µF 6.3 V X5R 0603 | VBAT – GND |
| U2 | Buck-boost | TI TPS63900DSKR | 1 EN, 2 SEL, 10 VIN → VBAT; 3 CFG1 → CFG1; 4 CFG2 → CFG2; 5 CFG3 → CFG3; 6 VOUT → 3V2; 7 LX2 → LX2; 8 GND + EP → GND; 9 LX1 → LX1 |
| L2 | Cuộn cảm nguồn | 2.2 µH, Murata DFE252010F-2R2M | LX1 – LX2 |
| R2 | Đặt VOUT = 3.2 V | 30.1 kΩ ±1 %, ≤ 100 ppm/°C | CFG1 – GND |
| R3 | Giới hạn dòng = Unlimited | 0 Ω | CFG2 – GND |
| R4 | VO(1) = 1.8 V (không dùng) | 0 Ω | CFG3 – GND |
| C3 | Ra DC-DC | 22 µF 6.3 V X5R 0603 | 3V2 – GND |

## 2. ESP32-H2FH4S và tụ nguồn

| Chân | Tên | Net | Linh kiện liên quan |
|---|---|---|---|
| 1, 2 | VDD3P3 | 3V2 | C4 22 µF + C5 1 µF + C6 0.1 µF sát chân |
| 3 | GPIO0 | NC | — |
| 4 | GPIO1 / ADC1_CH0 | VBAT_ADC | R8, R9, C25 |
| 5 | MTMS / GPIO2 | NC | — |
| 6 | MTDO / GPIO3 | NC | — |
| 7 | MTCK / GPIO4 | NC | — |
| 8 | MTDI / GPIO5 | NC | — |
| 9 | VDDPST1 | 3V2 | C12 0.1 µF |
| 10 | GPIO8 (strap) | IO8_STRAP | R11 100 kΩ lên 3V2, TP6 |
| 11 | GPIO9 (strap BOOT) | BTN | SW1, R10 100 kΩ lên 3V2, TP5, D3 (DNP) |
| 12 | GPIO10 | HALL_OUT | U3 OUT, TP9 |
| 13 | GPIO11 | LED_DRV | R12 1 kΩ → D1 |
| 14 | GPIO12 | NC | — |
| 15 | XTAL_32K_P / GPIO13 | X32K_P | Y2 (DNP), C17 (DNP) |
| 16 | XTAL_32K_N / GPIO14 | X32K_N | Y2 (DNP), C18 (DNP) |
| 17 | CHIP_EN | CHIP_EN | U4 qua R6 1 kΩ, C13 0.1 µF, TP4, (R7/C14 DNP) |
| 18 | VBAT | 3V2 | qua R5 0 Ω (như tham chiếu Espressif) |
| 19 | VDDA_PMU | 3V2 | C11 0.1 µF |
| 20 | VDDPST2 | 3V2 | C10 0.1 µF |
| 21 | GPIO22 | VBAT_EN | R9 |
| 22 | U0RXD / GPIO23 | U0RXD | TP8 |
| 23 | U0TXD / GPIO24 | U0TXD_CHIP | R13 510 Ω → U0TXD (TP7) |
| 24 | GPIO25 (strap JTAG) | NC | — (bỏ qua khi eFuse mặc định) |
| 25 | GPIO26 / USB_D– | NC | — (rev A: không đưa ra, xem ghi chú dưới bảng GPIO) |
| 26 | GPIO27 / USB_D+ | NC | — |
| 27, 30 | VDD3P3 | 3V2 | C8 1 µF + C9 0.1 µF |
| 28 | XTAL_N | XTAL_N | Y1 pin 3, C16 |
| 29 | XTAL_P | XTAL_P | L3 24 nH → XTAL_P_X (Y1 pin 1, C15) |
| 31 | VDD3P3 | 3V2 | C7 10 nF |
| 32 | ANT | LNA_IN | mạng matching (khối RF) |
| 33 | GND (EP) | GND | ≥ 9 via xuống GND |

## 3. Reset / boot / nạp UART

```
 3V2 ── U4 TPS3839K33DBZR ── 2 RESET ── R6 1k ──┬── CHIP_EN (pin 17) ── TP4
         3 VDD      1 GND                         │
                                                 C13 100n ── GND        [DNP: R7 10k 3V2→CHIP_EN, C14 1µ]

 3V2 ── R10 100k ──┬── GPIO9/BTN ── TP5 (BOOT)     3V2 ── R11 100k ── GPIO8 ── TP6
                   │
                  SW1 Omron B3U-1000P ── GND    (KHÔNG đặt tụ lên GPIO9 – Espressif)

 GPIO24 U0TXD ── R13 510 Ω ── TP7 (TXD)          GPIO23 U0RXD ── TP8 (RXD)
```

- **Boot thường**: GPIO9 = 1 (R10 + pull-up nội), GPIO8 = 1 (R11) ⇒ SPI Boot.
- **Vào chế độ nạp (Joint Download Boot)**: giữ GPIO9 = 0 (nhấn SW1 hoặc jig kéo TP5 xuống GND) khi reset/cấp nguồn; GPIO8 = 1 nhờ R11 (bắt buộc – mặc định GPIO8 *floating*). Nạp qua UART0 (TP7/TP8) bằng `esptool`/Flash Download Tool (USB-Serial-JTAG không đưa ra ở rev A, xem cuối §10).
- **Reset**: jig kéo TP4 (CHIP_EN) xuống GND – R6 giới hạn dòng đánh nhau với đầu ra push-pull của U4.
- R13 510 Ω trên U0TXD theo khuyến nghị Espressif (triệt hài; 470–560 Ω đều được).

## 4. Thạch anh

```
 pin 29 XTAL_P ── L3 24nH ── XTAL_P_X ──┬── Y1.1          Y1: ECS-320-10-37B2-CKY-TR (32 MHz, ±10 ppm, CL 10 pF, 2016)
                                        C15 15p ── GND     Y1.2, Y1.4 → GND
 pin 28 XTAL_N ─────────────────────────┬── Y1.3
                                        C16 15p ── GND
 [DNP] pin 15/16 ── Y2 ABS07-32.768KHZ-T (CL 12.5 pF, ESR ≤ 70 kΩ) ── C17/C18 22p ── GND
```

## 5. Khối RF và anten

```
 pin 32 ANT ─ LNA_IN ─┬─ L4 2.7nH ─ RF_A ─┬─ C21 0Ω ─ RF_M1 ─┬─ J2 Hirose MS-156C3 (C → A) ─ RF_50R ─┬─ L6 0Ω ─ RF_ANT ─┬─ ANT1.1 (feed)
                      C19 1.5p            C20 1.5p           L5 DNP                                 C22 DNP           C23 DNP
                      │(+stub 15mil)      │                  │                                       │                 │
                     GND                 GND                GND                                     GND               GND
 ANT1.2 (short) ─ GND                         ANT1 = footprint Texas_SWRA117D_2.4GHz_Right[_L1_x.xxmm]
```

Chân J2 (Hirose MS-156C3, footprint KiCad `CoaxialSwitch_Hirose_MS-156C3_Horizontal`): C = phía mạch (chip), A = phía anten, G = GND; khi cắm đầu đo, A bị ngắt và tín hiệu đi ra đầu đo. Không cắm đầu đo thì công tắc đóng, nên có thể giữ J2 ở sản xuất hàng loạt (hoặc thay bằng mẫu 0 Ω trong rev sau). Murata MM8130-2600RB8 là phương án tương đương nhưng **khác footprint**.

## 6. Cảm biến Hall

```
 3V2 ──┬── U3.1 VCC (DRV5032FADBZR, SOT-23)
       C24 0.1µ          U3.2 OUT ── HALL_OUT ── GPIO10 ── TP9
       │                 U3.3 GND ── GND
      GND
```
Không điện trở kéo (đầu ra push-pull). Footprint dự phòng TO-92 (DRV5032FBLPG) chung net nếu cơ khí yêu cầu cảm nhận trường ngang (💡).

## 7. LED trạng thái

```
 GPIO11 ── R12 1.0k ── D1 (Kingbright APTD1608LSURCK, đỏ 630 nm, Vf 1.75 V @ 2 mA) ── GND
```
I_LED = (3.2 – 1.75)/1 kΩ ≈ 1.45 mA. LED đỏ AlInGaP (Vf thấp) – LED xanh lam/lá/trắng (Vf ~2.8–3.2 V) **không** sáng ổn định ở 3.2 V.

## 8. Đo điện áp pin

```
 VBAT ── R8 1M (1%) ──┬── VBAT_ADC ── GPIO1 (ADC1_CH0)
                      C25 10n
                      │
                     GND
          VBAT_ADC ── R9 1M (1%) ── VBAT_EN ── GPIO22
```

## 9. Điểm test (mặt BOTTOM, pad Ø1.0 mm, lưới 2.54 mm cho jig pogo – cuối board, chung lưới với 2 pad dây pin J1)

| TP | Net | Dùng cho |
|---|---|---|
| TP1 | 3V2 | cấp nguồn từ jig khi nạp / đo rail |
| TP2 | GND | (GND cũng có ở J1.2) |
| TP3 | VBAT | đo sau PMOS (jig cấp nguồn qua 2 pad dây pin J1 – pogo vào lỗ THT từ mặt dưới) |
| TP4 | CHIP_EN | reset |
| TP5 | BTN (GPIO9) | vào download mode |
| TP6 | IO8_STRAP | kiểm tra strap |
| TP7 / TP8 | U0TXD / U0RXD | nạp firmware, log, test RF |
| TP9 | HALL_OUT | kiểm tra Hall |
| TP10 | VBAT_ADC | hiệu chuẩn ADC |

## 10. Bảng GPIO đầy đủ (đối chiếu datasheet v1.3 bảng 2-1, 2-3, 2-5 và HW guideline) ✅

| GPIO | Chân | Chức năng trong sản phẩm | Linh kiện | Trạng thái lúc reset (datasheet) | Trạng thái firmware khi chạy | Đánh thức light sleep (TOP PD) |
|---|---|---|---|---|---|---|
| GPIO0 | 3 | không dùng | — | input tắt, hi-Z | `gpio_reset_pin` (pull-up, IE off) | không (digital IO) |
| GPIO1 | 4 | ADC đo pin | R8/R9/C25 | input tắt, hi-Z | analog (ADC1_CH0) khi đo | không |
| GPIO2 | 5 | không dùng (MTMS – chỉ là chân JTAG, không phải strap) | — | IE | reset_pin | không |
| GPIO3 | 6 | không dùng (MTDO) | — | IE | reset_pin | không |
| GPIO4 | 7 | không dùng (MTCK) | — | IE/WPU tùy eFuse | reset_pin | không |
| GPIO5 | 8 | không dùng (MTDI) | — | IE | reset_pin | không |
| GPIO8 | 10 | **strap** (ROM log / download mode) | R11 100 kΩ pull-up | IE, floating ⇒ R11 kéo lên 1 | input, không dùng | có thể (LP IO) – không dùng |
| GPIO9 | 11 | **nút commissioning / reset / BOOT** | SW1, R10 | IE + WPU (=1) | input pull-up, ngắt mức LOW, **EXT1 LOW** | **có (EXT1)** |
| GPIO10 | 12 | **Hall OUT** | U3 | input tắt | input không pull, ngắt + **EXT1 mức đảo chiều** | **có (EXT1)** |
| GPIO11 | 13 | LED | R12, D1 | input tắt | output LOW + `gpio_hold_en` (giữ mức khi ngủ) | (LP IO) – không dùng |
| GPIO12 | 14 | không dùng (miền VBAT/VDDA_PMU) | — | input tắt | reset_pin | — |
| GPIO13 | 15 | XTAL_32K_P (DNP) / không dùng | Y2 DNP | input tắt | reset_pin khi không dùng 32k | — |
| GPIO14 | 16 | XTAL_32K_N (DNP) / không dùng | Y2 DNP | input tắt | reset_pin | — |
| GPIO22 | 21 | VBAT_EN (đóng/ngắt phân áp) | R9 | input tắt | `GPIO_MODE_DISABLE` (hi-Z); output LOW ~50 ms khi đo | không |
| GPIO23 | 22 | U0RXD | TP8 | IE + WPU (sau reset) | UART0 RX (console dev) | không |
| GPIO24 | 23 | U0TXD | R13, TP7 | output + WPU | UART0 TX | không |
| GPIO25 | 24 | không dùng (strap nguồn JTAG – bị bỏ qua với eFuse mặc định) | — | IE | reset_pin | không |
| GPIO26 | 25 | không dùng (USB_D–) | — | USB | USJ tắt (`CONFIG_USJ_ENABLE_USB_SERIAL_JTAG=n`) → reset_pin | không |
| GPIO27 | 26 | không dùng (USB_D+) | — | USB pull-up | như trên | không |

USB D–/D+ không được đưa ra test point ở rev A: trên PCB, chân 25/26 nằm ngay cạnh VDD3P3 (27), cặp thạch anh (28/29) và ANT (32); bỏ chúng giải phóng lối thoát cho đường clock 32 MHz (không via, quanh thạch anh) và via 3V2 của chân 27. Nạp firmware/console dùng UART0 (TP7/TP8) + BOOT (TP5) – firmware đã tắt USB-Serial-JTAG. Bản devkit (ESP32-H2-DevKitM-1) vẫn dùng được USB để gỡ lỗi.

Không có GPIO nào dùng chung với chức năng flash (GPIO15–21 nằm trong package, không đưa ra), RF (ANT là chân analog riêng) hay thạch anh chính (XTAL_P/N là chân analog riêng). Strap GPIO8/GPIO9 có trạng thái xác định khi reset; GPIO25 không cần điện trở vì eFuse `STRAP_JTAG_SEL` mặc định = 0.

## 11. Nguyên lý hoạt động từng khối (tóm tắt)

| Khối | Nguyên lý |
|---|---|
| Nguồn | PMOS dẫn khi pin đúng cực (V_GS = –V_pin), khóa khi ngược; TPS63900 single-mode buck-boost giữ 3.2 V từ 1.65–3.4 V vào; Iq 75 nA |
| Reset | TPS3839 giữ CHIP_EN thấp tới 200 ms sau khi 3V2 > 2.96 V; kéo reset khi 3V2 < 2.93 V |
| Clock | 32 MHz chính cho CPU/radio; RTC slow clock dùng RC 136 kHz nội (32.768 kHz tùy chọn) |
| RF | mạng CLC(CL) phía chip biến đổi 50 Ω → ~35 Ω liên hợp chip và lọc hài; GCPW 50 Ω; π tuning anten; MIFA |
| Hall | DRV5032FA tự lấy mẫu 20 Hz, giữ mức; MCU ngủ và được EXT1 đánh thức khi mức đổi |
| Nút | GPIO9 kéo lên; nhấn = LOW đánh thức EXT1; cũng là chân BOOT khi reset |
| LED | sáng ~1.45 mA chỉ khi commissioning/identify/reset; mức được giữ khi chip ngủ |
| Đo pin | phân áp 1:2 chỉ được nối đất (qua GPIO22) trong ~50 ms mỗi 12 h |

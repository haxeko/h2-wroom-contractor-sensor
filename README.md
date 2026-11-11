# h2-wroom-contractor-sensor

**Cảm biến cửa Matter over Thread, ESP32-H2, cảm biến Hall DRV5032FA, pin CR123A rời, ICD.**
Repo chứa **hai phiên bản phần cứng** dùng chung một mạch nguồn/Hall/nút/LED và **một firmware**:

| | **Bản module** (`wroom`) – khuyên dùng | **Bản chip rời** (`chip`) |
|---|---|---|
| SoC | module **ESP32-H2-WROOM-02C-H4S** (thạch anh, RF, anten nằm trong module) | chip **ESP32-H2FH4S** + thạch anh + mạng RF + anten MIFA in trên PCB |
| PCB | **32 × 20 mm, 2 lớp**, 1.0 mm | 36 × 18 mm, 4 lớp, 1.0 mm, kiểm soát trở kháng 50 Ω |
| BOM lắp ráp | 18 dòng / 27 linh kiện, nhỏ nhất 0402 | 27 dòng / 46 linh kiện, có 0201 |
| RF | không cần tinh chỉnh; 🧪 có thể tận dụng chứng nhận của module | phải tinh chỉnh anten bằng VNA, tự làm chứng nhận vô tuyến |
| Thiết kế KiCad | [`hardware/wroom/`](hardware/wroom/) | [`hardware/chip/`](hardware/chip/) |
| Tài liệu riêng | [`docs/wroom/`](docs/wroom/) | [`docs/chip/`](docs/chip/) |
| Đặt hàng JLCPCB | via 0.6 / 0.3 mm: không phát sinh phí | ⚠️ via 0.4 / 0.2 mm ⇒ JLCPCB đòi thêm phí **4-Wire Kelvin Test**; muốn tránh phải đổi via sang 0.45 / 0.2 mm và đi dây lại (chưa làm) |

Cả hai: ERC 0, DRC 0 vi phạm / 0 kết nối hở / 0 lệch sơ đồ (KiCad 10.0.8). Chưa có phép đo phần cứng nào.

Quy ước trạng thái: ✅ **đã kiểm chứng** (datasheet / mã nguồn SDK / đã build) · 🧪 **cần thử nghiệm** trên phần cứng thật · 💡 **đề xuất** thiết kế.

## Cấu trúc thư mục

```
hardware/
  lib/                     thư viện KiCad dùng chung: mcs.kicad_sym, mcs.pretty (module WROOM, pad dây pin, anten…)
  wroom/                   BẢN MODULE: matter_contact_sensor_wroom.kicad_{pro,sch,pcb,dru}, drc_report.json
    fab/                     file đặt hàng: *-gerber.zip, assembly/*-bom.csv, assembly/*-cpl.csv, PDF, ảnh
  chip/                    BẢN CHIP RỜI: matter_contact_sensor.kicad_{pro,sch,pcb,dru}, drc_report.json
    fab/                     file đặt hàng của bản chip rời
    antenna/                 footprint gốc anten MIFA TI AN043 + 3 biến thể tinh chỉnh
    bom.csv                  BOM đầy đủ có hãng, mã thay thế, giá (bản chip rời; phần chung dùng cho cả hai)
    netlist.csv              netlist mức chân của bản chip rời
firmware/
  matter_contact_sensor/   firmware chung cho cả hai board (ESP-IDF v5.5.5 + esp-matter release/v1.6)
docs/
  README.md                mục lục tài liệu
  common/                  01 tổng quan · 02 nguồn pin · 03 Hall · 08 firmware · 09 tuổi thọ pin · 10 kế hoạch thử · 11 lộ trình
  wroom/                   12 bản module
  chip/                    04 anten RF · 05 sơ đồ · 06 PCB · 07 BOM
tools/
  design_data.py           dữ liệu thiết kế gốc (bản chip rời; phần mạch chung)
  design_data_wroom.py     dữ liệu thiết kế bản module (lấy phần chung từ design_data.py)
  kicad/                   sinh thư viện, sơ đồ, PCB (router), file sản xuất
  battery_life.py, magnet_field.py, coin_cell_buffer.py, cpwg_impedance.py, gen_antenna_variants.py, netlist.py
```

Quy tắc khi sửa:
- **Mạch chung** (nguồn, Hall, nút, LED, đo pin, pad test): sửa ở `tools/design_data.py`, rồi sinh lại **cả hai** board.
- **Riêng bản module**: `tools/design_data_wroom.py`, `tools/kicad/build_pcb_wroom.py`.
- **Riêng bản chip rời**: phần MCU / thạch anh / RF trong `tools/design_data.py`, `tools/kicad/build_pcb.py`.
- **Linh kiện thư viện**: `tools/kicad/gen_libs.py` → `hardware/lib/`.
- Không sửa tay các file trong `fab/`: luôn xuất lại bằng `export_fab.py`.

## Thông số chung

| Hạng mục | Giá trị |
|---|---|
| Firmware | ESP-IDF **v5.5.5** + esp-matter **release/v1.6**: build OK, image 1.50 MB (slot OTA 1.92 MB còn 20 %), cùng một file build cho cả hai board |
| Matter | Contact Sensor (0x0015) + Power Source (CR123A) trên endpoint 1; ICD **SIT** (slow poll 15 s, idle 3600 s) |
| Nguồn | CR123A rời, 2 dây vào J1 → PMOS AO3401A chống ngược cực → **TPS63900** buck-boost 3.2 V (Iq 75 nA) + TPS3839 giám sát |
| Hall | **DRV5032FADBZR** omnipolar 1.6 µA, GPIO10 (LP IO) + EXT1 đảo mức ⇒ phát hiện cả OPEN và CLOSED khi chip ngủ |
| Tuổi thọ pin (ước tính) | **~2.3–2.6 năm** (10–20 lần/ngày), ~2.0–2.5 năm (50–100), ~1.8–2.0 năm (200) với 1500–1700 mAh – 🧪 phải đo |

## Phát hiện quan trọng khi đối chiếu SDK

1. Với esp-matter v1.6, `BooleanState::StateValue` do `BooleanStateCluster` (code-driven) quản lý; `esp_matter::attribute::update()` trả về `ESP_ERR_NOT_SUPPORTED` ⇒ firmware gọi `BooleanStateCluster::SetStateValue()` (tự sinh sự kiện StateChange).
2. Khi bật `CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP` (cần cho sàn ~25 µA), đánh thức GPIO thường không còn hoạt động trên ESP32-H2; phải dùng **EXT1 trên LP IO GPIO7–14** ⇒ quyết định chân Hall/nút.
3. ESP-IDF đặt công suất phát 802.15.4 mặc định ở **20 dBm**; firmware hạ xuống 10 dBm ngay từ khung đầu tiên bằng linker wrap của `esp_ieee802154_enable()`.
4. Slow poll của ICD SIT bị connectedhomeip giới hạn ≤ 15 s bằng `static_assert`.
5. Khi chưa ghép nối, BLE giữ thạch anh chính chạy trong light sleep (vài mA thay vì ~25 µA) ⇒ firmware Deep-sleep sau khi cửa sổ commissioning đóng (docs/common/08 §3.6).
6. Pin cúc áo CR2450 không hợp với ESP32-H2: nội trở vượt 20 Ω sau khoảng 250 mAh ⇒ chỉ dùng được ~40 % dung lượng (khoảng nửa năm) (docs/wroom/12 §8).

## Lệnh thường dùng

```bash
# Thư viện + sơ đồ (KiCad 10 + kicad-cli)
python3 tools/kicad/gen_libs.py                          # -> hardware/lib/
python3 tools/kicad/gen_schematic.py --variant wroom     # -> hardware/wroom/
python3 tools/kicad/gen_schematic.py                     # -> hardware/chip/

# PCB: đặt linh kiện + đi dây + đổ đồng + DRC   (pcbnew Python = /usr/bin/python3.12 trên Ubuntu)
/usr/bin/python3.12 tools/kicad/build_pcb_wroom.py       # bản module
/usr/bin/python3.12 tools/kicad/build_pcb.py             # bản chip rời

# File sản xuất: Gerber, khoan, BOM, CPL, PDF, ảnh -> hardware/<board>/fab/
python3 tools/kicad/export_fab.py --variant wroom
python3 tools/kicad/export_fab.py

# Tính toán
python3 tools/battery_life.py --tx-dbm 10 --slow-poll-s 15 --subscribers 2
python3 tools/magnet_field.py
python3 tools/netlist.py          # netlist + kiểm tra ERC đơn giản (bản chip rời)
python3 tools/cpwg_impedance.py   # đường 50 Ω (bản chip rời)

# Firmware (ESP-IDF v5.5.5 + esp-matter release/v1.6 đã export)
cd firmware/matter_contact_sensor && idf.py set-target esp32h2 && idf.py build
```
Các script sinh PCB cho kết quả xác định: chạy lại cho ra đúng hai board đang có trong repo (đã kiểm tra: 285 đoạn đường + via ở bản module, 388 ở bản chip rời).

## Phạm vi và giới hạn

- Mọi con số "thực tế" là ước tính có nguồn, đánh dấu 🧪, kèm quy trình đo; việc cần làm trên mạch mẫu ở docs/wroom/12 §6, docs/chip/06 §10 và docs/common/10.
- Trước khi đặt bản chip rời: kỹ sư layout rà soát và chốt stack-up / trở kháng với nhà sản xuất (docs/chip/06 §10), và xử lý via 0.4 / 0.2 mm nếu đặt ở JLCPCB.
- Dữ liệu commissioning trong firmware là dữ liệu **TEST** của SDK; sản phẩm thật cần VID/PID, DAC, dữ liệu nhà máy và chứng nhận CSA.
- Lịch sử thiết kế trước khi tách repo: [`haxeko/matter-thread-contractor`](https://github.com/haxeko/matter-thread-contractor) (commit `2f9c032`).

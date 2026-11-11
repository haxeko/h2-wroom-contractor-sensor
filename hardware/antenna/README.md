# Footprint anten PCB 2.4 GHz (MIFA – TI AN043 / SWRA117D)

| File | Nội dung |
|---|---|
| `Texas_SWRA117D_2.4GHz_Left.kicad_mod` | Bản sao **nguyên vẹn** của footprint thư viện KiCad `RF_Antenna:Texas_SWRA117D_2.4GHz_Left` (nhánh master, định dạng KiCad 10) |
| `Texas_SWRA117D_2.4GHz_Right.kicad_mod` | Bản sao **nguyên vẹn** của `RF_Antenna:Texas_SWRA117D_2.4GHz_Right` (ảnh gương của bản Left) – **bản dùng trên PCB rev A** |
| `Texas_SWRA117D_2.4GHz_{Left,Right}_L1_3.64mm.kicad_mod` | nhánh hở L1 rút ngắn 0.3 mm |
| `Texas_SWRA117D_2.4GHz_{Left,Right}_L1_3.34mm.kicad_mod` | rút ngắn 0.6 mm |
| `Texas_SWRA117D_2.4GHz_{Left,Right}_L1_3.04mm.kicad_mod` | rút ngắn 0.9 mm |

Sinh lại biến thể: `python3 tools/gen_antenna_variants.py` (sau đó `python3 tools/kicad/gen_libs.py` để chép vào `hardware/kicad/mcs.pretty`).

- Pad 1 = feed (nối `RF_ANT`), pad 2 = điểm ngắn mạch xuống GND (via 0.3 mm); `net_tie_pad_groups "1,2"` để DRC chấp nhận anten nối feed–GND.
- Vùng anten (Dwgs.User) 15.2 × 5.2 mm phía trên mép GND; mép GND tại y = –0.25 mm trong hệ tọa độ footprint (stub feed/short đi vào vùng GND 0.5 mm – kích thước D4).
- Trên PCB rev A (36 × 18 mm): footprint `_Right` xoay 90°, gốc tại (5.45; 14.95) mm tính từ góc trên-trái PCB ⇒ vùng keep-out anten x = 0…5.2 mm, cạnh dưới của vùng anten trùng mép "mặt A" (y = 18), điểm feed ở y = 14.95. Rule area keep-out **mọi lớp** (không đường, không via, không đổ đồng) cho toàn bộ dải x = 0…5.2 mm do `tools/kicad/build_pcb.py` tạo.
- Đổi biến thể L1 sau đo VNA: sửa footprint của ANT1 trong `tools/design_data.py` (ví dụ `mcs:Texas_SWRA117D_2.4GHz_Right_L1_3.34mm`) rồi chạy lại chuỗi sinh schematic/PCB.
- Mở bằng KiCad ≥ 9/10 (định dạng `version 20260206`); với KiCad cũ hơn, lấy footprint cùng tên từ thư viện đi kèm phiên bản đó.

Giấy phép/ghi công: footprint gốc thuộc thư viện KiCad (https://gitlab.com/kicad/libraries/kicad-footprints), phát hành theo **CC-BY-SA 4.0** kèm ngoại lệ cho thiết kế sử dụng thư viện; các biến thể L1 là tác phẩm phái sinh cùng giấy phép. Kích thước anten: Texas Instruments, *AN043 – Small Size 2.4 GHz PCB antenna* (SWRA117D).

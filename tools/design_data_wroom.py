"""
Design data of the Matter contact sensor, module variant (ESP32-H2-WROOM-02C).

Same circuit as tools/design_data.py (rev A, bare ESP32-H2) except the radio part: the module
contains the ESP32-H2, 32 MHz crystal, RF matching, PCB antenna, 3V3 decoupling and the EN RC delay
(Espressif ESP32-H2-WROOM-02C datasheet v1.2, 2025-10-13). The GPIO assignment is identical, so
the firmware runs unchanged:
  GPIO1 VBAT_ADC, GPIO8 strap, GPIO9 BTN, GPIO10 HALL_OUT, GPIO11 LED, GPIO22 VBAT_EN, GPIO23/24 UART0

Supply and battery: identical to the bare-chip board - CR123A off the PCB, two wires soldered to J1,
P-MOSFET reverse-polarity protection, TPS63900 at 3.2 V without an input current limit. A CR123A has
well under 1 Ohm of internal resistance, so no bulk capacitor is needed (a CR2450 coin cell was tried
and dropped: only ~40 % of its capacity is usable with this radio, docs/12 section 7).

Used by tools/kicad/gen_schematic.py --variant wroom and tools/kicad/build_pcb_wroom.py.
Pin keys are module pin numbers (= footprint pad numbers, datasheet table 2).
"""
from dataclasses import replace

from design_data import PARTS as CHIP_PARTS
from design_data import PRJ, Part

RAIL = "3V2"   # regulated rail (TPS63900 VO(2) = 3.2 V), same net name as the bare-chip board

MODULE_PINS = {
    "1": RAIL, "2": "CHIP_EN", "3": "NC_IO4", "4": "NC_IO5", "5": "HALL_OUT", "6": "LED_DRV",
    "7": "IO8_STRAP", "8": "BTN", "9": "GND", "10": "NC_IO12", "11": "NC_IO13", "12": "NC_IO14", "13": "GND",
    "14": "NC_VBAT",  # module VBAT: tied to the internal 3V3 by default (datasheet table 2)
    "15": "VBAT_EN", "16": "NC_16", "17": "NC_17", "18": "NC_18", "19": "NC_19", "20": "NC_IO25",
    "21": "U0RXD", "22": "U0TXD_CHIP", "23": "NC_IO26", "24": "NC_IO27", "25": "NC_IO3", "26": "NC_IO2",
    "27": "VBAT_ADC", "28": "NC_IO0", "29": "GND",
}

# parts shared with the bare-chip design (power, reset/boot, UART, Hall, LED, battery measurement, TPs)
SHARED = ["J1", "D2", "Q1", "R1", "C1", "C2", "U2", "L2", "R2", "R3", "R4", "C3", "C4", "C6",
          "U4", "R6", "R10", "SW1", "D3", "R11", "R13", "U3", "C24", "R12", "D1", "R8", "R9", "C25",
          "TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7", "TP8", "TP9", "TP10"]
_chip = {p.ref: p for p in CHIP_PARTS}

PARTS = [
    Part("U1", f"{PRJ}:ESP32-H2-WROOM-02C", f"{PRJ}:ESP32-H2-WROOM-02C", "ESP32-H2-WROOM-02C-H4S",
         dict(MODULE_PINS), "mcu", "ESP32-H2-WROOM-02C-H4S", "Espressif",
         description="ESP32-H2 module, 4 MB flash, PCB antenna, 20 x 18 x 3.2 mm",
         datasheet="https://documentation.espressif.com/esp32-h2-wroom-02c_datasheet_en.pdf"),
] + [replace(_chip[r], pins={k: RAIL if v == "3V2" else v for k, v in _chip[r].pins.items()},
                extra=dict(_chip[r].extra)) for r in SHARED]
for _i, _p in enumerate(PARTS):
    if _p.ref in ("C4", "C6"):
        PARTS[_i] = replace(_p, description="module 3V3 (pin 1)")
    if _p.ref == "U2":
        # 2-layer board, no hole below 0.3 mm: footprint WITHOUT the 0.2 mm thermal vias in the exposed
        # pad (TI: vias in the pad are optional; the pad is tied to GND pin 8 on the top layer)
        PARTS[_i] = replace(_p, footprint="Package_SON:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm")

NC_NETS = {n for n in MODULE_PINS.values() if n.startswith("NC_")}
PWR_FLAG_NETS = ["GND", "VBAT"]

SCH_TITLE = "Matter Contact Sensor - ESP32-H2-WROOM-02C / Hall / CR123A"
SCH_BLOCKS = [
    ("NGUON: CR123A (ngoai PCB, day vao J1) -> PMOS chong nguoc cuc -> TPS63900 buck-boost 3V2", 20, 35,
     [["J1", "D2", "Q1", "R1", "C1", "C2"], ["U2", "L2", "R2", "R3", "R4", "C3"]]),
    ("MODULE ESP32-H2-WROOM-02C (thach anh, RF, anten, RC EN ben trong module)", 235, 35,
     [["U1"], ["C4", "C6"]]),
    ("RESET (TPS3839) / BOOT (GPIO9) / STRAP GPIO8 / UART0", 20, 175,
     [["U4", "R6"], ["SW1", "R10", "D3", "R11", "R13"]]),
    ("HALL DRV5032FA / LED / DO DIEN AP PIN", 400, 205,
     [["U3", "C24"], ["R12", "D1"], ["R8", "R9", "C25"]]),
    ("TEST POINTS (mat BOTTOM, jig pogo)", 235, 330,
     [["TP1", "TP2", "TP3", "TP4", "TP5"], ["TP6", "TP7", "TP8", "TP9", "TP10"]]),
]
SCH_NOTES = [
    "Ghi chu thiet ke (ban module):",
    "1. Module ESP32-H2-WROOM-02C can 3.0-3.6 V -> TPS63900 dat 3.2 V (CFG1 = 30.1k 1%), khong gioi han dong vao.",
    "2. Module da co thach anh 32 MHz, mach RF, anten PCB, tu 3V3 va tu 1 uF tren EN (datasheet v1.2).",
    "3. GPIO giong ban chip roi: firmware dung chung. GPIO8 keo len R11; KHONG dat tu len GPIO9.",
    "4. Chan VBAT (14) de trong: noi san voi 3V3 ben trong module (mac dinh).",
    "5. Anten module nho ra ngoai mep PCB (Espressif: vung anten khong co dong phia duoi).",
    "6. Pin CR123A nam ngoai PCB, 2 day 0.15 mm2 han vao J1: 1 = +, 2 = -.",
    "7. Sinh tu tools/design_data_wroom.py - chay tools/kicad/gen_schematic.py --variant wroom.",
]

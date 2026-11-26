"""
Master design data of the Matter contact sensor rev A (single source of truth).
Battery off the PCB (wired to J1), PCB 36 x 18 mm.

Used by:
  tools/netlist.py              -> hardware/chip/netlist.csv + simple ERC checks
  tools/kicad/gen_schematic.py  -> hardware/chip/matter_contact_sensor.kicad_sch
  tools/kicad/build_pcb.py      -> hardware/chip/matter_contact_sensor.kicad_pcb (through the
                                   netlist exported by KiCad from the schematic)

Pin keys are the SYMBOL pin numbers, which equal the FOOTPRINT pad numbers.
"""
from dataclasses import dataclass, field

PRJ = "mcs"  # project symbol/footprint library nickname


@dataclass
class Part:
    ref: str
    lib_id: str
    footprint: str
    value: str
    pins: dict
    block: str
    mpn: str = ""
    manufacturer: str = ""
    dnp: bool = False
    description: str = ""
    datasheet: str = "~"
    extra: dict = field(default_factory=dict)


R0402 = "Resistor_SMD:R_0402_1005Metric"
C0201 = "Capacitor_SMD:C_0201_0603Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
L0201 = "Inductor_SMD:L_0201_0603Metric"
L0402 = "Inductor_SMD:L_0402_1005Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"


def R(ref, value, a, b, block, mpn="", dnp=False, desc=""):
    return Part(ref, "Device:R", R0402, value, {"1": a, "2": b}, block, mpn, "Yageo", dnp, desc)


def C(ref, value, a, b, block, fp=C0402, mpn="", dnp=False, desc=""):
    return Part(ref, "Device:C", fp, value, {"1": a, "2": b}, block, mpn, "Murata", dnp, desc)


def L(ref, value, a, b, block, fp=L0402, mpn="", dnp=False, desc=""):
    return Part(ref, "Device:L", fp, value, {"1": a, "2": b}, block, mpn, "Murata", dnp, desc)


def TP(ref, net):
    return Part(ref, "Connector:TestPoint", "TestPoint:TestPoint_Pad_D1.0mm", "TP", {"1": net}, "tp",
                description="Pogo test pad (bottom side)", extra={"in_bom": False, "in_pos": False})


ESP32_PINS = {
    "1": "3V2", "2": "3V2", "3": "NC_GPIO0", "4": "VBAT_ADC", "5": "NC_GPIO2", "6": "NC_GPIO3",
    "7": "NC_GPIO4", "8": "NC_GPIO5", "9": "3V2", "10": "IO8_STRAP", "11": "BTN", "12": "HALL_OUT",
    "13": "LED_DRV", "14": "NC_GPIO12", "15": "X32K_P", "16": "X32K_N", "17": "CHIP_EN",
    "18": "VBAT_PIN18", "19": "3V2", "20": "3V2", "21": "VBAT_EN", "22": "U0RXD", "23": "U0TXD_CHIP",
    "24": "NC_GPIO25", "25": "NC_GPIO26", "26": "NC_GPIO27", "27": "3V2", "28": "XTAL_N", "29": "XTAL_P",
    "30": "3V2", "31": "3V2", "32": "LNA_IN", "33": "GND",
}

PARTS = [
    # ------------------------------------------------------------------ power
    # battery off the PCB: CR123A in the housing between Keystone 1087-1 (+) / 1087-2 (-)
    # contacts held in housing slots, two 0.15 mm2 wires soldered to the contact tails and to J1
    Part("J1", "Connector_Generic:Conn_01x02", f"{PRJ}:BatteryWires_2x0.15sqmm_P2.54mm_D0.7mm", "CR123A wires",
         {"1": "VBAT_RAW", "2": "GND"}, "power", "", "",
         description="Solder pads for the off-board CR123A: pad 1 = + (VBAT_RAW), pad 2 = - (GND); "
                     "0.15 mm2 stranded wire. Cell contacts in the housing: Keystone 1087-1 + 1087-2",
         datasheet="https://www.keyelco.com/userAssets/file/K75p41.pdf",
         extra={"in_bom": False, "in_pos": False}),
    # D2/D3 MUST be bidirectional: a unidirectional TVS would short a reversed cell in front of Q1
    Part("D2", "Device:D_TVS", "Diode_SMD:D_SOD-882", "PESD5V0U1BL", {"1": "VBAT_RAW", "2": "GND"}, "power",
         "PESD5V0U1BL,315", "Nexperia", description="Bidirectional ESD 5 V, nA leakage"),
    # AO3401A: same SOT-23 pinout (1 G, 2 S, 3 D) as DMG2305UX-7, cheaper and stocked everywhere
    Part("Q1", f"{PRJ}:DMG2305UX", SOT23, "AO3401A", {"1": "Q1_G", "2": "VBAT", "3": "VBAT_RAW"},
         "power", "AO3401A", "Alpha & Omega", description="P-MOSFET reverse polarity protection"),
    R("R1", "100k", "Q1_G", "GND", "power", "RC0402FR-07100KL"),
    C("C1", "22u", "VBAT", "GND", "power", C0603, "GRM188R60J226MEA0D"),
    C("C2", "22u", "VBAT", "GND", "power", C0603, "GRM188R60J226MEA0D"),
    Part("U2", "Regulator_Switching:TPS63900",
         "Package_SON:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias", "TPS63900DSKR",
         {"1": "VBAT", "2": "VBAT", "3": "CFG1", "4": "CFG2", "5": "CFG3", "6": "3V2", "7": "LX2",
          "8": "GND", "9": "LX1", "10": "VBAT", "11": "GND"}, "power", "TPS63900DSKR", "Texas Instruments",
         description="Buck-boost 75 nA IQ, VOUT = 3.2 V (CFG1 30.1k)",
         datasheet="https://www.ti.com/lit/ds/symlink/tps63900.pdf"),
    L("L2", "2.2u", "LX1", "LX2", "power", "Inductor_SMD:L_1008_2520Metric", "DFE252010F-2R2M"),
    R("R2", "30.1k 1%", "CFG1", "GND", "power", "RC0402FR-0730K1L", desc="TPS63900 VO(2) = 3.2 V"),
    R("R3", "0R", "CFG2", "GND", "power", "RC0402JR-070RL", desc="input current limit = unlimited"),
    R("R4", "0R", "CFG3", "GND", "power", "RC0402JR-070RL", desc="VO(1) = 1.8 V (unused)"),
    C("C3", "22u", "3V2", "GND", "power", C0603, "GRM188R60J226MEA0D"),
    # ------------------------------------------------------------------ MCU
    Part("U1", f"{PRJ}:ESP32-H2FH4S",
         "Package_DFN_QFN:VQFN-32-1EP_4x4mm_P0.4mm_EP2.8x2.8mm_ThermalVias", "ESP32-H2FH4S",
         dict(ESP32_PINS), "mcu", "ESP32-H2FH4S", "Espressif",
         description="ESP32-H2 SoC, 802.15.4 + BLE, 4 MB flash in package",
         datasheet="https://www.espressif.com/sites/default/files/documentation/esp32-h2_datasheet_en.pdf"),
    R("R5", "0R", "VBAT_PIN18", "3V2", "mcu", "RC0402JR-070RL", desc="VBAT pin feed (Espressif ref R2)"),
    C("C4", "22u", "3V2", "GND", "mcu", C0603, "GRM188R60J226MEA0D", desc="VDD3P3 pins 1/2"),
    C("C5", "1u", "3V2", "GND", "mcu", C0402, "GRM155R61A105KE15D", desc="VDD3P3 pins 1/2"),
    C("C6", "100n", "3V2", "GND", "mcu", C0402, "GRM155R71C104KA88D", desc="VDD3P3 pins 1/2"),
    C("C7", "10n", "3V2", "GND", "mcu", C0402, "GRM155R71H103KA88D", desc="VDD3P3 pin 31"),
    C("C8", "1u", "3V2", "GND", "mcu", C0402, "GRM155R61A105KE15D", desc="VDD3P3 pins 27/30"),
    C("C9", "100n", "3V2", "GND", "mcu", C0402, "GRM155R71C104KA88D", desc="VDD3P3 pins 27/30"),
    C("C10", "100n", "3V2", "GND", "mcu", C0402, "GRM155R71C104KA88D", desc="VDDPST2 pin 20"),
    C("C11", "100n", "3V2", "GND", "mcu", C0402, "GRM155R71C104KA88D", desc="VDDA_PMU/VBAT 18/19"),
    C("C12", "100n", "3V2", "GND", "mcu", C0402, "GRM155R71C104KA88D", desc="VDDPST1 pin 9"),
    # ------------------------------------------------------------------ reset / boot / UART
    Part("U4", "Power_Supervisor:TPS3839DBZ", SOT23, "TPS3839K33DBZR", {"1": "GND", "2": "RST_N", "3": "3V2"},
         "reset", "TPS3839K33DBZR", "Texas Instruments", description="Supervisor 2.93 V, 150 nA",
         datasheet="https://www.ti.com/lit/ds/symlink/tps3839.pdf"),
    R("R6", "1k", "RST_N", "CHIP_EN", "reset", "RC0402FR-071KL"),
    C("C13", "100n", "CHIP_EN", "GND", "reset", C0402, "GRM155R71C104KA88D"),
    R("R7", "10k", "3V2", "CHIP_EN", "reset", "RC0402FR-0710KL", dnp=True, desc="RC reset fallback"),
    C("C14", "1u", "CHIP_EN", "GND", "reset", C0402, "GRM155R61A105KE15D", dnp=True, desc="RC reset fallback"),
    R("R10", "100k", "3V2", "BTN", "reset", "RC0402FR-07100KL", desc="GPIO9 strap pull-up"),
    Part("SW1", "Switch:SW_Push", "Button_Switch_SMD:SW_SPST_B3U-1000P", "B3U-1000P", {"1": "BTN", "2": "GND"},
         "reset", "B3U-1000P", "Omron", description="Commissioning / reset / BOOT button"),
    Part("D3", "Device:D_TVS", "Diode_SMD:D_SOD-882", "PESD5V0U1BL", {"1": "BTN", "2": "GND"}, "reset",
         "PESD5V0U1BL,315", "Nexperia", dnp=True, description="ESD on button (optional)"),
    R("R11", "100k", "3V2", "IO8_STRAP", "reset", "RC0402FR-07100KL", desc="GPIO8 strap pull-up (download mode)"),
    R("R13", "499R", "U0TXD_CHIP", "U0TXD", "reset", "RC0402FR-07499RL", desc="U0TXD harmonic suppression"),
    # ------------------------------------------------------------------ clocks
    L("L3", "24n", "XTAL_P", "XTAL_P_X", "xtal", L0402, "LQW15AN24NG00D"),
    Part("Y1", "Device:Crystal_GND24", "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm", "32MHz 10ppm CL10pF",
         {"1": "XTAL_P_X", "2": "GND", "3": "XTAL_N", "4": "GND"}, "xtal", "ECS-320-10-37B2-CKY-TR", "ECS Inc."),
    C("C15", "15p", "XTAL_P_X", "GND", "xtal", C0402, "GRM1555C1H150JA01D"),
    C("C16", "15p", "XTAL_N", "GND", "xtal", C0402, "GRM1555C1H150JA01D"),
    Part("Y2", "Device:Crystal", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", "32.768kHz",
         {"1": "X32K_P", "2": "X32K_N"}, "xtal", "ABS07-32.768KHZ-T", "Abracon", dnp=True),
    C("C17", "22p", "X32K_P", "GND", "xtal", C0402, "GRM1555C1H220JA01D", dnp=True),
    C("C18", "22p", "X32K_N", "GND", "xtal", C0402, "GRM1555C1H220JA01D", dnp=True),
    # ------------------------------------------------------------------ RF
    C("C19", "1.5p", "LNA_IN", "GND", "rf", C0201, "GRM0335C1H1R5BA01D", desc="chip-side shunt (Espressif C12)"),
    L("L4", "2.7n", "LNA_IN", "RF_A", "rf", L0201, "LQP03TN2N7B02D", desc="series (Espressif L2)"),
    C("C20", "1.5p", "RF_A", "GND", "rf", C0201, "GRM0335C1H1R5BA01D", desc="shunt (Espressif C11)"),
    Part("C21", "Device:C", C0201, "0R", {"1": "RF_A", "2": "RF_M1"}, "rf", "RC0201JR-070RL", "Yageo",
         description="0R / 10pF DC-block option"),
    L("L5", "DNP", "RF_M1", "GND", "rf", L0201, "", dnp=True),
    Part("J2", f"{PRJ}:MS-156C3", "Connector_Coaxial:CoaxialSwitch_Hirose_MS-156C3_Horizontal", "MS-156C3",
         {"C": "RF_M1", "A": "RF_50R", "G": "GND"}, "rf", "MS-156C3", "Hirose",
         description="RF switch connector for conducted test (EVT/DVT)"),
    C("C22", "DNP", "RF_50R", "GND", "rf", C0201, "", dnp=True, desc="antenna pi tuning"),
    Part("L6", "Device:L", L0201, "0R", {"1": "RF_50R", "2": "RF_ANT"}, "rf", "RC0201JR-070RL", "Yageo",
         description="antenna pi tuning (series)"),
    C("C23", "DNP", "RF_ANT", "GND", "rf", C0201, "", dnp=True, desc="antenna pi tuning"),
    Part("ANT1", "Device:Antenna_Shield", f"{PRJ}:Texas_SWRA117D_2.4GHz_Right", "MIFA TI SWRA117D",
         {"1": "RF_ANT", "2": "GND"}, "rf", "PCB antenna", "-",
         description="Meandered IFA (TI AN043), copper on F.Cu",
         datasheet="https://www.ti.com/lit/an/swra117d/swra117d.pdf", extra={"in_bom": False, "in_pos": False}),
    # ------------------------------------------------------------------ Hall
    # DRV5032FA (20 Hz, 1.6 uA) instead of FB (5 Hz, 0.69 uA): same thresholds/pinout, lower price
    Part("U3", f"{PRJ}:DRV5032FAxDBZ", SOT23, "DRV5032FADBZR", {"1": "3V2", "2": "HALL_OUT", "3": "GND"},
         "hall", "DRV5032FADBZR", "Texas Instruments", description="Omnipolar Hall switch 20 Hz 1.6 uA",
         datasheet="https://www.ti.com/lit/ds/symlink/drv5032.pdf"),
    C("C24", "100n", "3V2", "GND", "hall", C0402, "GRM155R71C104KA88D"),
    # ------------------------------------------------------------------ LED
    R("R12", "1k", "LED_DRV", "LED_A", "led", "RC0402FR-071KL"),
    Part("D1", "Device:LED", "LED_SMD:LED_0603_1608Metric", "red 630nm", {"1": "GND", "2": "LED_A"}, "led",
         "APTD1608LSURCK", "Kingbright"),
    # ------------------------------------------------------------------ battery measurement
    R("R8", "1M 1%", "VBAT", "VBAT_ADC", "vbat", "RC0402FR-071ML"),
    R("R9", "1M 1%", "VBAT_ADC", "VBAT_EN", "vbat", "RC0402FR-071ML"),
    C("C25", "10n", "VBAT_ADC", "GND", "vbat", C0402, "GRM155R71H103KA88D"),
    # ------------------------------------------------------------------ test points
    TP("TP1", "3V2"), TP("TP2", "GND"), TP("TP3", "VBAT"), TP("TP4", "CHIP_EN"), TP("TP5", "BTN"),
    TP("TP6", "IO8_STRAP"), TP("TP7", "U0TXD"), TP("TP8", "U0RXD"), TP("TP9", "HALL_OUT"),
    TP("TP10", "VBAT_ADC"),
]

# Nets that legitimately have one connection (unused ESP32-H2 pins -> no-connect flags)
NC_NETS = {n for n in ESP32_PINS.values() if n.startswith("NC_")}
# Nets that need a PWR_FLAG in the schematic (power_in pins fed only through passive parts)
PWR_FLAG_NETS = ["GND", "VBAT", "VBAT_PIN18"]


def by_ref():
    return {p.ref: p for p in PARTS}

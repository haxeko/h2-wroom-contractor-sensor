#!/usr/bin/env python3
"""
Generate the project libraries of hardware/kicad/:
  mcs.kicad_sym : ESP32-H2FH4S, ESP32-H2-WROOM-02C, DRV5032FAxDBZ, DMG2305UX, MS-156C3
  mcs.pretty/   : MIFA antenna Left/Right (nominal + L1 tuning variants), battery wire pads, CR2450 edge tab pads, ESP32-H2-WROOM-02C, tooling hole
  sym-lib-table, fp-lib-table
"""
import copy
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, find_all  # noqa: E402
from symlib import get_symbol  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
KDIR = ROOT / "hardware" / "kicad"
ANT_SRC = ROOT / "hardware" / "antenna"
NICK = "mcs"

F = [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]


def prop(name, value, x=0.0, y=0.0, hide=False, justify=None):
    eff = copy.deepcopy(F)
    if justify:
        eff.append([Sym("justify"), Sym(justify)])
    p = [Sym("property"), name, value, [Sym("at"), x, y, 0], [Sym("show_name"), Sym("no")],
         [Sym("do_not_autoplace"), Sym("no")]]
    if hide:
        p.append([Sym("hide"), Sym("yes")])
    p.append(eff)
    return p


def pin(ptype, x, y, angle, name, number, length=2.54):
    return [Sym("pin"), Sym(ptype), Sym("line"), [Sym("at"), x, y, angle], [Sym("length"), length],
            [Sym("name"), name, copy.deepcopy(F)], [Sym("number"), number, copy.deepcopy(F)]]


def header_flags():
    return [[Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            [Sym("in_pos_files"), Sym("yes")], [Sym("duplicate_pin_numbers_are_jumpers"), Sym("no")]]


# ESP32-H2 QFN32 (datasheet v1.3, table 2-1); None = empty slot
ESP_LEFT = [("1", "VDD3P3", "power_in"), ("2", "VDD3P3", "power_in"), ("27", "VDD3P3", "power_in"),
            ("30", "VDD3P3", "power_in"), ("31", "VDD3P3", "power_in"), ("9", "VDDPST1", "power_in"),
            ("20", "VDDPST2", "power_in"), ("19", "VDDA_PMU", "power_in"), ("18", "VBAT", "power_in"), None,
            ("17", "CHIP_EN", "input"), None, ("29", "XTAL_P", "passive"), ("28", "XTAL_N", "passive"), None,
            ("15", "XTAL_32K_P/GPIO13", "bidirectional"), ("16", "XTAL_32K_N/GPIO14", "bidirectional"), None,
            ("32", "ANT", "passive")]
ESP_RIGHT = [("3", "GPIO0", "bidirectional"), ("4", "GPIO1/ADC1_CH0", "bidirectional"),
             ("5", "MTMS/GPIO2", "bidirectional"), ("6", "MTDO/GPIO3", "bidirectional"),
             ("7", "MTCK/GPIO4", "bidirectional"), ("8", "MTDI/GPIO5", "bidirectional"), None,
             ("10", "GPIO8", "bidirectional"), ("11", "GPIO9", "bidirectional"), ("12", "GPIO10", "bidirectional"),
             ("13", "GPIO11", "bidirectional"), ("14", "GPIO12", "bidirectional"), None,
             ("21", "GPIO22", "bidirectional"), ("22", "U0RXD/GPIO23", "bidirectional"),
             ("23", "U0TXD/GPIO24", "bidirectional"), ("24", "GPIO25", "bidirectional"),
             ("25", "GPIO26/USB_D-", "bidirectional"), ("26", "GPIO27/USB_D+", "bidirectional")]


def esp32h2_symbol():
    name = "ESP32-H2FH4S"
    top = 2.54 * (len(ESP_LEFT) - 1) / 2  # 22.86
    s = [Sym("symbol"), name] + header_flags()
    hw = 17.78  # body half width: room for the long pin names on both sides
    s += [prop("Reference", "U", -hw, top + 3.81, justify="left"),
          prop("Value", name, 2.54, top + 3.81, justify="left"),
          prop("Footprint", "Package_DFN_QFN:VQFN-32-1EP_4x4mm_P0.4mm_EP2.8x2.8mm_ThermalVias", 0, -33, True),
          prop("Datasheet", "https://www.espressif.com/sites/default/files/documentation/esp32-h2_datasheet_en.pdf",
               0, -35.5, True),
          prop("Description", "ESP32-H2 RISC-V SoC, IEEE 802.15.4 + Bluetooth LE 5, 4 MB in-package flash, QFN32 4x4 mm",
               0, -38, True),
          prop("ki_keywords", "Espressif ESP32-H2 Thread Zigbee Matter BLE", 0, 0, True)]
    body = [Sym("symbol"), f"{name}_0_1",
            [Sym("rectangle"), [Sym("start"), -hw, top + 2.54], [Sym("end"), hw, -(top + 2.54)],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("background")]]]]
    pins = [Sym("symbol"), f"{name}_1_1"]
    for i, ent in enumerate(ESP_LEFT):
        if ent:
            pins.append(pin(ent[2], -(hw + 2.54), round(top - 2.54 * i, 2), 0, ent[1], ent[0]))
    for i, ent in enumerate(ESP_RIGHT):
        if ent:
            pins.append(pin(ent[2], hw + 2.54, round(top - 2.54 * i, 2), 180, ent[1], ent[0]))
    pins.append(pin("power_in", 0, -(top + 5.08), 90, "GND", "33"))
    s += [body, pins, [Sym("embedded_fonts"), Sym("no")]]
    return s


# ESP32-H2-WROOM-02C (datasheet v1.2, 2025-10-13, table 2 "Pin Definitions"); None = empty slot
WROOM_LEFT = [("1", "3V3", "power_in"), ("14", "VBAT", "passive"), None, ("2", "EN", "input"), None,
              ("11", "IO13/XTAL_32K_P", "bidirectional"), ("12", "IO14/XTAL_32K_N", "bidirectional"), None,
              ("16", "NC", "no_connect"), ("17", "NC", "no_connect"), ("18", "NC", "no_connect"),
              ("19", "NC", "no_connect")]
WROOM_RIGHT = [("28", "IO0", "bidirectional"), ("27", "IO1/ADC1_CH0", "bidirectional"),
               ("26", "IO2/MTMS", "bidirectional"), ("25", "IO3/MTDO", "bidirectional"),
               ("3", "IO4/MTCK", "bidirectional"), ("4", "IO5/MTDI", "bidirectional"), None,
               ("7", "IO8", "bidirectional"), ("8", "IO9", "bidirectional"), ("5", "IO10", "bidirectional"),
               ("6", "IO11", "bidirectional"), ("10", "IO12", "bidirectional"), None,
               ("15", "IO22", "bidirectional"), ("21", "RXD0/IO23", "bidirectional"),
               ("22", "TXD0/IO24", "bidirectional"), ("20", "IO25", "bidirectional"),
               ("23", "IO26/USB_D-", "bidirectional"), ("24", "IO27/USB_D+", "bidirectional")]
WROOM_DS = "https://documentation.espressif.com/esp32-h2-wroom-02c_datasheet_en.pdf"


def wroom_symbol():
    name = "ESP32-H2-WROOM-02C"
    n = max(len(WROOM_LEFT), len(WROOM_RIGHT))
    top = 2.54 * (n - 1) / 2
    hw = 15.24
    s = [Sym("symbol"), name] + header_flags()
    s += [prop("Reference", "U", -hw, top + 3.81, justify="left"),
          prop("Value", name, 2.54, top + 3.81, justify="left"),
          prop("Footprint", "mcs:ESP32-H2-WROOM-02C", 0, -30, True),
          prop("Datasheet", WROOM_DS, 0, -32.5, True),
          prop("Description", "ESP32-H2 module, IEEE 802.15.4 + Bluetooth LE 5, PCB antenna, 2/4 MB flash, "
                              "20 x 18 x 3.2 mm, 29 pins", 0, -35, True),
          prop("ki_keywords", "Espressif ESP32-H2 module Thread Zigbee Matter BLE", 0, 0, True)]
    body = [Sym("symbol"), f"{name}_0_1",
            [Sym("rectangle"), [Sym("start"), -hw, top + 2.54], [Sym("end"), hw, -(top + 2.54)],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("background")]]]]
    pins = [Sym("symbol"), f"{name}_1_1"]
    for i, ent in enumerate(WROOM_LEFT):
        if ent:
            pins.append(pin(ent[2], -(hw + 2.54), round(top - 2.54 * i, 2), 0, ent[1], ent[0]))
    for i, ent in enumerate(WROOM_RIGHT):
        if ent:
            pins.append(pin(ent[2], hw + 2.54, round(top - 2.54 * i, 2), 180, ent[1], ent[0]))
    for k, num in enumerate(("9", "13", "29")):
        pins.append(pin("power_in", -2.54 + 2.54 * k, -(top + 5.08), 90, "GND", num))
    s += [body, pins, [Sym("embedded_fonts"), Sym("no")]]
    return s


def renamed_copy(lib_id, new_name, value, description, datasheet):
    s = get_symbol(lib_id)
    old = s[1]
    s[1] = new_name
    for u in find_all(s, Sym("symbol")):
        u[1] = u[1].replace(old, new_name, 1)
    for p in find_all(s, Sym("property")):
        if p[1] == "Value":
            p[2] = value
        elif p[1] == "Description":
            p[2] = description
        elif p[1] == "Datasheet":
            p[2] = datasheet
    return s


def ms156_symbol():
    name = "MS-156C3"
    s = [Sym("symbol"), name] + header_flags()
    s += [prop("Reference", "J", 0, 5.08), prop("Value", name, 0, -6.35),
          prop("Footprint", "Connector_Coaxial:CoaxialSwitch_Hirose_MS-156C3_Horizontal", 0, -8.89, True),
          prop("Datasheet", "https://www.hirose.com/product/series/MS-156", 0, -11.43, True),
          prop("Description", "Coaxial switch connector DC-11 GHz 50 Ohm: C = circuit side, A = antenna side; "
                              "inserting the test probe disconnects A", 0, -13.97, True)]
    body = [Sym("symbol"), f"{name}_0_1",
            [Sym("rectangle"), [Sym("start"), -3.81, 2.54], [Sym("end"), 3.81, -2.54],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("background")]]],
            [Sym("circle"), [Sym("center"), 0, 0], [Sym("radius"), 1.27],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("none")]]],
            [Sym("polyline"), [Sym("pts"), [Sym("xy"), -3.81, 0], [Sym("xy"), -1.27, 0]],
             [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("none")]]],
            [Sym("polyline"), [Sym("pts"), [Sym("xy"), 1.27, 0], [Sym("xy"), 3.81, 0]],
             [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("none")]]]]
    pins = [Sym("symbol"), f"{name}_1_1", pin("passive", -6.35, 0, 0, "C", "C"), pin("passive", 6.35, 0, 180, "A", "A"),
            pin("passive", 0, -5.08, 90, "G", "G")]
    s += [body, pins, [Sym("embedded_fonts"), Sym("no")]]
    return s


def write_symbol_lib():
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20251024], [Sym("generator"), "mcs_gen_libs"],
           [Sym("generator_version"), "10.0"],
           esp32h2_symbol(),
           renamed_copy("Sensor_Magnetic:DRV5033FAxDBZ", "DRV5032FAxDBZ", "DRV5032FADBZR",
                        "Low-power omnipolar Hall switch, push-pull, 20 Hz, 1.6 uA typ, SOT-23",
                        "https://www.ti.com/lit/ds/symlink/drv5032.pdf"),
           renamed_copy("Transistor_FET:DMG2301L", "DMG2305UX", "DMG2305UX-7",
                        "-4.2A Id, -20V Vds, P-Channel MOSFET, Rds 100 mOhm @ -2.5 V, SOT-23",
                        "https://www.diodes.com/assets/Datasheets/DMG2305UX.pdf"),
           ms156_symbol(), wroom_symbol()]
    (KDIR / f"{NICK}.kicad_sym").write_text(dumps(lib) + "\n")


# Off-board battery: two solder pads for the CR123A wires. Hole / pad as KiCad
# Connector_Wire:SolderWire-0.15sqmm_1x02_P4mm_D0.5mm_OD1.5mm (drill 0.7, pad 1.7 mm) but at a 2.54 mm
# pitch so the pads sit on the 2.54 mm pogo grid of the test pads (the jig powers the board through
# them from the bottom side). Wire: 0.15 mm2 (26 AWG) stranded, insulation OD <= 1.5 mm.
WIRE_PITCH = 2.54
WIRE_PAD, WIRE_DRILL = 1.7, 0.7


def battery_wires_fp():
    """Pad 1 = + (VBAT_RAW, square), pad 2 = - (GND), pad 2 at +2.54 mm in y."""
    name = "BatteryWires_2x0.15sqmm_P2.54mm_D0.7mm"
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), 1, 1], [Sym("thickness"), 0.15]]]
    big = [Sym("effects"), [Sym("font"), [Sym("size"), 1.2, 1.2], [Sym("thickness"), 0.2]]]
    p = WIRE_PITCH
    c = WIRE_PAD / 2 + 0.25

    def rect(x0, y0, x1, y1, layer, width):
        return [Sym("fp_rect"), [Sym("start"), round(x0, 3), round(y0, 3)], [Sym("end"), round(x1, 3), round(y1, 3)],
                [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
                [Sym("layer"), layer]]

    fp = [Sym("footprint"), name, [Sym("version"), 20260206], [Sym("generator"), "mcs_gen_libs"],
          [Sym("generator_version"), "10.0"], [Sym("layer"), "F.Cu"],
          [Sym("descr"), "Solder pads for the two wires of an off-board CR123A (0.15 mm2 stranded, insulation OD "
                         "<= 1.5 mm), drill 0.7 / pad 1.7 mm as KiCad SolderWire-0.15sqmm, pitch 2.54 mm. "
                         "Pad 1 = +, pad 2 = -."],
          [Sym("tags"), "battery wire solder pad CR123A"],
          [Sym("property"), "Reference", "REF**", [Sym("at"), 0, -1.9, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("property"), "Value", name, [Sym("at"), 0, p + 1.9, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("attr"), Sym("through_hole"), Sym("exclude_from_pos_files"), Sym("exclude_from_bom")],
          rect(-c, -c, c, p + c, "F.CrtYd", 0.05),
          rect(-c + 0.15, -c + 0.15, c - 0.15, p + c - 0.15, "F.Fab", 0.1)]
    # polarity on the top silkscreen; on the bottom the square pad 1 marks + (the pogo grid leaves no
    # room for text there)
    for txt, y in (("+", 0.0), ("-", p)):
        fp.append([Sym("fp_text"), Sym("user"), txt, [Sym("at"), -1.75, y, 0], [Sym("layer"), "F.SilkS"],
                   copy.deepcopy(big)])
    fp.append([Sym("pad"), "1", Sym("thru_hole"), Sym("roundrect"), [Sym("at"), 0, 0], [Sym("size"), WIRE_PAD, WIRE_PAD],
               [Sym("drill"), WIRE_DRILL], [Sym("layers"), "*.Cu", "*.Mask"], [Sym("remove_unused_layers"), Sym("no")],
               [Sym("roundrect_rratio"), 0.15]])
    fp.append([Sym("pad"), "2", Sym("thru_hole"), Sym("circle"), [Sym("at"), 0, p], [Sym("size"), WIRE_PAD, WIRE_PAD],
               [Sym("drill"), WIRE_DRILL], [Sym("layers"), "*.Cu", "*.Mask"], [Sym("remove_unused_layers"), Sym("no")]])
    fp.append([Sym("embedded_fonts"), Sym("no")])
    return fp


# ESP32-H2-WROOM-02C land pattern (datasheet v1.2 figure 7, unit mm). Module frame: 18 (x) x 20 (y),
# antenna area = top 6 mm. Pads 1.5 x 0.9 mm, pitch 1.5 mm, 0.5 mm outside the module edge:
#   pins 1-9 left column, centre x = 0.25 from the left edge, pin 1 at y = 7.1 from the top edge
#   pins 28-20 right column (pin 28 at the top), pins 10-19 bottom row, centre 0.25 above the bottom
#   edge, pin 10 at x = 2.25 from the left edge. GND pad 29: 2.8 x 0.55 strip centred 7.99 above the
#   bottom edge + 2.8 x 1.6 block centred 6.27 above it, x centre 8.53 from the left edge, vias in the
#   block. Footprint origin = module centre.
def wroom_fp():
    name = "ESP32-H2-WROOM-02C"
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), 1, 1], [Sym("thickness"), 0.15]]]
    X0, Y0 = -9.0, -10.0                    # module top-left corner in footprint coordinates

    def rect(x0, y0, x1, y1, layer, width):
        return [Sym("fp_rect"), [Sym("start"), round(x0, 3), round(y0, 3)], [Sym("end"), round(x1, 3), round(y1, 3)],
                [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
                [Sym("layer"), layer]]

    def smd(num, x, y, w, h):
        return [Sym("pad"), num, Sym("smd"), Sym("rect"), [Sym("at"), round(x, 3), round(y, 3)],
                [Sym("size"), w, h], [Sym("layers"), "F.Cu", "F.Mask", "F.Paste"]]

    fp = [Sym("footprint"), name, [Sym("version"), 20260206], [Sym("generator"), "mcs_gen_libs"],
          [Sym("generator_version"), "10.0"], [Sym("layer"), "F.Cu"],
          [Sym("descr"), "Espressif ESP32-H2-WROOM-02C, 20 x 18 x 3.2 mm, land pattern per datasheet v1.2 "
                         "figure 7. Antenna area (top 6 mm) should overhang the base board edge."],
          [Sym("tags"), "ESP32-H2 WROOM module Espressif"],
          [Sym("property"), "Reference", "REF**", [Sym("at"), 0, 1, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("property"), "Value", name, [Sym("at"), 0, -7, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("property"), "Datasheet", WROOM_DS, [Sym("at"), 0, 0, 0], [Sym("layer"), "F.Fab"],
           [Sym("hide"), Sym("yes")], copy.deepcopy(eff)],
          [Sym("attr"), Sym("smd")],
          rect(X0, Y0, X0 + 18, Y0 + 20, "F.Fab", 0.1),
          [Sym("fp_line"), [Sym("start"), X0, Y0 + 6], [Sym("end"), X0 + 18, Y0 + 6],
           [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("dash")]], [Sym("layer"), "F.Fab"]],
          [Sym("fp_text"), Sym("user"), "ANTENNA", [Sym("at"), 0, Y0 + 3, 0], [Sym("layer"), "F.Fab"],
           copy.deepcopy(eff)],
          [Sym("fp_text"), Sym("user"), "${REFERENCE}", [Sym("at"), 0, 6, 0], [Sym("layer"), "F.Fab"],
           copy.deepcopy(eff)],
          [Sym("fp_circle"), [Sym("center"), X0 + 1.6, Y0 + 7.1], [Sym("end"), X0 + 1.85, Y0 + 7.1],
           [Sym("stroke"), [Sym("width"), 0.12], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("yes")],
           [Sym("layer"), "F.SilkS"]],
          rect(X0 - 0.75, Y0 - 0.25, X0 + 18.75, Y0 + 20.75, "F.CrtYd", 0.05)]
    for k in range(9):                                       # pins 1..9 and 28..20
        y = Y0 + 7.1 + 1.5 * k
        fp.append(smd(str(1 + k), X0 + 0.25, y, 1.5, 0.9))
        fp.append(smd(str(28 - k), X0 + 17.75, y, 1.5, 0.9))
    for k in range(10):                                      # pins 10..19
        fp.append(smd(str(10 + k), X0 + 2.25 + 1.5 * k, Y0 + 19.75, 0.9, 1.5))
    ex = X0 + 8.53
    fp.append(smd("29", ex, Y0 + 20 - 7.99, 2.8, 0.55))
    fp.append(smd("29", ex, Y0 + 20 - 6.27, 2.8, 1.6))
    for dx in (-0.9, 0.0, 0.9):
        fp.append([Sym("pad"), "29", Sym("thru_hole"), Sym("circle"), [Sym("at"), round(ex + dx, 3), Y0 + 20 - 6.27],
                   [Sym("size"), 0.5, 0.5], [Sym("drill"), 0.3], [Sym("layers"), "*.Cu"],
                   [Sym("remove_unused_layers"), Sym("no")], [Sym("zone_connect"), 2]])
    fp.append([Sym("embedded_fonts"), Sym("no")])
    return fp


# CR2450 coin cell lying NEXT to the board edge, in the board plane (cell bottom flush with the PCB
# bottom): Ø24.5 x 5.0 mm (Panasonic / Energizer / Maxell datasheets). Two flat solder tabs reach over
# the edge: + tab from the can (bottom face) onto pad 1 on B.Cu, - tab from the cap (top face) onto
# pad 2 on F.Cu, both pads at the same place on opposite sides. Origin = pad centre; the board edge is
# at x = PAD_W / 2 + EDGE_CLR, the cell starts TAB_GAP further.
CR2450_D, CR2450_H = 24.5, 5.0
TAB_PAD = (2.7, 4.6)
TAB_EDGE_CLR, TAB_GAP = 0.3, 1.0


def battery_tabs_fp():
    name = "BatteryTabs_CR2450_BoardEdge"
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), 1, 1], [Sym("thickness"), 0.15]]]
    big = [Sym("effects"), [Sym("font"), [Sym("size"), 1.2, 1.2], [Sym("thickness"), 0.2]]]
    w, h = TAB_PAD
    edge = w / 2 + TAB_EDGE_CLR
    cx = edge + TAB_GAP + CR2450_D / 2

    def rect(x0, y0, x1, y1, layer, width):
        return [Sym("fp_rect"), [Sym("start"), round(x0, 3), round(y0, 3)], [Sym("end"), round(x1, 3), round(y1, 3)],
                [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
                [Sym("layer"), layer]]

    fp = [Sym("footprint"), name, [Sym("version"), 20260206], [Sym("generator"), "mcs_gen_libs"],
          [Sym("generator_version"), "10.0"], [Sym("layer"), "F.Cu"],
          [Sym("descr"), "Solder pads for a tabbed CR2450 (24.5 x 5.0 mm) lying next to the board edge in the "
                         "board plane: pad 1 (+, can tab) on B.Cu, pad 2 (-, cap tab) on F.Cu, 2.7 x 4.6 mm, "
                         "0.3 mm from the edge. Cell outline on F.Fab."],
          [Sym("tags"), "battery CR2450 coin cell tab solder pad board edge"],
          [Sym("property"), "Reference", "REF**", [Sym("at"), 0, -3.4, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("property"), "Value", name, [Sym("at"), cx, 0, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("attr"), Sym("smd"), Sym("exclude_from_pos_files"), Sym("exclude_from_bom")],
          [Sym("fp_circle"), [Sym("center"), round(cx, 3), 0], [Sym("end"), round(cx + CR2450_D / 2, 3), 0],
           [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
           [Sym("layer"), "F.Fab"]],
          rect(-w / 2, -1.5, edge + TAB_GAP + 3.0, 1.5, "F.Fab", 0.1),
          [Sym("fp_text"), Sym("user"), "CR2450: + tab below, - tab on top", [Sym("at"), round(cx, 3), 3, 0],
           [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
          [Sym("fp_line"), [Sym("start"), round(edge, 3), -h / 2 - 1], [Sym("end"), round(edge, 3), h / 2 + 1],
           [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("dash")]], [Sym("layer"), "F.Fab"]],
          rect(-w / 2 - 0.25, -h / 2 - 0.25, w / 2 + 0.25, h / 2 + 0.25, "F.CrtYd", 0.05),
          [Sym("fp_text"), Sym("user"), "-", [Sym("at"), 0, round(-h / 2 - 1.0, 3), 0], [Sym("layer"), "F.SilkS"],
           copy.deepcopy(big)],
          [Sym("pad"), "1", Sym("smd"), Sym("rect"), [Sym("at"), 0, 0], [Sym("size"), w, h],
           [Sym("layers"), "B.Cu", "B.Mask"]],
          [Sym("pad"), "2", Sym("smd"), Sym("rect"), [Sym("at"), 0, 0], [Sym("size"), w, h],
           [Sym("layers"), "F.Cu", "F.Mask"]],
          [Sym("embedded_fonts"), Sym("no")]]
    return fp


def tooling_hole_fp(d=1.5):
    """Non-plated tooling hole for the test jig (pogo fixture locating pins)."""
    name = f"ToolingHole_NPTH_{d:g}mm"
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), 1, 1], [Sym("thickness"), 0.15]]]
    return [Sym("footprint"), name, [Sym("version"), 20260206], [Sym("generator"), "mcs_gen_libs"],
            [Sym("generator_version"), "10.0"], [Sym("layer"), "F.Cu"],
            [Sym("descr"), f"Non-plated {d:g} mm tooling hole for the test fixture"], [Sym("tags"), "tooling hole NPTH"],
            [Sym("property"), "Reference", "REF**", [Sym("at"), 0, -1.6, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
            [Sym("property"), "Value", name, [Sym("at"), 0, 1.6, 0], [Sym("layer"), "F.Fab"], copy.deepcopy(eff)],
            [Sym("attr"), Sym("exclude_from_pos_files"), Sym("exclude_from_bom")],
            [Sym("fp_circle"), [Sym("center"), 0, 0], [Sym("end"), d / 2 + 0.5, 0],
             [Sym("stroke"), [Sym("width"), 0.05], [Sym("type"), Sym("solid")]], [Sym("fill"), Sym("no")],
             [Sym("layer"), "F.CrtYd"]],
            [Sym("pad"), "", Sym("np_thru_hole"), Sym("circle"), [Sym("at"), 0, 0], [Sym("size"), d, d],
             [Sym("drill"), d], [Sym("layers"), "*.Cu", "*.Mask"]],
            [Sym("embedded_fonts"), Sym("no")]]


def write_footprint_lib():
    pretty = KDIR / f"{NICK}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    for src in sorted(ANT_SRC.glob("Texas_SWRA117D_2.4GHz_*.kicad_mod")):
        shutil.copyfile(src, pretty / src.name)
    for old in ("BatteryContacts_CR123A_SMD.kicad_mod", "BatteryContacts_CR123A_Keystone1087_THT.kicad_mod"):
        if (pretty / old).exists():
            (pretty / old).unlink()          # battery is off the PCB since the 36 mm board
    (pretty / "BatteryWires_2x0.15sqmm_P2.54mm_D0.7mm.kicad_mod").write_text(dumps(battery_wires_fp()) + "\n")
    (pretty / "BatteryTabs_CR2450_BoardEdge.kicad_mod").write_text(dumps(battery_tabs_fp()) + "\n")
    (pretty / "ESP32-H2-WROOM-02C.kicad_mod").write_text(dumps(wroom_fp()) + "\n")
    (pretty / "ToolingHole_NPTH_1.5mm.kicad_mod").write_text(dumps(tooling_hole_fp(1.5)) + "\n")


def write_tables():
    # module variant (hardware/kicad_wroom) uses the same project libraries
    wdir = ROOT / "hardware" / "kicad_wroom"
    wdir.mkdir(parents=True, exist_ok=True)
    (wdir / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n  (lib (name "mcs")(type "KiCad")(uri "${KIPRJMOD}/../kicad/mcs.kicad_sym")'
        '(options "")(descr "Matter contact sensor project symbols"))\n)\n')
    (wdir / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "mcs")(type "KiCad")(uri "${KIPRJMOD}/../kicad/mcs.pretty")'
        '(options "")(descr "Matter contact sensor project footprints"))\n)\n')
    (KDIR / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n  (lib (name "mcs")(type "KiCad")(uri "${KIPRJMOD}/mcs.kicad_sym")'
        '(options "")(descr "Matter contact sensor project symbols"))\n)\n')
    (KDIR / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "mcs")(type "KiCad")(uri "${KIPRJMOD}/mcs.pretty")'
        '(options "")(descr "Matter contact sensor project footprints"))\n)\n')


def main():
    KDIR.mkdir(parents=True, exist_ok=True)
    write_symbol_lib()
    write_footprint_lib()
    write_tables()
    print("libraries written to", KDIR.relative_to(ROOT))


if __name__ == "__main__":
    main()

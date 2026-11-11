#!/usr/bin/env python3
"""
Generate hardware/kicad/matter_contact_sensor.kicad_sch from tools/design_data.py, or with
--variant wroom hardware/kicad_wroom/matter_contact_sensor_wroom.kicad_sch from tools/design_data_wroom.py
(ESP32-H2-WROOM-02C module version).

Style: every symbol pin gets a short wire stub and a local net label (label-based schematic,
one A2 sheet, grouped by functional block). Unused ESP32-H2 pins get no-connect flags,
PWR_FLAGs are added on nets whose power inputs are fed through passive parts.
UUIDs are deterministic (uuid5) so the PCB keeps its links when the schematic is regenerated.
"""
import pathlib
import sys
import uuid

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
VARIANT = "wroom" if "--variant" in sys.argv and sys.argv[sys.argv.index("--variant") + 1] == "wroom" else "chip"
if VARIANT == "wroom":
    from design_data_wroom import NC_NETS, PARTS, PWR_FLAG_NETS, SCH_BLOCKS, SCH_NOTES, SCH_TITLE  # noqa: E402
else:
    from design_data import NC_NETS, PARTS, PWR_FLAG_NETS  # noqa: E402
from sexp import Sym, dumps, find_all  # noqa: E402
from symlib import get_symbol, pins  # noqa: E402

ROOT = HERE.parents[1]
KDIR = ROOT / "hardware" / ("kicad_wroom" if VARIANT == "wroom" else "kicad")
PROJECT = "matter_contact_sensor_wroom" if VARIANT == "wroom" else "matter_contact_sensor"
PROJECT_LIBS = {"mcs": str(ROOT / "hardware" / "kicad" / "mcs.kicad_sym")}
NS = uuid.UUID("6f1c2a4e-9d3b-4c55-8f0e-2b7a1d9c3e10")
ROOT_UUID = str(uuid.uuid5(NS, "root-sheet"))
STUB = 2.54
CHAR_W = 1.15
GRID = 1.27
PASSIVES = ("Device:R", "Device:C", "Device:L")
FIELD_ROOM = 6.35  # space reserved above non-passive symbols for Reference + Value


def uid(*names):
    return str(uuid.uuid5(NS, "/".join(str(n) for n in names)))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def font(size=1.27, bold=False):
    f = [Sym("font"), [Sym("size"), size, size]]
    if bold:
        f.append([Sym("bold"), Sym("yes")])
    return f


# --------------------------------------------------------------------------- geometry helpers
OUTWARD = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}  # schematic coords (y down)
LABEL_ANGLE = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"), (0, 1): (270, "right")}


def pin_points(part, sym_pins):
    """(pin, schematic offset x, y, outward dir) for each pin, relative to the symbol origin."""
    out = []
    for p in sym_pins:
        if p["unit"] not in (0, 1):
            continue
        ang = int(round(p["angle"])) % 360
        out.append((p, p["x"], -p["y"], OUTWARD[ang]))
    return out


def extents(part, sym_pins):
    """Bounding box (left, right, up, down) relative to origin incl. stubs + labels."""
    l = r = u = d = 5.08
    for p, x, y, (dx, dy) in pin_points(part, sym_pins):
        net = part.pins.get(p["number"])
        lab = 0 if (net is None or net in NC_NETS) else STUB + CHAR_W * len(net) + 1.5
        ex, ey = x + dx * lab, y + dy * lab
        l, r = max(l, -ex + 1.27, -x + 1.27), max(r, ex + 1.27, x + 1.27)
        u, d = max(u, -ey + 1.27, -y + 1.27), max(d, ey + 1.27, y + 1.27)
    if part.lib_id in PASSIVES:
        # Reference/Value are drawn to the right of the body: keep the next symbol clear of them
        value = part.value + (" (DNP)" if part.dnp else "")
        r = max(r, 2.54 + CHAR_W * max(len(part.ref), len(value)) + 1.27)
    return l, r, u, d


# --------------------------------------------------------------------------- layout (A2 sheet)
BLOCKS = [
    # title, x0, y0, rows of refs
    ("NGUON: CR123A (ngoai PCB, day vao J1) -> PMOS chong nguoc cuc -> TPS63900 buck-boost 3V2", 20, 35,
     [["J1", "D2", "Q1", "R1", "C1", "C2"], ["U2", "L2", "R2", "R3", "R4", "C3"]]),
    ("ESP32-H2FH4S + tu decoupling (dat sat chan)", 235, 35,
     [["U1"], ["R5", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12"]]),
    ("RESET (TPS3839) / BOOT (GPIO9) / STRAP GPIO8 / UART0", 20, 175,
     [["U4", "R6", "C13", "R7", "C14"], ["SW1", "R10", "D3", "R11", "R13"]]),
    ("THACH ANH 32 MHz (+/-10 ppm) va 32.768 kHz (DNP)", 20, 300,
     [["L3", "Y1", "C15", "C16"], ["Y2", "C17", "C18"]]),
    ("RF: CLC phia chip -> J2 cong do -> pi anten -> MIFA TI SWRA117D", 235, 205,
     [["C19", "L4", "C20", "C21", "L5", "J2"], ["C22", "L6", "C23", "ANT1"]]),
    ("HALL DRV5032FA / LED / DO DIEN AP PIN", 400, 205,
     [["U3", "C24"], ["R12", "D1"], ["R8", "R9", "C25"]]),
    ("TEST POINTS (mat BOTTOM, jig pogo)", 235, 330,
     [["TP1", "TP2", "TP3", "TP4", "TP5"], ["TP6", "TP7", "TP8", "TP9", "TP10"]]),
]


def build():
    parts = {p.ref: p for p in PARTS}
    lib_cache = {}

    def sym_for(lib_id):
        if lib_id not in lib_cache:
            lib_cache[lib_id] = get_symbol(lib_id, PROJECT_LIBS)
        return lib_cache[lib_id]

    items = []          # schematic items (wires, labels, no_connects, texts)
    instances = []      # symbol instances
    placed = set()

    def add_symbol(part, ox, oy):
        s = sym_for(part.lib_id)
        sp = pins(s)
        sym_uuid = uid("sym", part.ref)
        l, r, u, d = extents(part, sp)
        in_bom = "yes" if part.extra.get("in_bom", True) else "no"
        in_pos = "yes" if part.extra.get("in_pos", True) else "no"
        inst = [Sym("symbol"), [Sym("lib_id"), part.lib_id], [Sym("at"), ox, oy, 0], [Sym("unit"), 1],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym(in_bom)], [Sym("on_board"), Sym("yes")],
                [Sym("in_pos_files"), Sym(in_pos)], [Sym("dnp"), Sym("yes" if part.dnp else "no")],
                [Sym("uuid"), sym_uuid]]

        def field(name, value, x, y, hide=False, justify="left"):
            f = [Sym("property"), name, value, [Sym("at"), snap(x), snap(y), 0], [Sym("show_name"), Sym("no")],
                 [Sym("do_not_autoplace"), Sym("no")]]
            if hide:
                f.append([Sym("hide"), Sym("yes")])
            f.append([Sym("effects"), font(), [Sym("justify"), Sym(justify)]])
            return f

        if part.lib_id in PASSIVES:
            # vertical 2-pin symbol: fields to the right of the body, labels above/below
            fx, fy_ref, fy_val = ox + 2.54, oy - 1.27, oy + 1.27
        else:
            # everything else: fields stacked above the extents (pin stubs + labels included)
            fx, fy_ref, fy_val = ox - l + 1.27, oy - u - 5.08, oy - u - 2.54
        inst.append(field("Reference", part.ref, fx, fy_ref))
        val = part.value + (" (DNP)" if part.dnp else "")
        inst.append(field("Value", val, fx, fy_val))
        inst.append(field("Footprint", part.footprint, ox, oy, hide=True))
        inst.append(field("Datasheet", part.datasheet or "~", ox, oy, hide=True))
        inst.append(field("Description", part.description, ox, oy, hide=True))
        inst.append(field("MPN", part.mpn, ox, oy, hide=True))
        inst.append(field("Manufacturer", part.manufacturer, ox, oy, hide=True))
        seen_numbers = set()
        for p in sp:
            if p["number"] in seen_numbers:
                continue
            seen_numbers.add(p["number"])
            inst.append([Sym("pin"), p["number"], [Sym("uuid"), uid("pin", part.ref, p["number"])]])
        inst.append([Sym("instances"), [Sym("project"), PROJECT,
                                        [Sym("path"), f"/{ROOT_UUID}", [Sym("reference"), part.ref],
                                         [Sym("unit"), 1]]]])
        instances.append(inst)

        # pin stubs + labels / no-connects
        done_pos = set()
        for p, x, y, (dx, dy) in pin_points(part, sp):
            net = part.pins.get(p["number"])
            if net is None:
                raise SystemExit(f"{part.ref}: pin {p['number']} ({p['name']}) has no net in design_data")
            px, py = snap(ox + x), snap(oy + y)
            if (px, py) in done_pos:
                continue
            done_pos.add((px, py))
            if net in NC_NETS:
                items.append([Sym("no_connect"), [Sym("at"), px, py], [Sym("uuid"), uid("nc", part.ref, p["number"])]])
                continue
            ex, ey = snap(px + dx * STUB), snap(py + dy * STUB)
            items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), px, py], [Sym("xy"), ex, ey]],
                          [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                          [Sym("uuid"), uid("wire", part.ref, p["number"])]])
            ang, just = LABEL_ANGLE[(dx, dy)]
            items.append([Sym("label"), net, [Sym("at"), ex, ey, ang],
                          [Sym("effects"), font(), [Sym("justify"), Sym(just), Sym("bottom")]],
                          [Sym("uuid"), uid("label", part.ref, p["number"])]])
        return l, r, u, d

    def text(s, x, y, size=2.54, bold=True):
        items.append([Sym("text"), s, [Sym("exclude_from_sim"), Sym("no")], [Sym("at"), snap(x), snap(y), 0],
                      [Sym("effects"), font(size, bold), [Sym("justify"), Sym("left"), Sym("bottom")]],
                      [Sym("uuid"), uid("text", s)]])

    # ---- blocks
    for title, x0, y0, rows in (SCH_BLOCKS if VARIANT == "wroom" else BLOCKS):
        text(title, x0, y0 - 6)
        y = y0
        for row in rows:
            ext = []
            for ref in row:
                part = parts[ref]
                ext.append(extents(part, pins(sym_for(part.lib_id))))
            up = max(e[2] + (0 if parts[ref].lib_id in PASSIVES else FIELD_ROOM) for ref, e in zip(row, ext))
            down = max(e[3] for e in ext)
            cursor = x0
            oy = snap(y + up)
            for ref, (l, r, u, d) in zip(row, ext):
                ox = snap(cursor + l)
                add_symbol(parts[ref], ox, oy)
                placed.add(ref)
                cursor = ox + r + 3.81
            y = oy + down + 7.62

    missing = set(parts) - placed
    if missing:
        raise SystemExit(f"parts not placed: {sorted(missing)}")

    # ---- PWR_FLAGs
    flag_sym = sym_for("power:PWR_FLAG")
    fx = 400
    for i, net in enumerate(PWR_FLAG_NETS):
        ox, oy = snap(fx + i * 25.4), snap(362)
        ref = f"#FLG0{i + 1}"
        inst = [Sym("symbol"), [Sym("lib_id"), "power:PWR_FLAG"], [Sym("at"), ox, oy, 0], [Sym("unit"), 1],
                [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
                [Sym("in_pos_files"), Sym("yes")], [Sym("dnp"), Sym("no")], [Sym("uuid"), uid("flag", net)],
                [Sym("property"), "Reference", ref, [Sym("at"), ox, oy - 6.35, 0], [Sym("show_name"), Sym("no")],
                 [Sym("do_not_autoplace"), Sym("no")], [Sym("hide"), Sym("yes")], [Sym("effects"), font()]],
                [Sym("property"), "Value", "PWR_FLAG", [Sym("at"), ox, oy - 3.81, 0], [Sym("show_name"), Sym("no")],
                 [Sym("do_not_autoplace"), Sym("no")], [Sym("effects"), font()]],
                [Sym("property"), "Footprint", "", [Sym("at"), ox, oy, 0], [Sym("show_name"), Sym("no")],
                 [Sym("do_not_autoplace"), Sym("no")], [Sym("hide"), Sym("yes")], [Sym("effects"), font()]],
                [Sym("property"), "Datasheet", "~", [Sym("at"), ox, oy, 0], [Sym("show_name"), Sym("no")],
                 [Sym("do_not_autoplace"), Sym("no")], [Sym("hide"), Sym("yes")], [Sym("effects"), font()]],
                [Sym("pin"), "1", [Sym("uuid"), uid("flagpin", net)]],
                [Sym("instances"), [Sym("project"), PROJECT, [Sym("path"), f"/{ROOT_UUID}", [Sym("reference"), ref],
                                                              [Sym("unit"), 1]]]]]
        instances.append(inst)
        ex, ey = ox, snap(oy + STUB)
        items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), ox, oy], [Sym("xy"), ex, ey]],
                      [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]], [Sym("uuid"), uid("flagwire", net)]])
        items.append([Sym("label"), net, [Sym("at"), ex, ey, 270],
                      [Sym("effects"), font(), [Sym("justify"), Sym("right"), Sym("bottom")]],
                      [Sym("uuid"), uid("flaglabel", net)]])
    text("PWR_FLAG (nguon cap qua linh kien thu dong)", fx, 348, 1.8, True)

    # ---- notes
    notes = [
        "Ghi chu thiet ke:",
        "1. ESP32-H2 can 3.0-3.6 V -> TPS63900 dat 3.2 V (CFG1 = 30.1k 1%, CFG2 = 0R unlimited, SEL = EN = VIN).",
        "2. Hall + nut nhan tren LP IO (GPIO10/GPIO9): danh thuc EXT1 khi tat mien TOP trong light sleep.",
        "3. GPIO8 keo len R11 de vao Joint Download Boot; KHONG dat tu len GPIO9.",
        "4. Linh kien RF 0201, zigzag, stub 15 mil/100 Ohm o pad GND cua C19 (Espressif). Gia tri chot sau do VNA.",
        "5. Phan ap do pin chi duoc noi dat qua GPIO22 khi do (0 uA khi nghi).",
        "6. Pin CR123A nam ngoai PCB (tiep diem Keystone 1087-1/1087-2 trong vo), 2 day 0.15 mm2 han vao J1: 1 = +, 2 = -.",
        "7. Sinh tu tools/design_data.py - sua du lieu o do roi chay lai tools/kicad/gen_schematic.py.",
    ]
    if VARIANT == "wroom":
        notes = SCH_NOTES
    for i, n in enumerate(notes):
        text(n, 20, 370 + i * 4.5, 1.6, i == 0)

    # ---- lib_symbols
    lib_symbols = [Sym("lib_symbols")]
    for lib_id in sorted(lib_cache):
        s = [Sym("symbol"), lib_id] + list(lib_cache[lib_id][2:])
        lib_symbols.append(s)

    sch = [Sym("kicad_sch"), [Sym("version"), 20260306], [Sym("generator"), "eeschema"],
           [Sym("generator_version"), "10.0"], [Sym("uuid"), ROOT_UUID], [Sym("paper"), "A2"],
           [Sym("title_block"), [Sym("title"), SCH_TITLE if VARIANT == "wroom" else "Matter Contact Sensor - ESP32-H2 / Hall / CR123A"],
            [Sym("date"), "2026-11-06"], [Sym("rev"), "A"], [Sym("company"), "matter-thread-contractor"],
            [Sym("comment"), 1, f"Schematic generated from tools/{'design_data_wroom' if VARIANT == 'wroom' else 'design_data'}.py (single source of truth)"],
            [Sym("comment"), 2, "See docs/05_schematic.md for the design description and GPIO table"]],
           lib_symbols]
    sch += items + instances
    sch.append([Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]])
    sch.append([Sym("embedded_fonts"), Sym("no")])
    out = KDIR / f"{PROJECT}.kicad_sch"
    out.write_text(dumps(sch) + "\n")
    print(f"wrote {out.relative_to(ROOT)}: {len(instances)} symbols, {len(items)} items")


if __name__ == "__main__":
    build()

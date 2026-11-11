#!/usr/bin/python3.12
"""
Build hardware/kicad_wroom/matter_contact_sensor_wroom.kicad_pcb: module variant of the contact sensor
(ESP32-H2-WROOM-02C), 32 x 20 mm, 2 LAYERS, 1.0 mm. Battery: CR123A off the PCB, two wires soldered to
J1 at the far end, exactly as on the bare-chip board (no bulk capacitor needed, docs/12 section 7).

Re-uses tools/kicad/build_pcb.py (netlist import, project settings, placement legaliser, maze router,
cleanup, DRC); only the board-specific parts are defined here:
  * the module sits at the left end, rotated so that its 6 mm antenna area OVERHANGS the board edge
    (no copper of any layer under the antenna - Espressif "Positioning a Module on a Base Board");
  * two copper layers only (the RF part is inside the module, nothing on the base board needs a
    controlled impedance): GND is poured on both sides and stitched, the 3V2 rail is a routed net -
    a 0.4 mm trunk C3 -> C4 -> C6 -> module pin 1 plus 0.3 mm branches;
  * F.Cu under the module body: GND only (pour + stitching), signals leave the module pads through a
    short fixed escape + via and continue on B.Cu;
  * vias 0.6 / 0.3 mm everywhere and no 0.2 mm hole (U2 uses the footprint without thermal vias):
    the standard, cheapest class of 2-layer boards;
  * after the zone fill, repair_gnd() looks for GND copper that the tracks cut off from the rest on
    BOTH layers and ties it back with an extra via or, failing that, a routed GND track.

Run (Ubuntu KiCad 10 PPA python):  /usr/bin/python3.12 tools/kicad/build_pcb_wroom.py
"""
import argparse
import pathlib
import sys

import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_pcb as B  # noqa: E402
import design_data_wroom as W  # noqa: E402
from pcb_router import Rule, _disk  # noqa: E402

ROOT = HERE.parents[1]
B.KDIR = ROOT / "hardware" / "kicad_wroom"
B.PROJECT = "matter_contact_sensor_wroom"
B.SCH = B.KDIR / f"{B.PROJECT}.kicad_sch"
B.PCB = B.KDIR / f"{B.PROJECT}.kicad_pcb"
B.PRO = B.KDIR / f"{B.PROJECT}.kicad_pro"
B.DRU = B.KDIR / f"{B.PROJECT}.kicad_dru"
B.FP_DIRS = {"mcs": ROOT / "hardware" / "kicad" / "mcs.pretty"}
B.PARTS = W.PARTS

BW, BH = 32.0, 20.0
B.BW, B.BH = BW, BH
# ---- two layers: stack-up, route layers, via class, rules
B.COPPER_LAYERS = 2
B.STACKUP = [
    ("F.SilkS", "Top Silk Screen", None, None, None, None),
    ("F.Paste", "Top Solder Paste", None, None, None, None),
    ("F.Mask", "Top Solder Mask", 0.01, None, None, None),
    ("F.Cu", "copper", 0.035, None, None, None),
    ("dielectric 1", "core", 0.91, "FR4", 4.5, 0.02),
    ("B.Cu", "copper", 0.035, None, None, None),
    ("B.Mask", "Bottom Solder Mask", 0.01, None, None, None),
    ("B.Paste", "Bottom Solder Paste", None, None, None, None),
    ("B.SilkS", "Bottom Silk Screen", None, None, None, None),
]
B.ROUTE_LAYERS = ["F.Cu", "B.Cu"]
B.VIA = B.VIA_PWR = (0.6, 0.3)   # 0.3 mm hole / 0.6 mm pad: minimum of the cheap 2-layer class with margin
B.VIA_MIN_PITCH = 0.65           # centre-to-centre: hole-to-hole >= 0.35 mm
B.PLANE_NETS = {"/GND"}          # GND = pours on both sides; 3V2 is an ordinary routed net here
B.RULES = dict(B.RULES, min_through_hole_diameter=0.3, min_via_diameter=0.6)
B.ANT_KEEPOUT_X = 0.0
B.NETCLASSES = [
    # name, clearance, track, via dia, via drill, nets
    ("Default", 0.15, 0.15, 0.6, 0.3, []),
    ("PWR", 0.15, 0.4, 0.6, 0.3, ["/VBAT_RAW", "/VBAT", "/LX1", "/LX2", "/3V2"]),
    ("GND", 0.15, 0.3, 0.6, 0.3, ["/GND"]),
]
B.CUSTOM_RULES = "(version 1)\n# Matter contact sensor, ESP32-H2-WROOM-02C variant: board rules only (no RF on the base board)\n"
B.ESCAPE_PWR = {"29"}          # pad 29 has its own vias; pads 9 and 13 (GND) get a via like any GND pad

# module: centre (MX, MY), rotated 90 deg -> antenna (module top) towards -x, overhanging x < 0
MX, MY = 4.0, 10.0
TP_X1, TP_X2 = BW - 4.3, BW - 1.76
TP_Y = [2.9 + 2.54 * k for k in range(6)]
# Placement for two layers. The 3V2 trunk runs on the bottom from the module decoupling (C4/C6) to
# module pin 1 at the lower-left corner and splits the board in two; every net stays on its side:
#   above it  - module top row (UART, VBAT_ADC) and VBAT_EN: power stage, battery divider, R13
#   below it  - module bottom row (EN, Hall, LED, strap, button): reset supervisor, button, LED, Hall
B.PLACEMENT = {
    "U1": (MX, MY, 90),
    # power (same relative arrangement as the bare-chip board)
    "U2": (19.6, 3.9, 0), "L2": (23.05, 4.1, 270), "C1": (19.95, 1.4, 180), "C3": (19.95, 6.3, 180),
    "C2": (23.1, 1.2, 0), "R2": (16.35, 3.35, 180), "R3": (16.35, 4.40, 180), "R4": (16.35, 5.45, 180),
    "Q1": (24.6, 9.0, 0), "D2": (25.9, 11.6, 270), "R1": (23.6, 6.6, 0),
    # module 3V3 decoupling next to the module GND pad 13, on the 3V2 trunk
    "C4": (15.75, 8.4, 90), "C6": (16.8, 8.4, 90),
    # battery divider in the top strip between the module and C1: the ADC node (upper pads) is one
    # straight track, VBAT comes from the TPS63900 VIN track, VBAT_EN goes down to module pin 15
    "R9": (15.4, 1.3, 270), "C25": (16.5, 1.3, 270), "R8": (17.6, 1.3, 90),
    # UART TX series resistor next to its test pad TP7
    "R13": (26.3, 3.7, 0),
    # boot button, strap
    "SW1": (20.0, 10.6, 0), "R10": (20.0, 12.9, 0), "D3": (17.1, 11.2, 90), "R11": (16.3, 13.6, 90),
    # reset supervisor next to the module bottom row (EN = pin 2)
    "U4": (16.85, 17.6, 180), "R6": (19.85, 16.65, 0),
    # Hall at edge "A" (y = 20), LED
    "U3": (24.4, BH - 1.8, 0), "C24": (21.85, BH - 2.75, 90), "D1": (24.4, 14.6, 180), "R12": (21.6, 14.6, 0),
    # battery wires + test pads: 2 x 6 pogo grid, bottom side, far end; top-row nets on the upper pads,
    # bottom-row nets on the lower pads
    "J1": (TP_X2, TP_Y[2], 0),
    "TP7": (TP_X1, TP_Y[0], 0, "B"), "TP8": (TP_X1, TP_Y[1], 0, "B"), "TP3": (TP_X1, TP_Y[2], 0, "B"),
    "TP5": (TP_X1, TP_Y[3], 0, "B"), "TP6": (TP_X1, TP_Y[4], 0, "B"), "TP9": (TP_X1, TP_Y[5], 0, "B"),
    "TP10": (TP_X2, TP_Y[0], 0, "B"), "TP1": (TP_X2, TP_Y[1], 0, "B"),
    "TP2": (TP_X2, TP_Y[4], 0, "B"), "TP4": (TP_X2, TP_Y[5], 0, "B"),
}
B.FIXED = {"U1", "U2", "L2", "C1", "C3", "C2", "J1", "U3", "Q1"}
B.BOARD_ONLY = [
    ("Fiducial", "Fiducial_0.5mm_Mask1mm", 20.3, 19.0, "F"),
    ("Fiducial", "Fiducial_0.5mm_Mask1mm", 31.1, 1.0, "F"),
    ("mcs", "ToolingHole_NPTH_1.5mm", 26.3, 1.55, "F"),
    ("mcs", "ToolingHole_NPTH_1.5mm", (TP_X1 + TP_X2) / 2, BH - 1.45, "F"),
]
BOTH = {"F.Cu": 1.0, "B.Cu": 1.5}       # both layers; the bottom costs more so that its GND pour stays whole
# 3V2 trunk, routed first and strictly in this order: TPS63900 output capacitor -> module decoupling ->
# module pin 1 (the pin sits at the antenna end of the module: 26.5 mm of 0.4 mm track, ~33 mOhm)
RAIL_TRUNK = [("C3", "1"), ("C4", "1"), ("C6", "1"), ("U1", "1")]
RAIL_TRUNK_W, RAIL_BRANCH_W = 0.4, 0.3
B.SIGNALS = [
    ("/CFG1", 0.15, B.F_ONLY), ("/CFG2", 0.15, B.F_ONLY), ("/CFG3", 0.15, B.F_ONLY),
    ("/VBAT_RAW", 0.4, {"F.Cu": 1.0, "B.Cu": 1.5}),
    ("/Q1_G", 0.15, BOTH), ("/VBAT", 0.3, {"F.Cu": 1.0, "B.Cu": 1.2}),
    # short local nets first: VBAT_EN needs the narrow corridor between the module and R2..R4
    ("/VBAT_EN", 0.15, BOTH), ("/VBAT_ADC", 0.15, BOTH),
    ("/U0RXD", 0.15, BOTH), ("/U0TXD_CHIP", 0.15, BOTH),
    ("/CHIP_EN", 0.15, BOTH), ("/RST_N", 0.15, BOTH),
    ("/HALL_OUT", 0.15, BOTH), ("/IO8_STRAP", 0.15, BOTH), ("/BTN", 0.15, BOTH),
    ("/LED_DRV", 0.15, BOTH), ("/LED_A", 0.15, BOTH),
    ("/U0TXD", 0.15, BOTH),
]
# module side-column signal pins: fixed escape (pad centre -> via 1.5 mm inwards, under the module)
MODULE_ESCAPES = {"1", "2", "5", "6", "7", "8", "21", "22", "27"}   # 1 = 3V3: start of the 3V2 trunk
ESC_IN = 1.5
ESC_DX = {}
# F.Cu under the module body (between the escape vias of both pad columns, left of the bottom row)
UNDER_MODULE = (0.0, MY - 8.75 + ESC_IN + 0.35, MX + 9.75 - 0.85, MY + 8.75 - ESC_IN - 0.35)


class WroomRouter(B.Router):
    def add_obstacles(self):
        g = self.g
        for fp in self.board.GetFootprints():
            pad_clr = 0.5 if fp.IsBoardOnly() else None
            for pad in fp.Pads():
                attr = pad.GetAttribute()
                cx, cy, hw, hh = self.pad_rect(pad)
                if attr == pcbnew.PAD_ATTRIB_NPTH:
                    for L in range(len(B.ROUTE_LAYERS)):
                        g.add_circle(B.ROUTE_LAYERS[L], cx, cy, max(hw, hh), -1, 0.25)
                    self.vias.append((cx, cy))
                    g.add_hole(cx, cy, max(hw, hh) + 0.25 + 0.15)
                    continue
                net = pad.GetNetname()
                nid = self.nid.get(net, -1) if net else -1
                if not pad.IsOnCopperLayer():
                    continue
                clr = pad_clr or B.CLR
                for L in self.pad_layers(pad):
                    if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                        g.add_circle(B.ROUTE_LAYERS[L], cx, cy, hw, nid, clr)
                        g.add_rect(B.ROUTE_LAYERS[L], cx, cy, hw * 0.7, hh * 0.7, nid, 0.0, pad=True)
                    else:
                        g.add_rect(B.ROUTE_LAYERS[L], cx, cy, hw, hh, nid, clr, pad=True)
                if attr == pcbnew.PAD_ATTRIB_PTH:
                    self.vias.append((cx, cy))
                    drill = pcbnew.ToMM(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2
                    g.add_hole(cx, cy, drill + 0.25 + 0.15)
        e = 0.3 + B.BASE_W / 2 + 0.03
        edge = Rule("edge")
        for L in B.ROUTE_LAYERS:
            g.add_rule_rect([L], 0, 0, BW, e, edge)
            g.add_rule_rect([L], 0, BH - e, BW, BH, edge)
            g.add_rule_rect([L], 0, 0, e, BH, edge)
            g.add_rule_rect([L], BW - e, 0, BW, BH, edge)
        g.add_rule_rect(["F.Cu"], *UNDER_MODULE, Rule("under module", [self.nid["/GND"]]))
        # bottom-layer lanes under the module's lower pad row: kept for the signals of that row, so the
        # 3V2 trunk leaves pin 1 inwards and does not wall in the escape vias of pins 2..8
        g.add_rule_rect(["B.Cu"], 1.85, MY + 8.75 - ESC_IN + 0.4, MX + 10.5, BH,
                        Rule("lower lanes", [n for name, n in self.nid.items() if name != B.RAIL]))

    def module_escapes(self):
        fp = self.fps["U1"]
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num not in MODULE_ESCAPES:
                continue
            x, y = B.to_rel(pad.GetPosition())
            vy = round(y + (ESC_IN if y < MY else -ESC_IN), 3)
            net = pad.GetNetname()
            vx = round(x + ESC_DX.get(num, 0.0), 3)
            self.add_track(net, "F.Cu", (x, y), (vx, vy), RAIL_TRUNK_W if net == B.RAIL else B.BASE_W)
            self.add_via(net, vx, vy)
            if net == B.RAIL:
                self.rail_start = (vx, vy)

    def route_rail(self):
        """3V2: trunk in a fixed order (so that the module decoupling capacitors sit ON the supply path),
        then every other 3V2 pad as a branch to the nearest 3V2 copper."""
        net = B.RAIL
        nid = self.nid[net]
        lc = {B.ROUTE_LAYERS.index(k): v for k, v in BOTH.items()}
        extra = _disk((RAIL_TRUNK_W - B.BASE_W) / 2 / B.GRID_PITCH)
        pads = {(ref, pad.GetNumber()): pad for ref, pad in self.net_pads(net)}
        prev = set(self.pad_nodes(pads[RAIL_TRUNK[0]], net))
        for key in RAIL_TRUNK[1:]:
            srcs = self.pad_nodes(pads[key], net)
            if key == ("U1", "1"):
                # the trunk starts at the fixed escape via of pin 1, on either layer
                i, j = self.g.ij(*self.rail_start)
                srcs = [(L, i, j) for L in self.via_layers]
            res = None
            for budget, hw in ((600_000, 1.3), (3_000_000, 2.0), (3_000_000, 6.0)):
                res = self.g.astar(nid, srcs, prev, layer_cost=lc, via_cost=25.0, via_disk=self.vdisk,
                                   via_layers=self.via_layers, extra_disk=extra, max_expand=budget, h_weight=hw)
                if res is not None:
                    break
            if res is None:
                self.failed.append((net, key, "no path (trunk)"))
                print(f"    no path: {net} trunk to {key}", flush=True)
                return False
            self.commit_path(net, res[0], RAIL_TRUNK_W)
            prev = set(srcs)
        return self.route_net(net, RAIL_BRANCH_W, BOTH)

    # ---------------------------------------------------------------- GND continuity on two layers
    def gnd_clusters(self):
        """Connected groups of GND copper after the zone fill: pour islands of both layers, GND vias,
        pads and tracks. Returns (groups, main, items) - main is the largest group."""
        board = self.board
        mmi = pcbnew.FromMM
        parent = {}

        def find(a):
            parent.setdefault(a, a)
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        isl = []
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != "/GND":
                continue
            for lid in (pcbnew.F_Cu, pcbnew.B_Cu):
                if z.IsOnLayer(lid):
                    ps = z.GetFilledPolysList(lid)
                    for k in range(ps.OutlineCount()):
                        isl.append((lid, ps, k))
                        find(("isl", len(isl) - 1))

        def at(lid, pt):
            return [("isl", n) for n, (l, ps, k) in enumerate(isl) if l == lid and ps.Contains(pt, k)]

        vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "/GND"]
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "/GND"]
        pads = [(fp.GetReference(), pad) for fp in board.GetFootprints() for pad in fp.Pads()
                if pad.GetNetname() == "/GND"]
        for n, v in enumerate(vias):
            find(("via", n))
            for lid in (pcbnew.F_Cu, pcbnew.B_Cu):
                for i in at(lid, v.GetPosition()):
                    union(("via", n), i)
        for n, (ref, pad) in enumerate(pads):
            find(("pad", n))
            bb, c = pad.GetBoundingBox(), pad.GetPosition()
            hw, hh = bb.GetWidth() // 2 + mmi(0.1), bb.GetHeight() // 2 + mmi(0.1)   # inside a thermal spoke
            pts = [c, pcbnew.VECTOR2I(c.x + hw, c.y), pcbnew.VECTOR2I(c.x - hw, c.y),
                   pcbnew.VECTOR2I(c.x, c.y + hh), pcbnew.VECTOR2I(c.x, c.y - hh)]
            if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:      # round pads: spokes at 45 degrees
                d = int(hw * 0.7071)
                pts += [pcbnew.VECTOR2I(c.x + sx * d, c.y + sy * d) for sx in (-1, 1) for sy in (-1, 1)]
            for lid in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(lid):
                    for pt in pts:
                        for i in at(lid, pt):
                            union(("pad", n), i)
            for m, v in enumerate(vias):
                if pad.HitTest(v.GetPosition()):
                    union(("pad", n), ("via", m))
        for n, t in enumerate(tracks):
            find(("trk", n))
            for pt in (t.GetStart(), t.GetEnd()):
                for i in at(t.GetLayer(), pt):
                    union(("trk", n), i)
                for m, v in enumerate(vias):
                    if v.HitTest(pt):
                        union(("trk", n), ("via", m))
                for m, (ref, pad) in enumerate(pads):
                    if pad.IsOnLayer(t.GetLayer()) and pad.HitTest(pt):
                        union(("trk", n), ("pad", m))
                for m, t2 in enumerate(tracks):
                    if m != n and t2.GetLayer() == t.GetLayer() and t2.HitTest(pt):
                        union(("trk", n), ("trk", m))
        groups = {}
        for a in list(parent):
            groups.setdefault(find(a), []).append(a)
        # only groups that own a pad or a via matter; the main group is the largest one
        groups = {r: m for r, m in groups.items() if any(kind in ("pad", "via") for kind, _ in m)}
        main = max(groups, key=lambda r: len(groups[r]))
        return groups, main, {"isl": isl, "via": vias, "pad": pads, "trk": tracks}

    def repair_gnd(self):
        """Tie every GND group that the tracks cut off on both layers back to the main GND:
        (1) an extra via where its pour overlaps main-GND pour of the other layer, else
        (2) a routed 0.25 mm GND track from its copper to main-GND copper. Returns a report."""
        nid = self.nid["/GND"]
        done = []
        for _ in range(8):
            B.fill_zones(self.board)
            groups, main, it = self.gnd_clusters()
            if len(groups) == 1:
                break
            main_isl = {lid: [(ps, k) for kind, n in groups[main] if kind == "isl"
                              for (l, ps, k) in [it["isl"][n]] if l == lid] for lid in (pcbnew.F_Cu, pcbnew.B_Cu)}

            def nodes(members):
                out = []
                for kind, n in members:
                    if kind == "via":
                        x, y = B.to_rel(it["via"][n].GetPosition())
                        i, j = self.g.ij(x, y)
                        out += [(L, i, j) for L in self.via_layers]
                    elif kind == "pad":
                        out += self.pad_nodes(it["pad"][n][1], "/GND")
                return out

            progress = False
            for root, mem in groups.items():
                if root == main:
                    continue
                spot = None
                for kind, n in mem:
                    if kind != "isl" or spot:
                        continue
                    lid, ps, k = it["isl"][n]
                    other = pcbnew.B_Cu if lid == pcbnew.F_Cu else pcbnew.F_Cu
                    bb = ps.Outline(k).BBox()
                    x0, y0 = B.to_rel(bb.GetOrigin())
                    x1, y1 = B.to_rel(bb.GetEnd())
                    y = round(y0 / 0.25) * 0.25
                    while y <= y1 and not spot:
                        x = round(x0 / 0.25) * 0.25
                        while x <= x1:
                            probes = [B.P(x + dx, y + dy) for dx, dy in
                                      ((0, 0), (0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45))]
                            i, j = self.g.ij(x, y)
                            if all(ps.Contains(q, k) for q in probes) and \
                                    any(all(mp.Contains(q, mk) for q in probes) for mp, mk in main_isl[other]) and \
                                    self.via_spacing_ok(x, y) and self.g.via_ok(i, j, nid, self.vdisk, self.via_layers):
                                spot = (x, y)
                                break
                            x += 0.25
                        y += 0.25
                if spot:
                    self.add_via("/GND", *spot)
                    done.append(("via", spot))
                    progress = True
                    continue
                srcs = [n for n in nodes(mem) if self.g.passable(n[0], n[2] * self.g.nx + n[1], nid)]
                tgts = set(nodes(groups[main]))
                res = self.g.astar(nid, srcs, tgts, layer_cost={L: 1.0 for L in self.via_layers}, via_cost=10.0,
                                   via_disk=self.vdisk, via_layers=self.via_layers,
                                   extra_disk=_disk((0.25 - B.BASE_W) / 2 / B.GRID_PITCH),
                                   max_expand=1_500_000, h_weight=1.5) if srcs else None
                if res is not None:
                    self.commit_path("/GND", res[0], 0.25)
                    done.append(("track", self.g.xy(res[0][0][1], res[0][0][2])))
                    progress = True
            if not progress:
                break
        B.fill_zones(self.board)
        groups, main, it = self.gnd_clusters()
        left = []
        for root, mem in groups.items():
            if root != main:
                left.append([f"{it['pad'][n][0]}.{it['pad'][n][1].GetNumber()}" for kind, n in mem if kind == "pad"] +
                            [B.to_rel(it["via"][n].GetPosition()) for kind, n in mem if kind == "via"])
        return {"added": done, "isolated": left}

    def stitch_gnd(self):
        """GND vias tying the two pours together: board perimeter, then a 2 mm grid wherever both
        layers are free (also under the module, between the bottom-side tracks)."""
        pts = []
        x = 1.5
        while x < BW - 0.5:
            pts += [(x, 0.75), (x, BH - 0.75)]
            x += 2.0
        y = 1.5
        while y < BH - 1.0:
            pts += [(BW - 0.75, y), (0.75, y)]
            y += 2.0
        y = 2.5
        while y < BH - 2.0:
            x = 2.5
            while x < BW - 2.0:
                pts.append((x, y))
                x += 2.0
            y += 2.0
        nid = self.nid["/GND"]
        n = 0
        for x, y in pts:
            i, j = self.g.ij(x, y)
            x, y = self.g.xy(i, j)
            if self.via_spacing_ok(x, y) and self.g.via_ok(i, j, nid, self.vdisk, self.via_layers):
                self.add_via("/GND", x, y)
                n += 1
        return n

    def run(self):
        self.vdisk = _disk((B.VIA[0] / 2 - B.BASE_W / 2 + 0.02) / B.GRID_PITCH)
        self.vdisk_pwr = _disk((B.VIA_PWR[0] / 2 - B.BASE_W / 2 + 0.02) / B.GRID_PITCH)
        self.plane_disk = _disk((B.PLANE_W - B.BASE_W) / 2 / B.GRID_PITCH)
        self.add_obstacles()
        self.route_power_fixed()
        self.module_escapes()
        g2 = self.connect_plane("/GND")
        print("  GND pad vias", g2, flush=True)
        ok = self.route_rail()
        print(f"  routed {B.RAIL:14s} {'ok' if ok else 'FAILED'}", flush=True)
        for net, width, lc in B.SIGNALS:
            ok = self.route_net(net, width, lc)
            print(f"  routed {net:14s} {'ok' if ok else 'FAILED'}", flush=True)
        g3 = self.connect_plane("/GND", test_pads=True)
        print("  GND test pad vias", g3, flush=True)
        print("  cleanup (splits, pruned, vias):", self.cleanup(), flush=True)
        return {"GND vias": g2, "stitch": self.stitch_gnd()}


def add_zones(board, netinfo):
    full = [(0, 0), (BW, 0), (BW, BH), (0, BH)]
    for lid in (pcbnew.F_Cu, pcbnew.B_Cu):
        B.make_zone(board, lid, netinfo["/GND"], full, 0, name="GND")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-route", action="store_true")
    ap.add_argument("--no-drc", action="store_true")
    args = ap.parse_args()
    board, fps, netinfo, nets = B.build(args)
    for pad in fps["U1"].Pads():
        if pad.GetNumber() == "29":
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    for m in B.legalise(fps):
        print("legaliser moved", m)
    for o in B.courtyard_overlaps(fps):
        if not (o[0] == "U1" and o[1] == "EDGE"):
            print("courtyard overlap:", o)
    if not args.no_route:
        r = WroomRouter(board, fps, netinfo)
        info = r.run()
        print("routing:", info, r.stats)
        for f in r.failed:
            print("  FAILED", f)
    add_zones(board, netinfo)
    if not args.no_route:
        print("GND repair:", r.repair_gnd(), flush=True)
    pcbnew.SaveBoard(str(B.PCB), board)
    B.PCB.write_text(B.patch_stackup(B.PCB.read_text()))
    print("saved", B.PCB.relative_to(ROOT))
    if not args.no_drc:
        _, summary = B.run_drc()
        for k, v in sorted(summary.items()):
            print(f"  DRC {k[0]:12s} {k[1]:35s} {v}")


if __name__ == "__main__":
    main()

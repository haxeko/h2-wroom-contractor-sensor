"""
Small grid-based maze router (pure Python, no dependencies) used by build_pcb.py.

Model
-----
* The board is sampled on a square grid (default 0.05 mm) for each *routing* layer.
* Every copper object (pad, track, via, keep-out) is rasterised once into a per-layer
  `owner` array: 0 = free, net id = only this net may use the node, -1 = nobody may.
  A node is marked when it lies closer than (object clearance + half the routed track width
  + margin) to the object, so a track *centre line* that only visits passable nodes keeps the
  clearance (the margin covers the grid quantisation of diagonal steps).
* Rule areas are a second per-layer array (`keep`) holding a rule id; a rule lists the nets that
  are still allowed inside it (e.g. "nothing but XTAL_N/XTAL_P_X under the crystal").
* A* over (layer, i, j, direction) with octile moves, a turn penalty, per-layer cost, via cost.
  Wider tracks are handled by testing a disk of extra radius around every visited node.
* Multi-pin nets are routed as a tree: each further pad is connected to the nearest node of the
  already routed tree (pads + previous paths).
* "Plane" connections (GND, 3V2) search from the pad to the nearest node where a via fits.

The router knows nothing about KiCad: build_pcb.py feeds it primitive shapes and turns the
resulting node paths into PCB_TRACK / PCB_VIA objects.
"""
import heapq
import math
from array import array

SQ2 = math.sqrt(2.0)
# 8 directions: (di, dj)
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _disk(radius_cells):
    r = radius_cells
    out = []
    ir = int(math.ceil(r))
    for dj in range(-ir, ir + 1):
        for di in range(-ir, ir + 1):
            if di * di + dj * dj <= r * r + 1e-9:
                out.append((di, dj))
    return out


class Rule:
    def __init__(self, name, allowed_nets=()):
        self.name = name
        self.allowed = set(allowed_nets)


class Grid:
    def __init__(self, x0, y0, x1, y1, pitch, layers, base_half_width, margin=0.03):
        self.x0, self.y0, self.pitch = x0, y0, pitch
        self.nx = int(round((x1 - x0) / pitch)) + 1
        self.ny = int(round((y1 - y0) / pitch)) + 1
        self.layers = list(layers)
        n = self.nx * self.ny
        self.owner = [array("i", bytes(4 * n)) for _ in self.layers]
        self.keep = [array("h", bytes(2 * n)) for _ in self.layers]
        self.padmask = [bytearray(n) for _ in self.layers]   # 1 inside pad copper (no via-in-pad)
        self.holemask = bytearray(n)                          # 1 = too close to an existing hole
        self.rules = [None]
        self._combo = {}
        self.base_half = base_half_width
        self.margin = margin

    # ------------------------------------------------------------------ coordinates
    def ij(self, x, y):
        return int(round((x - self.x0) / self.pitch)), int(round((y - self.y0) / self.pitch))

    def xy(self, i, j):
        return round(self.x0 + i * self.pitch, 4), round(self.y0 + j * self.pitch, 4)

    def li(self, layer):
        return self.layers.index(layer)

    def _range(self, xa, ya, xb, yb):
        i0 = max(0, int(math.floor((xa - self.x0) / self.pitch)))
        j0 = max(0, int(math.floor((ya - self.y0) / self.pitch)))
        i1 = min(self.nx - 1, int(math.ceil((xb - self.x0) / self.pitch)))
        j1 = min(self.ny - 1, int(math.ceil((yb - self.y0) / self.pitch)))
        return i0, j0, i1, j1

    def _claim(self, L, idx, net):
        o = self.owner[L]
        v = o[idx]
        if v == 0:
            o[idx] = net
        elif v != net:
            o[idx] = -1

    # ------------------------------------------------------------------ rasterisation
    def add_rect(self, layer, cx, cy, hw, hh, net, clearance, pad=False):
        """Axis aligned rectangle (half sizes hw, hh) of copper owned by `net` (net=-1: obstacle)."""
        L = self.li(layer)
        infl = clearance + self.base_half + self.margin
        i0, j0, i1, j1 = self._range(cx - hw - infl, cy - hh - infl, cx + hw + infl, cy + hh + infl)
        for j in range(j0, j1 + 1):
            y = self.y0 + j * self.pitch
            dy = max(abs(y - cy) - hh, 0.0)
            if dy > infl:
                continue
            base = j * self.nx
            for i in range(i0, i1 + 1):
                x = self.x0 + i * self.pitch
                dx = max(abs(x - cx) - hw, 0.0)
                d2 = dx * dx + dy * dy
                if d2 < infl * infl:
                    self._claim(L, base + i, net)
                    if pad and dx == 0.0 and dy == 0.0:
                        self.padmask[L][base + i] = 1

    def add_circle(self, layer, cx, cy, r, net, clearance):
        L = self.li(layer)
        infl = r + clearance + self.base_half + self.margin
        i0, j0, i1, j1 = self._range(cx - infl, cy - infl, cx + infl, cy + infl)
        for j in range(j0, j1 + 1):
            y = self.y0 + j * self.pitch
            base = j * self.nx
            for i in range(i0, i1 + 1):
                x = self.x0 + i * self.pitch
                if (x - cx) ** 2 + (y - cy) ** 2 < infl * infl:
                    self._claim(L, base + i, net)

    def add_segment(self, layer, xa, ya, xb, yb, half_w, net, clearance):
        L = self.li(layer)
        infl = half_w + clearance + self.base_half + self.margin
        i0, j0, i1, j1 = self._range(min(xa, xb) - infl, min(ya, yb) - infl, max(xa, xb) + infl, max(ya, yb) + infl)
        vx, vy = xb - xa, yb - ya
        vv = vx * vx + vy * vy
        for j in range(j0, j1 + 1):
            y = self.y0 + j * self.pitch
            base = j * self.nx
            for i in range(i0, i1 + 1):
                x = self.x0 + i * self.pitch
                if vv == 0:
                    t = 0.0
                else:
                    t = max(0.0, min(1.0, ((x - xa) * vx + (y - ya) * vy) / vv))
                px, py = xa + t * vx - x, ya + t * vy - y
                if px * px + py * py < infl * infl:
                    self._claim(L, base + i, net)

    def _set_rule(self, k, idx, rid):
        """Overlapping rule areas: the node gets a rule allowing only the nets allowed by both."""
        old = k[idx]
        if old == 0 or old == rid:
            k[idx] = rid
            return
        key = (min(old, rid), max(old, rid))
        cid = self._combo.get(key)
        if cid is None:
            a, b = self.rules[old], self.rules[rid]
            self.rules.append(Rule(f"{a.name}+{b.name}", a.allowed & b.allowed))
            cid = len(self.rules) - 1
            self._combo[key] = cid
        k[idx] = cid

    def add_rule_rect(self, layers, xa, ya, xb, yb, rule):
        """Rule area (keep-out) on the given layers: only rule.allowed nets may enter."""
        self.rules.append(rule)
        rid = len(self.rules) - 1
        for layer in layers:
            L = self.li(layer)
            i0, j0, i1, j1 = self._range(xa, ya, xb, yb)
            k = self.keep[L]
            for j in range(j0, j1 + 1):
                base = j * self.nx
                for i in range(i0, i1 + 1):
                    self._set_rule(k, base + i, rid)
        return rid

    def add_rule_poly(self, layers, pts, rule, inflate=None):
        """Rule area given by a polygon (list of (x, y)). Nodes closer than `inflate` (default: half the
        base track width + margin) to the area are included, so track copper stays outside it."""
        if inflate is None:
            inflate = self.base_half + self.margin + 0.06
        self.rules.append(rule)
        rid = len(self.rules) - 1
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        i0, j0, i1, j1 = self._range(min(xs) - inflate, min(ys) - inflate, max(xs) + inflate, max(ys) + inflate)
        n = len(pts)
        offs = [(0.0, 0.0)]
        for rr in (inflate * 0.5, inflate):
            for k in range(16):
                a = k * math.pi / 8
                offs.append((rr * math.cos(a), rr * math.sin(a)))

        def inside(x, y):
            r = False
            for a in range(n):
                xa, ya = pts[a]
                xb, yb = pts[(a + 1) % n]
                if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
                    r = not r
            return r

        hits = []
        for j in range(j0, j1 + 1):
            y = self.y0 + j * self.pitch
            base = j * self.nx
            for i in range(i0, i1 + 1):
                x = self.x0 + i * self.pitch
                if any(inside(x + dx, y + dy) for dx, dy in offs):
                    hits.append(base + i)
        for layer in layers:
            k = self.keep[self.li(layer)]
            for idx in hits:
                self._set_rule(k, idx, rid)
        return rid

    # ------------------------------------------------------------------ queries
    def passable(self, L, idx, net):
        v = self.owner[L][idx]
        if v != 0 and v != net:
            return False
        r = self.keep[L][idx]
        if r and net not in self.rules[r].allowed:
            return False
        return True

    def disk_ok(self, L, i, j, net, disk):
        nx, ny = self.nx, self.ny
        o = self.owner[L]
        k = self.keep[L]
        rules = self.rules
        for di, dj in disk:
            ii, jj = i + di, j + dj
            if ii < 0 or jj < 0 or ii >= nx or jj >= ny:
                return False
            idx = jj * nx + ii
            v = o[idx]
            if v != 0 and v != net:
                return False
            r = k[idx]
            if r and net not in rules[r].allowed:
                return False
        return True

    def add_hole(self, cx, cy, keep):
        """Forbid new via centres closer than `keep` to an existing drilled hole."""
        i0, j0, i1, j1 = self._range(cx - keep, cy - keep, cx + keep, cy + keep)
        for j in range(j0, j1 + 1):
            y = self.y0 + j * self.pitch
            base = j * self.nx
            for i in range(i0, i1 + 1):
                x = self.x0 + i * self.pitch
                if (x - cx) ** 2 + (y - cy) ** 2 < keep * keep:
                    self.holemask[base + i] = 1

    def via_ok(self, i, j, net, via_disk, via_layers):
        if self.holemask[j * self.nx + i]:
            return False
        for L in via_layers:
            if not self.disk_ok(L, i, j, net, via_disk):
                return False
            if self.padmask[L][j * self.nx + i]:
                return False
        return True

    # ------------------------------------------------------------------ search
    def astar(self, net, sources, targets, *, layer_cost, via_cost, via_disk, via_layers,
              extra_disk=None, window=None, turn_cost=3.0, max_expand=2_000_000, via_targets=False,
              via_filter=None, h_weight=1.25):
        """sources: iterable of (L, i, j); targets: set of (L, i, j) (ignored if via_targets).
        layer_cost: dict L -> cost multiplier (layers missing are not used).
        via_targets: stop at the first node where a via can be placed (plane connection);
        via_filter(i, j) -> bool can restrict where such a via may go.
        h_weight > 1 = weighted A* (faster, paths within a few % of optimal).
        Returns (path, ends_with_via) with path = [(L, i, j), ...] from source to target, or None."""
        nx, ny = self.nx, self.ny
        if window is None:
            wi0, wj0, wi1, wj1 = 0, 0, nx - 1, ny - 1
        else:
            wi0, wj0, wi1, wj1 = window
        if not via_targets:
            tl = list(targets)
            ti0 = min(t[1] for t in tl)
            ti1 = max(t[1] for t in tl)
            tj0 = min(t[2] for t in tl)
            tj1 = max(t[2] for t in tl)
            tset = set(targets)
        hw = min(layer_cost.values()) * (1.0 if via_targets else h_weight)
        allowed = [set()] + [r.allowed for r in self.rules[1:]]
        owner, keep = self.owner, self.keep
        multi = len(layer_cost) > 1
        dirs = [(nd, di, dj, SQ2 if (di and dj) else 1.0) for nd, (di, dj) in enumerate(DIRS)]
        tpen = [0.0, turn_cost, 2.5 * turn_cost, None, None, None, 2.5 * turn_cost, turn_cost]
        pcache = {}

        def ok(L, idx):
            key = L * 10_000_000 + idx
            r = pcache.get(key)
            if r is None:
                v = owner[L][idx]
                if v != 0 and v != net:
                    r = False
                else:
                    kk = keep[L][idx]
                    r = (kk == 0) or (net in allowed[kk])
                pcache[key] = r
            return r

        def h(i, j):
            if via_targets:
                return 0.0
            dx = ti0 - i if i < ti0 else (i - ti1 if i > ti1 else 0)
            dy = tj0 - j if j < tj0 else (j - tj1 if j > tj1 else 0)
            if dx < dy:
                return (dy - dx + SQ2 * dx) * hw
            return (dx - dy + SQ2 * dy) * hw

        openh = []
        g = {}
        parent = {}
        vcache = {}
        ecache = {}
        cnt = 0
        push = heapq.heappush
        pop = heapq.heappop
        for (L, i, j) in sources:
            if L not in layer_cost:
                continue
            st = (L, i, j, 8)
            g[st] = 0.0
            parent[st] = None
            push(openh, (h(i, j), cnt, st))
            cnt += 1
        expanded = 0
        while openh:
            f, _, st = pop(openh)
            L, i, j, d = st
            gs = g[st]
            if f - h(i, j) > gs + 1e-9:
                continue
            if via_targets:
                if (via_filter is None or via_filter(i, j)) and self.via_ok(i, j, net, via_disk, via_layers):
                    return self._trace(parent, st), True
            elif (L, i, j) in tset:
                return self._trace(parent, st), False
            expanded += 1
            if expanded > max_expand:
                return None
            lc = layer_cost[L]
            rowj = j * nx
            for nd, di, dj, base in dirs:
                if d != 8:
                    tc = tpen[(nd - d) % 8]
                    if tc is None:
                        continue
                else:
                    tc = 0.0
                ii = i + di
                jj = j + dj
                if ii < wi0 or jj < wj0 or ii > wi1 or jj > wj1:
                    continue
                idx = jj * nx + ii
                if not ok(L, idx):
                    continue
                if di and dj and (not ok(L, rowj + ii) or not ok(L, jj * nx + i)):
                    continue
                if extra_disk is not None:
                    ek = L * 10_000_000 + idx
                    eok = ecache.get(ek)
                    if eok is None:
                        eok = self.disk_ok(L, ii, jj, net, extra_disk)
                        ecache[ek] = eok
                    if not eok:
                        continue
                ns = (L, ii, jj, nd)
                ng = gs + base * lc + tc
                if ng < g.get(ns, 1e30):
                    g[ns] = ng
                    parent[ns] = st
                    push(openh, (ng + h(ii, jj), cnt, ns))
                    cnt += 1
            if multi:
                key = rowj + i
                vok = vcache.get(key)
                if vok is None:
                    vok = self.via_ok(i, j, net, via_disk, via_layers)
                    vcache[key] = vok
                if vok:
                    for L2 in layer_cost:
                        if L2 == L:
                            continue
                        ns = (L2, i, j, 8)
                        ng = gs + via_cost
                        if ng < g.get(ns, 1e30):
                            g[ns] = ng
                            parent[ns] = st
                            push(openh, (ng + h(i, j), cnt, ns))
                            cnt += 1
        return None

    @staticmethod
    def _trace(parent, s):
        out = []
        while s is not None:
            out.append((s[0], s[1], s[2]))
            s = parent[s]
        out.reverse()
        return out


def path_to_segments(path):
    """Compress a node path into [(L, (i0, j0), (i1, j1))] straight runs and via positions."""
    segs, vias = [], []
    if not path:
        return segs, vias
    start = path[0]
    prev = path[0]
    pdir = None
    for node in path[1:]:
        if node[0] != prev[0]:
            if (prev[1], prev[2]) != (start[1], start[2]):
                segs.append((start[0], (start[1], start[2]), (prev[1], prev[2])))
            vias.append((prev[1], prev[2]))
            start = node
            pdir = None
            prev = node
            continue
        d = (node[1] - prev[1], node[2] - prev[2])
        if pdir is not None and d != pdir:
            segs.append((start[0], (start[1], start[2]), (prev[1], prev[2])))
            start = prev
        pdir = d
        prev = node
    if (prev[1], prev[2]) != (start[1], start[2]):
        segs.append((start[0], (start[1], start[2]), (prev[1], prev[2])))
    return segs, vias

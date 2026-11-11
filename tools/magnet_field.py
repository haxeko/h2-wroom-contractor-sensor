#!/usr/bin/env python3
"""
Magnetic field of a block (cuboid) NdFeB magnet at the Hall sensor, vs. the gap between
the sensor housing and the magnet housing.  Used to size the magnet for:

  Option A: DRV5032FA/FB omnipolar switch (same thresholds)  (BOP 1.5/3.0/4.8 mT, BRP 0.5/1.5/3.0 mT min/typ/max)
  Option B: DRV5012 latch + bias magnet (BOP +0.6..+3.3 mT, BRP -3.3..-0.6 mT)

Model: uniformly magnetised cuboid = two charged sheets (+M on the north face, -M on the south
face); B = Br/(4*pi) * integral of (r - r')/|r - r'|^3 over the faces (numerical 2-D Gauss
quadrature). Valid outside the magnet. Validated against the closed-form on-axis formula.

Axes: x along the door edge (length of both housings), y = horizontal direction from the magnet
towards the sensor, z = vertical (perpendicular to the mounting surface and to the PCB).
The SOT-23 / X2SON Hall element of the DRV5032 senses Bz (field perpendicular to the package
top, i.e. perpendicular to the PCB). The TO-92 version senses the field through its flat face.

Usage:  python3 tools/magnet_field.py
"""
import math

import numpy as np

MU0 = 4e-7 * math.pi
GAUSS_N = 24
_gx, _gw = np.polynomial.legendre.leggauss(GAUSS_N)


def _face_field(px, py, pz, x0, x1, y0, y1, zf):
    """Field (per unit Br) of a uniformly charged rectangle in the plane z=zf, charge density 1."""
    xs = 0.5 * (x1 - x0) * _gx + 0.5 * (x1 + x0)
    ys = 0.5 * (y1 - y0) * _gx + 0.5 * (y1 + y0)
    wx = 0.5 * (x1 - x0) * _gw
    wy = 0.5 * (y1 - y0) * _gw
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    W = np.outer(wx, wy)
    dx, dy, dz = px - X, py - Y, pz - zf
    r3 = (dx * dx + dy * dy + dz * dz) ** 1.5
    return np.array([np.sum(W * dx / r3), np.sum(W * dy / r3), np.sum(W * dz / r3)]) / (4 * math.pi)


def block_field(point, size, br, axis="z", subdiv=4):
    """B (tesla, vector) of a block magnet centred at the origin.
    size = (Lx, Ly, Lz) in metres, magnetised along +axis ('z' or 'y'). Faces are subdivided
    for accuracy close to the magnet."""
    px, py, pz = point
    lx, ly, lz = size
    if axis == "y":  # rotate: treat y as the magnetisation axis
        b = block_field((px, pz, py), (lx, lz, ly), br, "z", subdiv)
        return np.array([b[0], b[2], b[1]])
    total = np.zeros(3)
    for sign, zf in ((+1, lz / 2), (-1, -lz / 2)):
        for i in range(subdiv):
            for j in range(subdiv):
                x0 = -lx / 2 + lx * i / subdiv
                y0 = -ly / 2 + ly * j / subdiv
                total += sign * _face_field(px, py, pz, x0, x0 + lx / subdiv, y0, y0 + ly / subdiv, zf)
    return br * total


def on_axis_closed_form(z, size, br):
    """Bz on the magnetisation axis at distance z from the north face (supplier formula)."""
    L, W, D = size
    def f(t):
        return math.atan(L * W / (2 * t * math.sqrt(4 * t * t + L * L + W * W)))
    return br / math.pi * (f(z) - f(z + D))


def validate():
    size = (0.010, 0.005, 0.003)
    for z in (0.002, 0.005, 0.010, 0.020):
        num = block_field((0, 0, size[2] / 2 + z), size, 1.2)[2]
        ref = on_axis_closed_form(z, size, 1.2)
        assert abs(num - ref) / ref < 0.01, (z, num, ref)
    return True


# ------------------------------------------------------------------------- geometry
# distances in metres
SENSOR_TO_WALL = 0.0025   # Hall die -> outer surface of the sensor housing (wall 1.2 + 1.3 mm)
MAGNET_WALL = 0.0012      # magnet housing wall
DH = 0.0                  # vertical offset sensor die - magnet centre (design target 0)

MAGNETS = [
    # name, (Lx along door edge, Ly towards sensor, Lz vertical), Br (T), magnetisation axis
    ("N35 10x5x3 (truc Z)", (0.010, 0.005, 0.003), 1.19, "z"),
    ("N35 15x5x3 (truc Z)", (0.015, 0.005, 0.003), 1.19, "z"),
    ("N35 20x6x3 (truc Z)", (0.020, 0.006, 0.003), 1.19, "z"),
    ("N52 15x5x3 (truc Z)", (0.015, 0.005, 0.003), 1.44, "z"),
]

THRESHOLDS = [
    ("BOP max 4.8 mT (đóng chắc chắn)", 4.8e-3),
    ("BOP typ 3.0 mT", 3.0e-3),
    ("BRP typ 1.5 mT", 1.5e-3),
    ("BRP min 0.5 mT (mở chắc chắn)", 0.5e-3),
]


def bz_at_gap(gap, size, br, axis="z", dh=DH, dx=0.0):
    y = SENSOR_TO_WALL + gap + MAGNET_WALL + size[1] / 2
    b = block_field((dx, y, dh), size, br, axis)
    return b[2] if axis == "z" else b[1]


def gap_for_threshold(th, size, br, axis="z", dh=DH, dx=0.0):
    lo, hi = 0.0, 0.20
    if abs(bz_at_gap(lo, size, br, axis, dh, dx)) < th:
        return None
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if abs(bz_at_gap(mid, size, br, axis, dh, dx)) >= th:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    validate()
    print("Mô hình đã kiểm chứng với công thức trục từ dạng đóng (sai số < 1 %).\n")
    print(f"Giả định: die Hall cách mặt ngoài vỏ cảm biến {SENSOR_TO_WALL*1e3:.1f} mm, "
          f"vách vỏ nam châm {MAGNET_WALL*1e3:.1f} mm, lệch cao die-tâm nam châm {DH*1e3:.1f} mm.\n")

    print("### |Bz| tại cảm biến theo khe hở giữa hai vỏ (mT)\n")
    gaps = [0, 5, 10, 15, 20, 25, 30, 40]
    print("| Nam châm | " + " | ".join(f"{g} mm" for g in gaps) + " |")
    print("|---|" + "---|" * len(gaps))
    for name, size, br, axis in MAGNETS:
        vals = [abs(bz_at_gap(g / 1000, size, br, axis)) * 1e3 for g in gaps]
        print(f"| {name} | " + " | ".join(f"{v:.2f}" for v in vals) + " |")

    print("\n### Khe hở tại đó |Bz| bằng ngưỡng DRV5032FA/FB (mm)\n")
    print("| Nam châm | " + " | ".join(t[0] for t in THRESHOLDS) + " |")
    print("|---|" + "---|" * len(THRESHOLDS))
    for name, size, br, axis in MAGNETS:
        cells = []
        for _, th in THRESHOLDS:
            g = gap_for_threshold(th, size, br, axis)
            cells.append("—" if g is None else f"{g*1e3:.1f}")
        print(f"| {name} | " + " | ".join(cells) + " |")

    name, size, br, axis = MAGNETS[1]
    print(f"\n### Dung sai lắp đặt - {name}, khe 10 mm (|Bz| mT)\n")
    print("| Lệch dọc cạnh cửa dx | Lệch cao dh = -4 mm | dh = 0 | dh = +4 mm |")
    print("|---|---|---|---|")
    for dx in (0, 5, 10):
        row = [abs(bz_at_gap(0.010, size, br, axis, dh / 1000, dx / 1000)) * 1e3 for dh in (-4, 0, 4)]
        print(f"| {dx} mm | " + " | ".join(f"{v:.2f}" for v in row) + " |")

    # Option B: latch + bias magnet
    print("\n### Phương án B (DRV5012 latch): nam châm phụ phân cực trong vỏ cảm biến\n")
    bias = 4.5e-3
    need = 3.3e-3 + bias
    g = gap_for_threshold(need, size, br, axis)
    print(f"Bias -{bias*1e3:.1f} mT (> |BRP max| 3.3 mT) -> nam châm cửa phải tạo >= {need*1e3:.1f} mT "
          f"(BOP max 3.3 + bias). Với {name}: khe đóng tối đa đảm bảo = "
          f"{'—' if g is None else f'{g*1e3:.1f} mm'} (so với Phương án A ở 4.8 mT: "
          f"{gap_for_threshold(4.8e-3, size, br, axis)*1e3:.1f} mm), và phụ thuộc chiều cực N/S.")


if __name__ == "__main__":
    main()

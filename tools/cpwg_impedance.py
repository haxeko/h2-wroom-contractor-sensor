#!/usr/bin/env python3
"""
Grounded coplanar waveguide (GCPW / CPWG) impedance - quasi-static closed form
(Wadell, "Transmission Line Design Handbook", eq. 3.4.3.1; Ghione & Naldi), conductor
thickness and solder mask neglected -> real impedance is ~1-3 ohm LOWER (thick copper) and
~1-2 ohm LOWER again with solder mask. ALWAYS confirm with the PCB fab's field solver
(e.g. JLCPCB impedance calculator / Polar SI9000) and order impedance control.

Usage: python3 tools/cpwg_impedance.py
"""
import math


def ellipk(m):
    """Complete elliptic integral of the first kind K(m), m = k^2 (AGM method)."""
    a, b = 1.0, math.sqrt(1.0 - m)
    for _ in range(40):
        a, b = 0.5 * (a + b), math.sqrt(a * b)
    return math.pi / (2.0 * a)


def kk_ratio(k):
    """K(k)/K(k')"""
    return ellipk(k * k) / ellipk(1.0 - k * k)


def cpwg_z0(w, s, h, er):
    """w: trace width, s: gap to coplanar ground, h: dielectric height to the ground plane."""
    k = w / (w + 2 * s)
    k1 = math.tanh(math.pi * w / (4 * h)) / math.tanh(math.pi * (w + 2 * s) / (4 * h))
    r = kk_ratio(k)       # K(k)/K(k')
    r1 = kk_ratio(k1)     # K(k1)/K(k1')
    #   eeff = (1 + er * K(k')/K(k) * K(k1)/K(k1')) / (1 + K(k')/K(k) * K(k1)/K(k1'))
    #   Z0   = 60*pi/sqrt(eeff) / (K(k)/K(k') + K(k1)/K(k1'))
    t = (1.0 / r) * r1
    eeff = (1.0 + er * t) / (1.0 + t)
    z0 = 60.0 * math.pi / math.sqrt(eeff) / (r + r1)
    return z0, eeff


def solve_width(s, h, er, target=50.0):
    lo, hi = 0.02, 5.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        z, _ = cpwg_z0(mid, s, h, er)
        if z > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    print("### Kiểm tra với stack-up tham chiếu của Espressif (prepreg 7628 8.22 mil, Dk 4.6)\n")
    z, e = cpwg_z0(12.6, 12.2, 8.22, 4.6)
    print(f"w = 12.6 mil, gap = 12.2 mil -> Z0 = {z:.1f} ohm (eeff {e:.2f}); Espressif công bố 50 ohm "
          "(đã tính đồng dày + solder mask)\n")

    cases = [
        ("4 lớp 1.0 mm, L1-L2 prepreg 7628 ~0.21 mm, er 4.4", 0.21, 4.4, [0.20, 0.25, 0.30]),
        ("4 lớp 1.0 mm, L1-L2 prepreg 3313 ~0.10 mm, er 4.1", 0.10, 4.1, [0.15, 0.20, 0.25]),
        ("2 lớp 0.8 mm, er 4.5", 0.76, 4.5, [0.15, 0.20, 0.25]),
        ("2 lớp 1.0 mm, er 4.5", 0.96, 4.5, [0.15, 0.20, 0.25]),
    ]
    # The ideal formula reads ~5.5 ohm high for Espressif's verified 50-ohm geometry
    # (copper thickness + solder mask). Use the same offset as an empirical calibration.
    target = 50.0 * z / 50.0
    print(f"### Bề rộng đường GCPW cho ~50 ohm thực tế (mục tiêu công thức {target:.1f} ohm, "
          "đã hiệu chỉnh theo tham chiếu Espressif)\n")
    print("| Stack-up | h (mm) | er | gap 1 | w | gap 2 | w | gap 3 | w |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name, h, er, gaps in cases:
        cells = []
        for s in gaps:
            w = solve_width(s, h, er, target)
            cells += [f"{s:.2f}", f"{w:.2f}"]
        print(f"| {name} | {h} | {er} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()

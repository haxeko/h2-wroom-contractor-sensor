#!/usr/bin/env python3
"""
Study: can a CR2450 coin cell power the ESP32-H2-WROOM-02C board? (docs/12 section 8)

Answer: only for the first ~250 mAh (40 %) of the cell, whatever the capacitors - which is why both
boards use a CR123A. The script is kept to reproduce the numbers.

Circuit studied (rev B of the coin-cell board, same idea as the CR2032 button design):
    cell --R_int--+-- Q1 --+-- VBAT ---- TPS63900 (no input current limit) ---- 3V2 ---- module
                           |
                      C_bulk (MLCC, on the BATTERY side of the converter)

Why the bulk capacitor sits on the battery side: the buck-boost keeps 3.2 V while its input falls
to the UVLO (1.8 V), so the capacitor may swing ~1.1 V. On the 3V2 side only ~0.2 V is allowed
(module minimum 3.0 V) and the capacitor has to be ~5x larger for the same pulse.

Model
  * Cell: open-circuit voltage + internal resistance, both versus the capacity already used.
    Energizer CR2450 datasheet, "Internal Resistance Characteristics", pulse test at 21 degC
    (2 s pulses of 9 mA on a 0.39 mA background). The 2 s value is used for every pulse length,
    which is pessimistic for the millisecond radio frames (never measured on hardware).
  * TPS63900 (SLVSET3D): constant-power load, P_in = I_rail * 3.2 V / eta; eta 0.90 (fig. 8-7),
    0.87 at VIN 1.8 V. Stops when VIN < UVLO: the rail collapses and the module resets.
  * Module currents at 3.3 V (ESP32-H2-WROOM-02C datasheet v1.2): 802.15.4 RX 26 mA,
    TX 0 dBm 36 mA (table 13); CPU running at 64 MHz 13 mA, 96 MHz 17 mA (table 14).
  * Event timings are ESTIMATES (802.15.4 at 250 kb/s: 127-byte frame = 4.3 ms). The Thread
    re-attach keeps the receiver on for 0.75 s (parent request to routers) and then 1.25 s
    (routers + REEDs): no MLCC can carry that, the cell alone has to.

Output: for each bulk capacitor option, the capacity (mAh used) up to which every event keeps
VIN above the UVLO margin, and the same for the rev A circuit (25 mA input limit + 6 x 220 uF on
the 3V4 rail), which cannot keep the rail up during a continuous receive.

Usage: python3 tools/coin_cell_buffer.py [--cpu-mhz 64|96] [--tx-ma 36] [--detail]
"""
import argparse

V_OUT = 3.2
V_UVLO_MARGIN = 1.80      # TPS63900 UVLO: 1.75 V typ rising, 1.65 V typ falling; keep VIN >= 1.8 V
V_MODULE_MIN = 3.0        # ESP32-H2-WROOM-02C VDD33 min (datasheet table 10)
RX, SLEEP = 26.0, 0.03

# Energizer CR2450 (620 mAh to 2.0 V at 7.5 kOhm), read from the datasheet chart
CELL_IR = [(0, 10.0), (100, 10.5), (200, 12.0), (250, 20.0), (300, 30.0), (350, 40.0),
           (400, 60.0), (450, 90.0), (480, 120.0)]
CELL_VOC = [(0, 2.97), (300, 2.95), (400, 2.93), (450, 2.90), (500, 2.85)]

# effective capacitance on VBAT at ~3 V DC bias (to measure): C1 + C2 = 2 x 22 uF 0603 ~ 18 uF,
# one 220 uF 6.3 V X5R 1210 ~ 130 uF, one 100 uF 6.3 V X5R 1206 ~ 45 uF
C_BASE = 18.0
BULK_OPTIONS = [("khong co tu lon", 0.0), ("2 x 100 uF 1206", 90.0), ("1 x 220 uF 1210", 130.0),
                ("2 x 220 uF 1210", 260.0), ("4 x 220 uF 1210", 520.0), ("6 x 220 uF 1210", 780.0)]


def interp(table, x):
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def eta(v_in):
    return 0.90 if v_in >= 2.5 else 0.87 + 0.03 * max(0.0, v_in - 1.8) / 0.7


def profiles(cpu, tx):
    """(name, [(duration ms, rail current mA), ...])"""
    poll = [(2, cpu), (1.3, RX), (1.2, tx), (0.9, RX), (3, cpu)]
    report = [(1.3, RX), (4.3, tx), (0.9, RX), (1.0, cpu)]
    gap = lambda ms: [(ms, SLEEP)]                                   # noqa: E731
    return [
        ("poll Thread (moi 15 s)", poll),
        ("dong/mo cua: 2 bao cao + 2 poll nhanh", [(5, cpu)] + report * 2 + gap(500) + poll + gap(500) + poll),
        ("khoi phuc subscription (CPU 300 ms + 4 khung)", [(300, cpu)] + (report + [(100, cpu)]) * 4),
        ("khoi dong (CPU 400 ms)", [(400, cpu)]),
        ("Thread re-attach (thu lien tuc 0.75 s)", [(4.3, tx), (750, RX)]),
        ("Thread re-attach day du (0.75 s + 1.25 s)", [(4.3, tx), (750, RX), (4.3, tx), (1250, RX)]),
    ]


def simulate_vbat(seq, c_uf, used_mah, dt=0.005):
    """Bulk capacitor on VBAT, no input current limit. Returns (min VBAT, peak cell current mA)."""
    v_oc, r_int = interp(CELL_VOC, used_mah), interp(CELL_IR, used_mah)
    c = (C_BASE + c_uf) * 1e-6
    v = v_oc
    v_min, i_max = v, 0.0
    for dur_ms, i_rail_ma in seq:
        for _ in range(max(1, int(dur_ms / dt))):
            i_in = i_rail_ma / 1000.0 * V_OUT / (eta(v) * v)
            i_cell = (v_oc - v) / r_int
            v += (i_cell - i_in) * (dt / 1000.0) / c
            if v < 1.0:                       # converter long gone
                return 0.0, i_max
            v_min, i_max = min(v_min, v), max(i_max, i_cell * 1000.0)
    return v_min, i_max


def simulate_rev_a(seq, used_mah, i_lim_ma=25.0, v_set=3.4, c_uf=620.0, dt=0.01):
    """Rev A: average input current limit + buffer on the regulated rail. Returns min rail voltage."""
    v_oc, r_int = interp(CELL_VOC, used_mah), interp(CELL_IR, used_mah)
    c = c_uf * 1e-6
    v = v_min = v_set
    for dur_ms, i_load_ma in seq + [(200, SLEEP)]:
        for _ in range(max(1, int(dur_ms / dt))):
            i_load = i_load_ma / 1000.0
            need = i_load if v >= v_set else i_load + (v_set - v) * c / (dt / 1000.0)
            k = need * v_set / 0.90
            disc = v_oc * v_oc - 4 * r_int * k
            i_in = min((v_oc - disc ** 0.5) / (2 * r_int) if disc > 0 else 1.0, i_lim_ma / 1000.0)
            v_cell = v_oc - i_in * r_int
            if v_cell < V_UVLO_MARGIN:
                v_cell, i_in = V_UVLO_MARGIN, (v_oc - V_UVLO_MARGIN) / r_int
            v = min(v_set, v + (i_in * v_cell * 0.90 / max(v, 1.0) - i_load) * (dt / 1000.0) / c)
            v_min = min(v_min, v)
    return v_min


def usable_mah(ok):
    """Largest used capacity (10 mAh steps) for which ok(mAh) is still true."""
    last = None
    for mah in range(0, 521, 10):
        if not ok(mah):
            break
        last = mah
    return last


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cpu-mhz", type=int, default=64, choices=(64, 96))
    ap.add_argument("--tx-ma", type=float, default=36.0, help="rail current while transmitting (0 dBm: 36 mA)")
    ap.add_argument("--detail", action="store_true", help="also print min VBAT / peak cell current per state of charge")
    a = ap.parse_args()
    cpu = 13.0 if a.cpu_mhz == 64 else 17.0
    profs = profiles(cpu, a.tx_ma)
    fmt = lambda m: "khong dat" if m is None else f"{m} mAh"         # noqa: E731

    print(f"CR2450 Energizer (R trong 2 s: 10 Ohm moi, 20 Ohm @250 mAh, 30 @300, 60 @400), CPU {a.cpu_mhz} MHz, "
          f"TX {a.tx_ma:.0f} mA, 3V2. Dat = VBAT >= {V_UVLO_MARGIN} V.\n")
    print("### Dung luong da dung (mAh) ma su kien con chay duoc - tu lon o phia PIN, khong gioi han dong\n")
    print("| Su kien | " + " | ".join(n for n, _ in BULK_OPTIONS) + " |")
    print("|---|" + "---|" * len(BULK_OPTIONS))
    for pname, seq in profs:
        row = [fmt(usable_mah(lambda m: simulate_vbat(seq, c_uf, m)[0] >= V_UVLO_MARGIN)) for _, c_uf in BULK_OPTIONS]
        print(f"| {pname} | " + " | ".join(row) + " |")

    print("\n### Rev A (gioi han dong vao 25 mA + 6 x 220 uF tren rail 3V4) - dat = rail >= 3.0 V\n")
    print("| Su kien | con chay duoc den |")
    print("|---|---|")
    for pname, seq in profs:
        print(f"| {pname} | {fmt(usable_mah(lambda m: simulate_rev_a(seq, m) >= V_MODULE_MIN))} |")

    if a.detail:
        print("\n### Chi tiet: VBAT thap nhat (V) / dong pin dinh (mA)\n")
        for pname, seq in profs:
            print(f"#### {pname}\n")
            print("| Da dung | R trong | " + " | ".join(n for n, _ in BULK_OPTIONS) + " |")
            print("|---|---|" + "---|" * len(BULK_OPTIONS))
            for mah in (0, 200, 250, 300, 350, 400):
                cells = []
                for _, c_uf in BULK_OPTIONS:
                    v, i = simulate_vbat(seq, c_uf, mah)
                    cells.append(f"{v:.2f} / {i:.0f}" + ("" if v >= V_UVLO_MARGIN else " x"))
                print(f"| {mah} mAh | {interp(CELL_IR, mah):.0f} Ohm | " + " | ".join(cells) + " |")
            print()


if __name__ == "__main__":
    main()

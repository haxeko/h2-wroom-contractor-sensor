#!/usr/bin/env python3
"""
Battery-life estimator - Matter-over-Thread contact sensor
ESP32-H2 (SIT ICD, light sleep) + DRV5032FA + TPS63900 buck-boost (3.2 V) + CR123A.

Every input is a named parameter with its source. Values marked "ESTIMATE" must be replaced
by measurements (docs/09_battery_life.md, section "Đo dòng thực tế").

Usage:
    python3 tools/battery_life.py                # default tables (markdown)
    python3 tools/battery_life.py --tx-dbm 0 --slow-poll-s 15 --subscribers 3
    # CR2450 coin cell, NOT used by any board (docs/12 section 8)
    python3 tools/battery_life.py --capacity-mah 600 620 --usable-fraction 0.40 --tx-dbm 0
    # (0.40: the cell's internal resistance passes 20 Ohm at ~250 mAh, tools/coin_cell_buffer.py)
"""
import argparse

# --------------------------------------------------------------------------- parameters
P = {
    # --- battery ---------------------------------------------------------------------
    "capacity_mah": [1500, 1700],          # CR123A nominal (user spec 1500-1700 mAh)
    "vbat_avg_v": 2.95,                    # mid-life Li-MnO2 voltage at light load (ESTIMATE)
    "usable_fraction": 0.85,               # practical: pulse load, cut-off, temperature, ageing
    "self_discharge_pct_per_year": 1.5,    # Li-MnO2 ~1-2 %/year at 20 degC (cell datasheets)
    # --- converter (TPS63900, datasheet SLVSET3D) --------------------------------------
    "vout_v": 3.2,                         # RCFG1 = 30.1 k (table 7-2)
    "efficiency": 0.90,                    # fig. 8-7: ~90 % at 10 uA..10 mA, VI 2.5..3.0 V
    "converter_iq_ua": 0.075,              # IQ into VIN, typ (table 6.5)
    # --- always-on loads on the 3V2 rail -----------------------------------------------
    "esp32h2_sleep_ua": 27.0,              # measured by Espressif, icd_app H2 SIT figure (27.04 uA);
                                           # datasheet table 5-9: 25 uA typ (TOP domain off)
    "hall_ua": 1.6,                        # DRV5032FA (20 Hz) ICC(AVG) typ @3 V (3.5 uA max); FB: 0.69 uA
    "supervisor_ua": 0.15,                 # TPS3839K33 typ
    "leakage_ua": 0.3,                     # caps, GPIO pads, PCB (ESTIMATE)
    # --- Thread polling (SIT ICD) -------------------------------------------------------
    "slow_poll_s": 15.0,                   # CONFIG_ICD_SLOW_POLL_INTERVAL_MS (SIT max 15 s)
    "fast_poll_s": 0.5,                    # CONFIG_ICD_FAST_POLL_INTERVAL_MS
    "q_poll_20dbm_mc": 0.30,               # charge per poll at 20 dBm: icd_app H2 SIT figure
                                           # (1.769 mC / 20 s window - 27 uA floor) / 4 polls
    "t_tx_per_poll_ms": 1.2,               # data-request frame + ramp (802.15.4, 250 kb/s)
    "tx_dbm": 10,                          # CONFIG_CS_THREAD_TX_POWER_DBM
    # --- ICD idle/active cycle and subscriptions -----------------------------------------
    "idle_mode_s": 3600.0,                 # CONFIG_ICD_IDLE_MODE_INTERVAL_SEC
    "active_mode_s": 1.0,                  # CONFIG_ICD_ACTIVE_MODE_INTERVAL_MS
    "active_threshold_s": 1.0,             # CONFIG_ICD_ACTIVE_MODE_THRESHOLD_MS
    "subscribers": 2,                      # e.g. Apple Home hub + Home Assistant
    "q_report_mc": 1.2,                    # one report + status response + MRP ack (ESTIMATE)
    "q_wake_mc": 0.10,                     # Hall wake-up + debounce wakes (ESTIMATE)
    # --- housekeeping -------------------------------------------------------------------
    "vbat_meas_per_day": 2,
    "q_vbat_meas_mc": 0.3,                 # 50 ms awake @ ~6 mA
    "commissioning_mah": 1.0,              # one-time: BLE advertising + PASE/CASE (ESTIMATE)
    "practical_margin": 1.20,              # +20 % on all dynamic currents (network retries...)
}

# 802.15.4 TX current (mA) vs power, ESP32-H2 datasheet v1.3 table 5-7 (20 dBm: 118 mA was
# measured by Espressif; the datasheet peak is 140 mA)
TX_TABLE = [(-24, 24.0), (0, 36.0), (9, 60.0), (20, 120.0)]


def tx_current_ma(dbm):
    pts = sorted(TX_TABLE)
    if dbm <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if dbm <= x1:
            return y0 + (y1 - y0) * (dbm - x0) / (x1 - x0)
    return pts[-1][1]


def q_poll_mc(p):
    """Charge of one data poll at the configured TX power."""
    saving = (tx_current_ma(20) - tx_current_ma(p["tx_dbm"])) * p["t_tx_per_poll_ms"] / 1000.0
    return p["q_poll_20dbm_mc"] - saving


def rail_breakdown_ua(p, events_per_day):
    """Average current on the 3V2 rail, per contributor (uA)."""
    day = 86400.0
    qp = q_poll_mc(p)
    static = p["esp32h2_sleep_ua"] + p["hall_ua"] + p["supervisor_ua"] + p["leakage_ua"]
    polls = qp / p["slow_poll_s"] * 1000.0                       # mC/s -> uA
    n_active_polls = max(1, round(p["active_mode_s"] / p["fast_poll_s"]))
    keepalive = (n_active_polls * qp + p["subscribers"] * p["q_report_mc"]) / p["idle_mode_s"] * 1000.0
    n_thr_polls = max(1, round(p["active_threshold_s"] / p["fast_poll_s"]))
    q_event = p["q_wake_mc"] + p["subscribers"] * p["q_report_mc"] + n_thr_polls * qp
    events = events_per_day * q_event / day * 1000.0
    house = p["vbat_meas_per_day"] * p["q_vbat_meas_mc"] / day * 1000.0
    return {"sleep+always-on": static, "thread polls": polls, "ICD keep-alive": keepalive,
            "door events": events, "battery meas.": house}


def battery_current_ua(p, rail_ua):
    return rail_ua * p["vout_v"] / (p["efficiency"] * p["vbat_avg_v"]) + p["converter_iq_ua"]


def life_years(p, cap_mah, events_per_day, practical):
    br = rail_breakdown_ua(p, events_per_day)
    static = br["sleep+always-on"]
    dynamic = sum(v for k, v in br.items() if k != "sleep+always-on")
    if practical:
        dynamic *= p["practical_margin"]
    i_bat = battery_current_ua(p, static + dynamic)                     # uA
    cap = cap_mah * (p["usable_fraction"] if practical else 1.0) - p["commissioning_mah"]
    if practical:
        i_bat += cap_mah * p["self_discharge_pct_per_year"] / 100.0 / 8760.0 * 1000.0
    hours = cap / (i_bat / 1000.0)
    return hours / 8760.0, i_bat, static + dynamic


SCENARIOS = [
    ("Bình thường", 10), ("Bình thường", 20),
    ("Sử dụng nhiều", 50), ("Sử dụng nhiều", 100),
    ("Rất nhiều", 200),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tx-dbm", type=float)
    ap.add_argument("--slow-poll-s", type=float)
    ap.add_argument("--idle-mode-s", type=float)
    ap.add_argument("--subscribers", type=int)
    ap.add_argument("--sleep-ua", type=float, help="ESP32-H2 light-sleep floor (measured)")
    ap.add_argument("--q-poll-mc", type=float, help="measured charge per poll at 20 dBm")
    ap.add_argument("--capacity-mah", type=float, nargs=2, metavar=("LOW", "HIGH"),
                    help="cell capacity range, e.g. 600 620 for a CR2450 (default CR123A 1500 1700)")
    ap.add_argument("--usable-fraction", type=float, help="practical fraction of the capacity (default 0.85)")
    ap.add_argument("--vout-v", type=float, help="TPS63900 output voltage (default 3.2 V on both boards)")
    a = ap.parse_args()
    p = dict(P)
    for arg, key in (("tx_dbm", "tx_dbm"), ("slow_poll_s", "slow_poll_s"), ("idle_mode_s", "idle_mode_s"),
                     ("subscribers", "subscribers"), ("sleep_ua", "esp32h2_sleep_ua"),
                     ("q_poll_mc", "q_poll_20dbm_mc"), ("capacity_mah", "capacity_mah"),
                     ("usable_fraction", "usable_fraction"), ("vout_v", "vout_v")):
        v = getattr(a, arg)
        if v is not None:
            p[key] = v

    print(f"Cấu hình: TX {p['tx_dbm']} dBm, slow poll {p['slow_poll_s']} s, idle mode {p['idle_mode_s']} s, "
          f"{p['subscribers']} subscriber, Vout {p['vout_v']} V, eta {p['efficiency']:.2f}")
    print(f"Điện tích mỗi lần poll: {q_poll_mc(p):.3f} mC (TX {tx_current_ma(p['tx_dbm']):.0f} mA)\n")

    print("### Phân bổ dòng trung bình trên rail 3V2 (uA)\n")
    hdr = "| Kịch bản | Lần đóng/mở/ngày | " + " | ".join(rail_breakdown_ua(p, 0).keys()) + " | Tổng rail |"
    print(hdr)
    print("|" + "---|" * (hdr.count("|") - 1))
    for name, cycles in SCENARIOS:
        br = rail_breakdown_ua(p, 2 * cycles)   # 1 cycle = OPEN + CLOSED = 2 reports
        print(f"| {name} | {cycles} | " + " | ".join(f"{v:.2f}" for v in br.values()) + f" | {sum(br.values()):.1f} |")

    print("\n### Tuổi thọ pin (năm)\n")
    c0, c1 = (int(c) for c in p["capacity_mah"])
    print(f"| Kịch bản | Lần đóng/mở/ngày | I pin lý thuyết (uA) | Lý thuyết {c0} mAh | Lý thuyết {c1} mAh "
          f"| I pin thực tế (uA) | Thực tế {c0} mAh | Thực tế {c1} mAh |")
    print("|---|---|---|---|---|---|---|---|")
    for name, cycles in SCENARIOS:
        ev = 2 * cycles
        t15, ib_t, _ = life_years(p, c0, ev, False)
        t17, _, _ = life_years(p, c1, ev, False)
        p15, ib_p, _ = life_years(p, c0, ev, True)
        p17, _, _ = life_years(p, c1, ev, True)
        print(f"| {name} | {cycles} | {ib_t:.1f} | {t15:.2f} | {t17:.2f} | {ib_p:.1f} | {p15:.2f} | {p17:.2f} |")

    print(f"\n### Độ nhạy (kịch bản 20 lần/ngày, {c0} mAh, thực tế)\n")
    print("| Thay đổi | I pin (uA) | Tuổi thọ (năm) |")
    print("|---|---|---|")
    variants = [
        ("Mặc định", {}),
        ("TX 20 dBm (mặc định ESP-IDF)", {"tx_dbm": 20}),
        ("TX 0 dBm", {"tx_dbm": 0}),
        ("Slow poll 5 s", {"slow_poll_s": 5}),
        ("Slow poll 10 s", {"slow_poll_s": 10}),
        ("Idle mode 600 s (cấu hình cũ)", {"idle_mode_s": 600}),
        ("Idle mode 1800 s", {"idle_mode_s": 1800}),
        ("1 subscriber", {"subscribers": 1}),
        ("4 subscriber (Apple+Google+HA+Aqara)", {"subscribers": 4}),
        ("LIT 60 s (nếu controller đăng ký ICD)", {"slow_poll_s": 60}),
        ("Sleep floor 20 uA (nếu đo được thấp hơn)", {"esp32h2_sleep_ua": 20}),
        ("Sleep floor 35 uA (board kém)", {"esp32h2_sleep_ua": 35}),
        ("Vout 3.3 V", {"vout_v": 3.3}),
        ("Hiệu suất DC-DC 85 %", {"efficiency": 0.85}),
    ]
    for label, delta in variants:
        q = dict(p)
        q.update(delta)
        y, ib, _ = life_years(q, c0, 40, True)
        print(f"| {label} | {ib:.1f} | {y:.2f} |")

    # Reference only: direct connection to the cell (OUT OF the 3.0 V datasheet minimum)
    q = dict(p)
    rail = sum(rail_breakdown_ua(q, 40).values())
    print(f"\nTham khảo (ngoài spec 3.0 V): cấp trực tiếp từ pin, I pin ~= I rail = {rail:.1f} uA "
          f"-> {c0 / (rail / 1000.0) / 8760.0:.2f} năm lý thuyết NẾU chip chạy được tới cuối pin.")


if __name__ == "__main__":
    main()

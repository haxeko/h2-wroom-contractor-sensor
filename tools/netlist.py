#!/usr/bin/env python3
"""
Writes hardware/chip/netlist.csv from tools/design_data.py (single source of truth) and runs
simple ERC-style checks:
  - every net (except intentional no-connect nets) has >= 2 pins
  - every supply pin of U1 is on 3V2 (or VBAT_PIN18 through R5)
  - no duplicate reference

The KiCad schematic/PCB are generated from the same data (tools/kicad/), and KiCad's own ERC/DRC
are run on them.

Usage: python3 tools/netlist.py
"""
import collections
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from design_data import NC_NETS, PARTS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "hardware" / "chip" / "netlist.csv"

U1_SUPPLY_PINS = {"1", "2", "9", "18", "19", "20", "27", "30", "31"}


def main():
    nets = collections.defaultdict(list)
    refs = set()
    rows = []
    for p in PARTS:
        assert p.ref not in refs, f"duplicate reference {p.ref}"
        refs.add(p.ref)
        for pin, net in p.pins.items():
            nets[net].append(f"{p.ref}.{pin}")
            rows.append((p.ref, pin, net, p.value, p.mpn, p.footprint, "DNP" if p.dnp else "yes"))

    problems = []
    for net, members in sorted(nets.items()):
        if len(members) < 2 and net not in NC_NETS:
            problems.append(f"net {net} has a single connection: {members}")
    u1 = next(p for p in PARTS if p.ref == "U1")
    for pin in U1_SUPPLY_PINS:
        if u1.pins[pin] not in ("3V2", "VBAT_PIN18"):
            problems.append(f"U1 supply pin {pin} on {u1.pins[pin]}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Ref", "Pin", "Net", "Value", "MPN", "Footprint", "Populated"])
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} pins, {len(nets)} nets, {len(PARTS)} parts")
    print(f"intentional NC nets: {', '.join(sorted(NC_NETS))}")
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("ERC checks passed")


if __name__ == "__main__":
    main()

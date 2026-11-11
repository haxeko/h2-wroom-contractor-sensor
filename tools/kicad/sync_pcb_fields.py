#!/usr/bin/python3.12
"""
Copy Value / MPN / Manufacturer / Description from tools/design_data.py into the footprints of the
ROUTED bare-chip board, without touching placement or copper. Use it after a BOM-only change (same
footprint, same nets) instead of re-running build_pcb.py, which would re-route the whole board.

Run:  /usr/bin/python3.12 tools/kicad/sync_pcb_fields.py     (then export_fab.py)
"""
import pathlib
import sys

import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_pcb as B  # noqa: E402
from design_data import PARTS  # noqa: E402


def main():
    board = pcbnew.LoadBoard(str(B.PCB))
    parts = {p.ref: p for p in PARTS}
    changed = []
    for fp in board.GetFootprints():
        part = parts.get(fp.GetReference())
        if part is None:
            continue
        # gen_schematic.py appends " (DNP)" to the value of unpopulated parts
        want = {"Value": part.value + (" (DNP)" if part.dnp else ""), "MPN": part.mpn,
                "Manufacturer": part.manufacturer,
                "Description": part.description}
        for field in fp.GetFields():
            name = field.GetName()
            if name in want and want[name] and field.GetText() != want[name]:
                changed.append((fp.GetReference(), name, field.GetText(), want[name]))
                field.SetText(want[name])
    for c in changed:
        print("  %-4s %-12s %s -> %s" % c)
    if changed:
        pcbnew.SaveBoard(str(B.PCB), board)
        B.PCB.write_text(B.patch_stackup(B.PCB.read_text()))
    print(f"{len(changed)} field(s) updated in {B.PCB.relative_to(HERE.parents[1])}")
    _, summary = B.run_drc()
    for k, v in sorted(summary.items()):
        print(f"  DRC {k[0]:12s} {k[1]:35s} {v}")
    if not summary:
        print("  DRC: 0 violations, 0 unconnected, 0 parity")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Export the manufacturing / review outputs of hardware/kicad/matter_contact_sensor.* with kicad-cli
(KiCad 10). Everything lands in hardware/kicad/fab/:

  gerber/         Gerber X2 (4 copper layers, masks, paste, silk, Edge.Cuts) + Excellon drill (PTH/NPTH)
                  + drill maps + Gerber job file
  pos/            pick & place (top side, CSV, mm; DNP parts, antenna and test pads excluded)
  ipc-d-356.ipc   bare-board electrical test netlist
  matter_contact_sensor_schematic.pdf
  assembly_top.pdf      F.Fab + F.SilkS + Edge.Cuts with pad outlines (assembly drawing, DNP crossed out)
  layers.pdf            one page per copper layer
  render_top.png / render_bottom.png   3D renders (no 3D models are installed: bodies are not shown)
  stats.txt             board statistics
  matter_contact_sensor-gerber.zip      Gerber + drill files, ready to upload to a PCB fab
  assembly/             files for SMT assembly (JLCPCB-style column names):
                          matter_contact_sensor-bom.csv  Comment, Designator, Footprint, Quantity,
                                                         Manufacturer, MPN, LCSC Part # (only verified ones)
                          matter_contact_sensor-cpl.csv  Designator, Mid X, Mid Y, Layer, Rotation

Gerber, drill and pick & place coordinates use the drill/place origin set by build_pcb.py: the
lower-left board corner (X to the right, Y up).

Usage: python3 tools/kicad/export_fab.py                  (after /usr/bin/python3.12 tools/kicad/build_pcb.py)
       python3 tools/kicad/export_fab.py --variant wroom  (module variant, hardware/kicad_wroom/fab/)
"""
import csv
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
WROOM = "--variant" in sys.argv and sys.argv[sys.argv.index("--variant") + 1] == "wroom"
NAME = "matter_contact_sensor_wroom" if WROOM else "matter_contact_sensor"
KDIR = ROOT / "hardware" / ("kicad_wroom" if WROOM else "kicad")
PCB = KDIR / f"{NAME}.kicad_pcb"
SCH = KDIR / f"{NAME}.kicad_sch"
OUT = KDIR / "fab"

# LCSC numbers already checked during the BOM research (docs/07) or used for the same part in the
# BOM of the CR2032 Matter button; every other line is filled in by the assembler from the MPN
LCSC = {"ECS-320-10-37B2-CKY-TR": "C6190606", "GRM188R60J226MEA0D": "C77042", "B3U-1000P": "C231329",
        "AO3401A": "C15127", "TPS63900DSKR": "C1518762"}
POS = f"{NAME}-top-pos.csv"

# the bare-chip board has 4 copper layers, the module board 2
COPPER = "F.Cu,B.Cu" if WROOM else "F.Cu,In1.Cu,In2.Cu,B.Cu"
GERBER_LAYERS = COPPER + ",F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts"


def run(*args):
    r = subprocess.run(["kicad-cli", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"kicad-cli {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def assembly():
    """Gerber zip + assembly BOM / CPL. Only populated parts (no DNP, no antenna copper, test pads,
    battery wire pads, fiducials or tooling holes)."""
    with zipfile.ZipFile(OUT / f"{NAME}-gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted((OUT / "gerber").iterdir()):
            if f.suffix != ".pdf":
                z.write(f, f.name)
    asm = OUT / "assembly"
    asm.mkdir()
    raw = asm / "_raw.csv"
    run("sch", "export", "bom", "-o", str(raw), "--fields", "Value,Reference,Footprint,Manufacturer,MPN,${QUANTITY}",
        "--labels", "Comment,Designator,Footprint,Manufacturer,MPN,Quantity", "--group-by", "Value,Footprint,MPN",
        "--ref-range-delimiter", "", "--exclude-dnp", str(SCH))
    rows = list(csv.DictReader(raw.open(newline="")))
    raw.unlink()
    refs = set()
    with (asm / f"{NAME}-bom.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "Quantity", "Manufacturer", "MPN", "LCSC Part #"])
        for r in rows:
            w.writerow([r["Comment"], r["Designator"], r["Footprint"].split(":")[-1], r["Quantity"],
                        r["Manufacturer"], r["MPN"], LCSC.get(r["MPN"], "")])
            refs |= set(r["Designator"].split(","))
    pos = {p["Ref"]: p for p in csv.DictReader((OUT / "pos" / POS).open(newline=""))}
    missing = refs - set(pos)
    if missing:
        raise SystemExit(f"BOM parts missing from the position file: {sorted(missing)}")
    with (asm / f"{NAME}-cpl.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref in sorted(refs, key=lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):]))):
            p = pos[ref]
            w.writerow([ref, f"{float(p['PosX']):.4f}mm", f"{float(p['PosY']):.4f}mm",
                        "Top" if p["Side"] == "top" else "Bottom", f"{float(p['Rot']):g}"])
    return len(rows), len(refs)


def main():
    if "(footprint " not in PCB.read_text():
        raise SystemExit(f"{PCB.name} has no footprints (build_pcb.py still running or failed?)")
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "gerber").mkdir(parents=True)
    (OUT / "pos").mkdir()
    run("pcb", "export", "gerbers", "-o", str(OUT / "gerber"), "-l", GERBER_LAYERS, "--subtract-soldermask",
        "--use-drill-file-origin", str(PCB))
    run("pcb", "export", "drill", "-o", str(OUT / "gerber") + "/", "--format", "excellon", "--excellon-units", "mm",
        "--drill-origin", "plot", "--excellon-separate-th", "--generate-map", "--map-format", "pdf", str(PCB))
    run("pcb", "export", "pos", "-o", str(OUT / "pos" / POS), "--side", "front",
        "--format", "csv", "--units", "mm", "--exclude-dnp", "--use-drill-file-origin", str(PCB))
    run("pcb", "export", "ipcd356", "-o", str(OUT / "ipc-d-356.ipc"), str(PCB))
    run("sch", "export", "pdf", "-o", str(OUT / f"{NAME}_schematic.pdf"), str(SCH))
    run("pcb", "export", "pdf", "--mode-single", "-o", str(OUT / "assembly_top.pdf"), "-l",
        "F.Fab,F.SilkS,Edge.Cuts", "--sp", "--cdnp", "--include-border-title", str(PCB))
    run("pcb", "export", "pdf", "--mode-multipage", "-o", str(OUT / "layers.pdf"), "-l",
        COPPER, "--cl", "Edge.Cuts", "--include-border-title", str(PCB))
    for side in ("top", "bottom"):
        run("pcb", "render", "-o", str(OUT / f"render_{side}.png"), "--side", side, "--width", "2400", "--height",
            "1200", "--quality", "high", "--background", "opaque", "--zoom", "1.2" if WROOM else "1.8", str(PCB))
    run("pcb", "export", "stats", "-o", str(OUT / "stats.txt"), "--units", "mm", str(PCB))
    lines, parts = assembly()
    print(f"assembly: {lines} BOM lines, {parts} placed parts")
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            print(f.relative_to(ROOT), f.stat().st_size)


if __name__ == "__main__":
    main()

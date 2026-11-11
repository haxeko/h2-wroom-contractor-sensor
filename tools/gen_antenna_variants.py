#!/usr/bin/env python3
"""
Generate tuning variants of the TI AN043 (SWRA117D) meandered inverted-F antenna footprint.

Source footprints: KiCad library RF_Antenna:Texas_SWRA117D_2.4GHz_Left / _Right (mirror image)
(https://gitlab.com/kicad/libraries/kicad-footprints, CC-BY-SA 4.0 with the KiCad library
exception), copied unmodified to hardware/antenna/. The PCB uses the _Right version (feed at the
side-A edge, see docs/06_pcb_layout.md).

Only the open end of the last meander leg (dimension L1 = 3.94 mm in SWRA117D) is shortened.
A plastic housing (er ~2.5-3.5 at 1-2 mm distance) lowers the resonance frequency; a slightly
shorter radiating arm moves it back up. All variants are placed side by side on the EVT panel
and the one whose S11 minimum falls at 2.44 GHz INSIDE THE HOUSING is kept
(docs/04_antenna_rf.md, procedure step 4).

Usage: python3 tools/gen_antenna_variants.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "hardware" / "antenna" / "Texas_SWRA117D_2.4GHz_Left.kicad_mod"
KICAD_RIGHT = pathlib.Path("/usr/share/kicad/footprints/RF_Antenna.pretty/Texas_SWRA117D_2.4GHz_Right.kicad_mod")
L1_END_Y = -0.71           # y of the open end of the last leg in the source footprint
L1_NOMINAL = 3.94
TRIMS_MM = (0.3, 0.6, 0.9)


def main():
    for side in ("Left", "Right"):
        src = SRC.parent / f"Texas_SWRA117D_2.4GHz_{side}.kicad_mod"
        if side == "Right" and not src.exists():
            src.write_text(KICAD_RIGHT.read_text())
        text = src.read_text()
        sgn = -1 if side == "Left" else 1        # the Right footprint is the mirror image (x -> -x)
        xa, xb = f"{sgn * 11.85:g}", f"{sgn * 11.35:g}"
        old = f"(xy {xa} {L1_END_Y}) (xy {xb} {L1_END_Y})"
        if old not in text:
            raise SystemExit(f"unexpected source footprint geometry ({side}) - L1 end not found")
        for trim in TRIMS_MM:
            y = round(L1_END_Y - trim, 3)
            base = f"Texas_SWRA117D_2.4GHz_{side}"
            name = f"{base}_L1_{L1_NOMINAL - trim:.2f}mm"
            out = text.replace(old, f"(xy {xa} {y}) (xy {xb} {y})")
            out = out.replace(f'(footprint "{base}"', f'(footprint "{name}"', 1)
            out = out.replace(f'(property "Value" "{base}"', f'(property "Value" "{name}"', 1)
            out = re.sub(r'\(descr "[^"]*"\)',
                         f'(descr "TI SWRA117D MIFA, L1 shortened by {trim:.1f} mm for housing detuning. '
                         f'Derived from KiCad RF_Antenna:{base} (CC-BY-SA 4.0)")',
                         out, count=1)
            dst = SRC.parent / f"{name}.kicad_mod"
            dst.write_text(out)
            print(f"wrote {dst.relative_to(ROOT)}  (L1 = {L1_NOMINAL - trim:.2f} mm)")


if __name__ == "__main__":
    main()

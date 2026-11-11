"""
Load symbols from KiCad .kicad_sym libraries (with 'extends' flattening) and list their pins.
"""
import copy
import functools
import os

from sexp import Sym, find, find_all, loads

KICAD_SYMBOL_DIR = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")


@functools.lru_cache(maxsize=None)
def load_lib(path):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())


def lib_path(nick, project_libs=None):
    if project_libs and nick in project_libs:
        return project_libs[nick]
    return os.path.join(KICAD_SYMBOL_DIR, f"{nick}.kicad_sym")


def _raw_symbol(lib, name):
    for s in find_all(lib, Sym("symbol")):
        if s[1] == name:
            return s
    raise KeyError(name)


def get_symbol(lib_id, project_libs=None):
    """Return a flattened deep copy of the symbol named lib_id = 'Nick:Name' (name not prefixed)."""
    nick, name = lib_id.split(":", 1)
    lib = load_lib(lib_path(nick, project_libs))
    sym = copy.deepcopy(_raw_symbol(lib, name))
    ext = find(sym, Sym("extends"))
    if ext is not None:
        parent = get_symbol(f"{nick}:{ext[1]}", project_libs)
        # child keeps its own properties; take everything else from the parent
        child_props = {p[1]: p for p in find_all(sym, Sym("property"))}
        flat = [Sym("symbol"), name]
        for item in parent[2:]:
            if isinstance(item, list) and item and item[0] == Sym("property") and item[1] in child_props:
                flat.append(child_props.pop(item[1]))
            elif isinstance(item, list) and item and item[0] == Sym("symbol"):
                unit = copy.deepcopy(item)
                unit[1] = unit[1].replace(parent[1], name, 1)
                flat.append(unit)
            else:
                flat.append(copy.deepcopy(item))
        # remaining child-only properties and flags
        for p in child_props.values():
            flat.insert(2, p)
        sym = flat
    return sym


def pins(sym):
    """List of dicts: number, name, type, x, y, angle, length, unit (symbol coordinates, Y up)."""
    out = []
    for unit in find_all(sym, Sym("symbol")):
        uname = unit[1]
        try:
            unit_no = int(uname.rsplit("_", 2)[-2])
        except (ValueError, IndexError):
            unit_no = 0
        for p in find_all(unit, Sym("pin")):
            at = find(p, Sym("at"))
            length = find(p, Sym("length"))
            name = find(p, Sym("name"))
            number = find(p, Sym("number"))
            out.append({
                "number": str(number[1]), "name": str(name[1]), "type": str(p[1]),
                "x": float(at[1]), "y": float(at[2]), "angle": float(at[3]) if len(at) > 3 else 0.0,
                "length": float(length[1]) if length else 2.54, "unit": unit_no,
            })
    return out


if __name__ == "__main__":
    import sys
    for lid in sys.argv[1:]:
        s = get_symbol(lid)
        print(f"== {lid}")
        for p in find_all(s, Sym("property")):
            print(f"   prop {p[1]} = {p[2]!r}")
        for p in sorted(pins(s), key=lambda d: (len(d['number']), d['number'])):
            print(f"   pin {p['number']:>3} {p['name']:<12} {p['type']:<14} at ({p['x']},{p['y']}) ang {p['angle']} len {p['length']} unit {p['unit']}")

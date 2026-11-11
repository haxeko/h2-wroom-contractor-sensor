"""
Minimal S-expression reader/writer for KiCad files (.kicad_sym / .kicad_sch / .kicad_mod).

Atoms are kept as Python objects:
  - Sym(name)  : bare symbol (e.g. property, at, yes)
  - str        : quoted string
  - int/float  : numbers
Lists are Python lists. The writer emits KiCad-compatible text (KiCad accepts any whitespace).
"""
import re


class Sym(str):
    """Unquoted atom."""
    __slots__ = ()

    def __repr__(self):
        return f"Sym({str.__repr__(self)})"


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def loads(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"parse error at {pos}: {text[pos:pos + 40]!r}")
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(m.group(3).replace('\\"', '"').replace("\\\\", "\\"))
        else:
            tok = m.group(4)
            try:
                val = int(tok)
            except ValueError:
                try:
                    val = float(tok) if re.match(r"^-?\d*\.?\d+(e-?\d+)?$", tok) else Sym(tok)
                except ValueError:
                    val = Sym(tok)
            stack[-1].append(val)
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def _atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, bool):
        return "yes" if a else "no"
    if isinstance(a, int):
        return str(a)
    if isinstance(a, float):
        s = f"{a:.6f}".rstrip("0").rstrip(".")
        return s if s not in ("", "-0") else "0"
    s = str(a).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def dumps(node, indent=0):
    """Pretty printer: short lists on one line, long ones broken."""
    if not isinstance(node, list):
        return _atom(node)
    parts = [dumps(x, indent + 1) for x in node]
    one_line = "(" + " ".join(parts) + ")"
    if len(one_line) + indent <= 100 and "\n" not in one_line:
        return one_line
    pad = "\t" * (indent + 1)
    head = []
    rest = list(parts)
    # keep the token and leading atoms on the first line
    while rest and not rest[0].startswith("("):
        head.append(rest.pop(0))
    out = "(" + " ".join(head)
    for p in rest:
        out += "\n" + pad + p
    out += "\n" + "\t" * indent + ")"
    return out


def find(node, key):
    """First child list whose head is `key`."""
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def find_all(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def S(*items):
    """Build a list node; strings that are identifiers should be passed as Sym."""
    return list(items)

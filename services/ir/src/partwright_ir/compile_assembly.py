from partwright_ir.assembly import joint_order, joint_tree
from partwright_ir.expr import to_python
from partwright_ir.model import Connector, Design

MATE_PRELUDE = """

def _frame(origin, z, x):
    return Location(Plane(origin=origin, x_dir=AXES[x], z_dir=AXES[z]))


def _mate(parent, angle, offset, child):
    return _frame(*parent) * Rot(0, 0, angle) * Pos(0, 0, offset) * _frame(*child).inverse()
"""


def assembly_build(design: Design) -> str:
    assert design.assembly is not None
    connectors = {c.id: c for c in design.assembly.connectors}
    tree = joint_tree(design)
    mates = ", ".join(f"({j.id!r}, {tree[c][1]!r}, {c!r})" for c, (j, _) in tree.items())
    lines = [f"MATES = [{mates}]", "", "", "def build():", f"    L = {{p: Location() for p in {[p.id for p in design.parts]!r}}}"]
    for j in joint_order(design):
        parent, child = connectors[j.parent], connectors[j.child]
        mate = f"_mate({_frame(parent)}, {to_python(j.angle)}, {to_python(j.offset)}, {_frame(child)})"
        lines.append(f"    L[{child.part!r}] = L[{parent.part!r}] * {mate}")
    table = ", ".join(f"{p.id!r}: part_{i}().moved(L[{p.id!r}])" for i, p in enumerate(design.parts))
    return "\n".join([*lines, f"    return {{{table}}}", ""])


def _frame(c: Connector) -> str:
    origin = ", ".join(to_python(e) for e in c.origin)
    return f"(({origin}), {c.z!r}, {c.x!r})"

from scriber_ir.assembly import effective_assembly, joint_order, joint_tree
from scriber_ir.expr import to_python
from scriber_ir.model import Connector, Design, Joint, SpurGear

MATE_PRELUDE = """

def _frame(origin, z, x):
    return Location(Plane(origin=origin, x_dir=AXES[x], z_dir=AXES[z]))


def _mate(parent, angle, offset, child):
    return _frame(*parent) * Rot(0, 0, angle) * Pos(0, 0, offset) * _frame(*child).inverse()
"""


def assembly_build(design: Design) -> str:
    a = effective_assembly(design)
    assert a is not None
    connectors = {c.id: c for c in a.connectors}
    tree = joint_tree(design)
    mates = ", ".join(f"({j.id!r}, {tree[c][1]!r}, {c!r})" for c, (j, _) in tree.items())
    slack = ", ".join(f"{j.id!r}: {s}" for c, (j, p) in tree.items() if (s := _mesh_slack(design, j, p, c)))
    lines = [f"MATES = [{mates}]", *([f"SLACK = {{{slack}}}"] if slack else [])]
    lines += ["", "", "def build():", f"    L = {{p: Location() for p in {[p.id for p in design.parts]!r}}}"]
    for j in joint_order(design):
        parent, child = connectors[j.parent], connectors[j.child]
        mate = f"_mate({_frame(parent)}, {to_python(j.angle)}, {to_python(j.offset)}, {_frame(child)})"
        lines.append(f"    L[{child.part!r}] = L[{parent.part!r}] * {mate}")
    table = ", ".join(f"{p.id!r}: part_{i}().moved(L[{p.id!r}])" for i, p in enumerate(design.parts))
    return "\n".join([*lines, f"    return {{{table}}}", ""])


def _mesh_slack(design: Design, joint: Joint, parent: str, child: str) -> str | None:
    parts = {p.id: p for p in design.parts}
    a, b = (next((f for f in parts[pid].features if isinstance(f, SpurGear)), None) for pid in (parent, child))
    if joint.kind != "revolute" or a is None or b is None:
        return None
    # a centred mesh leaves half the pair's circular backlash on each flank, cos(pressure angle) of it along the normal
    return f"({to_python(a.backlash)} + {to_python(b.backlash)}) / 4 * cos({to_python(a.pressure_angle)})"


def _frame(c: Connector) -> str:
    origin = ", ".join(to_python(e) for e in c.origin)
    return f"(({origin}), {c.z!r}, {c.x!r})"

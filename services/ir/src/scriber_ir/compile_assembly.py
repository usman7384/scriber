from scriber_ir.assembly import effective_assembly, joint_order, joint_tree
from scriber_ir.expr import to_python
from scriber_ir.model import Connector, Design, Joint, SpurGear

MATE_PRELUDE = """

def _frame(origin, z, x):
    return Location(Plane(origin=origin, x_dir=AXES[x] if isinstance(x, str) else x, z_dir=AXES[z] if isinstance(z, str) else z))


def _copy(shape, mirror):
    return shape if mirror == "none" else shape.mirror(BASE[mirror])


def _mate(parent, angle, offset, child):
    return _frame(*parent) * Rot(0, 0, angle) * Pos(0, 0, offset) * _frame(*child).inverse()
"""


def assembly_build(design: Design) -> str:
    a = effective_assembly(design)
    assert a is not None
    connectors = {c.id: c for c in a.connectors}
    tree = joint_tree(design)
    owner = {c.id: c.part for c in a.connectors}
    placing = {j.id for j, _ in tree.values()}
    # joints that close a loop place nothing; they are only checked for contact
    closing = [f"({j.id!r}, {owner[j.parent]!r}, {owner[j.child]!r})" for j in a.joints if j.id not in placing]
    mates = ", ".join([*(f"({j.id!r}, {tree[c][1]!r}, {c!r})" for c, (j, _) in tree.items()), *closing])
    slack = ", ".join(f"{j.id!r}: {s}" for c, (j, p) in tree.items() if (s := _mesh_slack(design, j, p, c)))
    lines = [f"MATES = [{mates}]", *([f"SLACK = {{{slack}}}"] if slack else [])]
    ids = [p.id for p in design.parts] + [i.id for i in a.instances]
    lines += ["", "", "def build():", f"    L = {{p: Location() for p in {ids!r}}}"]
    for j in joint_order(design):
        parent, child = connectors[j.parent], connectors[j.child]
        mate = f"_mate({_frame(parent)}, {to_python(j.angle)}, {to_python(j.offset)}, {_frame(child)})"
        lines.append(f"    L[{child.part!r}] = L[{parent.part!r}] * {mate}")
    index = {p.id: i for i, p in enumerate(design.parts)}
    copies = [f"{c.id!r}: _copy(part_{index[c.part]}(), {c.mirror!r}).moved(L[{c.id!r}])" for c in a.instances]
    table = ", ".join([*(f"{p.id!r}: part_{i}().moved(L[{p.id!r}])" for i, p in enumerate(design.parts)), *copies])
    return "\n".join([*lines, f"    return {{{table}}}", ""])


def _mesh_slack(design: Design, joint: Joint, parent: str, child: str) -> str | None:
    parts = {p.id: p for p in design.parts}
    parts |= {i.id: parts[i.part] for i in design.assembly.instances} if design.assembly else {}
    a, b = (next((f for f in parts[pid].features if isinstance(f, SpurGear)), None) for pid in (parent, child))
    if joint.kind != "revolute" or a is None or b is None:
        return None
    # a centred mesh leaves half the pair's circular backlash on each flank, cos(pressure angle) of it along the normal
    return f"({to_python(a.backlash)} + {to_python(b.backlash)}) / 4 * cos({to_python(a.pressure_angle)})"


def _frame(c: Connector) -> str:
    origin = ", ".join(to_python(e) for e in c.origin)
    return f"(({origin}), {_axis(c.z)}, {_axis(c.x)})"


def _axis(a: str | tuple[float | str, float | str, float | str]) -> str:
    return repr(a) if isinstance(a, str) else f"({', '.join(to_python(e) for e in a)})"

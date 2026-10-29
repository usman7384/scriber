from collections.abc import Iterator

from partwright_ir.expr import ExprError, evaluate, names
from partwright_ir.model import Design, Expr, Joint

Problem = tuple[str, str]


def joint_tree(design: Design) -> dict[str, tuple[Joint, str]]:
    if design.assembly is None:
        return {}
    owner = {c.id: c.part for c in design.assembly.connectors}
    tree: dict[str, tuple[Joint, str]] = {}
    for j in design.assembly.joints:
        child = owner.get(j.child)
        if child is not None and owner.get(j.parent) is not None:
            tree.setdefault(child, (j, owner[j.parent]))
    return tree


def joint_order(design: Design) -> list[Joint]:
    tree = joint_tree(design)
    return [tree[c][0] for c in sorted(tree, key=lambda c: _depth(tree, c))]


def assembly_names(design: Design) -> set[str]:
    found: set[str] = set()
    for _, e in _exprs(design):
        try:
            found |= names(e)
        except ExprError:
            continue
    return found


def assembly_errors(design: Design) -> Iterator[Problem]:
    a = design.assembly
    if a is None:
        return
    parts = {p.id for p in design.parts}
    owner = {c.id: c.part for c in a.connectors}
    for label, ids in (("connector", [c.id for c in a.connectors]), ("joint", [j.id for j in a.joints])):
        if len(set(ids)) != len(ids):
            yield "assembly", f"duplicate {label} id"
    for c in a.connectors:
        if c.part not in parts:
            yield f"assembly.connectors.{c.id}", f"unknown part {c.part!r}; parts: {sorted(parts)}"
        if c.x[1] == c.z[1]:
            yield f"assembly.connectors.{c.id}", f"x {c.x!r} must be perpendicular to z {c.z!r}"
    yield from _joint_errors(design, owner)
    values = design.param_values()
    for path, e in _exprs(design):
        try:
            evaluate(e, values)
        except ExprError as err:
            yield path, str(err)


def _joint_errors(design: Design, owner: dict[str, str]) -> Iterator[Problem]:
    assert design.assembly is not None
    placed: dict[str, str] = {}
    for j in design.assembly.joints:
        where = f"assembly.joints.{j.id}"
        missing = [c for c in (j.parent, j.child) if c not in owner]
        if missing:
            yield where, f"unknown connectors {missing}; known: {sorted(owner)}"
        elif owner[j.parent] == owner[j.child]:
            yield where, f"both connectors are on part {owner[j.child]!r}"
        elif owner[j.child] in placed:
            yield where, f"part {owner[j.child]!r} is already placed by another joint; a part is the child of one joint at most"
        else:
            placed[owner[j.child]] = owner[j.parent]
    for start in placed:
        seen, part = {start}, placed[start]
        while part in placed:
            if part in seen:
                yield "assembly.joints", f"joints form a loop through part {part!r}; one part must stay fixed"
                return
            seen.add(part)
            part = placed[part]


def _depth(tree: dict[str, tuple[Joint, str]], part: str) -> int:
    depth = 0
    while part in tree and depth <= len(tree):
        part, depth = tree[part][1], depth + 1
    return depth


def _exprs(design: Design) -> Iterator[tuple[str, Expr]]:
    if design.assembly is None:
        return
    for c in design.assembly.connectors:
        yield from ((f"assembly.connectors.{c.id}.origin[{i}]", e) for i, e in enumerate(c.origin))
    for j in design.assembly.joints:
        yield from ((f"assembly.joints.{j.id}.{n}", e) for n, e in (("angle", j.angle), ("offset", j.offset)))

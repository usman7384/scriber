from scriber_api.schemas import FeatureNode, PartTree, Structure
from scriber_geometry import PartStructure
from scriber_ir import Design, feature_params
from scriber_ir.assembly import effective_assembly, joint_tree

AXES = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}


def structure(design: Design, parts: dict[str, PartStructure]) -> Structure:
    uses = feature_params(design)
    axes = _joint_axes(design, parts)
    return Structure(
        parts=[
            PartTree(
                id=p.id,
                name=p.name,
                features=[
                    FeatureNode(
                        id=f.id,
                        name=f.name,
                        kind=f.kind,
                        intent=f.intent,
                        params=uses[(p.id, f.id)],
                        faces=parts[p.id].features.get(f.id, []),
                    )
                    for f in p.features
                ],
                faces=parts[p.id].faces,
                explode=axes.get(p.id),
            )
            for p in design.parts
            if p.id in parts
        ]
    )


# A mated part slides along its joint's axis: the child connector's z, turned by where the part sits.
def _joint_axes(design: Design, parts: dict[str, PartStructure]) -> dict[str, tuple[float, float, float]]:
    a = effective_assembly(design)
    if a is None:
        return {}
    connectors = {c.id: c for c in a.connectors}
    axes = {}
    for child, (joint, _) in joint_tree(design).items():
        z = AXES[connectors[joint.child].z]
        m = parts[child].placement
        axes[child] = (
            m[0] * z[0] + m[1] * z[1] + m[2] * z[2],
            m[4] * z[0] + m[5] * z[1] + m[6] * z[2],
            m[8] * z[0] + m[9] * z[1] + m[10] * z[2],
        )
    return axes

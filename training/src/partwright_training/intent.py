from dataclasses import replace

from partwright_ir.model import Feature
from partwright_training.spec import Spec

# design intent for the S1/S2 generators' features, by feature id; the S3 families write their own
BY_ID = {
    "plate": "the plate everything else is cut into",
    "block": "the solid the ports and holes are machined into",
    "box": "outer envelope of the box",
    "body": "the main body of the part",
    "flange": "the flange disc that bolts to the mating flange",
    "boss": "raised seat for the port fitting",
    "pocket": "removes material where nothing bears on it",
    "cutout": "access opening in the wall",
    "hollow": "hollows the part out, leaving even walls",
    "corners": "softens the outside corners",
    "pocket_corners": "a cutter radius in the pocket corners",
    "bend": "inside bend radius of the formed corner",
    "top_chamfer": "breaks the sharp top edges",
    "end_chamfer": "lead-in chamfer on the end",
    "mounts": "bolt the part down",
    "corner_holes": "fix the plate at its corners",
    "bolt_holes": "bolt circle for the mating part",
    "screw_holes": "motor mounting screws",
    "flange_holes": "bolt the flange to its mating part",
    "hole_grid": "fixing pattern across the plate",
    "row_hole": "first hole of the fixing row",
    "hole_row": "repeats the fixing hole along the row",
    "floor_holes": "fix the box through its floor",
    "base_hole": "fix the base",
    "base_holes": "fix the base",
    "upright_holes": "fix the part mounted on the upright",
    "pin_hole": "pivot pin through both walls",
    "bore": "the shaft or pipe passes through here",
    "pilot": "centres the motor on its spigot",
    "centre_hole": "centre for turning between centres",
    "boss_bore": "the port through the boss",
    "port": "fluid connection",
    "front_port": "fluid connection on the front face",
    "side_port": "fluid connection on the side",
    "passage": "joins the ports inside the block",
    "slot_holes": "screws into the extrusion slots",
    "arm_hole": "first fixing hole along the arm",
    "arm_holes": "fixing holes in the arms",
    "arm_row": "repeats the arm hole along the arm",
    "arm_mirror": "the same hole in the other arm",
    "bar_hole": "first fixing hole on the bar",
    "bar_row": "one hole on each slot along the bar",
    "stem_hole": "fixing hole down the stem",
    "stem_row": "one hole on each slot down the stem",
    "corner_hole": "fixing hole in the gusset corner",
}
BY_KIND = {
    "extrude": "adds the material for this section",
    "revolve": "the turned body",
    "hole": "fixing or clearance hole",
    "pattern": "repeats the feature",
    "fillet": "rounds the edges",
    "chamfer": "breaks the edges",
    "shell": "hollows the part",
}


def intended(spec: Spec) -> Spec:
    parts = [p.model_copy(update={"features": [_with_intent(f) for f in p.features]}) for p in spec.design.parts]
    return replace(spec, design=spec.design.model_copy(update={"parts": parts}))


def _with_intent(f: Feature) -> Feature:
    if f.intent:
        return f
    return f.model_copy(update={"intent": BY_ID.get(f.id, BY_KIND.get(f.kind, "as requested"))})

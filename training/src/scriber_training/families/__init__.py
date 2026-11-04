import random
from collections.abc import Callable

from scriber_training.families.assemblies import assembly
from scriber_training.families.blocks import block
from scriber_training.families.boxes import box
from scriber_training.families.brackets import bracket
from scriber_training.families.enclosures import enclosure
from scriber_training.families.gears import gear
from scriber_training.families.housings import housing
from scriber_training.families.plates import plate
from scriber_training.families.profiles import profile
from scriber_training.families.pulleys import pulley
from scriber_training.families.shafts import shaft
from scriber_training.families.standards import standard
from scriber_training.families.supports import support
from scriber_training.families.tables import table
from scriber_training.families.turned import turned
from scriber_training.spec import Spec

FAMILIES: dict[str, Callable[[random.Random], Spec]] = {
    "plate": plate,
    "block": block,
    "turned": turned,
    "bracket": bracket,
    "box": box,
    "profile": profile,
    "standard": standard,
}
# S3 adds the high-level features, assemblies and hole tables; S1/S2 runs keep FAMILIES alone
S3_FAMILIES: dict[str, Callable[[random.Random], Spec]] = {
    **FAMILIES,
    "gear": gear,
    "pulley": pulley,
    "shaft": shaft,
    "housing": housing,
    "enclosure": enclosure,
    "assembly": assembly,
    "support": support,
    "table": table,
}

import random
from collections.abc import Callable

from partwright_training.families.assemblies import assembly
from partwright_training.families.blocks import block
from partwright_training.families.boxes import box
from partwright_training.families.brackets import bracket
from partwright_training.families.enclosures import enclosure
from partwright_training.families.gears import gear
from partwright_training.families.housings import housing
from partwright_training.families.plates import plate
from partwright_training.families.profiles import profile
from partwright_training.families.pulleys import pulley
from partwright_training.families.shafts import shaft
from partwright_training.families.standards import standard
from partwright_training.families.supports import support
from partwright_training.families.tables import table
from partwright_training.families.turned import turned
from partwright_training.spec import Spec

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

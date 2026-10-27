import random
from collections.abc import Callable

from partwright_training.families.blocks import block
from partwright_training.families.boxes import box
from partwright_training.families.brackets import bracket
from partwright_training.families.plates import plate
from partwright_training.families.profiles import profile
from partwright_training.families.standards import standard
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

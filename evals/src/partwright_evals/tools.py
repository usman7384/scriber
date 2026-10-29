import os
from pathlib import Path

FREECAD = "PARTWRIGHT_FREECAD"
PRUSASLICER = "PARTWRIGHT_PRUSASLICER"


def tool(variable: str) -> Path | None:
    value = os.environ.get(variable)
    return Path(value) if value else None


def missing(variable: str) -> str:
    return f"not configured: {variable} is unset"

from pathlib import Path
from typing import Any

from build123d import Edge, ExportDXF, Shape, Unit


def export_flats(flats: list[tuple[str, Shape[Any], list[Edge]]], path: Path) -> Path:
    # the flat pattern a shop cuts from: the outline with holes, and the bend lines on a layer of their own
    dxf = ExportDXF(unit=Unit.MM).add_layer("outline").add_layer("bends")
    for _, flat, lines in flats:
        dxf.add_shape(flat, layer="outline")
        dxf.add_shape(lines, layer="bends")
    dxf.write(path)
    return path

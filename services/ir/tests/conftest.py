from collections.abc import Sequence

import pytest

from partwright_ir import Design


@pytest.fixture
def bracket() -> Design:
    return Design.model_validate(
        {
            "title": "Mounting bracket",
            "params": [
                {"name": "plate_length", "value": 80, "unit": "mm"},
                {"name": "plate_width", "value": 60, "unit": "mm"},
                {"name": "thickness", "value": 5, "unit": "mm", "min": 1},
                {"name": "hole_diameter", "value": 6.6, "unit": "mm"},
                {"name": "hole_margin", "value": 10, "unit": "mm"},
            ],
            "parts": [
                {
                    "id": "bracket",
                    "name": "Bracket",
                    "sketches": [{"id": "outline", "entities": [{"kind": "rect", "width": "plate_length", "height": "plate_width"}]}],
                    "features": [
                        {"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness"},
                        {
                            "kind": "hole",
                            "id": "mount_holes",
                            "name": "Mounting holes",
                            "plane": {"offset": "thickness"},
                            "at": {
                                "kind": "grid",
                                "count_x": 2,
                                "count_y": 2,
                                "spacing_x": "plate_length - 2 * hole_margin",
                                "spacing_y": "plate_width - 2 * hole_margin",
                            },
                            "diameter": "hole_diameter",
                        },
                    ],
                }
            ],
        }
    )


@pytest.fixture
def wing() -> Design:
    def section(sid: str, offset: str | float, chord: str, le: Sequence[str | float], twist: str | float) -> dict[str, object]:
        plane = {"ref": "XZ", "offset": offset}
        return {
            "kind": "airfoil_section",
            "id": sid,
            "name": sid,
            "plane": plane,
            "naca": "2412",
            "chord": chord,
            "leading_edge": le,
            "twist": twist,
        }

    tip_le = ["wing_span / 2 * tan(sweep)", "wing_span / 2 * tan(dihedral)"]
    return Design.model_validate(
        {
            "title": "Wing",
            "params": [
                {"name": "wing_span", "value": 1000, "unit": "mm"},
                {"name": "root_chord", "value": 250, "unit": "mm"},
                {"name": "tip_chord", "value": 120, "unit": "mm"},
                {"name": "sweep", "value": 20, "unit": "deg"},
                {"name": "dihedral", "value": 5, "unit": "deg"},
                {"name": "twist", "value": 2, "unit": "deg"},
            ],
            "parts": [
                {
                    "id": "wing",
                    "name": "Wing",
                    "sketches": [],
                    "features": [
                        section("root_airfoil", 0, "root_chord", [0, 0], 0),
                        section("tip_airfoil", "wing_span / 2", "tip_chord", tip_le, "-twist"),
                        {
                            "kind": "loft",
                            "id": "main_wing",
                            "name": "main_wing",
                            "sections": ["root_airfoil", "tip_airfoil"],
                            "ruled": True,
                        },
                        {
                            "kind": "pattern",
                            "id": "full_wing",
                            "name": "full_wing",
                            "features": ["main_wing"],
                            "type": "mirror",
                            "mirror_plane": "XZ",
                        },
                    ],
                }
            ],
        }
    )

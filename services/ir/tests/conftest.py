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

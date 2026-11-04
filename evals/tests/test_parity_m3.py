import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from scriber_agent import FakeLLM, Message
from scriber_cli.config import load
from scriber_evals.parity import Rig, run_row
from scriber_evals.parity_m3 import FIXTURES, ROWS
from scriber_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})
PLATE = (FIXTURES / "base_plate.json").read_text(encoding="utf-8")


def plate(length: float, width: float, thickness: float) -> str:
    design = json.loads(PLATE)
    values = {"length": length, "width": width, "thickness": thickness}
    design["params"] = [{**p, "value": values.get(p["name"], p["value"])} for p in design["params"]]
    return json.dumps(design)


def updates(**values: float) -> str:
    return json.dumps({"updates": [{"name": k, "value": v} for k, v in values.items()], "design": None})


BRACKET = json.dumps(
    {
        "title": "Angled bracket",
        "params": [{"name": "hole_d", "value": 5.5, "unit": "mm"}],
        "parts": [
            {
                "id": "bracket",
                "name": "Bracket",
                "sketches": [
                    {"id": "s", "entities": [{"kind": "rect", "width": 70, "height": 50}]},
                    {"id": "g", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [[-20, 5], [20, 5], [-20, 45]]}]},
                ],
                "features": [
                    {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 5},
                    {"kind": "extrude", "id": "gusset", "name": "Gusset", "sketch": "g", "extent": "symmetric", "distance": 5},
                    {
                        "kind": "hole",
                        "id": "holes",
                        "name": "Screw holes",
                        "plane": {"offset": 5},
                        "at": {"kind": "points", "points": [[25, 15], [25, -15]]},
                        "diameter": "hole_d",
                    },
                ],
            }
        ],
    }
)
BEAM = json.dumps(
    {
        "title": "Support beam",
        "params": [
            {"name": "span", "value": 1000, "unit": "mm", "provenance": {"source": "document", "ref": "{span}"}},
            {"name": "width", "value": 60, "unit": "mm"},
            {"name": "height", "value": 40, "unit": "mm"},
        ],
        "parts": [
            {
                "id": "beam",
                "name": "Beam",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "span", "height": "width"}]}],
                "features": [{"kind": "extrude", "id": "body", "name": "Beam", "sketch": "s", "distance": "height"}],
            }
        ],
    }
)
SUGGESTIONS = json.dumps(
    {
        "suggestions": [
            {"target": "thickness", "change": {"thickness": 6}, "rationale": "a stiffer plate under the bolt load"},
            {"target": "hole_d", "change": {"hole_d": 7}, "rationale": "more room for positional tolerance"},
        ]
    }
)
ANSWERS: dict[str, list[str]] = {
    "IN-16": [NO_REQS, plate(150, 90, 6), NO_REQS, PLATE],
    "IN-17": [NO_REQS, updates(length=150, width=90)],
    "GE-9": [json.dumps({"param": "rib_count", "values": [4, 6, 8]})],
    "GE-13": [NO_REQS, PLATE] * 10,
    "PR-7": [SUGGESTIONS],
    "AP-2": [NO_REQS, BRACKET],
    "AP-3": [NO_REQS, updates(thickness=15)],
    "AP-7": [NO_REQS, PLATE] * 10,
    "CD-1": [NO_REQS, BEAM],
    "WP-6": [NO_REQS, PLATE],
    "CX-3": [NO_REQS, PLATE],
}


class Citing(FakeLLM):
    # stands in for a model that cites the spec fact it read in the project block
    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str:
        answer = super().chat(messages, schema, seed, temperature, think)
        found = re.search(r"\[([^\]]+)\] beam_span", "\n".join(m.content for m in messages))
        return answer.replace("{span}", found.group(1)) if found else answer


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


@pytest.mark.parametrize("row", sorted(ROWS))
def test_m3_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    llm = Citing(ANSWERS.get(row, []))
    rig = Rig(tmp_path, geometry, llm, load(ROOT / "config.yaml"))
    ev = run_row(row, ROWS[row], rig)
    assert ev.passed, ev
    assert llm.responses == [], f"{row} left scripted answers unused"
    assert (tmp_path / row / "transcript.jsonl").stat().st_size > 0


def test_m3_failing_model_is_a_failed_row(geometry: LocalGeometry, tmp_path: Path) -> None:
    rig = Rig(tmp_path, geometry, FakeLLM([NO_REQS, updates(thickness=12)]), load(ROOT / "config.yaml"))
    ev = run_row("AP-3", ROWS["AP-3"], rig)
    assert not ev.passed and ev.measured["after"] == 12

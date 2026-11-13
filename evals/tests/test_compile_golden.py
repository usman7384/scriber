import hashlib
from pathlib import Path

import pytest

from scriber_agent.prompts import EXAMPLES
from scriber_ir import Design, answer_json, compile_design

M1 = Path(__file__).parents[1] / "parity" / "m1"
DESIGNS = {d["title"]: Design.model_validate(d) for _, d in EXAMPLES} | {
    p.stem: Design.model_validate_json(p.read_text(encoding="utf-8")) for p in M1.glob("*.json")
}
# compiled source and answer JSON recorded before airfoil sections and lofts were added; source re-recorded when blends became skippable
GOLDEN = {
    "Round cover plate": ("e1240c65805d02ae", "555c8f7c76680338"),
    "Angle bracket": ("b601297fb38bdf98", "b6daa6c0a58a7fca"),
    "Open-top tray": ("2d41045fbc61e873", "d039d771327e4af4"),
    "Flanged bushing": ("2e6a903b532ad762", "ada009029f4a7c0a"),
    "Valve block": ("94b40496f8035662", "a16c02e323b9038e"),
    "glider": ("9a263cb2526fd64d", "0e6d496d58f0124d"),
    "tube": ("ec018f50aa85055f", "6839ee4304487007"),
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_v2_designs_compile_byte_identically(name: str) -> None:
    design = DESIGNS[name]
    assert (_sha(compile_design(design)), _sha(answer_json(design))) == GOLDEN[name]

import hashlib
from pathlib import Path

import pytest

from partwright_agent.prompts import EXAMPLES
from partwright_ir import Design, answer_json, compile_design

M1 = Path(__file__).parents[1] / "parity" / "m1"
DESIGNS = {d["title"]: Design.model_validate(d) for _, d in EXAMPLES} | {
    p.stem: Design.model_validate_json(p.read_text(encoding="utf-8")) for p in M1.glob("*.json")
}
# compiled source and answer JSON recorded before airfoil sections and lofts were added (D-030 aircraft rows)
GOLDEN = {
    "Round cover plate": ("342a21bd816d2c6e", "555c8f7c76680338"),
    "Angle bracket": ("542afd469e38e056", "b6daa6c0a58a7fca"),
    "Open-top tray": ("f970e4a5aacef180", "d039d771327e4af4"),
    "Flanged bushing": ("ad78500e3c5b1662", "ada009029f4a7c0a"),
    "Valve block": ("2713cb53955e194d", "a16c02e323b9038e"),
    "glider": ("3a041ba20057612c", "0e6d496d58f0124d"),
    "tube": ("ef42c1df9bbb6ca4", "6839ee4304487007"),
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_v2_designs_compile_byte_identically(name: str) -> None:
    design = DESIGNS[name]
    assert (_sha(compile_design(design)), _sha(answer_json(design))) == GOLDEN[name]

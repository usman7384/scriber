import hashlib

import pytest

from partwright_agent.prompts import EXAMPLES
from partwright_ir import Design, answer_json, compile_design, design_hash

# compiled source, design hash and answer JSON of the worked examples before assemblies were added to the IR
GOLDEN = {
    "Round cover plate": ("342a21bd816d2c6e", "4a9c157051247440", "555c8f7c76680338"),
    "Angle bracket": ("542afd469e38e056", "5c2d3640448584a1", "b6daa6c0a58a7fca"),
    "Open-top tray": ("f970e4a5aacef180", "07ea67c86b57b9ee", "d039d771327e4af4"),
    "Flanged bushing": ("ad78500e3c5b1662", "6bf5da07fc4e59a1", "ada009029f4a7c0a"),
    "Valve block": ("2713cb53955e194d", "6d252b532273946e", "a16c02e323b9038e"),
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@pytest.mark.parametrize("example", [d for _, d in EXAMPLES], ids=lambda d: str(d["title"]))
def test_designs_without_assembly_compile_and_hash_byte_identically(example: dict[str, object]) -> None:
    design = Design.model_validate(example)
    assert (sha(compile_design(design)), design_hash(design), sha(answer_json(design))) == GOLDEN[design.title]

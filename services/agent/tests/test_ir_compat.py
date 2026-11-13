import hashlib

import pytest

from scriber_agent.prompts import EXAMPLES
from scriber_ir import Design, answer_json, compile_design, design_hash

# compiled source, design hash and answer JSON of the worked examples before assemblies were added to the IR;
# source re-recorded when blends became skippable
GOLDEN = {
    "Round cover plate": ("e1240c65805d02ae", "4a9c157051247440", "555c8f7c76680338"),
    "Angle bracket": ("b601297fb38bdf98", "5c2d3640448584a1", "b6daa6c0a58a7fca"),
    "Open-top tray": ("2d41045fbc61e873", "07ea67c86b57b9ee", "d039d771327e4af4"),
    "Flanged bushing": ("2e6a903b532ad762", "6bf5da07fc4e59a1", "ada009029f4a7c0a"),
    "Valve block": ("94b40496f8035662", "6d252b532273946e", "a16c02e323b9038e"),
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@pytest.mark.parametrize("example", [d for _, d in EXAMPLES], ids=lambda d: str(d["title"]))
def test_designs_without_assembly_compile_and_hash_byte_identically(example: dict[str, object]) -> None:
    design = Design.model_validate(example)
    assert (sha(compile_design(design)), design_hash(design), sha(answer_json(design))) == GOLDEN[design.title]

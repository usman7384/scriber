from pathlib import Path

from partwright_agent import FakeLLM
from partwright_geometry import LocalGeometry
from partwright_training.collect import collect


def test_failing_answers_become_repairs_with_the_verified_target(geometry: LocalGeometry, tmp_path: Path) -> None:
    llm = FakeLLM(['{"title": "cut off'] * 7)
    samples = list(collect(range(7), llm, geometry, tmp_path))
    assert samples and len(samples) == len(llm.calls)
    for s in samples:
        roles = [r for r, _ in s.messages]
        assert roles == ["system", "user", "user", "assistant"]
        assert "cut off before it was complete JSON" in s.messages[2][1]
        assert s.detail == "on-policy fake"

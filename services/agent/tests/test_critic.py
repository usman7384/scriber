import json

import pytest
from pydantic import ValidationError

from scriber_agent import FakeLLM, critique


def test_critic_sends_the_views_and_reads_the_verdict() -> None:
    llm = FakeLLM([json.dumps({"findings": ["only 3 of the 4 corner holes"], "matches": False})])
    verdict = critique("plate with 4 corner holes", [b"iso", b"plan"], llm)
    assert not verdict.matches and verdict.findings == ("only 3 of the 4 corner holes",)
    assert llm.calls[0][-1].images == (b"iso", b"plan") and "4 corner holes" in llm.calls[0][-1].content


def test_critic_fails_fast_on_a_malformed_answer() -> None:
    with pytest.raises(ValidationError):
        critique("plate", [b"iso"], FakeLLM(["not json"]))

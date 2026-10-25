from pathlib import Path

from partwright_context import ProposedFact
from partwright_context.extract import process
from partwright_context.parsed import Line
from partwright_context.proposals import grounded

LINES = [Line(1, 1, "Bracket report"), Line(1, 2, "The design load is two thousand newtons, i.e. 2000 N, applied at the tip.")]


def test_only_proposals_quoted_from_the_chunk_with_their_value_survive() -> None:
    proposals = [
        ProposedFact(name="design load", value=2000, unit="N", quote="2000 N, applied at the tip"),
        ProposedFact(name="invented", value=12, unit="mm", quote="a 12 mm boss"),
        ProposedFact(name="wrong value", value=3000, unit="N", quote="2000 N, applied"),
        ProposedFact(name="bad unit", value=2000, unit="furlong", quote="2000 N"),
    ]
    [fact] = grounded("d0", LINES, proposals, [])
    assert (fact.name, fact.value, fact.unit, fact.line) == ("design_load", 2000.0, "N", 2)
    assert fact.source.ref == "d0#p1:l2"


def test_processing_runs_the_injected_proposer_after_the_deterministic_pass(tmp_path: Path) -> None:
    doc = tmp_path / "report.txt"
    doc.write_text("Tip load: 2 kN\nUse a safety factor of 2.5 for all brackets.\n", encoding="utf-8")
    calls: list[str] = []

    def propose(text: str) -> list[ProposedFact]:
        calls.append(text)
        return [
            ProposedFact(name="tip load", value=2, unit="kN", quote="Tip load: 2 kN"),
            ProposedFact(name="safety factor", value=2.5, quote="safety factor of 2.5"),
        ]

    found = [(f.name, f.value, f.unit) for f in process(doc, "0" * 64, None, propose).facts]
    assert len(calls) == 1
    assert found.count(("tip_load", 2000.0, "N")) == 1
    assert ("safety_factor", 2.5, "") in found

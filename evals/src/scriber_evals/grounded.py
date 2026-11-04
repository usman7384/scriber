import argparse
import json
import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from scriber_agent import LLM, Grounding, Requirement, Step, check, generate
from scriber_cli.config import llm_for, load
from scriber_context import Fact, LocalContext, OllamaEmbedder, document_text
from scriber_geometry import BuildError, LocalGeometry
from scriber_ir import Process, RuleKind, RuleSet

Mode = Literal["prompt", "grounded"]


class LabelFact(BaseModel):
    kind: str
    value: float | str
    count: int | None = None
    at: tuple[float, float] | None = None


class LabelRule(BaseModel):
    kind: RuleKind
    value: float


class Case(BaseModel):
    id: str
    rows: list[str]
    request: str
    process: Process
    checks: list[Requirement]
    facts: list[LabelFact]
    rules: list[LabelRule]


class Score(BaseModel):
    tp: int
    fp: int
    fn: int


class ModeResult(BaseModel):
    mode: Mode
    built: bool
    checks_passed: int
    checks_total: int
    failed_checks: list[str]
    rule_errors: list[str]
    rule_warnings: int
    params: int
    cited: int
    cited_correct: int
    attempts: int
    seconds: float

    @property
    def passed(self) -> bool:
        return self.built and self.checks_passed == self.checks_total and not self.rule_errors


class CaseReport(BaseModel):
    id: str
    facts: Score
    rules: Score
    retrieval_recall: float | None
    modes: list[ModeResult]


def load_cases(path: Path) -> list[Case]:
    return [Case.model_validate(c) for c in yaml.safe_load(path.read_text(encoding="utf-8"))]


def score_facts(labels: list[LabelFact], facts: list[Fact]) -> tuple[Score, list[Fact]]:
    free, matched = list(facts), []
    for label in labels:
        hit = next((f for f in free if _same(label, f)), None)
        if hit is not None:
            free.remove(hit)
            matched.append(hit)
    return Score(tp=len(matched), fp=len(free), fn=len(labels) - len(matched)), matched


def score_rules(labels: list[LabelRule], rules: RuleSet) -> Score:
    found = [(r.kind, r.value) for r in rules.rules if r.source.ref]
    hits = sum(any(k == lab.kind and abs(v - lab.value) < 1e-6 for k, v in found) for lab in labels)
    return Score(tp=hits, fp=len(found) - hits, fn=len(labels) - hits)


def _same(label: LabelFact, fact: Fact) -> bool:
    if label.kind != fact.kind:
        return False
    if isinstance(label.value, str) or isinstance(fact.value, str):
        same = str(label.value).casefold() == str(fact.value).casefold()
    else:
        same = abs(label.value - fact.value) < 1e-6
    return same and (label.count is None or label.count == fact.count) and (label.at is None or label.at == fact.at)


def run_case(case: Case, files: Path, llm: LLM, geometry: LocalGeometry, ctx: LocalContext, out: Path) -> CaseReport:
    paths = sorted(p for p in (files / case.id).iterdir() if p.is_file())
    for p in paths:
        ctx.ingest(case.id, p)
    facts, matched = score_facts(case.facts, ctx.facts(case.id))
    project_rules = ctx.rules(case.id)
    pack = ctx.retrieve(case.id, case.request)
    in_pack = {f.id for f in [*pack.facts, *pack.conventions]}
    recall = sum(f.id in in_pack for f in matched) / len(matched) if matched else None
    docs = "\n\n".join(f"## {p.name}\n{document_text(p, geometry.describe)}" for p in paths)
    prompt_only = f"{case.request}\n\nProject documents:\n{docs}"
    grounding = Grounding(pack=pack, rules=project_rules, process=case.process)
    rules = project_rules.for_process(case.process)
    modes = [
        _run_mode("prompt", case, list(generate(prompt_only, llm, geometry, out / case.id / "prompt")), rules, geometry, ctx, out),
        _run_mode(
            "grounded",
            case,
            list(generate(case.request, llm, geometry, out / case.id / "grounded", context=grounding)),
            rules,
            geometry,
            ctx,
            out,
        ),
    ]
    return CaseReport(id=case.id, facts=facts, rules=score_rules(case.rules, project_rules), retrieval_recall=recall, modes=modes)


def _run_mode(
    mode: Mode, case: Case, steps: list[Step], rules: RuleSet, geometry: LocalGeometry, ctx: LocalContext, out: Path
) -> ModeResult:
    r = steps[-1].result
    design = r.design if r and r.artifact else None
    artifact, errors, warnings = None, [], 0
    if design is not None:
        try:
            artifact = geometry.build(design, out / case.id / f"{mode}-scored", rules, case.process)
            errors = [f"{f.rule_id}: {f.message}" for f in artifact.findings if f.severity == "error"]
            warnings = sum(f.severity == "warning" for f in artifact.findings)
        except BuildError as e:
            errors = [f"rebuild failed: {e}"]
    results = check(case.checks, artifact) if artifact else []
    refs = {(f.source.ref, f.value) for f in ctx.facts(case.id)}
    cited = [p for p in design.params if p.provenance.source == "document"] if design else []
    return ModeResult(
        mode=mode,
        built=artifact is not None,
        checks_passed=sum(c.passed for c in results),
        checks_total=len(case.checks),
        failed_checks=[f"{c.requirement.description}: {c.actual}" for c in results if not c.passed],
        rule_errors=errors,
        rule_warnings=warnings,
        params=len(design.params) if design else 0,
        cited=len(cited),
        cited_correct=sum((p.provenance.ref, p.value) in refs for p in cited),
        attempts=r.attempts if r else 0,
        seconds=steps[-1].elapsed_ms / 1000,
    )


def scorecard(reports: list[CaseReport]) -> str:
    def total(attr: str) -> Score:
        return Score(**{k: sum(getattr(getattr(r, attr), k) for r in reports) for k in ("tp", "fp", "fn")})

    def pr(s: Score) -> str:
        p = s.tp / (s.tp + s.fp) if s.tp + s.fp else 0.0
        rc = s.tp / (s.tp + s.fn) if s.tp + s.fn else 0.0
        return f"P {p:.2f} / R {rc:.2f} ({s.tp} tp, {s.fp} fp, {s.fn} fn)"

    recalls = [r.retrieval_recall for r in reports if r.retrieval_recall is not None]
    lines = [
        "## Extraction and retrieval",
        "",
        f"- Facts: {pr(total('facts'))}",
        f"- Rules: {pr(total('rules'))}",
        f"- Retrieval: {sum(recalls) / len(recalls):.2f} of extracted labelled facts reach the context pack ({len(recalls)} cases)",
        "",
        "## Generation: prompt-only vs grounded",
        "",
        "| mode | fully passing | built | checks | rule errors | params cited (correct / cited / all) | median s |",
        "|---|---|---|---|---|---|---|",
    ]
    for mode in ("prompt", "grounded"):
        ms = [m for r in reports for m in r.modes if m.mode == mode]
        secs = sorted(m.seconds for m in ms)[len(ms) // 2]
        lines.append(
            f"| {mode} | {sum(m.passed for m in ms)}/{len(ms)} | {sum(m.built for m in ms)}/{len(ms)} "
            f"| {sum(m.checks_passed for m in ms)}/{sum(m.checks_total for m in ms)} | {sum(len(m.rule_errors) for m in ms)} "
            f"| {sum(m.cited_correct for m in ms)} / {sum(m.cited for m in ms)} / {sum(m.params for m in ms)} | {secs:.0f} |"
        )
    lines += ["", "| case | facts P/R | rules | retrieval | prompt | grounded |", "|---|---|---|---|---|---|"]
    for r in reports:
        modes = {m.mode: m for m in r.modes}
        cells = [_cell(modes[m]) for m in ("prompt", "grounded")]
        ret = "-" if r.retrieval_recall is None else f"{r.retrieval_recall:.2f}"
        facts = f"{r.facts.tp}/{r.facts.tp + r.facts.fp} found, {r.facts.fn} missed"
        lines.append(f"| {r.id} | {facts} | {r.rules.tp}/{r.rules.tp + r.rules.fn} | {ret} | {cells[0]} | {cells[1]} |")
    return "\n".join(lines) + "\n"


def _cell(m: ModeResult) -> str:
    if not m.built:
        return f"not built ({m.attempts} attempts)"
    status = "PASS" if m.passed else "fail"
    rules = f", {len(m.rule_errors)} rule errors" if m.rule_errors else ""
    return f"{status} {m.checks_passed}/{m.checks_total}{rules}, cited {m.cited_correct}/{m.params}"


def main() -> None:
    p = argparse.ArgumentParser(prog="scriber-grounded")
    p.add_argument("--cases", type=Path, default=Path("evals/grounded/cases.yaml"))
    p.add_argument("--files", type=Path, default=Path("evals/grounded/files"))
    p.add_argument("--out", type=Path, default=Path("evals/results"))
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--model")
    args = p.parse_args()
    config = load(args.config)
    run_dir = args.out / f"grounded-{time.strftime('%Y%m%d-%H%M%S')}"
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    reports: list[CaseReport] = []
    try:
        embedder = OllamaEmbedder(config.embeddings.model, host=config.llm.host)
        with LocalContext(run_dir / "data", embedder, describe=geometry.describe) as ctx:
            for case in load_cases(args.cases):
                report = run_case(case, args.files, llm_for(config, args.model), geometry, ctx, run_dir / "cases")
                reports.append(report)
                print(json.dumps(report.model_dump()), flush=True)
    finally:
        geometry.close()
    (run_dir / "results.json").write_text(json.dumps([r.model_dump() for r in reports], indent=2), encoding="utf-8")
    (run_dir / "SCORECARD.md").write_text(scorecard(reports), encoding="utf-8")
    print(scorecard(reports))


if __name__ == "__main__":
    main()

# Claude subagents act as the agent's model (see docs/agents/training.md); scoring uses our own pipeline
import json
import sys
from pathlib import Path

from partwright_agent import design_messages, evaluate, repair_message, requirement_messages
from partwright_agent.grounding import grounded
from partwright_agent.requirements import Requirement, RequirementList, check
from partwright_agent.standards import reference_data
from partwright_evals.run import design_checks, load_cases
from partwright_geometry import LocalGeometry
from partwright_ir import Design, json_schema

ROOT = Path(__file__).parent
REPO = Path("D:/Projects/bye-kyrall")
CASES = [*load_cases(REPO / "evals/cases/m1.yaml"), *load_cases(REPO / "evals/cases/challenge.yaml")]
MAX_ATTEMPTS = 4
HEADER = (
    "You are the language model inside a CAD design agent. Read nothing except this file. "
    "Answer exactly as the assistant's next message in the conversation below: one JSON object, no prose, no code fences. "
    "Write that JSON, and only it, to the file named at the end, then reply 'done'.\n"
)


def render(messages: list[tuple[str, str]], schema: dict[str, object], out: Path) -> str:
    parts = [HEADER, "=== JSON SCHEMA THE ANSWER MUST SATISFY ===", json.dumps(schema, separators=(",", ":")), "", "=== CONVERSATION ==="]
    parts += [f"[{role}]\n{text}\n" for role, text in messages]
    parts.append(f"=== WRITE YOUR ANSWER TO ===\n{out}")
    return "\n".join(parts)


def task(case_id: str) -> list[tuple[str, str]]:
    case = next(c for c in CASES if c.id == case_id)
    return design_messages(case.prompt, reference_data(case.prompt), "", few_shot=True)


def prompts() -> None:
    for c in CASES:
        d = ROOT / c.id
        d.mkdir(exist_ok=True)
        (d / "prompt_1.md").write_text(render(task(c.id), json_schema(), d / "answer_1.json"), encoding="utf-8")
    schema = RequirementList.model_json_schema()
    reqs = "\n\n".join(render(requirement_messages(c.prompt), schema, ROOT / c.id / "requirements.json") for c in CASES)
    (ROOT / "requirements_prompt.md").write_text(
        "This file holds one independent task per case. Do each one separately and write each answer to its own file.\n\n" + reqs,
        encoding="utf-8",
    )
    print(len(CASES), "cases")


def _reqs(case_id: str) -> list[Requirement]:
    path = ROOT / case_id / "requirements.json"
    case = next(c for c in CASES if c.id == case_id)
    try:
        return grounded(RequirementList.model_validate_json(path.read_text(encoding="utf-8")).requirements, case.prompt)
    except (OSError, ValueError):
        return []


def score(case_id: str, attempt: int) -> None:
    d = ROOT / case_id
    raw = (d / f"answer_{attempt}.json").read_text(encoding="utf-8").strip().removeprefix("```json").removesuffix("```").strip()
    geometry = LocalGeometry()
    try:
        problems, design, artifact, _ = evaluate(raw, Design.model_validate_json, _reqs(case_id), geometry.build, d / f"build_{attempt}")
        result = {"attempt": attempt, "problems": problems, "built": artifact is not None, "valid": bool(artifact and artifact.ok)}
        if artifact is not None and design is not None:
            case = next(c for c in CASES if c.id == case_id)
            checks = [(c.requirement.description, c.passed, c.actual) for c in check(case.checks, artifact)]
            checks += design_checks(case, design, geometry, d / f"robust_{attempt}")
            result["checks"] = [{"name": n, "passed": p, "actual": a} for n, p, a in checks]
    finally:
        geometry.close()
    (d / f"result_{attempt}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if problems and attempt < MAX_ATTEMPTS:
        messages = [*task(case_id), ("user", repair_message(raw, problems, unchanged=False))]
        (d / f"prompt_{attempt + 1}.md").write_text(render(messages, json_schema(), d / f"answer_{attempt + 1}.json"), encoding="utf-8")
    status = "done" if not problems else ("retry" if attempt < MAX_ATTEMPTS else "failed")
    print(case_id, attempt, status, "; ".join(problems)[:300])


def report() -> None:
    rows = []
    for c in CASES:
        results = sorted((ROOT / c.id).glob("result_*.json"), key=lambda p: int(p.stem.split("_")[1]))
        last = json.loads(results[-1].read_text(encoding="utf-8")) if results else {"attempt": 0, "built": False, "valid": False}
        checks = last.get("checks", [])
        total = len(c.checks) + len(c.params) + len(c.robust)
        passed = sum(x["passed"] for x in checks)
        failed = "; ".join(f"{x['name']}: {x['actual']}" for x in checks if not x["passed"]) or "; ".join(last.get("problems", []))
        rows.append((c.id, last["built"], last["valid"], passed, total, last["attempt"], failed[:200]))
    print("| case | built | valid | checks | attempts | failed |\n|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]}/{r[4]} | {r[5]} | {r[6]} |")
    perfect = sum(r[1] and r[2] and r[3] == r[4] for r in rows)
    print(f"\nfully correct {perfect}/{len(rows)}, checks {sum(r[3] for r in rows)}/{sum(r[4] for r in rows)}")


if __name__ == "__main__":
    {"prompts": lambda: prompts(), "score": lambda: score(sys.argv[2], int(sys.argv[3])), "report": lambda: report()}[sys.argv[1]]()

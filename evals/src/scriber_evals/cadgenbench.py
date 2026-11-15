import argparse
import time
from collections.abc import Iterator
from pathlib import Path
from typing import get_args

import yaml
from build123d import Location, Plane, Vector, export_step, import_step
from pydantic import BaseModel

from scriber_agent import LLM, Step, dump_steps, generate
from scriber_agent.anthropic_llm import Effort
from scriber_agent.llm import Usage, usage_of
from scriber_cli.config import ModelOptions, llm_for, load
from scriber_geometry import LocalGeometry

AXES = (Vector(1, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1))


class Fixture(BaseModel):
    id: str
    prompt: str
    images: list[Path]
    editing: bool


class Outcome(BaseModel):
    id: str
    status: str
    attempts: int = 0
    seconds: float = 0.0
    message: str = ""
    tokens: str = ""


def fixtures(data: Path) -> Iterator[Fixture]:
    for d in sorted(p for p in data.iterdir() if (p / "description.yaml").is_file()):
        spec = yaml.safe_load((d / "description.yaml").read_text(encoding="utf-8"))
        editing = spec["input_type"] != "text+image"
        images = [] if editing else [d / f for f in spec["input_files"]]
        yield Fixture(id=d.name, prompt=spec["description"].strip(), images=images, editing=editing)


def last_built(task_dir: Path) -> Path | None:
    # a part that built but failed a check still beats an empty answer, so take the newest attempt with a STEP
    built = [d / "model.step" for d in task_dir.glob("attempt_*") if (d / "model.step").is_file()]
    return max(built, key=lambda s: int(s.parent.name.split("_")[1]), default=None)


def kept_step(task_dir: Path, steps: list[Step]) -> Path | None:
    # the part the loop judged best, not just the newest one that built
    result = steps[-1].result if steps else None
    if result is not None:
        chosen = task_dir / f"attempt_{result.attempts}" / "model.step"
        if chosen.is_file():
            return chosen
    return last_built(task_dir)


def orient(step_in: Path, step_out: Path) -> None:
    # the grader recommends a centred bounding box with extents Lx >= Ly >= Lz
    shape = import_step(step_in)
    box = shape.bounding_box()
    size = (box.size.X, box.size.Y, box.size.Z)
    order = sorted(range(3), key=lambda i: -size[i])
    frame = Plane(origin=box.center(), x_dir=AXES[order[0]], z_dir=AXES[order[2]])
    export_step(shape.moved(Location(frame).inverse()), step_out)


def attempt(
    f: Fixture, llm: LLM, vision: LLM, geometry: LocalGeometry, run: Path, work: Path, repairs: int, staged: bool = False
) -> Outcome:
    (run / f.id).mkdir(parents=True, exist_ok=True)  # an empty folder is scored as missing
    if f.editing:
        return Outcome(id=f.id, status="skipped", message="editing tasks need STEP import, which Scriber does not have")
    start = time.monotonic()
    metered = [llm] if vision is llm else [llm, vision]
    spent = sum((usage_of(m) for m in metered), Usage())
    images = tuple(p.read_bytes() for p in f.images)
    steps = list(generate(f.prompt, llm, geometry, work / f.id, repairs, images=images, vision=vision, staged=staged))
    seconds = round(time.monotonic() - start, 1)
    tokens = str(sum((usage_of(m) for m in metered), Usage()) - spent)
    (work / f.id / "steps.json").write_text(dump_steps(steps), encoding="utf-8")
    attempts = max((s.attempt for s in steps), default=0)
    step = kept_step(work / f.id, steps)
    if step is None:
        return Outcome(id=f.id, status="not built", attempts=attempts, seconds=seconds, message=steps[-1].message[:300], tokens=tokens)
    orient(step, run / f.id / "output.step")
    result = steps[-1].result
    aside = len(result.disputed) if result else 0
    done = "built" if not aside else f"built, {aside} of {len(result.checks) if result else 0} checks set aside"
    status = done if steps[-1].kind == "done" else f"built ({step.parent.name}), checks failed"
    return Outcome(id=f.id, status=status, attempts=attempts, seconds=seconds, message=steps[-1].message[:300], tokens=tokens)


def salvage(fid: str, run: Path, work: Path, error: str) -> Outcome:
    # a dropped connection late in a task still leaves the attempts that built; submit the newest
    step = last_built(work / fid)
    if step is None:
        return Outcome(id=fid, status="error", message=error)
    orient(step, run / fid / "output.step")
    return Outcome(id=fid, status=f"built ({step.parent.name}), then error", attempts=int(step.parent.name.split("_")[1]), message=error)


def main() -> None:
    p = argparse.ArgumentParser(prog="scriber-cadgenbench", description="Run Scriber on the CADGenBench fixtures")
    p.add_argument("data", type=Path, help="local copy of HuggingAI4Engineering/cadgenbench-data")
    p.add_argument("--model", help="designs the part; defaults to llm.default")
    p.add_argument("--vision", help="reads the drawings; defaults to --model when it is hosted, else llm.vision")
    p.add_argument("--ids", nargs="*", default=[], help="only these fixtures")
    p.add_argument("--effort", choices=get_args(Effort), help="how hard an Anthropic model works; default is the config's, low")
    p.add_argument("--thinking", action="store_true", help="turn extended thinking on for Anthropic models; off by default")
    p.add_argument("--staged", action="store_true", help="plan dense drawings into stages: the body first, then features by view")
    p.add_argument("--out", type=Path, default=Path("evals/results"))
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = p.parse_args()
    config = load(args.config)
    llm = llm_for(config, args.model, args.effort, args.thinking)
    hosted = args.model is not None and config.llm.models.get(args.model, ModelOptions()).provider != "ollama"
    # a hosted model reads its own drawings; only a local text model needs the separate vision model
    vision = llm_for(config, args.vision or (args.model if hosted else config.llm.vision), args.effort, args.thinking)
    run = args.out / f"cadgenbench-{llm.name.replace(':', '_').replace('/', '_')}-{time.strftime('%Y%m%d-%H%M%S')}"
    work = run.with_name(run.name + "-work")
    chosen = [f for f in fixtures(args.data) if not args.ids or f.id in args.ids]
    run.mkdir(parents=True)
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    try:
        with (run.parent / f"{run.name}.jsonl").open("w", encoding="utf-8") as log:
            for f in chosen:
                try:
                    outcome = attempt(f, llm, vision, geometry, run, work, config.agent.max_repairs, args.staged)
                except Exception as e:  # a model-server error (quota, overload, offline) fails this task, not the run
                    outcome = salvage(f.id, run, work, f"{type(e).__name__}: {e}"[:300])
                log.write(outcome.model_dump_json() + "\n")
                log.flush()
                print(f"{outcome.id}: {outcome.status} ({outcome.attempts} attempts, {outcome.seconds} s) {outcome.message}", flush=True)
                if outcome.tokens:
                    print(f"    tokens: {outcome.tokens}", flush=True)
    finally:
        geometry.close()
    print(f"submission folder: {run}")


if __name__ == "__main__":
    main()

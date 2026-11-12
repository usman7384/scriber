import argparse
import time
from collections.abc import Iterator
from pathlib import Path

import yaml
from build123d import Location, Plane, Vector, export_step, import_step
from pydantic import BaseModel

from scriber_agent import LLM, Step, generate
from scriber_cli.config import llm_for, load
from scriber_geometry import Artifact, LocalGeometry

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


def fixtures(data: Path) -> Iterator[Fixture]:
    for d in sorted(p for p in data.iterdir() if (p / "description.yaml").is_file()):
        spec = yaml.safe_load((d / "description.yaml").read_text(encoding="utf-8"))
        editing = spec["input_type"] != "text+image"
        images = [] if editing else [d / f for f in spec["input_files"]]
        yield Fixture(id=d.name, prompt=spec["description"].strip(), images=images, editing=editing)


def last_built(steps: list[Step]) -> Artifact | None:
    return next((s.result.artifact for s in reversed(steps) if s.result and s.result.artifact), None)


def orient(step_in: Path, step_out: Path) -> None:
    # the grader recommends a centred bounding box with extents Lx >= Ly >= Lz
    shape = import_step(step_in)
    box = shape.bounding_box()
    size = (box.size.X, box.size.Y, box.size.Z)
    order = sorted(range(3), key=lambda i: -size[i])
    frame = Plane(origin=box.center(), x_dir=AXES[order[0]], z_dir=AXES[order[2]])
    export_step(shape.moved(Location(frame).inverse()), step_out)


def attempt(f: Fixture, llm: LLM, vision: LLM, geometry: LocalGeometry, run: Path, work: Path, repairs: int) -> Outcome:
    (run / f.id).mkdir(parents=True, exist_ok=True)  # an empty folder is scored as missing
    if f.editing:
        return Outcome(id=f.id, status="skipped", message="editing tasks need STEP import, which Scriber does not have")
    start = time.monotonic()
    images = tuple(p.read_bytes() for p in f.images)
    steps = list(generate(f.prompt, llm, geometry, work / f.id, repairs, images=images, vision=vision))
    seconds = round(time.monotonic() - start, 1)
    attempts = max((s.attempt for s in steps), default=0)
    artifact = last_built(steps)
    if artifact is None:
        return Outcome(id=f.id, status="not built", attempts=attempts, seconds=seconds, message=steps[-1].message[:300])
    orient(artifact.files["step"], run / f.id / "output.step")
    return Outcome(id=f.id, status="built", attempts=attempts, seconds=seconds, message=steps[-1].message[:300])


def main() -> None:
    p = argparse.ArgumentParser(prog="scriber-cadgenbench", description="Run Scriber on the CADGenBench fixtures")
    p.add_argument("data", type=Path, help="local copy of HuggingAI4Engineering/cadgenbench-data")
    p.add_argument("--model", help="designs the part; defaults to llm.default")
    p.add_argument("--vision", help="reads the drawings; defaults to llm.vision")
    p.add_argument("--ids", nargs="*", default=[], help="only these fixtures")
    p.add_argument("--out", type=Path, default=Path("evals/results"))
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = p.parse_args()
    config = load(args.config)
    llm = llm_for(config, args.model)
    vision = llm_for(config, args.vision or config.llm.vision)
    run = args.out / f"cadgenbench-{llm.name.replace(':', '_').replace('/', '_')}-{time.strftime('%Y%m%d-%H%M%S')}"
    work = run.with_name(run.name + "-work")
    chosen = [f for f in fixtures(args.data) if not args.ids or f.id in args.ids]
    run.mkdir(parents=True)
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    try:
        with (run.parent / f"{run.name}.jsonl").open("w", encoding="utf-8") as log:
            for f in chosen:
                try:
                    outcome = attempt(f, llm, vision, geometry, run, work, config.agent.max_repairs)
                except Exception as e:  # a model-server error (quota, overload, offline) fails this task, not the run
                    outcome = Outcome(id=f.id, status="error", message=f"{type(e).__name__}: {e}"[:300])
                log.write(outcome.model_dump_json() + "\n")
                log.flush()
                print(f"{outcome.id}: {outcome.status} ({outcome.attempts} attempts, {outcome.seconds} s) {outcome.message}", flush=True)
    finally:
        geometry.close()
    print(f"submission folder: {run}")


if __name__ == "__main__":
    main()

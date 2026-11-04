from pathlib import Path

from scriber_agent import Grounding, Result
from scriber_cli.config import Config
from scriber_context import LocalContext, OllamaEmbedder
from scriber_geometry import LocalGeometry
from scriber_ir import Process, ShapeDescriptor


def open_context(config: Config, geometry: LocalGeometry) -> LocalContext:
    embedder = OllamaEmbedder(config.embeddings.model, host=config.llm.host)
    return LocalContext(config.data_dir / "context", embedder, describe=geometry.describe)


def grounding(ctx: LocalContext, project: str, request: str, process: Process) -> Grounding:
    return Grounding(pack=ctx.retrieve(project, request), rules=ctx.rules(project), process=process)


def record(ctx: LocalContext, project: str, version: Path, result: Result, geometry: LocalGeometry) -> None:
    if not result.ok or result.design is None or result.artifact is None:
        return
    shapes: dict[str, ShapeDescriptor] = {}
    if len(result.design.parts) == 1:
        shapes[result.design.parts[0].id] = geometry.describe(result.artifact.files["step"])
    ctx.record_generation(project, f"{version.parent.name}/{version.name}", result.design, result.used, shapes)


def show(ctx: LocalContext, project: str) -> None:
    for d in ctx.documents(project):
        print(f"{d.name:<36} {d.kind:<5} {d.role:<10} facts {d.facts:>3}  rules {d.rules:>2}  id {d.id}")
    s = ctx.stats(project)
    print(
        f"knowledge base level {s.level}: {s.files} files, {s.facts} facts, {s.rules} rules, {s.entities} entities, {s.relations} relations"
    )
    for r in ctx.rules(project).rules:
        print(f"rule {r.id:<44} {r.kind} {r.value:g}{r.unit} {r.binding} ({r.source.ref or 'default'})")

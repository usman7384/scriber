import argparse
import io
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import get_args

import httpx
import uvicorn

from partwright_agent import Result, Step, generate, refine
from partwright_api import SerialGeometry, Settings, create_app, thumbnail_targets
from partwright_cli import project, store
from partwright_cli.config import Config, llm_for, load, tool_path
from partwright_cli.pipe import pipe
from partwright_cli.view import serve
from partwright_context import LocalContext, OllamaEmbedder, archive_files, ingest_all
from partwright_geometry import BuildError, LocalGeometry
from partwright_ir import ParamError, Process, apply_params, label


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    config = load(args.config)
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    try:
        return int(args.run(args, config, geometry))
    finally:
        geometry.close()


def _generate(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    model_dir = args.out or config.output_dir / store.slug(args.prompt)
    version = store.next_version(model_dir)
    llm, agent = llm_for(config, args.model), config.agent
    if not args.project:
        return _run(generate(args.prompt, llm, geometry, version, agent.max_repairs, agent.seed), version)[0]
    with project.open_context(config, geometry) as ctx:
        context = project.grounding(ctx, args.project, args.prompt, args.process)
        code, result = _run(generate(args.prompt, llm, geometry, version, agent.max_repairs, agent.seed, context), version)
        if result:
            project.record(ctx, args.project, version, result, geometry)
    return code


def _refine(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    design = store.latest_design(args.model_dir)
    version = store.next_version(args.model_dir)
    llm, agent = llm_for(config, args.model), config.agent
    if not args.project:
        return _run(refine(design, args.instruction, llm, geometry, version, agent.max_repairs, agent.seed), version)[0]
    with project.open_context(config, geometry) as ctx:
        context = project.grounding(ctx, args.project, args.instruction, args.process)
        code, result = _run(refine(design, args.instruction, llm, geometry, version, agent.max_repairs, agent.seed, context), version)
        if result:
            project.record(ctx, args.project, version, result, geometry)
    return code


def _context_add(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    with project.open_context(config, geometry) as ctx:
        outcomes = ingest_all(ctx, args.project, archive_files(args.files))
    for o in outcomes:
        print(f"{o.name}: {o.kind}, {o.facts} facts" if o.status == "parsed" else f"{o.name}: FAILED {o.error}")
    failed = sum(o.status == "failed" for o in outcomes)
    print(f"{len(outcomes) - failed}/{len(outcomes)} files parsed")
    if args.report:
        args.report.write_text(json.dumps([o.model_dump() for o in outcomes], indent=2), encoding="utf-8")
    return 1 if failed else 0


def _pipe(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    headers = {"X-API-Token": args.token} if args.token else {}
    with httpx.Client(base_url=args.api or f"http://{config.api.host}:{config.api.port}", headers=headers, timeout=30) as http:
        job = pipe(sys.stdin.buffer.read(), http, args.project, args.name)
        if job["status"] != "done":
            print(f"error: {job['error']}", file=sys.stderr)
            return 1
        print(f"model {job['model_id']} v{job['version']}")
        if args.out:
            step = http.get(f"/models/{job['model_id']}/export", params={"fmt": "step", "version": job["version"]})
            args.out.write_bytes(step.raise_for_status().content)
            print(f"saved {args.out}")
    return 0


def _context_show(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    with project.open_context(config, geometry) as ctx:
        project.show(ctx, args.project)
    return 0


def _params(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    design = store.latest_design(args.model_dir)
    if not args.set:
        for p in design.params:
            print(f"{label(p.name):<32} {p.value:>10g} {p.unit:<4} {p.provenance.source}")
        return 0
    try:
        updates = {k: float(v) for k, v in (s.split("=", 1) for s in args.set)}
        edited = apply_params(design, updates)
        version = store.next_version(args.model_dir)
        artifact = geometry.build(edited, version)
    except (ParamError, BuildError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    store.save(version, [], Result(design=edited, artifact=artifact, checks=[], attempts=1, repairs=0))
    print(f"{version}: rebuilt in {artifact.elapsed_ms} ms, {'valid' if artifact.ok else 'INVALID'}")
    return 0 if artifact.ok else 1


def _serve(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    serial = SerialGeometry(geometry)
    api = config.api
    settings = Settings(
        data_dir=config.data_dir,
        auth=api.auth,
        max_repairs=config.agent.max_repairs,
        seed=config.agent.seed,
        ollama_host=config.llm.host,
        public_url=f"http://{api.host}:{api.port}",
        freecad=tool_path("PARTWRIGHT_FREECAD"),
        prusaslicer=tool_path("PARTWRIGHT_PRUSASLICER"),
    )
    embedder = OllamaEmbedder(config.embeddings.model, host=config.llm.host)
    with LocalContext(config.data_dir / "context", embedder, describe=serial.describe) as ctx:
        app = create_app(settings, llm_for(config, args.model), serial, ctx, vision=llm_for(config, config.llm.vision))
        print(f"serving the API at http://{api.host}:{api.port}/ (docs at /docs, auth: {api.auth})", flush=True)
        uvicorn.run(app, host=api.host, port=api.port, access_log=False)
    return 0


def _view(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    serve(args.root or config.output_dir, args.port, not args.no_browser)
    return 0


def _run(steps: Iterator[Step], version: Path) -> tuple[int, Result | None]:
    seen: list[Step] = []
    for step in steps:
        seen.append(step)
        print(f"[{step.elapsed_ms / 1000:6.1f}s] {step.kind:<12} #{step.attempt} {step.message}", flush=True)
    final = seen[-1].result
    store.save(version, seen, final)
    if final and final.ok:
        print(f"saved {version}")
        return 0, final
    print(f"generation did not pass all checks; see {version / 'steps.json'}", file=sys.stderr)
    return 1, final


def _thumbnails(args: argparse.Namespace, config: Config, geometry: LocalGeometry) -> int:
    targets = thumbnail_targets(config.data_dir)
    for glb, png in targets:
        geometry.thumbnail(glb, png)
    print(f"rendered {len(targets)} thumbnails")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="partwright")
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--model", help="Ollama model tag; defaults to llm.default in config")
    sub = p.add_subparsers(required=True)
    g = sub.add_parser("generate", help="design a part from a description")
    g.add_argument("prompt")
    g.add_argument("--out", type=Path)
    _project_args(g)
    g.set_defaults(run=_generate)
    r = sub.add_parser("refine", help="change an existing model in natural language")
    r.add_argument("model_dir", type=Path)
    r.add_argument("instruction")
    _project_args(r)
    r.set_defaults(run=_refine)
    c = sub.add_parser("context", help="manage a project's engineering files").add_subparsers(required=True)
    ca = c.add_parser("add", help="ingest files into a project")
    ca.add_argument("project")
    ca.add_argument("files", type=Path, nargs="+", help="files or folders (read recursively)")
    ca.add_argument("--report", type=Path, help="write the per-file outcome as JSON")
    ca.set_defaults(run=_context_add)
    cs = c.add_parser("show", help="list a project's files, knowledge base and rules")
    cs.add_argument("project")
    cs.set_defaults(run=_context_show)
    pa = sub.add_parser("params", help="list or set parameters and rebuild")
    pa.add_argument("model_dir", type=Path)
    pa.add_argument("--set", nargs="*", metavar="NAME=VALUE")
    pa.set_defaults(run=_params)
    pi = sub.add_parser("pipe", help="build a model from sizing XML on stdin through a running API")
    pi.add_argument("--api", help="API base URL; defaults to the api section of config")
    pi.add_argument("--project", help="project id; a new project when omitted")
    pi.add_argument("--token", help="API token when the server uses tokens")
    pi.add_argument("--name", default="sizing.xml", help="file name recorded as provenance")
    pi.add_argument("--out", type=Path, help="save the STEP here")
    pi.set_defaults(run=_pipe)
    s = sub.add_parser("serve", help="run the HTTP API (host, port and auth from the api section of config)")
    s.set_defaults(run=_serve)
    t = sub.add_parser("thumbnails", help="re-render every saved version's thumbnail")
    t.set_defaults(run=_thumbnails)
    v = sub.add_parser("view", help="open a 3D viewer for the models in the output folder")
    v.add_argument("root", type=Path, nargs="?", help="folder of model folders; defaults to output_dir in config")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--no-browser", action="store_true")
    v.set_defaults(run=_view)
    return p


def _project_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--project", help="ground the design in this project's files and rules")
    p.add_argument("--process", choices=get_args(Process), default="any", help="manufacturing process for DFM checks")


if __name__ == "__main__":
    sys.exit(main())

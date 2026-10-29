import json
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import IO, Any

from partwright_geometry.checks import assembly_findings, validity_findings
from partwright_geometry.mass import assembly_mass, with_mass
from partwright_geometry.models import MESH_SUFFIXES, STEP_SUFFIXES, Artifact, AssemblyReport, BuildError, Finding, PartMetrics, Vec
from partwright_ir import Design, Process, RuleSet, ShapeDescriptor, compile_design, design_hash

FEATURE_COMMENT = re.compile(r"^    # (\S+) ")
NO_RULES = RuleSet()


class LocalGeometry:
    def __init__(self, timeout_s: float = 120.0) -> None:
        self.timeout_s = timeout_s
        self._proc: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()

    def build(self, design: Design, out_dir: Path, rules: RuleSet = NO_RULES, process: Process = "any") -> Artifact:
        start = time.monotonic()
        out_dir.mkdir(parents=True, exist_ok=True)
        source = compile_design(design)
        (out_dir / "model.py").write_text(source, encoding="utf-8")
        (out_dir / "design.json").write_text(design.model_dump_json(indent=2), encoding="utf-8")
        rules_json = rules.for_process(process).model_dump(mode="json")
        reply = self._call({"op": "build", "source": source, "out_dir": str(out_dir), "title": design.title, "rules": rules_json})
        if not reply["ok"]:
            raise BuildError("kernel", reply["error"], failing_feature(source, reply["lines"]))
        materials = {p.id: p.material for p in design.parts}
        parts = [with_mass(m, materials[m.id]) for m in map(PartMetrics.model_validate, reply["parts"])]
        files = {k: Path(v) for k, v in reply["files"].items()} | {"py": out_dir / "model.py", "ir": out_dir / "design.json"}
        assembly = _assembly(reply.get("assembly"), parts)
        findings = validity_findings(parts) + [Finding.model_validate(f) for f in reply["findings"]]
        return Artifact(
            design_hash=design_hash(design),
            files=files,
            parts=parts,
            findings=findings + (assembly_findings(assembly) if assembly else []),
            elapsed_ms=int((time.monotonic() - start) * 1000),
            assembly=assembly,
        )

    def describe(self, path: Path) -> ShapeDescriptor:
        return ShapeDescriptor.model_validate(self._read("describe", path, STEP_SUFFIXES | MESH_SUFFIXES)["descriptor"])

    def import_step(self, path: Path) -> list[PartMetrics]:
        return [PartMetrics.model_validate(p) for p in self._read("import_step", path, STEP_SUFFIXES)["parts"]]

    def sections(self, step: Path, ys: list[float]) -> list[list[Vec]]:
        reply = self._call({"op": "sections", "path": str(step), "ys": ys})
        if not reply["ok"]:
            raise BuildError("kernel", f"sections of {step.name}: {reply['error']}")
        return [[(x, y, z) for x, y, z in outline] for outline in reply["sections"]]

    def thumbnail(self, glb: Path, png: Path, size: int = 256) -> Path:
        reply = self._call({"op": "thumbnail", "path": str(glb), "png": str(png), "size": size})
        if not reply["ok"]:
            raise BuildError("kernel", f"thumbnail of {glb.name}: {reply['error']}")
        return png

    def close(self) -> None:
        if self._proc:
            self._proc.kill()
            self._proc.wait()
            self._proc = None

    def _read(self, op: str, path: Path, suffixes: frozenset[str]) -> dict[str, Any]:
        if path.suffix.lower() not in suffixes:
            raise ValueError(f"{path.name}: expected one of {', '.join(sorted(suffixes))}")
        reply = self._call({"op": op, "path": str(path)})
        if not reply["ok"]:
            raise BuildError("kernel", f"{path.name}: {reply['error']}")
        return reply

    def _call(self, request: dict[str, Any]) -> dict[str, Any]:
        proc = self._worker()
        assert proc.stdin
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        try:
            line = self._lines.get(timeout=self.timeout_s)
        except queue.Empty:
            self.close()
            raise BuildError("timeout", f"geometry build exceeded {self.timeout_s:g} s") from None
        if line is None:
            self.close()
            raise BuildError("crash", "geometry kernel process exited unexpectedly")
        result: dict[str, Any] = json.loads(line)
        return result

    def _worker(self) -> subprocess.Popen[str]:
        if self._proc and self._proc.poll() is None:
            return self._proc
        self._lines = queue.Queue()
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "partwright_geometry.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        assert self._proc.stdout
        threading.Thread(target=_pump, args=(self._proc.stdout, self._lines), daemon=True).start()
        return self._proc


def _assembly(raw: dict[str, Any] | None, parts: list[PartMetrics]) -> AssemblyReport | None:
    if raw is None:
        return None
    mass, cog = assembly_mass(parts) if all(p.mass_g is not None for p in parts) else (None, None)
    return AssemblyReport.model_validate({**raw, "mass_g": mass, "center_of_mass": cog})


def failing_feature(source: str, lines: list[int]) -> str | None:
    rows = source.splitlines()
    for line in reversed(lines):
        for row in reversed(rows[:line]):
            if row.startswith("def "):
                break
            if match := FEATURE_COMMENT.match(row):
                return match.group(1)
    return None


def _pump(stream: IO[str], lines: "queue.Queue[str | None]") -> None:
    for line in stream:
        if line.startswith("{"):
            lines.put(line)
    lines.put(None)

import argparse
import json
import time
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from partwright_agent import LLM
from partwright_cli.config import Config, llm_for, load
from partwright_geometry import LocalGeometry

Value = str | float | int | bool | None
Measured = Mapping[str, Value]


@dataclass(frozen=True)
class Rig:
    out: Path
    geometry: LocalGeometry
    llm: LLM
    config: Config
    vision: LLM | None = None


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    row: str
    passed: bool
    measured: dict[str, Value]
    note: str = ""


Demo = Callable[[Rig], Evidence]


def evidence(row: str, measured: Measured, *checks: bool, note: str = "") -> Evidence:
    return Evidence(row=row, passed=all(checks), measured=dict(measured), note=note)


def registry() -> dict[str, Demo]:
    from partwright_evals import (
        parity_m1,
        parity_m2,
        parity_m3,
        parity_m4_aircraft,
        parity_m4_assembly,
        parity_m4_interop,
        parity_m4_mesh,
        parity_m4_mission,
        parity_m4_vision,
        parity_m5_conventions,
        parity_m5_onshape,
        parity_m5_parts,
        parity_m5_platform,
        parity_m6,
    )

    modules = (
        parity_m1,
        parity_m2,
        parity_m3,
        parity_m4_aircraft,
        parity_m4_assembly,
        parity_m4_interop,
        parity_m4_mesh,
        parity_m4_mission,
        parity_m4_vision,
        parity_m5_conventions,
        parity_m5_onshape,
        parity_m5_parts,
        parity_m5_platform,
        parity_m6,
    )
    return {row: demo for m in modules for row, demo in m.ROWS.items()}


def run_row(row: str, demo: Demo, rig: Rig) -> Evidence:
    out = rig.out / row
    out.mkdir(parents=True, exist_ok=True)
    try:
        ev = demo(Rig(out, rig.geometry, rig.llm, rig.config, rig.vision))
    except Exception as e:  # a crashing demo is a failed row, recorded with its traceback
        (out / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        ev = Evidence(row=row, passed=False, measured={}, note=f"{type(e).__name__}: {e}"[:300])
    (out / "evidence.json").write_text(ev.model_dump_json(indent=2), encoding="utf-8")
    return ev


def report(results: list[Evidence], model: str) -> str:
    lines = [f"Model: `{model}`", "", "| row | result | measured | note |", "|---|---|---|---|"]
    for e in results:
        measured = ", ".join(f"{k}={v}" for k, v in e.measured.items())
        lines.append(f"| {e.row} | {'pass' if e.passed else 'FAIL'} | {measured} | {e.note} |")
    lines.append(f"\n{sum(e.passed for e in results)}/{len(results)} rows pass")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(prog="partwright-parity")
    p.add_argument("rows", nargs="*", help="row ids, e.g. EX-1 IN-1; all registered rows when empty")
    p.add_argument("--model")
    p.add_argument("--out", type=Path, default=Path("evals/results"))
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = p.parse_args()
    demos = registry()
    unknown = set(args.rows) - set(demos)
    if unknown:
        raise SystemExit(f"no demo for {sorted(unknown)}")
    config = load(args.config)
    llm = llm_for(config, args.model)
    run_dir = args.out / f"parity-{time.strftime('%Y%m%d-%H%M%S')}"
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    results = []
    try:
        for row in args.rows or sorted(demos):
            results.append(run_row(row, demos[row], Rig(run_dir, geometry, llm, config, llm_for(config, config.llm.vision))))
            print(results[-1].model_dump_json(), flush=True)
    finally:
        geometry.close()
    (run_dir / "PARITY.md").write_text(report(results, llm.name), encoding="utf-8")
    (run_dir / "evidence.json").write_text(json.dumps([e.model_dump() for e in results], indent=2), encoding="utf-8")
    print(report(results, llm.name))


if __name__ == "__main__":
    main()

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from scriber_ir import Datum, Design, Feature, Param, Sketch

PLAN_NOTE = """Before modelling, split this part into stages so that each answer stays short.
Stage 1 is the main body: the outline, the main extrudes, revolves or sheet, and parameters for the overall sizes.
Each later stage adds one group of features read from the views, sections or details that show them: pockets, ribs, bosses,
hole patterns, slots, blends. Use 2 to 6 stages; a part of about a dozen features or fewer is one stage. Answer with JSON only."""


class Stage(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    views: str = Field(description="the views, sections and details this stage reads")
    features: str = Field(description="what this stage models, with the callouts it uses")


class StagePlan(BaseModel):
    stages: list[Stage] = Field(min_length=1, max_length=6)


class Changes(BaseModel):
    part: str = Field(description="id of the part the changes go into")
    params: list[Param] = Field(default=[], description="new parameters, or whole entries replacing those of the same name")
    datums: list[Datum] = []
    sketches: list[Sketch] = Field(default=[], description="new sketches, or whole sketches replacing those of the same id")
    features: list[Feature] = Field(default=[], description="new features, or whole features replacing those of the same id")
    remove: list[str] = Field(default=[], description="ids of datums, sketches and features, or parameter names, to delete")


def stage_message(stage: Stage, number: int, total: int) -> str:
    scope = f"Stage {number} of {total}, {stage.name}: {stage.features} (from {stage.views})."
    if number == 1:
        return f"{scope} Model only this; later stages add the rest. Answer with the complete design JSON."
    return (
        f"{scope} The design so far is the previous answer. Add only this stage. Answer only the additions, "
        '{"part": <part id>, "params": [...], "datums": [...], "sketches": [...], "features": [...]}, with new ids; '
        "earlier ids and parameters may be referenced, not changed."
    )


def change_repair(problems: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    return (
        "The design is the previous answer; it is too long to write again. Fix these problems by answering only the changes, "
        '{"part": <part id>, "params": [...], "datums": [...], "sketches": [...], "features": [...], "remove": [...]}: '
        "whole entries, new or replacing the one with the same id or name, and the ids or names to delete.\n" + listed
    )


def stage_repair(problems: list[str], number: int) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    return f"Stage {number} did not build:\n{listed}\nAnswer the corrected answer for stage {number} in the same form."


def merged(design: Design, change: Changes) -> Design:
    if change.part not in {p.id for p in design.parts}:
        raise ValueError(f"the changes name part {change.part!r}; the parts are {[p.id for p in design.parts]}")
    gone = set(change.remove)
    data = design.model_dump()
    data["params"] = _replaced(data["params"], [p.model_dump() for p in change.params], "name", gone)
    for part in data["parts"]:
        if part["id"] == change.part:
            for key, given in (("datums", change.datums), ("sketches", change.sketches), ("features", change.features)):
                part[key] = _replaced(part[key], [g.model_dump() for g in given], "id", gone)
    return Design.model_validate(data)


def _replaced(old: list[dict[str, Any]], new: list[dict[str, Any]], key: str, gone: set[str]) -> list[dict[str, Any]]:
    # an entry with a known id or name takes that one's place, so the feature order stays; the rest are added at the end
    given = {n[key]: n for n in new}
    kept = [given.pop(o[key], o) for o in old if o[key] not in gone]
    return kept + [n for n in new if n[key] in given]

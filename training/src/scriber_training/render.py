import random
from dataclasses import dataclass

from scriber_training.spec import SECTIONS, Spec

STYLES = ("oneline", "bullets", "numbered", "spec")
INTROS = ("Design this part:", "Please model the following part.", "I need a CAD model of this part:", "Part request:")
SPEC_PREAMBLE = (
    "Model one continuous parametric solid. Units are millimetres, Z is up and -Y is the front.",
    "Act as a mechanical design engineer and produce a single watertight, fully parametric solid. Units: mm.",
    "Create a clean parametric feature tree for a single solid part. All dimensions are in millimetres.",
)


EXPOSE = ("Parameters to expose: {names}.", "Name the parameters {names}.", "Keep {names} as named parameters.")


@dataclass(frozen=True)
class Prompt:
    style: str
    text: str
    required_params: tuple[str, ...] = ()


def render(spec: Spec, rng: random.Random, style: str | None = None) -> Prompt:
    style = style or rng.choice(STYLES)
    texts = [t for _, t in spec.statements]
    if style == "oneline":
        return Prompt(style, ", ".join(texts) + ".")
    if style == "bullets":
        return Prompt(style, rng.choice(INTROS) + "\n" + "\n".join(f"- {t}" for t in texts))
    if style == "numbered":
        return Prompt(style, "Requirements:\n" + "\n".join(f"REQ-{i:02d}: {t}." for i, t in enumerate(texts, 1)))
    return _spec_sheet(spec, rng)


def _spec_sheet(spec: Spec, rng: random.Random) -> Prompt:
    lines = [f"# {spec.title}", "", rng.choice(SPEC_PREAMBLE)]
    number = 0
    for section in SECTIONS:
        items = [t for s, t in spec.statements if s == section]
        if items:
            number += 1
            lines += ["", f"## {number}. {section}", *(f"- {t}" for t in items)]
    params = tuple(spec.params())
    lines += ["", f"## {number + 1}. Parameters", "Expose these named parameters: " + ", ".join(f"`{p}`" for p in params) + "."]
    return Prompt("spec", "\n".join(lines), params)


def exposing(prompt: Prompt, spec: Spec, rng: random.Random) -> Prompt:
    names = rng.sample(spec.params(), min(3, len(spec.params())))
    listed = " and ".join([", ".join(f"`{n}`" for n in names[:-1]), f"`{names[-1]}`"])
    return Prompt(prompt.style, f"{prompt.text}\n{rng.choice(EXPOSE).format(names=listed)}", tuple(names))

from pydantic import BaseModel

from scriber_ir.model import Design


class ParamChange(BaseModel):
    name: str
    old: float | None
    new: float | None


class DesignDiff(BaseModel):
    params: list[ParamChange]
    features_added: list[str]
    features_removed: list[str]
    features_changed: list[str]

    @property
    def empty(self) -> bool:
        return not (self.params or self.features_added or self.features_removed or self.features_changed)


def diff(a: Design, b: Design) -> DesignDiff:
    pa, pb = a.param_values(), b.param_values()
    params = [ParamChange(name=n, old=pa.get(n), new=pb.get(n)) for n in sorted(pa.keys() | pb.keys()) if pa.get(n) != pb.get(n)]
    fa, fb = _features(a), _features(b)
    return DesignDiff(
        params=params,
        features_added=sorted(fb.keys() - fa.keys()),
        features_removed=sorted(fa.keys() - fb.keys()),
        features_changed=sorted(k for k in fa.keys() & fb.keys() if fa[k] != fb[k]),
    )


def _features(d: Design) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in d.parts:
        sketches = {s.id: s.model_dump_json() for s in part.sketches}
        for f in part.features:
            used = getattr(f, "sketch", None)
            out[f"{part.id}.{f.id}"] = f.model_dump_json() + sketches.get(used or "", "")
    return out

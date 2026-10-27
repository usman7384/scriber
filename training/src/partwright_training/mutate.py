import copy
import json
import random
from collections.abc import Callable
from typing import Any

Design = dict[str, Any]
Mutation = Callable[[Design, random.Random], Design | None]


def _features(d: Design) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = d["parts"][0]["features"]
    return features


def _holes(d: Design) -> list[dict[str, Any]]:
    return [f for f in _features(d) if f["kind"] == "hole"]


def drop_hole_plane(d: Design, rng: random.Random) -> Design | None:
    holes = _holes(d)
    if not holes:
        return None
    del rng.choice(holes)["plane"]
    return d


def pattern_before_source(d: Design, rng: random.Random) -> Design | None:
    features = _features(d)
    patterns = [i for i, f in enumerate(features) if f["kind"] == "pattern"]
    if not patterns:
        return None
    features.insert(1, features.pop(rng.choice(patterns)))
    return d


def bad_face(d: Design, rng: random.Random) -> Design | None:
    refs = [x["plane"] for x in [*_features(d), *d["parts"][0]["sketches"]] if "." in x.get("plane", {}).get("ref", "")]
    if not refs:
        return None
    plane = rng.choice(refs)
    owner, face = plane["ref"].split(".")
    plane["ref"] = rng.choice((f"{owner}.side", f"{owner}.upper", face, f"{owner}_{face}"))
    return d


def renamed_param(d: Design, rng: random.Random) -> Design | None:
    if not d["params"]:
        return None
    p = rng.choice(d["params"])
    p["name"] = rng.choice((f"{p['name']}_mm", f"main_{p['name']}", p["name"].split("_")[-1] + "_value"))
    return d


def word_in_number(d: Design, rng: random.Random) -> Design | None:
    slots = [(f, k) for f in _features(d) for k in ("distance", "depth", "radius", "length") if k in f]
    if not slots:
        return None
    f, k = rng.choice(slots)
    f[k] = rng.choice(("top", "through", "auto", "max", "full"))
    return d


def revolve_boss(d: Design, rng: random.Random) -> Design | None:
    features = _features(d)
    bosses = [i for i, f in enumerate(features) if f["id"] == "boss"]
    if not bosses:
        return None
    f = features[bosses[0]]
    features[bosses[0]] = {"kind": "revolve", "id": "boss", "name": f["name"], "sketch": f["sketch"], "axis": "Y", "angle": 360}
    return d


def port_outside(d: Design, rng: random.Random) -> Design | None:
    side = [h for h in _holes(d) if h["plane"]["ref"].split(".")[-1] in ("front", "left", "right") and h["at"]["kind"] == "points"]
    if not side:
        return None
    point = rng.choice(side)["at"]["points"][0]
    point[1] = f"-({point[1]})" if rng.random() < 0.5 else f"{point[1]} + 100"
    return d


def wrong_value(d: Design, rng: random.Random) -> Design | None:
    dims = [p for p in d["params"] if p["unit"] == "mm" and p["value"] >= 20]
    if not dims:
        return None
    p = rng.choice(dims)
    p["value"] = round(p["value"] * rng.choice((0.5, 0.8, 1.25, 1.5)), 1)
    return d


def drop_feature(d: Design, rng: random.Random) -> Design | None:
    features = _features(d)
    used = {s for f in features for s in f.get("features", [])}
    removable = [i for i, f in enumerate(features[1:], 1) if f["kind"] in ("hole", "extrude") and f["id"] not in used]
    if not removable:
        return None
    del features[rng.choice(removable)]
    return d


def no_hole_size(d: Design, rng: random.Random) -> Design | None:
    holes = [h for h in _holes(d) if "fastener" in h or "diameter" in h]
    if not holes:
        return None
    h = rng.choice(holes)
    for key in ("fastener", "diameter", "thread"):
        h.pop(key, None)
    return d


def edge_too_close(d: Design, rng: random.Random) -> Design | None:
    margins = [p for p in d["params"] if p["name"].endswith("margin")]
    if not margins:
        return None
    p = rng.choice(margins)
    p["value"] = round(p["value"] * rng.choice((0.4, 0.5, 0.6)), 1)
    return d


def big_fillet(d: Design, rng: random.Random) -> Design | None:
    radii = {f["radius"] for f in _features(d) if f["kind"] == "fillet" and isinstance(f["radius"], str)}
    params = [p for p in d["params"] if p["name"] in radii]
    if not params:
        return None
    p = rng.choice(params)
    p["value"] = round(p["value"] * rng.choice((4, 6, 10)) + 5, 1)
    return d


def overlapping_holes(d: Design, rng: random.Random) -> Design | None:
    listed = [h for h in _holes(d) if h["at"]["kind"] == "points"]
    if not listed:
        return None
    points = rng.choice(listed)["at"]["points"]
    x, y = points[0]
    # an exact duplicate is merged away by normalize, so the copy sits 1 mm off and overlaps instead
    points.append([x + 1 if isinstance(x, int | float) else f"({x}) + 1", y])
    return d


MUTATIONS: dict[str, Mutation] = {
    "big_fillet": big_fillet,
    "overlapping_holes": overlapping_holes,
    "edge_too_close": edge_too_close,
    "drop_hole_plane": drop_hole_plane,
    "pattern_before_source": pattern_before_source,
    "bad_face": bad_face,
    "renamed_param": renamed_param,
    "word_in_number": word_in_number,
    "revolve_boss": revolve_boss,
    "port_outside": port_outside,
    "wrong_value": wrong_value,
    "drop_feature": drop_feature,
    "no_hole_size": no_hole_size,
}


# failure modes from the replayed challenge runs (docs/agents/ir-v2.md) and the S1 4B's M1 runs are tried first half the time
FAILURES_SEEN = (
    "revolve_boss",
    "pattern_before_source",
    "port_outside",
    "word_in_number",
    "edge_too_close",
    "big_fillet",
    "overlapping_holes",
)


def mutate(design: Design, rng: random.Random) -> tuple[str, str] | None:
    if rng.random() < 0.05:
        text = json.dumps(design)
        return "truncated", text[: rng.randint(len(text) // 4, len(text) * 3 // 4)]
    order = rng.sample(list(MUTATIONS), len(MUTATIONS))
    if rng.random() < 0.5:
        order = [*rng.sample(FAILURES_SEEN, len(FAILURES_SEEN)), *order]
    for name in order:
        broken = MUTATIONS[name](copy.deepcopy(design), rng)
        if broken is not None:
            return name, json.dumps(broken)
    return None

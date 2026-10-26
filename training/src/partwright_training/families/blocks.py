import random
from dataclasses import dataclass

from partwright_training.fasteners import clearance, counterbore_depth, edge, head, tap_drill, thread
from partwright_training.spec import Draft, Spec, circle_sketch, count_word, finish, hole, num, pick, rect_sketch


@dataclass(frozen=True)
class _Block:
    length: float
    width: float
    height: float
    margin: float
    mount: str
    kind: str


def block(rng: random.Random) -> Spec:
    d = Draft(
        rng.choice(("Valve block", "Manifold block", "Sensor block", "Bearing block", "Clamp block", "Housing", "Mount block", "Body")),
        "block",
    )
    length = pick(rng, 50, 160, 5)
    width, height = pick(rng, 40, min(length, 120), 5), pick(rng, 25, 80, 5)
    size = f"{num(length)} x {num(width)} x {num(height)} mm"
    d.param("length", length, "mm", "block length along X", size)
    d.param("width", width, "mm", "block width along Y", size)
    d.param("height", height, "mm", "block height along Z", size)
    d.say("Overall dimensions", f"{d.title} {size} (X x Y x Z), origin at the centre of the bottom face")
    d.sketches.append(rect_sketch("outline", "length", "width"))
    d.features.append({"kind": "extrude", "id": "block", "name": "Block", "sketch": "outline", "distance": "height"})
    mount = rng.choice([s for s in ("M4", "M5", "M6", "M8") if head(s) < width / 4])
    cb_ok = height >= counterbore_depth(mount) + 8 and edge(mount, "counterbore") <= width / 4
    kind = "counterbore" if cb_ok and rng.random() < 0.7 else "simple"
    margin = pick(rng, max(7, head(mount) / 2 + 3, edge(mount, kind)), max(8, min(15, width / 5)))
    b = _Block(length, width, height, margin, mount, kind)
    axes: set[str] = set()
    _mounts(d, rng, b, axes)
    top = rng.choice(("port", "port", "boss", "boss", "none"))
    extra_height = 0.0
    if top == "port":
        _top_port(d, rng, b, axes)
    elif top == "boss":
        extra_height = _boss(d, rng, b, axes)
    if top != "port" or rng.random() < 0.4:
        _front_port(d, rng, b, axes)
    if rng.random() < 0.5:
        _side_port(d, rng, b, axes)
    if rng.random() < 0.4:
        _side_pocket(d, rng, b)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"height {num(height + extra_height)}", value=height + extra_height)
    if len(axes) > 1:
        d.need("hole_axes", "holes along several axes", count=len(axes))
    _edges(d, rng, b)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _top_port(d: Draft, rng: random.Random, b: _Block, axes: set[str]) -> None:
    sizes = [s for s in ("M6", "M8", "M10", "M12", "M16") if head(s) < min(b.width, b.length) / 2.5 and d.free(tap_drill(s), tap_drill(s))]
    if not sizes:
        return
    size = rng.choice(sizes)
    depth = pick(rng, max(10, b.height * 0.4), b.height - 6)
    d.param("port_depth", depth, "mm", "tapped port depth", f"{num(depth)} mm deep")
    d.say("Holes and ports", f"an {size} tapped port {num(depth)} mm deep in the centre of the top face")
    d.features.append(
        hole(
            "port",
            f"{size} port",
            "block.top",
            [(0, 0)],
            type="tapped",
            fastener=size,
            thread=thread(size),
            depth="port_depth",
            drill_point="118",
        )
    )
    tap = tap_drill(size)
    d.need("holes", f"{size} tap drill", count=1, diameter_min=tap - 0.1, diameter_max=tap + 0.1)
    axes.add("z")
    passages = [v for v in (4.0, 5.0, 6.0, 8.0) if v < tap and d.free(v, v)]
    if not passages or rng.random() < 0.3:
        return
    passage = rng.choice(passages)
    drop = pick(rng, max(passage / 2 + 4, 1.5 * passage), depth - passage / 2 - 3)
    if drop > depth - passage / 2 - 3:
        return
    d.param("passage_diameter", passage, "mm", "cross passage diameter", f"{num(passage)} mm passage")
    d.param("passage_drop", drop, "mm", "passage below the top face", f"{num(drop)} mm below the top")
    d.say("Holes and ports", f"a {num(passage)} mm passage from the front face that meets the port {num(drop)} mm below the top")
    d.features.append(
        hole("passage", "Cross passage", "block.front", [(0, "height - passage_drop")], diameter="passage_diameter", depth="width / 2")
    )
    d.need("crossing_holes", "passage meets the port", count=1)
    axes.add("y")


def _boss(d: Draft, rng: random.Random, b: _Block, axes: set[str]) -> float:
    reach = min(b.length, b.width) - 2 * b.margin - head(b.mount) - 6
    if reach < 16:
        return 0.0
    dia, h = pick(rng, 16, min(reach, 50), 2), pick(rng, 3, 12)
    d.param("boss_diameter", dia, "mm", "boss diameter", f"{num(dia)} mm diameter")
    d.param("boss_height", h, "mm", "boss height", f"{num(h)} mm high")
    d.say("Features", f"a round boss {num(dia)} mm diameter, {num(h)} mm high, centred on the top face")
    d.sketches.append(circle_sketch("boss_outline", "boss_diameter", "block.top"))
    d.features.append({"kind": "extrude", "id": "boss", "name": "Boss", "sketch": "boss_outline", "distance": "boss_height"})
    bore = pick(rng, 4, min(14, dia / 2), 1)
    if rng.random() < 0.6 and d.free(bore, bore):
        depth = pick(rng, h, h + b.height / 2)
        d.param("boss_bore_diameter", bore, "mm", "bore in the boss", f"{num(bore)} mm bore")
        d.param("boss_bore_depth", depth, "mm", "bore depth from the boss end", f"{num(depth)} mm deep")
        d.say("Holes and ports", f"a {num(bore)} mm bore {num(depth)} mm deep in the end of the boss")
        d.features.append(hole("boss_bore", "Boss bore", "boss.end", [(0, 0)], diameter="boss_bore_diameter", depth="boss_bore_depth"))
        d.need("holes", f"{num(bore)} mm bore", count=1, diameter_min=bore - 0.1, diameter_max=bore + 0.1)
        axes.add("z")
    return h


def _front_port(d: Draft, rng: random.Random, b: _Block, axes: set[str]) -> None:
    dia = pick(rng, 4, min(12, b.height / 3), 1)
    if "y" in axes or not d.free(dia, dia):
        return
    depth = pick(rng, 8, b.width / 2 - 10)
    z = pick(rng, max(dia / 2 + 6, 1.5 * dia), b.height - max(dia / 2 + 6, 1.5 * dia))
    d.param("front_port_diameter", dia, "mm", "front port diameter", f"{num(dia)} mm port")
    d.param("front_port_depth", depth, "mm", "front port depth", f"{num(depth)} mm deep")
    d.param("front_port_height", z, "mm", "front port centre above the bottom", f"{num(z)} mm above the bottom")
    d.say("Holes and ports", f"a {num(dia)} mm port {num(depth)} mm deep in the front face, centred, {num(z)} mm above the bottom")
    d.features.append(
        hole(
            "front_port", "Front port", "block.front", [(0, "front_port_height")], diameter="front_port_diameter", depth="front_port_depth"
        )
    )
    d.need("holes", f"{num(dia)} mm front port", count=1, diameter_min=dia - 0.1, diameter_max=dia + 0.1)
    axes.add("y")


def _side_port(d: Draft, rng: random.Random, b: _Block, axes: set[str]) -> None:
    size = rng.choice(("M5", "M6", "M8"))
    clear = b.width / 2 - b.margin - (head(b.mount) + 2 if b.kind == "counterbore" else clearance(b.mount)[1]) / 2
    if head(size) > b.height / 2 or clear < tap_drill(size) / 2 + 2 or not d.free(tap_drill(size), tap_drill(size)):
        return
    depth = pick(rng, 8, min(25, b.length / 2 - b.margin - 6))
    d.param("side_port_depth", depth, "mm", "side port depth", f"{num(depth)} mm deep")
    d.say("Holes and ports", f"an {size} tapped hole {num(depth)} mm deep in the centre of the right face")
    d.features.append(
        hole(
            "side_port",
            f"{size} side port",
            "block.right",
            [(0, "height / 2")],
            type="tapped",
            fastener=size,
            thread=thread(size),
            depth="side_port_depth",
        )
    )
    tap = tap_drill(size)
    d.need("min_holes", f"{size} side tap drill", count=1, diameter_min=tap - 0.1, diameter_max=tap + 0.1)
    axes.add("x")


def _side_pocket(d: Draft, rng: random.Random, b: _Block) -> None:
    pw = b.width - 2 * b.margin - head(b.mount) - 6
    ph = b.height - 10
    if pw < 10 or ph < 8:
        return
    pw, ph = pick(rng, 10, pw), pick(rng, 8, ph)
    depth = pick(rng, 2, min(10, b.length / 4), 0.5)
    d.param("pocket_width", pw, "mm", "side pocket width", f"{num(pw)} x {num(ph)} mm")
    d.param("pocket_height", ph, "mm", "side pocket height", f"{num(pw)} x {num(ph)} mm")
    d.param("pocket_depth", depth, "mm", "side pocket depth", f"{num(depth)} mm deep")
    d.say("Features", f"a rectangular relief pocket {num(pw)} x {num(ph)} mm, {num(depth)} mm deep, centred on the left face")
    sketch = rect_sketch("pocket_outline", "pocket_width", "pocket_height", plane="block.left")
    sketch["entities"][0]["center"] = [0, "height / 2"]
    d.sketches.append(sketch)
    d.features.append(
        {"kind": "extrude", "id": "pocket", "name": "Side pocket", "sketch": "pocket_outline", "mode": "cut", "distance": "pocket_depth"}
    )


def _mounts(d: Draft, rng: random.Random, b: _Block, axes: set[str]) -> None:
    kind = b.kind
    words = "counterbored" if kind == "counterbore" else "clearance"
    word = count_word(rng, 4)
    d.param("mount_margin", b.margin, "mm", "mounting hole centres from the edges", f"{num(b.margin)} mm from the edges")
    d.say(
        "Holes and ports",
        f"{word} {b.mount} {words} mounting holes through the block, one near each corner, {num(b.margin)} mm from the edges",
    )
    at = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "length - 2 * mount_margin", "spacing_y": "width - 2 * mount_margin"}
    mounts = {"kind": "hole", "id": "mounts", "name": "Mounting holes", "plane": {"ref": "block.top"}, "at": at, "fastener": b.mount}
    if kind == "counterbore":
        mounts["type"] = "counterbore"
        d.need("counterbores", "4 counterbores", count=4)
        d.take(head(b.mount), head(b.mount) + 2.5)
    d.features.append(mounts)
    lo, hi = clearance(b.mount)
    d.need("holes", f"4 {b.mount} mounting holes", count=4, diameter_min=lo, diameter_max=hi)
    d.need("hole_spacing", f"spacing {num(b.length - 2 * b.margin)}", value=b.length - 2 * b.margin)
    axes.add("z")


def _edges(d: Draft, rng: random.Random, b: _Block) -> None:
    if rng.random() < 0.5:
        c = rng.choice((0.5, 1.0, 1.5))
        d.param("edge_chamfer", c, "mm", "top edge chamfer", f"{num(c)} mm chamfer")
        d.say("Finish", f"{num(c)} mm chamfer on the top edges of the block")
        d.features.append(
            {
                "kind": "chamfer",
                "id": "top_chamfer",
                "name": "Top chamfer",
                "edges": {"of": "block", "normal": "+z", "extreme": "max"},
                "length": "edge_chamfer",
            }
        )
    elif rng.random() < 0.5:
        r = pick(rng, 2, min(6, b.margin - head(b.mount) / 2 - 1))
        d.param("corner_radius", r, "mm", "vertical edge radius", f"R{num(r)}")
        d.say("Finish", f"R{num(r)} on the four vertical edges")
        d.features.append(
            {
                "kind": "fillet",
                "id": "corners",
                "name": "Vertical edges",
                "edges": {"of": "block", "parallel": "z"},
                "radius": "corner_radius",
            }
        )

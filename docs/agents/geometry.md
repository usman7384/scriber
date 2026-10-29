# Geometry M2: DFM checks, CAD import, mass properties

Branch `feat/geometry-m2`. Only `services/geometry` changed.

## What exists

- DFM checks measured on the built B-rep inside the sandboxed worker, driven by a `partwright_ir.RuleSet` and a `Process`.
- `describe(path)` for STEP, STL and OBJ, and `import_step(path)`, also run in the worker with the same timeout and crash handling.
- Per-part centre of gravity and mass from a small density table keyed by the part's `material`, plus an assembly total.
- One warm worker shared by every geometry test module (`tests/conftest.py`). The geometry suite takes about 30 s instead of 58 s.

## How to call it

```python
geometry = LocalGeometry()
art = geometry.build(design, out_dir)  # unchanged: validity only
art = geometry.build(design, out_dir, rules=rules, process="milling_3axis")
art.ok  # False if any static rule is violated
for f in art.findings:
    f.rule_id, f.severity, f.binding, f.measured, f.required, f.location, f.suggestion

geometry.describe(Path("part.step"))  # ShapeDescriptor; also .stp, .stl, .obj
geometry.import_step(Path("part.step"))  # list[PartMetrics], one per leaf of the STEP product tree
assembly_mass(art.parts)  # (grams, centre of gravity); raises if a part has no known material
```

`build` applies `rules.for_process(process)` before sending the rules to the worker. A finding's severity is the rule's severity when `binding == "static"` and always `warning` when it is `dynamic`, so only static rules can block `Artifact.ok`. If a check raises on unusual geometry, the result is a `warning` finding saying "check could not run" instead of a failed build.

`Finding` gained optional fields: `binding` (default `static`), `measured`, `required`, `location: Location(point, face)` and `suggestion`. `PartMetrics` gained `center_of_mass` and `mass_g`. Every new field has a default, so existing constructors still work.

## Checks: method and limits

| Rule kind | Method | Approximation and limits |
|---|---|---|
| `min_hole_edge_ratio` | For each recognised hole (D-011), cut the part with the plane through the hole's mid-length, normal to its axis. In the section face whose outer wire encloses the hole centre, measure the distance from the centre to that outer wire. Required = ratio × Ø. The suggestion gives the distance to move the hole to and the largest Ø that would pass | Only the outer boundary is checked; hole-to-hole and hole-to-pocket distances are not. A hole concentric with a circular outer boundary (a tube or bushing bore) is skipped. A hole through a curved wall is measured in one plane only |
| `min_wall_thickness` | Sample each face on a 5×5 grid of UV cell centres, keeping only points inside the trimmed face. From each point, cast a ray along the inward normal, cut at the rule's limit, through one `IntCurvesFace_ShapeIntersector` loaded once per part; the nearest exit is the local thickness. An exit through a face that shares an edge with the start face and is turned more than 45° from facing it is the corner they share (a keyway edge), not a wall, and is ignored. Reports the thinnest point per part | Thickness is measured along the normal, so it reads high where walls are not parallel. Thin spots between samples, and knife edges, can be missed; acute corners between neighbouring faces read as walls only below 45°. A 40-tooth gear takes about 1.5 s |
| `min_hole_diameter` | Recognised holes with Ø below the limit | Full 360° concave cylinders count, and bores cut by a keyway or flat (one face over ≥ ¾ turn); slots and other partial bores are not checked |
| `max_overall_size` | Largest extent of the part's axis-aligned bounding box | Not an oriented box. The rule is a single scalar, not a per-axis build volume |
| `min_internal_corner_radius` | Tool axis is +Z. Sharp corners are concave straight edges parallel to Z (`Edge.convexity == CONCAVE`), measured as radius 0. Rounded corners are concave partial cylinders (span < 360°) with their axis parallel to Z, measured by their radius. One finding per corner | Inclined walls, B-spline blends and floor-to-wall edges (ball or bull-nose tooling) are not checked. There is no depth-to-radius rule and no accessibility or undercut check |
| `max_overhang_angle` | Build direction is +Z. Overhang = asin(−n_z), measured from vertical, over downward-facing faces. Planar faces use their single normal; curved faces use the worst of the 5×5 samples. Planar faces lying entirely at the part's minimum Z are the bed and are skipped | No bridge allowance, so the crowns of horizontal holes and short bridges are flagged. The orientation is fixed |

## Assembly checks

- Interference is the Boolean common of two placed parts. It counts as an overlap when its volume exceeds 1e-6 mm³ and its mean thickness (2 × volume / area) exceeds `TOUCH_MM` = 1 µm, the same tolerance a joint's gap must stay within to count as contact. Spline-fitted gear flanks at zero backlash touch to about 0.1 µm (up to 7e-5 mm³ of common volume); a pair turned 0.4° overlaps by 0.09 mm or more.
- A revolute joint between two parts that each carry a `spur_gear` is a mesh: the compiler emits `SLACK = {joint: (b1 + b2) / 4 · cos(pressure angle)}`, the flank gap a centred mesh with that backlash leaves, and the joint's contact allows it (`MateCheck.slack`).

## Import and descriptors

- STEP: `bbox_sorted` is ascending, in mm. Volume and area come from OCCT. `hole_diameters` come from the same hole recogniser as the build, and `face_kinds` counts faces by surface type (`plane`, `cylinder`, ...).
- STL and OBJ are read with `trimesh==5.2.0`, a new geometry dependency (MIT, needs only numpy, and it was already in the lockfile as a dev dependency). Mesh descriptors report the bbox, area and `{"triangle": n}`. Volume is reported only when the mesh is watertight and is 0.0 otherwise. Hole diameters are empty. Units are assumed to be mm.
- `import_step` gives part ids `part_0..n`, takes names from the STEP product labels, and reuses `part_metrics`, so holes, validity and centre of gravity match a native build exactly.

## Mass

The density table (g/cm³): 1.4301 / stainless 7.9, 6061 / aluminium 2.70, steel 7.85, PETG 1.27, PLA 1.24, ABS 1.04, PA12 1.01. The material string is matched by tokens, with the more specific entries first. An unknown material gives `mass_g = None`. Each part is assumed to be homogeneous.

## Checklist rows advanced (none marked done)

| Row | Evidence |
|---|---|
| VM-1 | `test_dfm.py::test_check_passes_or_fails[corner-sharp-fail, corner-small-fail, corner-pass, corner-not-milling, overhang-fail, overhang-pass]`: a pocket with sharp corners fails the 3 mm milling rule and a pocket with R4 corners passes. A 70° overhang fails the FDM 45° rule and a 45° overhang passes. SLA and SLS have only the generic checks |
| VM-3 | `test_dynamic_rule_only_warns`, plus `test_check_passes_or_fails`, which asserts that static violations are errors and make `art.ok` False |
| VM-4 (API half) | `test_hole_near_edge_recommends_moving_it`: Ø10 hole 10 mm from the edge → "move the hole centre to ≥ 15 mm from the edge", with its location. The UI half is open |
| IN-9 (input half) | `test_import.py`: STEP, STL and OBJ descriptor round trips, and `import_step` keeps the holes, names and volumes of each part. Turning an import into an editable "20 % longer" IR is open |
| AS-4 | `test_mass.py::test_assembly_mass_matches_hand_calculation`: a steel base plus a PLA puck matches the hand-calculated mass and centre of gravity to 1e-6 |
| VM-2 | Not advanced here. The geometry side gives the agent a concrete fix ("fillet parallel_z edges ≥ 3 mm") to apply |
| VM-6 | Unchanged. The validity checks still run on every build |

## Known gaps and integration notes

- The agent's repair prompt (`loop.py`) sends only `f.message`. It should also send `f.suggestion` and pass `rules` and `process` from the context service.
- Hole-to-hole spacing, min gap or slot width, draft, hole depth-to-diameter, and 3-axis accessibility are not built.
- Requested IR changes: an optional per-axis build volume for `max_overall_size`; an optional `direction` on rules for the tool axis or build direction (currently fixed to +Z); and `ShapeDescriptor.watertight: bool`, so a 0.0 mesh volume is not ambiguous.

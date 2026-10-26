# IR completeness: the smallest feature set that can describe any manufacturable part

Researched 2026-10-26. The question is how small the IR can stay while still describing essentially any machined, turned, printed, cast/moulded or sheet-metal part. It also has to be easy for a 4B model to emit as JSON, compile to build123d 0.13, and map 1:1 onto a FreeCAD PartDesign tree (D-007). "Checked in source" means the API was confirmed by reading the installed `build123d` 0.13.0 package in `.venv`, not by running it.

## TL;DR

- **Sketch + extrude covers most parts but not all.** Real histories are dominated by sketch and extrude. Turned, cast, swept and sheet parts need revolve, fillet/chamfer, shell, draft, sweep/loft and bends. Every surface class in real CAD data (plane, cylinder, cone, sphere, torus, extrusion, revolution and B-spline surfaces, plus offset) has a producing operation in the set {extrude, revolve, sweep/loft, fillet/chamfer, shell, booleans}.
- **The current IR is not complete even for polyhedra.** Sketch planes are only XY/XZ/YZ with an offset, so a face whose normal is oblique to all three axes cannot be made except as a chamfer side effect. **Rotated datum planes are the single most important completeness fix.** Face-attached planes and fine edge/face selection come next.
- **The proposal is 15 feature concepts and 4 support concepts**, grouped as P0 (9), P1 (8) and P2. One kind does each job: a pocket is an extrude cut and a groove is a revolve cut, with names restored in the FreeCAD export. References are by feature id plus a semantic region, never by topology index.
- **Escape hatch without raw geometry.** Shapes the IR does not cover are reached through (a) primitives combined with booleans, (b) spline sections in a loft or sweep, (c) an allowlisted catalogue of parametric generators (`bd_warehouse` gears, threads, fasteners, keyways), and (d) an imported base body (STEP or fitted mesh) with `mesh_fit` provenance.

## 1. Feature taxonomies that claim coverage

| Source | Feature set (summarised) | Takeaway for the IR |
|---|---|---|
| FreeCAD PartDesign 1.1 ([workbench page](https://wiki.freecad.org/PartDesign_Workbench), [source md](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/PartDesign_Workbench.md)) | Datum point/line/plane/LCS. Additive: Pad, Revolution, Loft, Pipe, Helix, 8 primitives. Subtractive: Pocket, Hole, Groove, sub-Loft/Pipe/Helix, primitives. Transform: Mirrored, Linear/Polar Pattern, MultiTransform. Dress-up: Fillet, Chamfer, Draft, Thickness. Boolean. Gear, Sprocket and Shaft wizards | This is the D-007 export target. Each additive/subtractive pair is one IR kind with `mode` |
| FreeCAD Hole ([doc](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/PartDesign_Hole.md)) | ISO/UTS profile, size, clearance class (ISO 273), threaded or modelled thread, counterbore/countersink/counterdrill, depth by dimension or through all, flat or angled drill point, taper | A semantic hole spec maps directly onto FreeCAD's Hole properties |
| FreeCAD Draft ([doc](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/PartDesign_Draft.md)) | Faces, neutral plane, pull direction, angle | Draft fails on faces tangent to fillets, so the IR order is **draft before fillet** |
| Onshape Part Studio ([feature basics](https://cad.onshape.com/help/Content/PartStudio/feature_basics.htm), [revolve](https://cad.onshape.com/help/Content/PartStudio/revolve.htm)) | Extrude, Revolve, Sweep, Loft, Thicken, Enclose, Rib, Fillet, Chamfer, Draft, Shell, Hole, Helix, Linear/Circular/Curve Pattern, Mirror, Boolean, Split, Transform, Move Face, Wrap, sheet metal. Most tools can add, remove or intersect | Confirms the `mode: add / cut / intersect` design |
| Zoo KCL std lib ([std-solid](https://docs.zoo.dev/docs/kcl-std/modules/std-solid), [std-sketch](https://docs.zoo.dev/docs/kcl-std/modules/std-sketch)) | extrude, revolve, sweep, loft; fillet, chamfer, shell/hollow, patterns, booleans | A code-CAD language that converged on the same core |
| STEP-NC AP238 `machining_feature` ([ARM](https://steptools.com/stds/stepnc/tech_resources/stepnc_arm_html/t_machining_feature.html)); ISO 10303-113/-1814 ([machining features module](https://steptools.com/stds/smrl/data/modules/machining_features/sys/contents.htm)) | boss, planar_face, pocket (open/closed), profile_feature, round_hole, rounded_end, slot, spherical_cap, step, thread (catalogue/defined), toolpath_feature, with transition features (chamfer, edge round) | A manufacturing vocabulary. Every entry maps to one or two IR concepts (table below) |
| MFCAD++ ([QUB dataset](https://pure.qub.ac.uk/en/datasets/mfcad-dataset-dataset-for-paper-hierarchical-cadnet-learning-from/)) | 24 machining-feature classes in 5 groups: steps, slots, through, non-through and transition features | A feature-recognition benchmark. The same five groups appear below |

**Machining-feature coverage by the proposed IR**

| AP238 / MFCAD feature | IR v2 expression |
|---|---|
| round_hole (through, blind, counterbore/countersink, tapered) | `hole` |
| thread (internal / external) | `hole.thread` / `thread` annotation |
| pocket (open/closed, with corner radius and floor fillet) | `extrude` cut of a sketch with corner radii + `fillet` on `concave` edges |
| slot, rounded_end | `slot` entity + `extrude` cut |
| step | `rect`/`path` on an edge + `extrude` cut |
| boss | `extrude` add |
| planar_face (facing) | `extrude` cut, `through_all` |
| profile_feature (outside/inside contour) | `path` + `extrude` |
| spherical_cap | `revolve` of an arc, or a `primitive` sphere |
| turned groove | `revolve` cut |
| chamfer / edge round (transition) | `chamfer` / `fillet` with selectors |

## 2. Learned and LLM CAD representations and their coverage limits

| Work | Operations covered | Coverage evidence |
|---|---|---|
| Fusion 360 Gallery reconstruction ([Willis et al.](https://arxiv.org/abs/2010.02392)) | sketch + extrude only | In the ~20k original designs, sketch and extrude appear in **84% and 79%** of designs and are **more than 3× as common as fillet and chamfer**. In the 8,625-design subset, **38%** have a single extrude. Mean sequence length is 4.74, median 4 |
| Fusion 360 Gallery segmentation ([docs](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/segmentation.md)) | face labels ExtrudeSide/End, CutSide/End, Fillet, Chamfer, RevolveSide/End | 35,680 models are explained by just extrude, cut, revolve, fillet and chamfer |
| DeepCAD ([Wu et al.](https://arxiv.org/abs/2105.09492)) | sketch (line/arc/circle) + extrude | Models using any other operation were **discarded**. **178,238** models were kept from the ~1M-model ABC/Onshape pool. Roughly a sixth survive (our arithmetic; ABC also contains unparseable models, so this is a loose indicator) |
| CADParser ([IJCAI 2023](https://www.ijcai.org/proceedings/2023/200)) | sketch, extrude, revolve, fillet, chamfer | ~40k models. Built because sketch-extrude data was judged too narrow |
| CC3D-Ops ([CADOps-Net](https://arxiv.org/abs/2208.10555)) | 11 operation types, with sweep/helix/dome lumped as "other" | 37k industrial-like models |
| SketchGraphs ([Seff et al.](https://arxiv.org/abs/2007.08506)) | 15M Onshape sketches | Entities: **line 68.5%, circle 10.0%, arc 9.5%, point 8.6%, spline 2.6%, ellipse 0.08%**. Constraints: coincident 42%, projected 10%, distance 7%, horizontal 6%, mirror 6%. **Line + arc + circle cover ~97% of curve entities** |
| CADEvolve ([2602.16317](https://arxiv.org/abs/2602.16317), Table 3; synthetic but said to "broadly follow" real histories) | full CadQuery set | Share of scripts using each operation: extrude 83%, fillet 28%, transform 20%, hole 12%, loft 8.5%, sweep 5.8%, revolve 4.8%, chamfer 4.8%, shell 2.0%, mirror 0.08%. The authors say real data has *more* revolve, chamfer, shell and mirror |
| CAD-Recode ([2412.14042](https://arxiv.org/abs/2412.14042)) | lines/arcs/circles, extrude, union/cut | The paper states that it cannot model operations beyond extrusion and that it fails on revolution and B-spline inputs |
| CAD-Coder ([2505.19713](https://arxiv.org/abs/2505.19713)) | CadQuery text-to-CAD | Non-executable output: base **Qwen2.5-7B 98.8%**, GPT-4o 93%, CAD-Coder after SFT + RL **1.45%** |
| Text2CAD, CADFusion, FlexCAD, Text-to-CadQuery | DeepCAD vocabulary (see `llm-cad-research.md`) | Inherit DeepCAD's sketch-extrude limit |

Reading: sketch + extrude (with cut) is the backbone of about four in five designs. A useful feature set adds, in rough order of frequency, **fillet, holes, patterns/transforms, chamfer, revolve, loft, sweep and shell**. No public analysis of whole Onshape feature histories with per-feature counts was found. The ABC paper gives surface and curve type distributions only as a figure ([ABC](https://arxiv.org/abs/1812.06216), Fig. 3).

## 3. Completeness: theory versus practice

- **Half-spaces.** A set is semialgebraic if and only if it is a finite Boolean combination of polynomial half-spaces (the classical result in real algebraic geometry, e.g. [DIMACS abstracts](https://archive.dimacs.rutgers.edu/archive/Workshops/Algorithmic/abstracts.html); [Geometric Modeling ch. 5](https://13thmonkey.org/documentation/CAD/Geometric_Modeling%2C_a_first_course/CH5.PDF)). Every polyhedron is a Boolean of planar half-spaces, and a half-space clipped to the bounding box is just a large extrude cut. **Polygon sketch + extrude (add/cut/intersect) on arbitrary planes is therefore complete for polyhedral solids.** The current IR's three axis planes make it incomplete.
- **Curved surfaces need more than extrude.** Extrude only creates ruled surfaces parallel to one direction.

| Surface type found in mechanical B-reps (ABC classes) | Minimal producing operation |
|---|---|
| plane | extrude (any plane), chamfer |
| cylinder | extrude circle/arc, hole, revolve, fillet |
| cone | revolve, extrude `taper`, countersink, draft |
| sphere | revolve an arc, sphere primitive |
| torus | revolve an offset circle, fillet |
| extrusion surface (spline profile) | extrude a spline/arc path |
| surface of revolution | revolve |
| B-spline / freeform | loft, sweep |
| offset surface | shell, thicken |

- **Necessary versus convenience.** Strictly, revolve, sweep and loft are needed for doubly-curved and freeform surfaces. Fillet and chamfer are needed in practice, because blends cannot be sketched practically and DFM requires internal corner radii. Shell and draft are geometrically reachable by booleans of offset profiles, but only as feature-level operations do they stay parametric and checkable (uniform wall, draft angle). Patterns, mirror and holes are pure convenience geometrically, but they are first-class for intent, rules (D-011, D-016) and FreeCAD parity.
- **B-rep versus feature-based.** A B-rep is complete but unparametric. A feature tree is parametric but only as complete as its operations. We keep the feature tree as truth (D-007) and accept an imported B-rep only as a frozen base body.

## 4. What must be first-class for manufacturing

| Process | Must be first-class in the IR | Why (our checks; see `dfm-and-standards.md`) |
|---|---|---|
| Machining (3-axis) | Semantic holes (fastener, fit, tapped, depth, drill point); internal corner radius via a `concave` + tool-axis edge selector; part `process` tag | hole-to-edge and depth:D rules, `min_internal_corner_radius`, tool access, D-016 rule scope |
| Turning | `revolve` about the part axis, grooves (revolve cut), external `thread` annotation, chamfers | lathe-able if every face is a surface of revolution about one axis |
| Printing (FDM/SLA/SLS) | `process`, build direction | overhang and min-wall checks need the up axis |
| Casting / moulding | `draft` (faces, pull, neutral plane), `shell` (uniform wall), fillets, part `pull` direction | draft check reads its pull direction from the IR, not from a guess |
| Sheet metal | thickness, bend radius, K-factor, an open profile, and a flat length computed as `Σ straight + Σ θ(R + K·t)` | hole-to-bend and min-flange checks, flat pattern |
| All | Threads as **cosmetic annotations with a designation** (e.g. `M6x1`), geometry at the tap-drill or major diameter | modelled threads are slow and fragile in OCCT. FreeCAD also leaves `ModelThread` off by default |
| All | Tolerances/fits (`H7`, ISO 2768-m) on features | spec checks (D-014) and drawings |

## 5. Small-LLM ergonomics

| Choice | Evidence | Rule for v2 |
|---|---|---|
| Shallow nesting | SO-Bench: a 4B model loses ~40% schema validity at depth > 6 while frontier models stay > 95% ([2511.21750](https://arxiv.org/abs/2511.21750)). DeepJSONEval: strict scores drop 17–38% going from 3–4 to 5–7 levels ([summary](https://www.alphaxiv.org/overview/2509.25922)) | Max depth 4 (Design → parts → features → selector). Flat lists linked by string ids |
| Closed enums, discriminated unions, constrained decoding | Grammar masking gives many more parsable outputs for small models ([2407.06146](https://arxiv.org/abs/2407.06146)). Free-form code from base Qwen2.5-7B is 98.8% non-executable (CAD-Coder) | Every choice is a `Literal`. `kind` discriminates every union. No free strings except ids, names and `Expr` |
| Names, not indices | Topology indices change on regeneration (FreeCAD's topological naming problem). A model cannot count faces | Reference `feature_id` + semantic `region` (`start`, `end`, `side`) + filters. The compiler resolves them geometrically |
| One way per job | D-013 and D-015: the 4B model churns when given freedom (a planning step and unused params both hurt) | No separate `pocket`/`groove`/`pad` kinds. Defaults on every optional field |
| Semantic specs instead of numbers | D-014: facts become checks | `hole.fastener: "M6"`, `fit: "normal"`; the compiler looks up ISO 273 / tap tables (bd_warehouse CSVs) |
| Grow only on evidence | D-010, D-012 eval harness | Add each kind behind an M1-eval gate; drop it if the suite regresses |

## 6. Proposed IR v2 concept list

Support concepts (existing ones kept): `Param` / `Expr` / `Provenance` unchanged.

| # | Concept | Why / what it unlocks | build123d mapping | FreeCAD PartDesign mapping | LLM-emission notes | Pri |
|---|---|---|---|---|---|---|
| S1 | **PlaneRef** `{ref, offset}`, where `ref` is `XY\|XZ\|YZ`, a datum id or `"<feature>.<region>"` | Sketch or hole on a face, e.g. a hole on a boss end | `Plane.XY.offset()`; `Plane(face)` for the matched face | Sketch `AttachmentSupport` (FlatFace) / attach to datum | A string with a regex; offset default 0 | P0 |
| S2 | **Datum plane** `{id, base, offset, rotate_about: X\|Y\|Z, angle, origin}` | **Oblique faces and angled holes; closes polyhedral completeness** | `Plane(...).rotated((ax,ay,az))`, `Plane(origin, x_dir, z_dir)` | `PartDesign::Plane` with AttachmentOffset | One rotation axis plus an angle, not quaternions | P0 |
| S3 | **Selector** `{of, region, convexity, parallel, normal, extreme}` for edges and faces | Fine fillet, chamfer, shell, draft and thread targets; internal corner radii | Faces/edges coincident with the feature's tool body; `Edge.is_interior` / `convexity` (checked in source); `filter_by(Axis)`, `sort_by`, `ShapeList` difference | Resolved to `Edge12`/`Face3` names at export time | `of` = feature id or `part`; every other field an enum with default `any` | P0 |
| S4 | **Part.process** + `pull`/`build` axis + `general_tolerance` | Rule scope (D-016), draft and overhang direction | metadata | Spreadsheet / properties | One enum: `milling_3axis\|turning\|fdm\|sla\|sls\|injection\|casting\|sheet_metal` | P0 |
| 1 | **Sketch entities**: keep rect, circle, slot, polygon; add **`path`** (start point + segments `{to}` or `{to, arc: cw\|ccw, radius}`, per-vertex `fillet`, `closed` flag) | Arbitrary profiles with arcs and corner fillets (~97% of real sketch curves); open paths for sweep, rib and sheet | `Line`, `RadiusArc`, `FilletPolyline`, `make_face` | Sketcher LineSegment / ArcOfCircle + coincident constraints; dimensions as constraints | Segment list depth 1; points are `Expr` pairs as today | P0 |
| 2 | **extrude** `{sketch, mode: add\|cut\|intersect, extent: blind\|symmetric\|two_sided\|through_all\|up_to_next, distance, distance2, reverse, taper}` | Pockets, bosses, facing, through-cuts without guessed lengths, tapered walls | `extrude(..., both, until=Until.NEXT, taper)`; `&` for intersect | Pad / Pocket (Length, ThroughAll, UpToFirst, TwoLengths, Midplane, TaperAngle); intersect → Boolean Common | Replaces `symmetric: bool`; default `blind` | P0 |
| 3 | **revolve** `{sketch, axis: X\|Y, axis_offset, angle, mode}` | Turned parts, grooves, spherical caps | `revolve(axis=Axis(...))` | Revolution / Groove | Adds only `axis_offset` | P0 |
| 4 | **hole** `{on: PlaneRef, at, type: simple\|counterbore\|countersink\|tapped, fastener?, fit?, thread?, diameter?, depth? (none = through), drill_point: flat\|118, cb/cs dims}` | DFM-aware holes from intent; angled holes via datum; tapped holes as cosmetic threads | Current cylinder tools + `Cone` for countersink/drill point; bd_warehouse `clearance_hole_sizes.csv` / `tap_hole_sizes.csv` | PartDesign Hole (Profile, Size, Threaded, CutType, DepthType, DrillPoint) | Either `fastener` or `diameter` (validator enforces exactly one); placement kinds unchanged | P0 |
| 5 | **pattern** `{features: [ids], kind: linear\|polar\|mirror, direction/axis/plane, count, spacing/angle}` | Repeat any feature (ribs, pockets, bosses), symmetric parts | Re-apply each feature's tool body at `Locations` / `PolarLocations`; `mirror(about=plane)` | LinearPattern / PolarPattern / Mirrored / MultiTransform (Originals) | References by feature id; one kind per object; a second direction is P1 | P0 |
| 6 | **fillet** `{edges: Selector, radius}`; **chamfer** `{edges, length, length2? or angle?}` | Internal milling radii, breaking edges, cast blends | `fillet`, `chamfer(length, length2, angle)` | Fillet / Chamfer (Base = resolved edges) | v1 `EdgeSet` values become selector presets | P0 |
| 7 | **shell** `{thickness, open: [Selector], direction: inward\|outward}` | Enclosures with any open face | `offset(amount=-t, openings=faces)` | Thickness | `open: []` = closed shell | P0 |
| 8 | **sweep** `{sketch, path: sketch id (open path) \| helix {pitch, height, diameter}, mode}` | Pipes, handles, springs, gaskets, modelled threads when needed | `sweep(path, is_frenet)`, `Helix` | AdditivePipe / SubtractivePipe, Additive/SubtractiveHelix | Path is another sketch, so references stay flat | P1 |
| 9 | **loft** `{sketches: [ids], ruled, mode}` | Transitions, ducts, freeform approximations | `loft(sections, ruled)` | AdditiveLoft / SubtractiveLoft | Section order = list order | P1 |
| 10 | **draft** `{faces: Selector, angle, pull, neutral: PlaneRef}` | Castings and mouldings | `draft(faces, neutral_plane, angle)` (checked in source) | Draft | Emit before fillets; the validator warns on the wrong order | P1 |
| 11 | **thread** (external, cosmetic) `{face: Selector, designation, length}` | Threaded shafts and studs on turned parts | metadata; geometry stays at the major diameter; optional helix sweep | Property / spreadsheet note (no PartDesign cosmetic external thread found) | Designation enum from ISO 261 tables | P1 |
| 12 | **primitive** `{shape: box\|cylinder\|sphere\|cone\|torus\|wedge, dims, at, rotate, mode}` | CSG fallback for anything a sketch makes awkward | `Box`, `Cylinder`, `Sphere`, `Cone`, `Torus`, `Wedge` | Additive/Subtractive primitives | Flat; `at` is an xyz `Expr` triple | P1 |
| 13 | **sheet** `{sketch (open path), thickness, width, bend_radius, k_factor}` + computed flat length | Brake-formed brackets, enclosures | `make_brake_formed(thickness, station_widths, line)` (checked in source) | SheetMetal addon (BaseBend, Unfold) when installed, else Pad of a thick profile | Single-axis bends only at P1 | P1 |
| 14 | **standard** `{catalog: gear_spur\|thread_iso\|keyway\|sprocket\|..., params}` | Constrained escape hatch: allowlisted parametric generators, no raw geometry | `bd_warehouse` classes | Involute gear / Sprocket where present, else a non-parametric Part feature | Closed catalog enum; params validated per entry | P1 |
| 15 | **Tolerance / fit** fields on hole, extrude and revolve | Spec checks, drawings, fits | metadata → requirement checks | Spreadsheet / TechDraw later | Enums (`H7`, `h6`, `IT7`) | P1 |
| — | **Assembly**: instances, mate frames by PlaneRef/axis, joints `rigid\|revolute\|prismatic\|cylindrical` | M4 assemblies | `RigidJoint`, `RevoluteJoint`, `LinearJoint`, `CylindricalJoint` | Assembly workbench joints | Separate top-level list; parts referenced by id | P1 (M4) |
| — | P2 set: `spline`/`ellipse`/`text` entities; sketch constraints solved by planegcs; variable or setback fillets; edge flanges + full unfold; `up_to_face`; imported base body (STEP or mesh fit); rib; multi-body booleans | Long tail | various | various | Gate each on eval demand | P2 |

## 7. Out of scope, and how those shapes are still reachable

| Not first-class | Reachable via |
|---|---|
| Class-A / freeform surfacing (boundary, fill, G2 blends) | `loft`/`sweep` through `spline` sections (P2) or an imported base body |
| Variable-radius / setback fillets, face blends | Constant fillets + chamfers; P2 if demanded |
| Lattices, gyroids, textures, knurls | Out of scope. Infill is the slicer's job; knurls are cosmetic notes |
| Topology-optimised / organic shapes | Imported base body (`mesh_fit` provenance) with DFM checks run on it |
| Modelled threads | Off by default; `sweep` along a helix or a `standard` thread for printed threads |
| Direct editing (move/replace/delete face) | Not needed: edit parameters and regenerate from the IR |
| Mould tooling (core/cavity, parting surfaces) | Out of scope; `draft` + `process` + `pull` make the part mouldable |
| Weldments / frames | `sweep` of a standard profile along a path, or an assembly of extrusions |
| Surface-only and multi-body modelling | Out of scope at P0/P1; one solid per part (validity gate) |

## 8. Migration from the current IR

- Add `ir_version: 2` to `Design`. A pure `upgrade_v1(dict) -> dict` in `services/ir` rewrites stored designs on load; eval golden designs are re-verified for identical volume and bounding box.
- Mechanical mappings:
  - `SketchPlane{base, offset}` becomes `PlaneRef{ref: base, offset}`.
  - `Extrude.symmetric: true` becomes `extent: symmetric`.
  - `Hole` gains `type` (`counterbore` when the counterbore fields are set, else `simple`) and `on`.
  - `EdgeSet` becomes selector presets: `all` → `{of: part}`; `top`/`bottom` → `{of: part, normal: ±Z, extreme: max/min}`; `parallel_*` → `{of: part, parallel: *}` (the current filter that skips curved faces is kept).
  - `Shell.open_face` becomes `open: [{of: part, normal: ±Z, extreme}]` or `[]`.
- Order of work: the P0 batch first (datum planes, `path`, extrude extents/intersect/taper, semantic hole, pattern, selectors, shell selector, process), each measured on the M1 eval. The FreeCAD exporter (D-007) targets v2 only, and the selector resolver is shared by the compiler and the exporter. Prompts and few-shot examples are updated in the same change as each kind.

## Open questions

1. Should selectors be objects (enum-checked by constrained decoding) or one dotted string such as `"pocket.side:concave:z"`, which is flatter but only regex-checked? Ollama/llama.cpp grammar support for `pattern` is partial. Needs an eval A/B.
2. How should selector regions be resolved: OCCT history (`BRepAlgoAPI` `Modified`/`Generated`) or geometric coincidence with the feature's tool body? Coincidence is simpler but ambiguous on coplanar merges.
3. Is the `pattern` of arbitrary features compiled as tool-body replay robust for features that depend on earlier geometry (`up_to_next`, fillets)? FreeCAD has the same limitation; restricting patterns to extrude, revolve, hole and primitive at P0 may be wise.
4. Sheet metal: is `make_brake_formed` plus our own flat-length formula enough for P1, or do users expect edge flanges and full unfold (FreeCAD SheetMetal addon, licence to be checked)?
5. Schema size versus 4B context: will one schema with all P0+P1 kinds still fit and keep validity, or does D-010's staged emission become necessary?

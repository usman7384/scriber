# IR v2 proposal

Status: proposed, awaiting approval. Evidence and citations: `docs/research/ir-completeness.md`.

## Goal

Small, but complete: every manufacturable mechanical part (machined, turned, printed, cast or moulded, brake-formed) has an IR description that compiles to one valid build123d solid and maps one-to-one onto a FreeCAD PartDesign feature tree (D-007). Small means one kind per job, closed enums, references by name, and nesting no deeper than four levels, because the 4B model loses schema validity quickly beyond that.

## Why v1 is not enough

- **Not complete even for flat faces.** Planes are only XY, XZ and YZ plus an offset, so a face tilted against all three axes cannot be built. Any polyhedron is a Boolean of half-spaces, so arbitrary planes plus extrude add/cut/intersect closes that gap.
- **No way to say "on that face".** Holes and sketches cannot start from a face of an earlier feature. The user's manifold prompts failed largely because every "front" and "side" port silently landed on the top plane.
- **Curved and swept shapes** need revolve with an offset axis, sweep and loft; sketches need arcs and corner fillets (lines, arcs and circles are about 97 % of real sketch curves).
- **Manufacturing intent is not first-class**: no countersink, tapped hole, drill point, draft, pull direction or process per part, so DFM rules cannot be scoped (D-016).

## Proposal

**P0 — completeness for prismatic and turned parts (implement first)**

| Concept | Replaces or adds | Unlocks |
|---|---|---|
| `PlaneRef`: `XY`/`XZ`/`YZ`, a datum id, or `"<feature>.<region>"` (start, end, side) + offset | replaces `SketchPlane` | sketches and holes on any earlier face |
| `datum` plane: base, offset, one rotation axis and angle | new | oblique faces, angled holes, polyhedral completeness |
| Selector object `{of, region, convexity, parallel, normal, extreme}` | replaces the six `EdgeSet` values | fillet internal corners only, chamfer one face's edges, shell any face |
| `part.process`, pull/build axis, general tolerance | new | rule scope, draft and overhang direction |
| `path` sketch entity: lines and arcs with per-corner fillets, open or closed | new | arbitrary 2D profiles; open paths for sweeps and sheet |
| extrude `extent`: blind, symmetric, two-sided, through-all, up-to-next; `mode` add/cut/intersect; `taper` | replaces `symmetric` | pockets and bosses without guessed lengths, passages that stop at a crossing bore |
| revolve `axis_offset` | extends revolve | grooves, turned parts off the origin |
| semantic `hole`: on any `PlaneRef`; type simple, counterbore, countersink, tapped; size from `fastener` + `fit` or an explicit diameter; drill point | extends hole | ISO 273 / tap sizes from intent, cosmetic threads, drill cones |
| `pattern`: linear, polar, mirror of listed feature ids | new | ribs, ears, port groups, symmetric parts |
| fillet/chamfer/shell take selectors | changes three features | precise blends and open faces |

**P1 — freeform, castings, sheet metal and the constrained escape hatch**: `sweep` (path or helix), `loft`, `draft`, external cosmetic `thread`, CSG `primitive`s, brake-formed `sheet` with computed flat length, an allowlisted `standard` catalogue (gears, threads, keyways from bd_warehouse), tolerance and fit fields, and assemblies with joints (already planned for M4).

**P2 — on eval demand only**: splines, ellipses and text in sketches, solved sketch constraints, variable fillets, flanges and unfold, up-to-face, imported base bodies, rib.

**Outside the IR**: lattices, textures and topology-optimised organic shapes come in as an imported base body with `mesh_fit` provenance and are checked like any part; no raw geometry from the model.

## Decisions on the research's open questions

1. **Selectors are objects**, not dotted strings: every field is a closed enum, so constrained decoding enforces them, and the nesting stays at four levels.
2. **Regions are resolved by geometric coincidence with the feature's tool body** (faces of the result that lie on the tool's start, end or side faces). OCCT history is more exact but harder to keep stable across kernels; revisit if coplanar merges cause ambiguity in practice.
3. **P0 patterns cover extrude, revolve, hole and primitive only.** Patterns of fillets or up-to-next features wait until replay is proven.
4. **Sheet metal stays brake-formed in P1**, with our own flat-length formula; flanges and unfold are P2 after checking the SheetMetal add-on's licence.
5. **Schema size is measured, not assumed.** P0 lands with staged emission behind a switch (parameters, then sketches and planes, then features), A/B-tested on the M1, grounded and challenge sets like D-013. The loser is deleted.

## How the challenge manifold maps onto P0

Main block, terraces and ears: `path` sketches + extrude add. Bosses: circles on `"block.end"`. Side relief pockets and the front recess with rounded corners: `path` with corner fillets on a side `PlaneRef` + extrude cut. Ribs: one extrude + `pattern`. Ports: semantic holes on the top, front and side faces, counterbored or tapped, with drill points. Internal passages: blind holes from two faces that meet (up-to-next or explicit depth). Sealing grooves: a ring sketch cut on the port's face. Bottom chamfer and selected fillets: selectors with `normal` and `convexity`. Engraved labels need P2 text and are not part of the challenge checks.

## Migration

`Design.ir_version = 2`, with a pure `upgrade_v1()` that rewrites stored designs on load (plane, extent, hole type and edge-set presets map mechanically) and golden tests that v1 designs rebuild with identical volume and bounding box. The prompt, worked examples, normaliser, validator, compiler, DFM probes and web parameter panel change in the same series; the FreeCAD exporter (M4) targets v2 only.

## Order of work and gates

1. `PlaneRef` + `datum` + selector resolver + `part.process` (compiler and validator, with unit and build tests).
2. `path`, extrude extents/intersect/taper, revolve offset.
3. Semantic hole (types, fastener/fit tables, drill point) and `pattern`.
4. Prompt and examples for all of the above; staged-emission A/B.
5. Each step must keep the M1 and grounded scores at or above their current values; the challenge set is reported every time and is the gate for M5.

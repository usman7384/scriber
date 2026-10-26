# IR v2 P0 (integrator)

Implemented in the order of `docs/IR_V2.md`; decisions D-017 to D-019.

## What landed

- Plane references: XY/XZ/YZ, rotated datums, and faces of earlier features (`"block.front"`, `"boss.end"`, `"part.top"`). Face planes keep their base plane's coordinates; offsets move outward; cuts go into the material and adds go outward.
- Selectors for fillet, chamfer and shell (`of`, `normal`, `parallel`, `convexity`, `extreme`).
- `path` sketch entities with arcs and corner fillets; extrude extents (blind, symmetric, two-sided, through-all, up-to-next), intersect and taper; revolve axis offset.
- Semantic holes on any plane: simple, counterbore, countersink, tapped, sized from `M<d>` or `M<d>x<pitch>` (M2–M30, interpolated between ISO 273 rows) or a diameter; drill points.
- Linear, polar and mirror patterns of extrude, revolve and hole tools; part `process`.
- v1 designs upgrade on load; every v1 fixture rebuilds unchanged.
- Validation: reference order, face names, extents, hole sizing, pattern sources (listing valid ids), revolve sketches that cross their axis (with the extrude to use instead), overlapping holes by depth.
- Agent: v2 rules and five worked examples (including a valve block with a tapped port, a crossing passage and counterbores); answers capped at `max_tokens`; cut-off answers are never quoted back in repairs.

Tests: 250 passing, including 21 real-kernel builds of the new features.

## Eval gates (qwen3.5:4b, 2026-10-26)

| Gate | v1 (last) | v2 | Verdict |
|---|---|---|---|
| M1 set, fully correct / checks | 5/10, 21/35, median 63 s (`m1-20261025-234808`) | 4/10, 16/35, median 133 s (`m1-20261026-032430`) | **not met**: fewer checks pass and generation is twice as slow |
| Grounded set, grounded mode | 2/10, 15/45, 5/10 built (`grounded-20261026-005645`) | 3/10, 23/45, 6/10 built (`grounded-20261026-035401`) | met |
| Challenge set | 0/2, nothing built | 0/2, nothing built (`challenge-20261026-025416`) | not met (expected; gate for M5) |
| Staged emission (A/B) | — | M1 2/10, 9/35 vs unstaged 4/10, 16/35; challenge slower | staged deleted (D-019) |

Replays of every failed answer show the remaining challenge blockers are model behaviour rather than missing IR: revolving a centred circle for a boss, patterning a feature before it exists, placing a front-face port outside the face after being told the valid range, writing a selector word into a numeric field. The M1 regression has two visible causes: longer answers (the v2 schema and five examples) and the model reaching for v2 features where a plain plate would do.

## Open

- Recover the M1 score on v2 (prompt length, example choice) before more IR is added.
- The challenge set will most likely need a stronger model or fine-tuning on our IR (M5 data pipeline) rather than more prompt work.

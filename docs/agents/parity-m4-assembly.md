# M4 assemblies (build agent)

Branch `feat/m4-assembly`. Rows: AS-2, AS-3, AS-4, GE-5, GE-6, PR-5, PR-8, and the API half of AS-1.

## What landed

- **IR** (`services/ir`): optional `Design.assembly` with `connectors` (id, part, origin in the part's own coordinates, `z` and `x` axis directions) and `joints` (`parent` and `child` connector, kind `fastened`/`revolute`/`slider`, `angle` about and `offset` along the parent's z). A joint places the child part so its connector frame coincides with the parent's; parts that are no joint's child stay where they are. Origins, angles and offsets are expressions, so a parameter edit moves a part together with the features that use the same parameter. Validation: unknown parts or connectors, axes that are not perpendicular, a part placed by two joints, loops, bad expressions. `scope`, `splice` and `part_hash` support component edits; `insert` mates a new single-part design at a named connector.
- **Compatibility**: a design without an assembly compiles to the same source and has the same `design_hash` and answer JSON as before (`services/agent/tests/test_ir_compat.py` pins the five worked examples). The IR JSON schema grows by the optional `assembly` property (16 551 → 18 456 characters), which the generate loop passes to constrained decoding.
- **Geometry**: compiled assemblies move each part by its joint chain (`Location` composition in the worker). Every part reports its `placement` (3×4 matrix), including parts read back from STEP. Assembly builds report pairwise interference volume (bounding-box prefilter, Boolean common), the gap at each joint, and total mass and CoG. Overlaps (`ASM-INTERFERENCE`) and joints whose parts do not touch (`ASM-MATE`) are errors, so the repair loop sees them. STEP keeps the product structure with one placed occurrence per part.
- **Agent**: `refine(..., target=part_id)` shows the model only that part and its parameters and splices the answer back; `place(prompt, assembly, mate, ...)` generates a part with one connector and mates it at the named connector (the request gets one added paragraph asking for the connector; the training prompts in `prompts.py` are unchanged).
- **API**: `GET /models/{id}/components` lists part ids, names, materials, parent part and joint; `POST /models/{id}/refine` with `target` now uses the scoped edit instead of prefixing the instruction.

## Demos

`evals/src/partwright_evals/parity_m4_assembly.py` (`ROWS`, not yet in `parity.registry()`); fixtures in `evals/parity/m4/assembly/` (drone, enclosure, servo mount, servo). Offline: `uv run pytest evals/tests/test_parity_m4_assembly.py`. Recorded run of the model-free rows (AS-2, AS-4, PR-8, real geometry worker): `evals/results/parity-m4-assembly-20261029-030241/`.

| Row | Demo | Offline (FakeLLM) | Live model needed |
|---|---|---|---|
| AS-2 | build drone, reload `design.json` and rebuild, read STEP back; compare placements | pass: 9 mates in the IR, 10 STEP occurrences, placement error 0 (IR and STEP) | no |
| AS-4 | drone mass and CoG vs a hand calculation from boxes and cylinders | pass: 196.2701 g both, CoG (1.931, 0, 3.2097) both | no |
| PR-8 | move `battery_x` −20 mm and rebuild | pass: CoG x −3.862 mm measured and predicted, the four frame holes move −20 mm and stay coaxial with the mount's, all mates valid | no |
| GE-6 | `generate(drone brief)` | pass with the fixture as the scripted answer: 1 frame, 4 arms, 4 motor mounts, 1 battery mount, 196.27 g | yes |
| GE-5 | `generate("enclosure with lid and 4 M3 screws")` | pass with the fixture: 6 components, all mated, max interference 0 mm³ over 9 touching pairs | yes |
| PR-5 | `refine(enclosure, "add vent slots", target="lid")` | pass: base part hash unchanged, lid gains a patterned slot cut (1321 mm³ removed) | yes |
| AS-3 | `place(servo brief, servo mount, "servo_pocket")` | pass: servo mated at `servo_pocket`, interference 0, mates valid | yes |

AS-1 (API half): `apps/api/tests/test_assembly.py`; the viewer half is a web row.

## Gaps

- The live-model rows (GE-5, GE-6, PR-5, AS-3) have not been run against a model; the 4B has never seen assemblies, and the schema change may affect its generation until it is trained on assembly answers.
- Joint kinds are recorded and exported but not simulated: revolute and slider joints are placed at their current `angle`/`offset`; there are no limits or motion.
- No part instancing: four identical screws are four parts.
- Mates are exported in our IR bundle only; STEP carries product structure and placements, not mate definitions (OCCT writes no AP242 kinematics).
- The enclosure models both threads at their major diameter (internal 3.0 mm, external 2.98 mm, the M3-6g maximum), so engaged threads do not count as interference.
- Interference uses the Boolean common volume; it is exact for touching faces in the fixtures but is not tolerance-aware for near-coincident curved faces.

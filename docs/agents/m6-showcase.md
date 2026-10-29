# M6 showcase benchmark

Closes nothing yet: it adds the gate for M6 (`docs/M6_SHOWCASE_PLAN.md`), the row `M6-SHOWCASE`, which passes only on a live run.

## Cases

`evals/cases/showcase.yaml`, 20 one-line prompts with dimensions, our own wording. Each names the 3 parameters it must expose.

| id | part | kind |
|---|---|---|
| sc01-gear-pair | module 2, 20/40-tooth spur gears at the 60 mm centre distance | assembly (revolute) |
| sc02-vbelt-pulley | 90 mm two-groove V-belt pulley with hub | revolve |
| sc03-keyed-shaft | stepped shaft, DIN 6885 keyway, two circlip grooves | keyway, groove |
| sc04-pillow-block | 52 mm pillow block, bolt holes 100 apart | part |
| sc05-gearbox-housing | 160 x 120 x 80 box, M5 bosses, bearing bosses with ribs, bolted lid | assembly (shell_with_lid, boss_pattern, rib) |
| sc06-nema17-mount | L bracket, 23 mm pilot, 31 mm square, belt slot | part |
| sc07-camera-mount | block with 1/4-20 tripod tap drill, two clearance holes | part |
| sc08-gripper-finger | tapered finger, mounting holes, patterned grip grooves | part |
| sc09-electronics-enclosure | 120 x 80 x 40 box, M3 bosses, lid with lip and vents | assembly (shell_with_lid) |
| sc10-hinge | butt hinge, three knuckles, pin with head, countersunk holes | assembly (3 parts) |
| sc11-shaft-clamp | two-piece clamp for a 20 mm shaft, M5 screws | assembly |
| sc12-servo-horn-bracket | disc horn carrying a pan bracket | assembly |
| sc13-flange-coupling | two keyed flange halves bolted face to face | assembly (keyway) |
| sc14-angle-bracket | 60 mm legs, two gussets, holes in both legs | part |
| sc15-hub-gear | module 1.5, 36 teeth, hub, keyed bore | spur_gear, keyway |
| sc16-heat-sink | 60 x 60 base, 15 fins | pattern |
| sc17-piston | 40 mm piston, rod bore, two O-ring grooves | groove |
| sc18-pi-tray | Raspberry Pi 4 tray, standoffs on 58 x 49, floor rib | boss_pattern, rib |
| sc19-handwheel | 125 mm wheel, five spokes, hub with bore | polar pattern |
| sc20-flange-bearing | square flange housing, 62 mm seat over a 50 mm bore | counterbore |

Checks are the harness requirement kinds plus three new ones in `partwright_evals.shapes` (case field `shape`): `teeth` (a closed section outline with that many lobes over its mid radius and that tip diameter, cut across x, y and z), `parts` (part count) and `mates` (that many joints, none broken, no interference).

## Gate

`partwright_evals.parity_m6.showcase` runs every case through the agent with `rig.llm`, then the checks, the parameter names and a +5 % edit of each named parameter that must rebuild valid. A case is fully correct when it is valid and every one of those passes. The row passes at 15/20 (75 %) fully correct and a median agent time under 120 s (edit rebuilds are not timed). Per-case output, `results.json`, `SCORECARD.md` and a PNG per built case go to the row's folder.

Run (once the module is in `parity.registry()`): `uv run partwright-parity M6-SHOWCASE --model partwright-ir:4b-s2`. Without the edits, the plain harness also takes the file: `uv run partwright-evals evals/cases/showcase.yaml --models partwright-ir:4b-s2`.

## References

`evals/parity/m6/reference/<id>.json` is a hand-written design per case, using the high-level features where a designer would. Every one builds with the real geometry worker and passes all of its checks and edits (`evals/tests/test_parity_m6.py`, about 100 s), so each case is achievable and its checks accept a correct part. They show that the new features carry these parts in a handful of features each (the gear pair is two `spur_gear`s and one revolute joint whose angle keeps a tooth gap facing the pinion for odd and even wheels), and that the auto lid mate, `boss_pattern` on a face of `shell_with_lid`, ribs drawn into a boss, and keyways in a gear's bore all compose. No feature bug turned up. Every reference and each of its +5 % edits also builds with no error finding under `DEFAULT_RULES` (`test_reference_and_its_edits_meet_the_default_rules`), so an agent working in a project with the default rules can meet each prompt exactly (`docs/agents/showcase-default-rules.md`).

Harness changes: `Case.shape`, `run_case` takes `max_repairs` and `seed` and times the agent without the edit rebuilds. `evals/cases/showcase.yaml` is in the training leak guard (`EVAL_CASES`).

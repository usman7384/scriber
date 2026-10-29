# M6: showcase parts with local models (plan, not started)

Goal: one-line prompts with dimensions give correct, editable, recognisable engineering parts and small assemblies, beyond plates and brackets, on the 6 GB laptop and local models only. Free-form organic shapes and whole machines (engines) stay out of scope.

## Why S2 cannot do this today

S2 writes every sketch, plane and face reference itself. A part with more than about six features accumulates errors faster than the repair loop fixes them, and shapes such as gear teeth need geometry the model cannot compute (live runs 2026-10-29: 64 % of benchmark dimensions in tolerance, 4/16 bracket variants, no assemblies; `docs/agents/integration-2026-10-29.md`).

## Approach: the model decides what, code computes how

1. **High-level IR features**, compiled deterministically and fully parametric: `spur_gear` (module, teeth, face width, bore, involute profile), `rib`, `boss_pattern`, `keyway`, `groove` (circlip, O-ring), `counterbore`/`countersink` patterns, `shell_with_lid` (lip, clearance, screw bosses), `bearing_seat` (from a bearing designation), `hex_pocket`, `thread` (cosmetic and modelled), `vent_pattern`. Each gets unit tests against hand-computed geometry. Answers become 5-10x shorter.
2. **Planning step**: a short structured plan (parts, their roles, joints) before any geometry; each part is generated and repaired on its own, then joined with assembly connectors (D-033). Plans are checked (every part used, every joint resolvable) before generation.
3. **S3 data** built from the new features: multi-feature parts and 2-6 part assemblies from the generators, plan-then-part samples, and the live-run failures as on-policy repairs. Same leak guard and gates (D-028).
4. **STEP to IR feature recognition** for uploaded parts (planes, cylinders, fillets, pads, pockets, holes from the exact B-rep), so edits start from a correct design instead of a rewrite.

## Milestone gate

A showcase benchmark of about 20 cases, each a one-line prompt with dimensions and hand-written checks, recorded as parity-style demos with screenshots:

- spur gear pair at the right centre distance, V-belt pulley, shaft with keyway and circlip grooves
- pillow-block bearing housing, gearbox housing with bosses, ribs and a bolted lid
- NEMA 17 motor mount with belt slot, camera mount with tripod thread, robot gripper finger
- electronics enclosure with lid, screw bosses and vents (mated assembly)
- hinge, clamp, servo bracket with horn (assemblies)

Exit: 15 of 20 fully correct on the default local model, median under 2 minutes, every part editable through its named parameters.

## Order of work

1. Features 1 at a time with tests, starting with the ones most cases need (`counterbore` patterns, `boss_pattern`, `rib`, `shell_with_lid`, `spur_gear`).
2. Showcase benchmark and its demos (baseline on S2 with the new features prompted).
3. Planning step and its checks.
4. S3 data and one night of training; gates; repeat for 3-4 rounds.
5. STEP to IR recognition in parallel (no model needed).

Estimate: 1-2 weeks, about one day of data and feature work plus one training night per round.

Risks: the 4B may plateau on multi-part planning; each new feature is engineering code that must be verified (gears especially); open-ended requests will still trail hosted frontier models.

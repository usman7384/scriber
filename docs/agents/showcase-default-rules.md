# Showcase prompts under the default rules, S3 workarounds relaxed

Closes no checklist row. It makes every M6 showcase case (`docs/agents/m6-showcase.md`) achievable under `DEFAULT_RULES` and lifts the S3 data limits that D-039 fixed.

## Showcase prompts

Six prompts fixed a hole closer to an edge than the default 1.5 x D rule allows. Each changed one number, with its check and reference, chosen so the reference and every +5 % parameter edit keep the rule:

| case | before | after | hole to edge |
|---|---|---|---|
| sc04-pillow-block | 130 x 38 x 15 base | 140 x 38 x 15 | Ø11: 15 → 20 mm (needs 16.5) |
| sc07-camera-mount | clearance holes 48 apart | 44 apart | Ø4.5: 6 → 8 (6.75) |
| sc10-hinge | 8 mm knuckles | 14 mm | Ø4.2 pin hole: 4 → 7 (6.3) |
| sc11-shaft-clamp | 50 x 20 x 15 halves | 55 x 20 x 15 | Ø5.5: 7.5 → 10 (8.25) |
| sc13-flange-coupling | 90 mm flange | 100 mm | Ø9: 12.5 → 17.5 (13.5) |
| sc20-flange-bearing | 86 x 86 x 12 flange | 105 x 105 x 12 | Ø11: 11 → 20.5 (16.5) |

All 20 references build with no error finding under `DEFAULT_RULES`, and so do their 60 edits; `evals/tests/test_parity_m6.py::test_reference_and_its_edits_meet_the_default_rules` holds it. The new numbers add no 8-gram that any S1-S3 generator text shares (300 seeds x 4 styles per family: 0 new drops).

## S3 limits lifted

See the S3 section of `docs/agents/training.md`.

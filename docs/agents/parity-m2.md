# Parity suite, M2 rows

`evals/src/partwright_evals/parity_m2.py` holds one scripted demo per M2 row (`ROWS`), run by `partwright-parity`. Fixtures are in `evals/parity/m2` (`make_fixtures.py` regenerates the PDFs and `holes.xlsx`). Offline tests: `evals/tests/test_parity_m2.py`, with `FakeLLM`, a real `LocalGeometry` and a real `LocalContext`.

```bash
uv run pytest evals/tests/test_parity_m2.py
uv run partwright-parity IN-2 IN-3 IN-9 IN-12 IN-13 IN-15 CX-4 CX-7 CX-8 CX-9 CX-10 CX-11 VM-1 VM-2 VM-3 VM-5 VM-7 CD-5 CD-8 DP-17
```

Every demo builds its own project store under its output folder with `HashEmbedder`, so retrieval is deterministic and needs no Ollama. A generation counts only when the loop ends in `done`. Each demo measures the built B-rep, STL or graph itself instead of trusting the loop's checks. Wall thickness is measured on a mid-height STL section, and corner radii by a probe rule that reports every concave Z corner.

## Rows

| Row | Demo | Needs the model |
|---|---|---|
| CX-9, VM-1, VM-3, VM-5, CD-8 | facts, DFM fixtures, static/dynamic gating, per-project override, IR export/re-import | no: closed offline |
| IN-2, IN-3, IN-9, IN-12, IN-13, IN-15, CX-4, CX-7, CX-8, CX-10, CX-11, DP-17 | generation from uploaded files, measured against the row's acceptance test | yes: the offline test checks the plumbing with a scripted answer, and the live run decides the row |
| VM-2, CD-5 | `refine` with milling rules, then corner radii, re-check, diff (`diff.json`, `diff.md`) | yes |
| VM-7 | per-case constraint coverage (`coverage.md`). The gate fails on any unevaluated input constraint, and `lid-spec.md` plants one (wall thickness) | yes, for the lid's size checks |

## Product changes made for these rows

- `partwright_agent.project_context.coverage(facts, checks)` maps each numeric fact to the check that evaluated it, or `None` (CX-7, VM-7). Requirements are now deduplicated with their tolerance, so a tighter tolerance on the same value is still checked.
- Hole-table facts reach the prompt with their position (`hole_h1 = 6.6mm at x=20, y=15`) (IN-2, IN-3).
- Thread callouts held by inserts or taps (`4×M3 heat-set inserts`) accept tap drill to insert bore (0.75 to 1.45 d) instead of ISO 273 clearance. Before this, the box convention forced 3.4 mm clearance holes (CX-8).
- `LocalContext.changed(project, old_doc, new_doc)` returns the ids of facts that a revised document changed. Its output feeds `stale` (CX-11).

## Gaps

- Hole positions from tables are not loop checks: the demo measures them, but the agent does not repair a misplaced hole. `coverage` reports them as unevaluated, so they are kept out of the VM-7 cases.
- CX-10 needs `intent` on every feature. The design prompt does not ask for it, so a live model may fail the row.
- `refine` prompts do not carry the project rules. VM-2 and CD-5 depend on the DFM finding and its suggestion reaching the repair.
- VM-7's gate runs in the parity suite and its CI test, not in `partwright-evals` (`run.py`).
- CD-8's export is the build folder (STEP + `design.json` + `model.py`). STEP alone carries no IR.

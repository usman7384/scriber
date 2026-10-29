# Integration run, 2026-10-29

One unattended session: S2 training, M1 to M5 parity demos built by parallel agents (each in its own worktree or file area, merged here), then live runs on the new default.

## Model

S2 trained overnight and replaced S1 (D-036); results in `docs/agents/training.md`.

## Parity suite (D-030)

`partwright-parity` registers 121 row demos across `evals/src/partwright_evals/parity_m1.py` … `parity_m5_*.py`; each also runs offline in `evals/tests/test_parity_*.py` with a scripted model. Agent notes: `parity-m2.md`, `parity-m3-api.md`, `parity-web.md`, `parity-m4-*.md`, `parity-m5-*.md`. Status per row: `docs/reference/PARITY_CHECKLIST.md`; summary: `docs/PARITY_REPORT.md`.

Live runs on `partwright-ir:4b-s2` (vision rows on `qwen3.5:4b`): `parity-20261029-112255` (51 rows, 13 pass) and `parity-20261029-132754` (11 rows, 4 pass). Rows that need no model were recorded earlier the same day.

## What the live runs show

- Speed is fine: benchmark median 33 s per part (PF-1, PF-7), 20 tok/s, 2.8 GB loaded (PF-8).
- Accuracy is the gap: 98 of 152 specified dimensions within tolerance on the 30-part benchmark (64 %, GE-8 needs 95 %); 13 of 16 standard flanges (DP-15) but 4 of 16 bracket variants (DP-14); hole positions from spec tables land 25 mm off (IN-2, IN-3).
- The 4B has not learned assemblies (GE-5, GE-6, AS-3, PR-5 fail live), design intent on features (CX-10) or suggestions (PR-7, CD-3 return none).
- Vision: `qwen3.5:4b` reads sketch dimensions correctly but its designs do not build (IN-4/5/6); the critic flags all wrong parts and 4 of 5 correct ones (VM-10); 40 % of drawing parameters recovered (GE-11).

These are the inputs to the next data round: assemblies, design intent, table-driven positions, multi-feature brackets, and vision-to-IR examples for the vision model.

## Not done

- VM-9, EX-4 (FCStd half), EX-5 (FreeCAD half): need PrusaSlicer or FreeCAD, which are not installed.
- EX-8: no marching-cubes or surface-nets dependency.
- CX-13 passed late in the session: the house-style adapter scores 60.3 vs 2.5 for its base (`parity-20261029-171950`).

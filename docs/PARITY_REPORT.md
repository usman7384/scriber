# Parity report

Generated from `docs/reference/PARITY_CHECKLIST.md` by `partwright-parity-report`; a row is done only with a passing
acceptance test and a recorded demo (D-030). Evidence paths are in each row's status.

**61 done, 31 in progress, 46 open, of 138 rows.**

| Area | done | in progress | open |
|---|---|---|---|
| Inputs | 6 | 6 | 5 |
| Context Manager / knowledge | 4 | 9 | 1 |
| Generation & output | 7 | 0 | 6 |
| Parameters & refinement | 6 | 2 | 2 |
| Verification & manufacturability | 4 | 2 | 4 |
| Assemblies | 2 | 1 | 1 |
| Export & interop | 4 | 3 | 1 |
| Workflow & platform | 10 | 3 | 2 |
| API & automation | 5 | 1 | 3 |
| Circular design / simulation hooks | 5 | 0 | 3 |
| Performance | 4 | 0 | 4 |
| Demo parts (eval cases) | 4 | 4 | 14 |

## In progress

| Row | Capability | Status |
|---|---|---|
| IN-2 | Text/spec file with exact specifications | in progress (M2): MD/CSV/XLSX specs give identical typed hole facts (`services/context` tests); full generation from `plate_spec.md` not run live |
| IN-3 | Spreadsheet (CSV/Excel) with exact connection points and sizes | in progress (M2): CSV and XLSX hole tables give identical facts with positions (`test_readers`); generation from a table not run live |
| IN-9 | Existing CAD (STEP) / past designs as reference | in progress (M2): STEP/STL describe + similar-part ranking (`test_import`, context retrieval); "20 % longer" edit not done |
| IN-12 | Requirements/specification documents (PDF, MD) | in progress (M2): live demo `m2demo`: requirements PDF facts (120x80x6, 4xM6, Ø20 ±0.1) became checks, 5/5 passed, params cite p1:l2/p1:l4 |
| IN-13 | Design rules and industry standards documents | in progress (M2): rules doc "hole-to-edge ≥ 2 x D" overrode the 1.5 default; violation caught on attempts 2-4 and repaired live |
| IN-15 | Reports and sizing calculations as context | in progress (M2): report values cited to page and line (context tests); not used in a live generation yet |
| CX-1 | Per-account/project engineering data repository; drag-drop multi-file upload with per-file progress | in progress (M3): API half, 6 file kinds in one upload all processed with progress (`parity-20261029-025007`); per-file UI not demoed |
| CX-2 | Context file table: Name, Type, Status, Used in, Uploaded, Action (delete), search, select | in progress (M3): file table, search, facts, delete in the UI (mock); graph removal on the server not demoed |
| CX-3 | Use selected files as context + description → Generate | in progress (M2): retrieved context is passed to generation and `used_in` recorded; choosing context ids by hand is M3 (API/UI) |
| CX-4 | Knowledge graph extracted from files, concepts and generated outputs | in progress (M2): knowledge graph built on ingest and extended on generation (28 → 63 relations in the live demo); KMM-28 ↔ M3 test |
| CX-6 | Knowledge-base level / score (files score, used in generation, level progress) | in progress (M3): API half, score and level follow the documented formula (`parity-20261029-025007`); UI not demoed |
| CX-7 | Generation checks itself against uploaded inputs (every input considered) | in progress (M2): every checkable spec fact becomes a requirement check (5/5 in demo); no coverage report for facts that are not checkable |
| CX-8 | Consistency with team conventions ("how you work", not only what) | in progress (M2): convention documents join every context pack and the prompt; not exercised in a live generation yet |
| CX-10 | Design intent captured and preserved | in progress (M2): parameters carry document provenance (ref + quote) through IR, design.json and params.json; features keep intent text only |
| CX-11 | Traceability requirement → feature → output | in progress (M2): `stale()` returns exactly the dependent model when REQ-1 changes (live demo) |
| PR-6 | Edit by selecting edges/faces | in progress (M5): top face maps to thickness, offset +2 gives 7.000 mm and no other change (`test_faces` on the real kernel; UI on the mock `parity-web-20261029-050842`); no live demo |
| PR-10 | Measurements (bounding box, distances) | in progress (M3): API half, bbox 120/80/5 matches the STEP (`parity-20261029-025007`); on-model labels not demoed |
| VM-2 | User picks manufacturing method; part altered automatically to pass | in progress (M2): process selects rules and violations drive repair (live); automatic geometric fixes (e.g. fillet to tool radius) not done |
| VM-4 | Rule violations shown as pop-up recommendations (e.g. hole-to-edge ≥ 1.5×D) | in progress (M3): finding marker 0.19 mm from the hole with suggestion, on real geometry output served by the mock API (`parity-web-20261029-021647`) |
| AS-1 | Segment selection & assembly tree | in progress (M5): API lists components (`test_assembly`); clicking parts in the viewer selects the same ids on the mock (`parity-web-20261029-050842`); no live run |
| EX-4 | Native parametric CAD export with feature tree (reference: Onshape write) | in progress (M4): IR bundle with feature tree and sketch constraints reopens (`parity-20261029-041904`); FreeCAD .FCStd blocked (not installed), FeatureScript export not built |
| EX-5 | Export to other CAD systems (CATIA, NX, SolidWorks, Creo; reference: read now, write in progress) | in progress (M5): docs/INTEROP.md export section; AP242 OCCT round trip drift 1.5e-16 (`parity-20261029-052939`); FreeCAD not installed |
| EX-6 | Share link (read-only view) | in progress (M3): API half, share link view 200 with GLB, write 401, revoked 404 (`parity-20261029-025007`); viewer page not demoed |
| WP-8 | Thumbnails for models and versions | in progress (M3): thumbnails change on edit in the UI (mock); server-side regeneration not demoed |
| WP-11 | Report a bug from the editor | in progress (M5): API stores model, version, text, user and screenshot byte-identical (`parity-20261029-052939`); web dialog posts the same shape on the mock (`parity-web-20261029-050842`); no end-to-end run |
| WP-14 | Beginner flow: idea → printable part without CAD experience | in progress (M5): prompt, Generate, Download STL in 3 UI steps on the mock (`parity-web-20261029-050842`); live generation and slicer check not run |
| AP-8 | Onshape integration: describe a change → native Onshape features | in progress (M5): a described change via refine, exported as 18 named native Onshape features with linked variables against a recorded API mock, 0 import or translation calls (`test_parity_m5_onshape`, scripted model); live run pending; mock written from public docs, not captured |
| DP-2 | Flanged adapter: Adapter Height 60.0 mm, Base Bolt Dia 8.5 mm, Base Bolt Spacing X 85.0 mm, Base Bolt Spacing Y 60.0 mm | in progress: live `partwright-ir:4b-s1` 1/4 checks, holes 5.5 instead of 8.5 (`parity-20261029-020105`); demo also checks the X 85 to 90 edit |
| DP-7 | Metal bracket with angled support and screw holes | in progress: live bracket valid with holes but no angled support or gusset (`parity-20261029-020105`) |
| DP-17 | Housing from model-ready context (Ø82 ±0.2 mm, 4×M6) | in progress (M2): analogous spec-driven plate (Ø20 ±0.1 bore, 4×M6) passes live; the Ø82 housing itself not run |
| DP-21 | L-bracket concept (Length 120, Width 40, Thickness 4, Fillet 2 mm, Al 6061; constraints min wall ≥ 2, hole Ø ≥ 3, max length < 200; "7/7 checks") | in progress: live 2/3 checks, holes 4.5 instead of 6 (`parity-20261029-020105`) |

## Open

| Row | Capability | Status |
|---|---|---|
| IN-4 | Hand-drawn sketch image | open |
| IN-5 | Photo/image of a part | open |
| IN-6 | Technical drawing (incl. legacy pre-CAD drawings) → parametric part | open |
| IN-16 | Multiple inputs combined in one request ("upload as many inputs as you need") | open |
| IN-17 | Attachments on edits (IMAGE/MESH/FILE in the edit panel) | open |
| CX-13 | Fine-tuning on company CAD/design habits (local) | open |
| GE-5 | Functional assemblies with mates | open |
| GE-6 | Whole-system assembly (drone: frame, control surfaces, mounts) | open |
| GE-8 | Exact generation from specs and requirements | open |
| GE-9 | Batch / variant generation (N variants from one prompt; hundreds/thousands of configurations) | open |
| GE-11 | Accurate dimensions from imperfect inputs ("up to 90 %" of a part from drawing/photo) | open |
| GE-13 | Generate mode / "Thinking level" selector | open |
| PR-5 | Targeted edit of a selected component/segment only | open |
| PR-7 | AI suggestions with Accept / Ignore, shown in 3D space | open |
| VM-7 | Automatic evals: every input reflected in output, no manual checking | open |
| VM-8 | Benchmark parts and test cases curated by CAD engineers | open |
| VM-9 | "Ready to manufacture" output (printable/machinable as exported) | open |
| VM-10 | Vision/visual critique of results (not claimed by reference; ours by design) | open |
| AS-3 | Place generated asset directly into an existing assembly | open |
| EX-8 | Implicit/field geometry → B-rep connection | open |
| WP-6 | Real-time generation progress | open |
| WP-15 | Runs locally / on-prem with small local models (laptop-class) | open |
| AP-2 | `generate` endpoint: prompt + optional image/mesh references | open |
| AP-3 | `modify` endpoint: natural-language change to an existing model | open |
| AP-7 | Batch processing | open |
| CD-1 | Requirement/calculation change → geometry updates automatically | open |
| CD-3 | Simulation results flow back into design | open |
| CD-5 | Manufacturing method change reshapes geometry | open |
| PF-1 | Concept → manufacturable model "in minutes" | open |
| PF-3 | Asset from drawing/photo, up to 90 % accurate, in < 1 min | open |
| PF-7 | "Seconds" claims (intro post, job ads) | open |
| PF-8 | Local small model on a standard laptop | open |
| DP-1 | Quad frame ("White Quad Frame" / "Rendered Quad Frame") | open |
| DP-3 | Round pipe flange with hub (export tile) | open |
| DP-4 | Glider / sailplane with refinement "Increase length to 450mm for higher fineness" | open |
| DP-6 | T-joint bracket for 2020 aluminium extrusion | open |
| DP-8 | Greenhouse Hose Connector: Barb Base Diameter 16.0, Barb Length 30.0, Bore Diameter 12.0, Fitting Diameter 26.4 mm (more params hidden) | open |
| DP-11 | Parametric Enclosure System: Lid Clearance 0.2 mm, Outer Height 50.0 mm, Outer Length 250.0 mm, Outer Width 100.0 mm; four M3 screws | open |
| DP-12 | Hobby servo motor asset from datasheet drawing + photo → Onshape | open |
| DP-13 | Fin-ray gripper finger, 3 versions with different rib counts | open |
| DP-14 | Bracket family (16 variants: L-angles, U-channels, T-plates, gussets, ring with tabs, pedestal mount, lug) | open |
| DP-15 | Flange family (16 variants: bolt-circle, weld-neck style, square-plate with spigot, rectangular frame, ring) | open |
| DP-16 | Drone assembly with frame, control surfaces, mounts; battery mount moved for CoG | open |
| DP-18 | Context-file parts: KMM-28 motor mount, KMP-30 motor plate, KSB-120 standard box, 10-hole plate 200×120, KFW-1200 fixed wing, aluminium profile types | open |
| DP-20 | Robot arms, enclosures, brackets, jigs (claimed range) | open |
| DP-22 | Air intake (timelapse video title) | open |

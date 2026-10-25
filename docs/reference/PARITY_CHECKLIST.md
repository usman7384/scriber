# Capability parity checklist (M0 Phase 0)

Built from `docs/reference/*` (sources in `SOURCES.md`, S#). One row per observable capability of the reference product. Every row starts **open**. A row closes only with a passing acceptance test and a recorded demo (see AGENTS.md).

Conventions:
- Evidence cites source IDs; quotes are short; "(inferred)" marks a capability deduced rather than shown; "(vision)" marks something the reference describes as future/aspirational; "(prior research, not re-confirmed)" marks a briefed item not found again in public sources.
- Modules: services/geometry, services/ir, services/agent, services/context, apps/api, apps/web, training, evals, docs.
- Tests are written against our product. "Gen(x)" = a generation request through `apps/api` with input x. Tolerances are absolute unless stated. All tests run offline with fixtures.

## Inputs

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| IN-1 | High-level natural-language prompt → part | S1 prompt card + FAQ; S3 `/generate` takes a text prompt; S40 "you describe what you need" | services/agent, apps/api | Gen("Hollow cylinder, 50mm height, 2mm wall thickness") → STEP with 1 valid solid; height 50 ±0.1 mm; (OD−ID)/2 = 2 ±0.05 mm | in progress (M1): live `qwen3.5:4b` passes m1-bracket and dp5 hollow cylinder (evals/results m1-20261025-210241) |
| IN-2 | Text/spec file with exact specifications | S1 tile "text file with exact specifications"; S13 specs of geometry and constraints | services/context, services/agent | Upload `plate_spec.md` (200×120×5 mm plate, 10 holes Ø6.6 at listed coords) + Gen → bbox 200×120×5 ±0.1; exactly 10 cylindrical through-holes; each centre within 0.05 mm of spec | open |
| IN-3 | Spreadsheet (CSV/Excel) with exact connection points and sizes | S21 "Excel sheet with the exact connection points and sizes"; S13 context file `plate_10holes_200x120_….csv` | services/context | Gen from `holes.xlsx` and `holes.csv` (same 10 rows x,y,Ø) → identical models; hole positions ±0.05 mm | open |
| IN-4 | Hand-drawn sketch image | S1 "share a sketch"; FAQ; S9 | services/agent | Gen(sketch PNG of L-bracket annotated 120/40/4 mm, 2 holes Ø6) → params length 120, width 40, thickness 4 within ±2 %, 2 holes | open |
| IN-5 | Photo/image of a part | S1 IMAGE button; S20 asset generation "only a picture"; S41 "show a picture" | services/agent | Gen(photo of a standard 9 g hobby servo + its datasheet dims) → bbox within 10 % of datasheet L×W×H; ≥5 named params | open |
| IN-6 | Technical drawing (incl. legacy pre-CAD drawings) → parametric part | S20 06:15 and 04:30; S21 reverse-engineering from drawings | services/agent | Gen(drawing PDF of a flange: OD 120, PCD 90, 6×Ø11, hub Ø60) → named params equal drawing values ±0.1 mm | open |
| IN-7 | Mesh (STL/OBJ) → parametric reconstruction with feature tree | S1 MESH button; S20 use case 3; S28 Mesh-To-CAD "in minutes" | services/geometry, services/agent | Fixture: our flange exported to STL. Gen(STL) → B-rep; Hausdorff ≤ 0.5 % of bbox diagonal; ≥3 sketch-based features; editing OD regenerates a valid solid | open |
| IN-8 | Mesh from topology optimisation / simulation / 3D scan → parametric | S17; S20 03:00, 07:30; S28 | services/geometry, evals | Fixture: TO-style organic bracket STL + scan STL with 0.1 mm Gaussian noise → valid B-rep, Hausdorff ≤ 1 % diag, mounting holes recovered as exact cylinders (fit error ≤ 0.05 mm) | open |
| IN-9 | Existing CAD (STEP) / past designs as reference | S17 "existing CAD"; S24 "past designs"; S14 upload of `.step` | services/context, services/geometry | Upload `bracket.step` + Gen("same bracket, 20 % longer") → output length = 1.2× source ±0.1 mm; other dims unchanged ±0.05 | open |
| IN-10 | Read native CAD (claimed: Onshape read/write; CATIA, NX, SolidWorks, Creo read) | S21; S23 | services/geometry, docs | Import STEP AP242 and an Onshape document fixture (mocked API) → named bodies and feature list preserved; docs record which proprietary formats are out of scope for OSS | open |
| IN-11 | Sizing-tool results (XML) → full parametric aircraft | S20 05:30 "takes this XML file as an input"; slide "Blended Wing Drone" | services/context, services/agent | Gen(`sizing.xml`: NACA 2412, span 1000, root chord 250, tip 120, sweep 20°, dihedral 5°, twist 2°) → span 1000 ±1 mm, chords ±0.5, sweep/dihedral ±0.2°, airfoil sections match NACA 2412 ±0.2 % chord | open |
| IN-12 | Requirements/specification documents (PDF, MD) | S13, S14, S24, S20 KG slide | services/context | Upload `requirements.pdf` ("mount 4×M6", "bore Ø82 ±0.2") + Gen → 4 holes clearance Ø6.4–6.6; bore Ø82 ±0.2; trace links REQ→feature present | open |
| IN-13 | Design rules and industry standards documents | S13 "design rules, or standards"; S13 file `screw-design-norm.md` | services/context, services/agent | Upload rule doc "hole-to-edge ≥ 1.5×D" + Gen(plate with Ø10 holes near edge) → all holes ≥ 15 mm from edges; rule ID cited in report | open |
| IN-14 | Mission/system definitions | S17, S20 02:00 "mission definition"; S11 "mission" | services/context, services/agent | Gen(mission.yaml: payload 500 g, endurance 20 min, span ≤ 1.2 m) → config + params each linked to a mission field; span ≤ 1200 mm | open |
| IN-15 | Reports and sizing calculations as context | S20 08:30 "reports, sizing tool results" | services/context | Upload `report.pdf` containing a computed wall thickness 3.2 mm → Gen enclosure uses 3.2 ±0.01 and cites the report | open |
| IN-16 | Multiple inputs combined in one request ("upload as many inputs as you need") | S1 FAQ; S3 prompt + image/mesh references | apps/api, services/agent | Gen(prompt + image + spec.md) → response metadata lists all 3 inputs with role "used"; removing spec changes at least one spec-driven param | open |
| IN-17 | Attachments on edits (IMAGE/MESH/FILE in the edit panel) | S13 editor panel | apps/web, apps/api | Modify request with an image attachment is accepted and the attachment ID appears in the version provenance | open |

## Context Manager / knowledge

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| CX-1 | Per-account/project engineering data repository; drag-drop multi-file upload with per-file progress | S13; S14 image 1 (Uploading (6), progress %); S40 | services/context, apps/web | Upload 6 files (PDF, STEP, MD, TXT, CSV, PNG) → list returns 6 with status "processed"; web e2e shows per-file progress events 0→100 | open |
| CX-2 | Context file table: Name, Type, Status, Used in, Uploaded, Action (delete), search, select | S13 screenshot 2; S14 image 1 | apps/web, services/context | Playwright: table shows the 6 files with all columns; search "motor" filters to matching names; delete removes file from list and from KG | open |
| CX-3 | Use selected files as context + description → Generate | S14 "Use Selected as context…"; S13 "[Coming Soon]" | services/context, apps/api | Gen with `context_ids=[a,b]` → generation record lists exactly a,b; each file's "Used in" shows the new generation | open |
| CX-4 | Knowledge graph extracted from files, concepts and generated outputs | S13 caption; S24; S20 08:30 | services/context | Upload 3 docs mentioning "KMM-28 motor mount", "4×M3" → KG has entity KMM-28 with relation to M3 fastener; after Gen, generated part node links to both | open |
| CX-5 | KG visualisation with relation/entity counters and fullscreen | S13; S14 ("0 relations / 0 entities", expand icon) | apps/web | Playwright: rendered node count == API entity count; counters match API; fullscreen toggle works | open |
| CX-6 | Knowledge-base level / score (files score, used in generation, level progress) | S14 "Knowledge Base Level 0", "394 Files score", "2 Used in generation"; S40 | services/context, apps/web | After N uploads and M generations, API returns score/used/level per documented formula; UI shows same numbers | open |
| CX-7 | Generation checks itself against uploaded inputs (every input considered) | S13 "checks against your input"; S20 10:30 | services/agent, evals | Spec with 10 numeric constraints → verification report lists 10/10 evaluated with pass/fail; any fail triggers repair or is surfaced | open |
| CX-8 | Consistency with team conventions ("how you work", not only what) | S24/S28 launch text; S40 "designs your way"; S13 | services/context, services/agent | Context `Box_Best_Practice.md` (wall 2.5 mm, M3 heat-set bosses) + Gen("small electronics box") → wall 2.5 ±0.01, 4 M3 bosses, without these being in the prompt | open |
| CX-9 | Structured "model-ready context" extraction (values, tolerances, standards) | S20 slide: "Ø82 ± 0.2 mm, AX-XXXX, 4 x M6" | services/context | Extraction on fixture docs returns typed items {name, value, unit, tol, source} incl. Ø82 ±0.2 mm and 4×M6 | open |
| CX-10 | Design intent captured and preserved | S13, S14, S17 "why the part looks that way", S21 | services/ir, services/context | Every IR feature carries intent + provenance (source doc/rule/prompt); survives save → load → export of our native format byte-identically | open |
| CX-11 | Traceability requirement → feature → output | S20 slide "traceable, actionable knowledge" | services/context, services/ir | Query "features derived from REQ-3" returns the feature IDs; changing REQ-3 marks them stale | open |
| CX-12 | Legacy data ingestion (archives of CAD, drawings, documents) | S21 "parse it, convert it, and fine-tune on it"; S17 | services/context | Batch ingest folder (50 STEP + 20 PDF fixtures) → ≥95 % parsed; per-file error report; no crash | open |
| CX-13 | Fine-tuning on company CAD/design habits (local) | S17, S20 09:30–10:30, S21 | training, evals | Fine-tune script on fixture corpus yields an adapter; conventions benchmark score improves ≥10 pts vs base on held-out set | open |
| CX-14 | Design libraries, supplier catalogs, material databases (vision) | S9 (stated as what an agent could do) | services/context | (vision) Material lookup "Aluminum 6061" attaches density/E to the part; mass computed ±1 % | open |

## Generation & output

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| GE-1 | Fully parametric, editable B-rep (not mesh/render) | S1 "fully functional, parametric CAD"; S24 "Not a mesh. Not a rendering."; S17 | services/geometry, services/ir | Output STEP contains only B-rep solids (no triangulated faces); BRepCheck valid; re-compiling the IR yields identical volume ±1e-6 | in progress (M1): only B-rep solids exported; STEP reload volume equal and validity in `test_build`; no explicit no-mesh-face assertion yet |
| GE-2 | Models as code / "compilability": a hidden script generates the model; error checks, feature extraction, metadata | S21 "we generate a script"; S28 "compilable, parametric geometry" | services/ir, services/geometry | Every generation persists IR + compiled build123d script; script re-runs deterministically; compile errors reported with feature ID; feature list extractable from IR | in progress (M1): IR `design.json` + compiled `model.py` persisted per version; compile deterministic; kernel errors name the failing feature |
| GE-3 | Constrained sketches | S17; S20 02:30 and slide "Constrained sketches" | services/geometry, services/ir | All sketches in generated IR solve with 0 remaining DOF; native export shows constraints per sketch | open |
| GE-4 | Designer-like feature tree (named, ordered features) | S17; S20 Onshape tree (root_airfoil, mid_airfoil, tip_airfoil, main_wing, winglet_assembly, full_aircraft); S28 "clean and organized feature tree" | services/ir, services/geometry | BWB fixture → feature list contains named sections/lofts in build order; no feature named "imported"; names are snake_case and unique | open |
| GE-5 | Functional assemblies with mates | S13 "functional assemblies"; S17 "assembly mates"; S24 "fully parametric assembly" | services/geometry, services/ir | Gen("enclosure with lid and 4 M3 screws") → ≥6 components; mates/joints defined for every component; pairwise interference volume 0 | open |
| GE-6 | Whole-system assembly (drone: frame, control surfaces, mounts) | S40 "every part is designed until you've got a whole drone" | services/agent, services/geometry | Gen(drone brief) → assembly with frame, 4 arms, 4 motor mounts, battery mount; mass and CoG reported | open |
| GE-7 | Reproducibility: same input, same output | S20 slide "Same Input same Output"; S20 10:30 | services/agent, evals | Same request ×5 with fixed seed → identical IR hash and volume | open: generation is seeded at temperature 0, reproducibility test not written |
| GE-8 | Exact generation from specs and requirements | S20 slide "Exact generation from Specs and Requirements" | services/agent, evals | Spec-driven eval set (≥30 parts): ≥95 % of specified dims within stated tolerance | open |
| GE-9 | Batch / variant generation (N variants from one prompt; hundreds/thousands of configurations) | S28/S30 "Generate 3 Versions of the Gripper with various number of Ribs"; S17 "thousands of early configurations"; S11 "100 detailed variations" | services/agent, apps/api | Batch("3 versions with 4, 6, 8 ribs") → 3 valid models whose rib counts are 4, 6, 8; 100-variant sweep completes with 100 valid solids | open |
| GE-10 | Generated model gets a descriptive title | S13 "Greenhouse Hose Connector"; S21 "Parametric Enclosure System", "Blended Wing Body Aircraft" | services/agent | Every generation returns a non-empty title ≤ 60 chars | in progress (M1): title is schema-required (≤ 60 chars) on every design |
| GE-11 | Accurate dimensions from imperfect inputs ("up to 90 %" of a part from drawing/photo) | S20 slide "up to 90% of the part with accurate dimensions" | evals | Drawing/photo eval set: ≥90 % of ground-truth params recovered within 2 % | open |
| GE-12 | Downstream metadata (named faces/regions, materials) for simulation | S21 "embed metadata that gets used downstream in simulation" | services/ir, services/geometry | Exported model has named face groups (e.g. `mount_face`, `load_face`) readable from STEP/our format; material attached | open |
| GE-13 | Generate mode / "Thinking level" selector | S40 frame "Generate mode: Thinking Level" | apps/web, services/agent | Request with level=low/high → agent logs differ in reasoning budget; both produce valid output on 5 fixtures | open |

## Parameters & refinement

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| PR-1 | Named, unit-bearing parameter panel (slider + numeric field + unit) | S1 (Adapter Height 60.0 MM, Base Bolt Dia 8.5 MM, Base Bolt Spacing X 85.0 MM, Base Bolt Spacing Y 60.0 MM); S13; S21 | services/ir, apps/web | API returns params [{name, value, unit, min, max, provenance}]; Playwright: panel shows one row per param with slider and numeric field, units displayed | in progress (M1): `params.json` has name, label, value, unit, min, max, provenance; panel is M3 |
| PR-2 | Edit parameter → regenerate (claimed < 1 s for simple parts) | S21 "in less than a second it's updated"; S13 "real time" | services/geometry, apps/api | Set Base Bolt Spacing X 85→90 → hole centres 90 ±0.01 apart; p50 regen latency < 1 s for ≤ 20-feature parts on reference hardware | open |
| PR-3 | "Apply instantly" toggle (live vs on commit) | S21 images | apps/web | Toggle off: slider drag does not regenerate until Enter; toggle on: regenerates on change (debounced) | open |
| PR-4 | Conversational refinement of the whole object | S1 "Increase length to 450mm for higher fineness"; S3 `/modify`; S13 "Target: Entire Object" | services/agent, apps/api | Modify("Increase length to 450 mm") on glider fixture → length param 450 ±0.01; other params unchanged | in progress (M1): `partwright refine` live: "make the plate 100 mm long and use 6.6 mm holes" → exactly 2 param updates; glider fixture not built |
| PR-5 | Targeted edit of a selected component/segment only | S2 "Segment selection & assemblies"; S3 `/edit`; S21 "isolate and change only one thing" | services/agent, services/ir | Edit(lid only, "add vent slots") on enclosure assembly → base component IR hash unchanged; lid gains slots | open |
| PR-6 | Edit by selecting edges/faces | S1 FAQ "selecting edges, faces, or parameters" | apps/web, services/geometry | Select top face of plate, set offset +2 mm → thickness +2 ±0.01; no other param changes | open |
| PR-7 | AI suggestions with Accept / Ignore, shown in 3D space | S1 suggestion bubble IGNORE/ACCEPT; S2 "AI suggestion"; S9 agent suggests alterations in 3D | services/agent, apps/web | Suggestion object {target, change, rationale}; Accept applies it (param changes); Ignore leaves IR hash unchanged | open |
| PR-8 | Change propagation through an assembly (move battery mount for CoG; one part change propagates) | S40 battery-mount example; S11 propagation vision | services/agent, services/geometry | On drone fixture: move battery mount −20 mm → CoG shifts as computed ±1 mm; mating holes in frame move with it; mates still valid | open |
| PR-9 | Version history / timeline with thumbnails and restore | S2 "History"; S21 Enclosure image ("Version 1 · 7d ago", "Restore this version", thumbnails) | apps/api, apps/web | 3 edits → history lists 4 versions with prompt and PNG thumbnail; restore v1 → params equal v1 | open |
| PR-10 | Measurements (bounding box, distances) | S2 "Measurements"; S21 Aircraft image (112.8 cm / 16.4 cm / 36.4 cm labels) | apps/web, services/geometry | Measure API returns bbox L/W/H ±0.01 mm; web overlay shows the three labels with units | open |

## Verification & manufacturability

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| VM-1 | DFM checks for 3-axis milling, FDM, SLA, SLS (sheet metal next) | S21; S23 | services/geometry | Fixture pocket with sharp internal corner → milling check FAIL (rule ID); FDM overhang 70° unsupported → FAIL; corrected fixtures PASS | open |
| VM-2 | User picks manufacturing method; part altered automatically to pass | S21 "the part is altered to meet the checks"; S17 manufacturing method changes reshape geometry | services/agent, services/geometry | Choose "3-axis milling" on pocket fixture → internal corners filleted ≥ tool radius 3 mm; re-check PASS; IR records the change | open |
| VM-3 | Static vs dynamic requirements | S21 | services/geometry | Rule set marks each rule static/dynamic; static violations block "ready" status, dynamic ones produce warnings only | open |
| VM-4 | Rule violations shown as pop-up recommendations (e.g. hole-to-edge ≥ 1.5×D) | S21 | services/geometry, apps/web | Plate with Ø10 hole 10 mm from edge → recommendation "move to ≥ 15 mm" via API and visible in UI next to the hole | open |
| VM-5 | Rules tunable per industry and per user/project | S21 | services/context, services/geometry | Project override hole-to-edge 1.5→2.0 → same fixture now flags at 18 mm; default project unaffected | open |
| VM-6 | Geometric validity: watertight, manifold, valid B-rep | S11 "watertight, manufacturable file" | services/geometry | Every generated part: BRepCheck valid, closed shell; exported STL watertight (0 boundary edges) | in progress (M1): BRepCheck validity + one-solid + volume checks every build; STL watertight in `test_exports_reload` |
| VM-7 | Automatic evals: every input reflected in output, no manual checking | S17; S20 10:30–11:00 | evals | CI eval run prints per-case constraint coverage; fails if any input constraint is unevaluated | open |
| VM-8 | Benchmark parts and test cases curated by CAD engineers | S31 CAD working-student role | evals | Benchmark repo with ≥ 30 hand-built parametric reference parts + specs; harness computes param accuracy and Hausdorff per case | open |
| VM-9 | "Ready to manufacture" output (printable/machinable as exported) | S1 tile; S38 workshop "prepare it for printing"; S40 | services/geometry, evals | Exported STL of 5 fixtures slices with PrusaSlicer CLI without errors; STEP opens in FreeCAD with 1 solid per part | open |
| VM-10 | Vision/visual critique of results (not claimed by reference; ours by design) | AGENTS.md (our pipeline), no reference evidence | services/agent | Rendered views of a deliberately wrong part (missing hole) are flagged by the critic on 4/5 fixtures | open |

## Assemblies

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| AS-1 | Segment selection & assembly tree | S2 card "Segment selection & assemblies"; S13 toolbar segment/assembly icons | apps/web, services/ir | Assembly API lists components with IDs; clicking a component in the viewer selects the same ID | open |
| AS-2 | Assembly mates exported (not just placed parts) | S17; S20 08:00 "you also have the mates" | services/geometry | Exported assembly (our format + STEP product structure) contains mate definitions; reloading restores positions ±1e-6 | open |
| AS-3 | Place generated asset directly into an existing assembly | S20 slide "Place in the assembly directly" | services/agent, services/geometry | Gen(servo) with target assembly + mate reference "servo_pocket" → servo mated, no interference | open |
| AS-4 | Assembly mass properties / CoG | (inferred) S40 CoG battery-mount example | services/geometry | Drone fixture with materials → mass and CoG match hand calculation ±1 % | open |

## Export & interop

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| EX-1 | Export STEP | S1, S3, S13, S14 | services/geometry, apps/api | Download(format=step) → AP214/AP242 file reloads in OCCT with same solid count and volume ±1e-6 | in progress (M1): STEP AP214 export + reload in tests |
| EX-2 | Export STL | S1, S3, S13 | services/geometry | Download(stl) → watertight mesh, chordal deviation ≤ 0.05 mm | in progress (M1): STL export, watertight in tests; chordal deviation not measured |
| EX-3 | Export GLB | S1, S3, S13 | services/geometry | Download(glb) → Khronos glTF validator 0 errors; per-component nodes named | in progress (M1): GLB export (magic bytes checked); Khronos validator not run yet |
| EX-4 | Native parametric CAD export with feature tree (reference: Onshape write) | S20 Onshape screenshots; S21 "read and write in Onshape"; S28 "not a STEP file being imported" | services/geometry, docs | Export to an open native format with history (FreeCAD .FCStd and our IR bundle) → reopened file shows named features + constraints; Onshape FeatureScript export tested against fixtures (no live account) | open |
| EX-5 | Export to other CAD systems (CATIA, NX, SolidWorks, Creo; reference: read now, write in progress) | S21 | docs | Docs page states supported paths (STEP AP242 + PMI) and gaps; STEP opens in FreeCAD round-trip test | open |
| EX-6 | Share link (read-only view) | S2 "Share"; S13 toolbar link icon; S20 "(shared)" title | apps/api, apps/web | Create share link → unauthenticated GET renders viewer read-only; revoke → 404 | open |
| EX-7 | Integration with CAX/PLM automatic workflows | S20 slide "Automatic workflows (CAX, PLM, etc.)"; S2 Enterprise "Advanced integrations" | apps/api | Webhook on new version posts {model_id, version, files} to a stub PLM; retries on 5xx | open |
| EX-8 | Implicit/field geometry → B-rep connection | S20 07:00 | services/geometry | (inferred) SDF fixture (gyroid-filled bracket) → B-rep approximation within 0.2 mm, valid solid | open |

## Workflow & platform

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| WP-1 | Web app with 3D viewer (three.js-class), view cube, orbit | S1 bundle (three.js); S13 view cube Top/Front/Right | apps/web | Playwright: GLB loads; clicking view-cube "Top" sets camera to top view (camera up/forward vectors asserted) | open |
| WP-2 | Prompt card with IMAGE / MESH / FILE attachments and GENERATE | S1 hero; S40 | apps/web | Playwright: attach one file of each kind, submit → one generation job with 3 attachments | open |
| WP-3 | Editor: Back, title, New Generation, floating edit panel with target chip | S13 | apps/web | Playwright: editor shows title from GE-10; target chip switches between "Entire object" and the selected component | open |
| WP-4 | Suggested prompt chips / example prompts | S1 ("Hollow cylinder…", "T-joint bracket for 2020 aluminum extrusion"); S40 (Stirrer Stand, Band Clamp, Pendant Mount, Blade, Pulley, Fastener) | apps/web | Clicking a chip fills the prompt box with its text | open |
| WP-5 | Dashboard: home, projects/files, context manager, settings, help, API page | S14 nav rail; S3 dashboard "API Docs" | apps/web | Playwright navigation: each nav item routes to its page; generations list per project | open |
| WP-6 | Real-time generation progress | S40 GENERATE progress bar; S34 (inferred) WebSocket/SSE; (prior research, not re-confirmed) | apps/api, apps/web | Gen emits ≥3 progress events over SSE/WebSocket ending at 100 %; UI bar reflects them | open |
| WP-7 | Async jobs with observability | S1 Sentry bundle; (prior research, not re-confirmed) | apps/api | Job API returns id → status queued/running/done/failed; failures recorded with trace ID in logs | open |
| WP-8 | Thumbnails for models and versions | S21 Enclosure image; S40 part gallery; (prior research) | services/geometry, apps/web | Each version has a PNG thumbnail ≥ 256 px, regenerated on edit | open |
| WP-9 | Generated-part gallery / library | S40 card gallery of parts | apps/web | Library page lists user's parts with thumbnail + title, sorted by date | open |
| WP-10 | Community tab: shared projects (fork requested by users) | S43 (team reply says it exists; unverified) | apps/web, apps/api | Publish part to community → visible to another local user; "fork" creates an editable copy with provenance | open |
| WP-11 | Report a bug from the editor | S13, S21 "Report a Bug" | apps/web, apps/api | Bug report stores {model_id, version, text, screenshot} | open |
| WP-12 | Usage plans/quotas (10 free generations; editor gating) | S2 | apps/api, docs | (business; optional) configurable per-user generation limit returns HTTP 429 after N; default unlimited | open |
| WP-13 | UI language selector (EN; DE inferred) | S1 "English" selector | apps/web | (inferred) i18n EN/DE strings for all UI labels; switcher persists | open |
| WP-14 | Beginner flow: idea → printable part without CAD experience | S1 FAQ; S38 workshop; S21 "design for non-designers" | apps/web, evals | Scripted e2e: prompt "motor holder for 28 mm motor, 2 M3 screws" → STL that passes VM-9 in ≤ 3 UI steps | open |
| WP-15 | Runs locally / on-prem with small local models (laptop-class) | S17, S20 09:30–10:30 ("can run on a MacBook"); S21 | services/agent, training, docs | Full stack runs with network disabled on reference laptop (see docs/HARDWARE.md); 10 eval prompts complete | open |

## API & automation

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| AP-1 | Per-user API tokens, header or Bearer auth, create/revoke in dashboard | S3 | apps/api, apps/web | Token works in `X-API-Token` and `Authorization: Bearer`; revoked token → 401 | open |
| AP-2 | `generate` endpoint: prompt + optional image/mesh references | S3 | apps/api | POST /generate {"prompt": "Design a metal bracket with angled support and screw holes"} → job id; result has ≥1 hole and a gusset/angled feature | open |
| AP-3 | `modify` endpoint: natural-language change to an existing model | S3 | apps/api | POST /modify {model_id, "make it 10 mm thicker"} → thickness +10 ±0.01 | open |
| AP-4 | `edit` endpoint: targeted parametric edit on a component | S3 | apps/api | POST /edit {model_id, component_id, params} → only that component's IR changes | open |
| AP-5 | `download` endpoint: GLB / STEP / STL | S3 | apps/api | POST /download {format} for each of glb, step, stl → files pass EX-1..EX-3 checks | open |
| AP-6 | Build custom apps on the API (phone holder; shadow box from tool STL; jigs/fixtures) | S41; S21 | apps/api, docs | Example script: tool STL → shadow-box insert with pocket offset 1.0 ±0.05 mm; documented in docs | open |
| AP-7 | Batch processing | S3 "batch processing" on request | apps/api | POST batch of 10 prompts → 10 jobs, all complete, results listable | open |
| AP-8 | Onshape integration: describe a change → native Onshape features | S28/S30; S20 | services/geometry, apps/api | Against a recorded Onshape API mock: request creates a part studio with named features; no import-of-STEP call is made | open |
| AP-9 | Pipeline from external tool output (sizing XML) with no manual input | S20 slide "no manual input required" | apps/api, services/context | CLI `pipe sizing.xml | api` produces model passing IN-11 with zero UI interaction | open |

## Circular design / simulation hooks

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| CD-1 | Requirement/calculation change → geometry updates automatically | S17; S20 01:30 | services/context, services/agent | Edit spec value (span 1000→1100) in context → regeneration auto-triggered; new span 1100 ±1; old version retained | open |
| CD-2 | Change report: what changed and why | S20 01:30 ("not only a report…" implies reports exist) | services/agent | Diff report lists changed params/features with old/new values and triggering source | open |
| CD-3 | Simulation results flow back into design | S17; S20 slide feedback arrows; S11 vision | services/agent, apps/api | Mock FEA result JSON (max stress 1.4× allowable on `mount_face`) → agent proposes thickness increase; accepting reduces mock stress below limit | open |
| CD-4 | Topology-optimisation STL fed back as parametric | S17; S20 03:00 | services/geometry | Same as IN-8 with a TO fixture; result replaces original part in assembly keeping mates | open |
| CD-5 | Manufacturing method change reshapes geometry | S17; S20 slide "DfM Checks, Geometry editing" | services/agent | Switch method FDM→3-axis milling on bracket → VM-2 edits applied; diff report produced | open |
| CD-6 | Connect to sizing and analysis tools so design updates when physics does | S11 (vision); S28 conceptual-design post | services/context, apps/api | Adapter interface for "sizing tool" with one reference adapter (XML); re-run on changed XML updates the model (as CD-1) | open |
| CD-7 | Differentiable workflow | S20 slide "Differentiable workflow" | services/ir | (inferred) API returns finite-difference sensitivities d(metric)/d(param) for mass and bbox on fixtures | open |
| CD-8 | Single format through requirements → design → simulation → manufacturing | S11 (vision); S21 own formats | services/ir, docs | IR round-trip: IR → model → export → re-import IR with no loss of params/intent | open |

## Performance

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| PF-1 | Concept → manufacturable model "in minutes" | S1; S13; S14 | evals | Median end-to-end time on eval set ≤ 5 min on reference hardware (docs/HARDWARE.md) | open |
| PF-2 | Each blended-wing part generated in < 5 min | S20 slide | evals | BWB fixture: every part < 5 min | open |
| PF-3 | Asset from drawing/photo, up to 90 % accurate, in < 1 min | S20 slide | evals | IN-5/IN-6 fixtures complete < 60 s each | open |
| PF-4 | Parameter edit update < 1 s | S21 | evals | PR-2 latency check | open |
| PF-5 | Mesh → parametric CAD in minutes | S28 | evals | IN-7 fixture < 5 min | open |
| PF-6 | Variant exploration in minutes instead of weeks (hundreds/thousands of variants) | S21; S28; S20 | evals | 1,000 parameter variants of the BWB recompile (no LLM) in ≤ 10 min | open |
| PF-7 | "Seconds" claims (intro post, job ads) | S7, S31 | evals, docs | Record measured p50 for single-part prompts; docs state honestly whether "seconds" is met | open |
| PF-8 | Local small model on a standard laptop | S20 10:00 | training, evals | Model fits in 16 GB RAM, ≥ 10 tok/s on reference laptop | open |

## Demo parts (eval cases)

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| DP-1 | Quad frame ("White Quad Frame" / "Rendered Quad Frame") | S1 hero: X-config quad, centre plate, 4 arms, motor pads; no dims shown | evals | Gen("5-inch X quad frame, 4 mm carbon plate, 16×16 M2 FC mount, M3 motor mounts 16/19 mm") → 4 symmetric arms, holes per spec ±0.05 | open |
| DP-2 | Flanged adapter: Adapter Height 60.0 mm, Base Bolt Dia 8.5 mm, Base Bolt Spacing X 85.0 mm, Base Bolt Spacing Y 60.0 mm | S1 "Build on your own terms" | evals | Gen with these 4 params → height 60, 4 holes Ø8.5 on 85×60 rectangle ±0.05; edit X→90 regenerates | open: 0/4 (4B) and 1/4 (7B) checks; holes not cut on the flange |
| DP-3 | Round pipe flange with hub (export tile) | S1 "Ready to manufacture" (no dims) | evals | Gen("DN50 PN16 flange") → EN 1092-1 dims (OD 165, PCD 125, 4×Ø18) ±0.1 | open |
| DP-4 | Glider / sailplane with refinement "Increase length to 450mm for higher fineness" | S1 | evals | Gen glider then Modify("increase length to 450 mm") → fuselage length 450 ±0.5; fineness ratio increases | open |
| DP-5 | Hollow cylinder 50 mm height, 2 mm wall | S1 example prompt | evals | As IN-1 | in progress (M1): 3/3 checks on both models |
| DP-6 | T-joint bracket for 2020 aluminium extrusion | S1 example prompt | evals | Holes Ø5.5 for M5 at 20 mm pitch matching 2020 slot centres ±0.05; plate fits 20 mm profile faces | open |
| DP-7 | Metal bracket with angled support and screw holes | S3 API example | evals | As AP-2 | in progress (M1): 1/1 checks on 4B; 7B gave up |
| DP-8 | Greenhouse Hose Connector: Barb Base Diameter 16.0, Barb Length 30.0, Bore Diameter 12.0, Fitting Diameter 26.4 mm (more params hidden) | S13, S14 | evals | Gen with these params → barb OD 16, barb length 30, bore Ø12 through, fitting Ø26.4 ±0.05; hex collar present | open |
| DP-9 | Blended Wing Body Aircraft: Dihedral 5.0°, Root Chord 250.0 mm, Sweep 20.0°, Tip Chord 120.0 mm, Wing Span 1000.0 mm; viewer bbox labels 112.8 / 16.4 / 36.4 cm; Onshape tree root/mid/tip airfoil, main_wing, winglet_tip_airfoil, winglet_assembly, full_aircraft | S21 Aircraft image; S20 slides; S42 printing video | evals | Gen from params → span 1000 ±1 (bbox span reported separately incl. winglets), feature names include root/mid/tip airfoil sketches and winglet assembly | open |
| DP-10 | BWB from sizing-tool XML (NACA profile, span, root/tip chord, twist, tail span, tail NACA, control surfaces, sweep; plus stability margin, CoG, MTOM, inner volume, battery energy/power density, motor power, prop diameter/pitch, blades) | S20 slide | evals | As IN-11; additionally inner-volume requirement met (enclosed volume ≥ spec) | open |
| DP-11 | Parametric Enclosure System: Lid Clearance 0.2 mm, Outer Height 50.0 mm, Outer Length 250.0 mm, Outer Width 100.0 mm; four M3 screws | S21 Enclosure image | evals | Assembly box + lid + 4 M3 screws; outer 250×100×50 ±0.1; lid clearance 0.2 ±0.02; screws mated in bosses | open |
| DP-12 | Hobby servo motor asset from datasheet drawing + photo → Onshape | S20 slide | evals | As IN-5; mounting-tab hole spacing per datasheet ±0.1 | open |
| DP-13 | Fin-ray gripper finger, 3 versions with different rib counts | S30 | evals | As GE-9 | open |
| DP-14 | Bracket family (16 variants: L-angles, U-channels, T-plates, gussets, ring with tabs, pedestal mount, lug) | S21 Brackets image (no dims) | evals | 16 prompts, one per variant type → each valid, recognisable by feature checks (e.g. gusset count, hole count) | open |
| DP-15 | Flange family (16 variants: bolt-circle, weld-neck style, square-plate with spigot, rectangular frame, ring) | S21 Flange image (no dims) | evals | 16 prompts with standard sizes → bolt-circle dims ±0.1 | open |
| DP-16 | Drone assembly with frame, control surfaces, mounts; battery mount moved for CoG | S40 | evals | As GE-6 and PR-8 | open |
| DP-17 | Housing from model-ready context (Ø82 ±0.2 mm, 4×M6) | S20 KG slide | evals | As IN-12 | open |
| DP-18 | Context-file parts: KMM-28 motor mount, KMP-30 motor plate, KSB-120 standard box, 10-hole plate 200×120, KFW-1200 fixed wing, aluminium profile types | S13 file names (content not visible) | evals | (inferred) Write our own spec docs for each name; Gen per spec meets all listed dims | open |
| DP-19 | Lamp; personalised phone holder (API app) | S41 | evals | Phone holder app: phone width 75 mm input → cradle inner width 75 +0.5 clearance ±0.05 | open |
| DP-20 | Robot arms, enclosures, brackets, jigs (claimed range) | S40; S13 file `designing-robot-arms.md` | evals | One fixture each: 2-link arm with servo pockets, PCB enclosure (100×60 board, M3), jig for DP-2 part | open |
| DP-21 | L-bracket concept (Length 120, Width 40, Thickness 4, Fillet 2 mm, Al 6061; constraints min wall ≥ 2, hole Ø ≥ 3, max length < 200; "7/7 checks") | S8 concept art (not a product screenshot) | evals | Gen with these params/constraints → all constraints pass, report shows N/N checks | open: 2/3 checks; holes in the upright leg not cut |
| DP-22 | Air intake (timelapse video title) | S42 metadata only | evals | (inferred) Gen("NACA flush air intake for 40 mm duct") → valid solid; duct Ø40 ±0.1 | open |

## Row counts
Inputs 17 · Context 14 · Generation 13 · Parameters 10 · Verification 10 · Assemblies 4 · Export 8 · Workflow 15 · API 9 · Circular 8 · Performance 8 · Demo parts 22 · **Total 138**.

## Gaps & unknowns
- **Claimed but not shown publicly**: DFM checks/auto-fix (only described in S21); CATIA/NX/SolidWorks/Creo read; Community tab (S43 reply only); "differentiable workflow" meaning; simulation feedback loop (diagram only); local small model (statement only, no release); any accuracy/benchmark numbers; speed claims ("seconds", "< 5 min", "< 1 min", "< 1 s") without measurement method.
- **API**: only four endpoint names and a one-field example are public; schemas, async model, webhooks, limits unknown. Not probed by rule.
- **Inaccessible sources**: Dealroom (bot check), Caplight (sign-up), X timelines and X article (login), LinkedIn profiles (login), Industrial AI Network event/company pages (did not render), MakerSpace listing (empty render), TikTok/Instagram/Discord (not fetched), docs.kyrall.com (no DNS). Funding amounts and investors unknown.
- **Partly seen**: parameter panels are cropped (hose connector, enclosure, BWB show only 4–5 rows); Context Manager accepted file types hint not fully legible; talk Q&A (if any) not in the recording segment.
- **Stack**: React/TS + FastAPI + WebSocket/SSE comes from an unverified third-party repo (S34); the full-stack job post is gone. three.js and Sentry are confirmed from the site bundle.
- **Not found at all**: Vimeo videos, podcasts, other recorded talks, public GitHub/SDK, OpenAPI spec, German-language press beyond deutsche-startups.de.

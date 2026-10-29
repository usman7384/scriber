# Known issues

- Disk: ~14 GB free on each drive. Large caches (HF 55 GB, uv ~9 GB) on C: are the user's to clear.
- Reference API schemas are not public beyond endpoint names; `/api/v1` aliases follow names only.
- M1 eval: 4/10 cases fully correct on `qwen3.5:4b`. Holes on faces other than the base plane, standard flange sizes and square hole patterns are the main failures (`docs/agents/m1.md`).
- A single generation takes 1–3 minutes on the RTX 3060 Laptop (15–30 tok/s); the reference claims seconds to minutes.
- GitHub CI has not run: the repo has no remote. All CI steps pass locally.
- Rules apply to every matching feature; there is no scope such as "fastener holes only" (D-016).
- The hole-to-edge suggestion offers "or reduce Ø", which the model used to dodge the rule; the spec requirement caught it, but the suggestion should not offer it when a hole size is required.
- A grounded generation took 6 attempts and 113 s in the M2 demo; the 4B needs many repairs for multi-feature layouts.
- DFM checks are approximations (sampled wall thickness, build/tool direction fixed at +Z); see `docs/agents/geometry.md`.
- PDF text extraction keeps the cp1252 Ø as an unknown character in some fact texts; values are unaffected.
- IR v2: face references need a flat face perpendicular to an axis; sloped faces need a datum. Selector regions are matched geometrically with the feature's tool body, which can be ambiguous where coplanar faces merge.
- IR v2: patterns replay extrude, revolve and hole tools only; mirror is about base planes through the origin.
- Counterbore seats above M12 and countersinks above M20 are derived from head-diameter rules, not tabulated values.
- The API process started before IR v2 keeps the v1 compiler until it is restarted.

- The prompted qwen3.5:4b is very sensitive to prompt bytes: with greedy decoding, reordering the worked examples or adding one sentence to the project block flips individual grounded cases both ways (A/B on g01, g02, g06, 2026-10-26). Single-run eval differences of one or two cases are within that noise; it also adds unrequested chamfers and fillets copied from the examples, which sometimes fail in the kernel.
- Gate runs repeat almost exactly within a session: the prompted 4B scored the same on M1 and grounded in three back-to-back runs, and the tuned 4B differed in one grounded round (2026-10-27). But first answers changed between 2026-10-26 and 2026-10-27 with the same Ollama 0.40.11, model and first-attempt prompt (dp7, g02, g04), probably through server state such as prompt-cache reuse. Repeating a gate therefore does not sample variance, and a one- or two-case difference between days cannot be credited to a code change.
- The default model `partwright-ir:4b-s2` is not published: a fresh clone has to build it (`docs/agents/training.md`, about 8 h on the laptop) or pass `--model qwen3.5:4b`. Its GGUF has no vision projector, so image requests go to `llm.vision` (D-027, D-032).
- S2 leaves more project-rule errors in grounded final designs than S1 (4 vs 0 on the grounded set, 2026-10-29).
- A clockwise IR `polygon` extrudes toward −Z: build123d takes the face normal from the winding, so `extrude` goes the other way (checked 2026-10-29: a CW square with distance 5 spans z −5…0). The mesh reconstructor emits counter-clockwise polygons; the compiler does not normalise winding.
- Mesh reconstruction (`reconstruct_mesh`) handles only Z-stacked prismatic meshes and rebuilds fillets and chamfers as sharp edges; see `docs/agents/parity-m4-mesh.md`.
- API users are token names and projects are not user-scoped: any valid token reads and edits every project. The community space and the generation limit are per user, nothing else is.
- `examples/shadow_box.py` takes the tool outline from the mid-height section of the STL, so tools whose outline changes with height get a pocket that fits only that section.
- EX-5's other-CAD check is FreeCAD 1.1.4, which shares OCCT with us; no proprietary system has opened our STEP. FreeCAD heals what it reads: the cross-drilled shaft collar (b05) comes back with a volume 5e-6 lower, so VM-9 allows 1e-4.
- FreeCAD `.FCStd` export maps extrudes and simple/tapped holes only; sketches on faces other than the start or end of a blind extrude are placed as numbers and do not follow edits (`docs/INTEROP.md`).
- Live parity runs on `partwright-ir:4b-s2` (2026-10-29): 64 % of specified benchmark dimensions within tolerance (GE-8 needs 95 %); spec-table hole positions 25 mm off (IN-2, IN-3); no assemblies, design intent or suggestions from the model (GE-5, GE-6, AS-3, PR-5, CX-10, PR-7, CD-3). Details in `docs/agents/integration-2026-10-29.md`.
- Vision through `qwen3.5:4b`: dimensions are read from sketches, but the designs do not build (IN-4/5/6); the visual critic also rejects 4 of 5 correct parts (VM-10), so it stays out of the generate loop (D-032).
- Six M6 showcase references (sc04, sc07, sc10, sc11, sc13, sc20) fail the default 1.5 x D hole-edge rule because their prompts place the holes that close; the references follow the prompts (`docs/agents/geometry-s3-fixes.md`).

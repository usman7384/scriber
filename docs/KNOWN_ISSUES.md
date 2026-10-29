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
- The default model `partwright-ir:4b-s1` is not published: a fresh clone has to build it (`docs/agents/training.md`, about 9 h on the laptop) or pass `--model qwen3.5:4b`. Its GGUF has no vision projector, so it cannot take images (D-027).
- A clockwise IR `polygon` extrudes toward −Z: build123d takes the face normal from the winding, so `extrude` goes the other way (checked 2026-10-29: a CW square with distance 5 spans z −5…0). The mesh reconstructor emits counter-clockwise polygons; the compiler does not normalise winding.
- Mesh reconstruction (`reconstruct_mesh`) handles only Z-stacked prismatic meshes and rebuilds fillets and chamfers as sharp edges; see `docs/agents/parity-m4-mesh.md`.
- GE-3: derived sketch constraints leave 1 DOF on one recorded polygon ("Stepped shaft", `turning_section`, re-solve error 0.04 mm); 893 of 895 recorded sketches are fully constrained. The GE-3 offline test is a strict xfail until the derivation handles it.

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


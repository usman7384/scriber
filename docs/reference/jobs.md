# Job postings and stack signals (S31–S34)

Source: Ashby public job board https://jobs.ashbyhq.com/kyrall (read via Ashby's public posting API), cross-checked on Indeed (S32). 3 open postings on 2026-10-25. Common intro: "AI-powered design agent" turning ideas into ready-to-manufacture 3D models "in seconds"; Munich; backed by European VCs.

| Posting | Published | Signals |
|---|---|---|
| ML Engineer – 3D Geometry for CAD (full-time, Munich) | 2026-07-16 | Models that understand, manipulate and **generate CAD parts**; problems in 3D representations, geometric relationships, **manufacturability**. Build/optimise models for 3D shape understanding/generation; **data pipelines converting CAD formats into ML representations**; geometric deep learning training; production deployment and performance. Must: PyTorch or TensorFlow; 3D representations **B-reps, point clouds, meshes, voxels, implicit surfaces**; Python. Nice: CAD libraries, computational geometry, MLOps. Mission line: "first truly functional hardware design agent" |
| Working Student – Data Engineering (20 h/wk) | 2026-09-23 | Data team "owns the data our models learn from": **source 3D parametric data, write parsers for CAD formats**, maintain the pipeline, deliver datasets. Python; B-reps/meshes/point clouds |
| Working Student – CAD design (20 h/wk) | 2026-10-13 | Build clean fully parametric CAD of real parts; **review AI-generated models for design intent, manufacturability, correctness**; **create benchmark parts and test cases to evaluate the design agent**; feedback to AI/data teams. Tools: SolidWorks, Onshape, CATIA, Siemens NX, Fusion; DFM (machining, sheet metal, 3D printing); nice: technical drawings, **GD&T**, Python/CAD scripting |

## Roadmap signals (inferred)
- Own geometry models trained on parametric CAD data (inferred from ML + data roles; consistent with S20/S21 statements about small local models).
- Eval/benchmark suite curated by CAD engineers (explicit in CAD working-student role).
- Drawings and GD&T awareness (nice-to-have) suggests drawing input/output or tolerance handling is on the roadmap (inferred, weak).
- Implicit-surface experience requested: matches the talk's point about connecting implicit design to B-rep (inferred).

## Web/backend stack signals
- First-party: homepage bundle preloads three.js, lottie, Sentry, lucide/tabler icons (S1). Supports: browser 3D viewer on three.js; error monitoring with Sentry.
- A search snippet (S32) referenced a **"Full-Stack Engineer (Frontend + Backend)"** posting on Indeed; it is no longer listed and its text could not be read.
- **S34 (inferred, attribution unverified)**: public repo `havenousername/fullstack-kyrall` (2026-04-16) titled "Fullstack Developer Test" for mid/senior developers: **Python FastAPI** backend, **React + TypeScript** frontend with **TanStack Router** and **Vite**, real-time updates via **WebSocket and Server-Sent Events**, assets typed **"glb" or "gltf"** with auto-updating values and last-modified timestamps, filtering/sorting table. Only the repo name links it to Kyrall; treat as a likely take-home test reflecting their stack.
- Prior research (not re-confirmed from a first-party posting): async generation jobs with observability, GLB viewer with thumbnails, real-time progress. Partly corroborated: GENERATE progress bar (S40), version thumbnails (S21 Enclosure image), Sentry (S1), GLB format (S3).

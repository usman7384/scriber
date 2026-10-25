# Blog (S6–S13)

Blog: https://kyrall.ghost.io/ (Ghost). 7 posts as of 2026-10-25, listed via the RSS feed. Theses summarised in our own words.

| # | Date | Title | URL | Author |
|---|---|---|---|---|
| S7 | 2025-07-03 | Introducing Kyrall | https://kyrall.ghost.io/introducing-kyrall/ | Kyrall |
| S8 | 2025-08-26 | Avoiding the Horseless Carriage | https://kyrall.ghost.io/avoiding-the-horseless-carriage/ | Kyrall |
| S9 | 2025-09-26 | Beyond the Chatbox: Rethinking Interfaces for AI First Products | https://kyrall.ghost.io/beyond-the-chatbox-rethinking-interfaces-for-ai-first-products/ | Kyrall |
| S10 | 2025-10-31 | From Whale Oil to Coal and Non-linear Thinking | https://kyrall.ghost.io/from-whale-oil-to-coal-and-non-linear-thinking/ | Kyrall |
| S11 | 2026-03-09 | You Don't Need Full Control in 3D Design. You Need the Right Result | https://kyrall.ghost.io/you-dont-need-full-control-in-3d-design-you-need-the-right-result/ | Kyrall |
| S12 | 2026-04-24 | The Strawman Critique of "Text-to-CAD" | https://kyrall.ghost.io/the-strawman-critique-of-text-to-cad/ | Kyrall |
| S13 | 2026-07-06 | Today, we're officially launching Kyrall | https://kyrall.ghost.io/today-were-officially-launching-kyrall/ | Yasin Öztürk |

## S7 Introducing Kyrall (2025-07-03)
- Thesis: software that automates turning ideas into manufacturable functional parts with real-world constraints.
- Capabilities mentioned: concept to production-ready models "in seconds"; no CAD experience needed; target domains hardware, robotics, industrial systems. Company says it is funded and hiring.
- Images: logo only.

## S8 Avoiding the Horseless Carriage (2025-08-26)
- Thesis: AI-first design tools should not mimic existing CAD UIs; reduce clutter, be accessible, experiment carefully.
- Features: none concrete.
- Images: (1) an antique three-wheeled motor carriage; (2) a UI concept illustration, file named as an AI image-generator output, so treat it as **concept art, not a product screenshot**. It shows a dark window: left "Parameters" list (Length 120 mm, Width 40 mm, Thickness 4 mm, Fillet Radius 2 mm, material button "Aluminum 6061"), a "Constraints" list with green checks (min wall ≥ 2 mm, hole Ø ≥ 3 mm, max length < 200 mm), a Generate button; right, an L-bracket with two holes and dimension callouts 120 mm, 40 mm, 4 mm; status bar "Generated model v12 · 0,4 s · Valid: 7/7 checks". Useful as a design-intent signal (parameters + constraints + check count + versioning), not as evidence of shipped features.

## S9 Beyond the Chatbox (2025-09-26)
- Thesis: chat is the wrong default interface; outputs should be rich, interactive, generated interfaces; for CAD the main output is a directly manipulable 3D model.
- Features/capabilities mentioned: multimodal inputs (text, sketches, documents, images); output into an interactive 3D workspace; the agent suggests alterations directly in 3D space; vision of suggestions from prior work and design libraries, integration of supplier catalogs, material databases and online repositories (stated as what an agent "could" do, i.e. roadmap/vision).
- Images: stock photo only.

## S10 From Whale Oil to Coal (2025-10-31)
- Thesis: technology shifts are non-linear; simplifying design (like Canva/Lovable) can create a much larger market; Jevons paradox.
- Features: none.

## S11 You Don't Need Full Control (2026-03-09)
- Thesis: control over the outcome matters more than control over every input; requirements can be transmitted to the system without a human setting 200 parameters; tractor-vs-hand-plough analogy.
- Capabilities/roadmap mentioned: system handles ~95% of design (meets requirements, respects constraints, watertight manufacturable file), then **export to STEP or native CAD formats** so the engineer does the last 5%; human in the loop for review. Vision list: 100 detailed assembly variations in minutes, parametrically consistent and manufacturing-ready; modifying one part propagates through the whole assembly respecting downstream constraints; 3D modeling connected directly to sizing and analysis tools so the design updates when the physics does; one unified format from requirements through design, simulation, manufacturing.
- Inputs named: requirements, boundary conditions, specifications, initial conditions from sizing tools and analysis; the "mission" (load, envelope, environment).
- Images: stock photo only.

## S12 The Strawman Critique of "Text-to-CAD" (2026-04-24)
- Thesis: critics attack an unrealistic version (one prompt → jet engine). The real shift is manual geometry creation → automated design pipelines where engineers define constraints, requirements and design rules, and the system generates/refines geometry.
- Capabilities implied: integrating constraints, parameters, interfaces and requirements from across the design process into an automated pipeline; engineer adjusts the system, not surfaces. Acknowledges STL/STEP do not preserve design intent.
- Images: stock photo only.

## S13 Launch post (2026-07-06, Yasin Öztürk)
- Thesis: CAD is manual and fragmented; Kyrall turns engineering data (specs, requirements, sizing results) into parametric manufacturable models in minutes.
- Features named: generate **functional assemblies** from your engineering knowledge; capture design intent and best practices; adjust dimensions and refine parts in real time; export GLB, STL, STEP; **Context Manager** (headline feature): engineering data repository that grounds output in your files; upload specs (geometry and constraints), design rules or standards; generates from them, checks against input, stays consistent with team practice; updated UI; API; faster generation tuned over months.
- Screenshot 1, caption "Kyrall Editor" (also used by S14): dark editor. Top bar: BACK, part title "Greenhouse Hose Connector", user avatar menu, NEW GENERATION button. Top-centre floating "Editor" panel with a chip "Target: Entire Object", a prompt box (placeholder: prompt to edit the model), attachment buttons IMAGE, MESH, FILE and an EDIT button. Top-right view cube (Top/Front/Right faces). Left vertical toolbar of icons: parameters (active), a segment/explode icon, an assembly/components icon, a ruler (measurements), a link (share), a cube-with-arrow (export), a lightbulb (AI suggestions; mapping inferred from the pricing feature list). Bottom-left history/document icon. Bottom-right "Report a Bug". Parameters panel (scrollable, slider + numeric field + unit per row): Barb Base Di… 16.0 MM, Barb Length 30.0 MM, Bore Diameter 12.0 MM, Fitting Diame… 26.4 MM (more rows hidden below). The model: white hose-barb connector (barbed tube, hex collar, larger cylindrical fitting).
- Screenshot 2, caption "Context Manager & Knowledge Graph": left table "Context Files (13)" with columns checkbox, Name, Status (green check), Type, Uploaded, Actions (trash), search box. Visible files: KYR-RF-001_item_Aluminium_Profile_Types.md, KYR-DN-005_KFW-1200_FixedWing_Geometric_Requirements….md, KYR-DN-004_KMM-28_Motor_Mount.md, Fixed_Wing_Aircraft.txt, Aircraft.txt, plate_10holes_200x120_kyr_7f3a2c.csv, kmp-30-motor-plate.md, ksb-120-standard-box.md, screw-design-norm.md, designing-robot-arms.md, Box_Best_Practice.md (types MD, TXT, CSV; dated Jul 3–4 2026). Bottom: input "[Coming Soon] Use Selected as context" and GENERATE. Right: "Knowledge Graph" panel, a dense node-link graph centred on a Kyrall node, fullscreen icon, caption saying links were extracted between uploaded files, concepts and generated outputs.

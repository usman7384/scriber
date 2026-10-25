# Interviews (S21)

## Xometry Pro: "Clicking in CAD by Itself Is Not Engineering" – Kyrall (2026-06-16)
URL: https://xometry.pro/en/articles/ai-interviews-kyrall/ . Interviewee Osama Atwi (co-founder); interviewer Andreas Velling (Xometry). Paraphrased in our words.

Contains the "text-to-CAD is a bad name" remark: the label suggests typing "design me a jet engine" and getting one. Senior mechanical-engineer testers prompted that way and were disappointed; the company now admits it set expectations badly.

### Problem framing
- Manual labour inside design, simulation and manufacturing, and disconnect between them.
- STEP/STL lose design intent (the decisions and sequence behind a part); native parametric files keep the steps but not all intent. Simulation results are hard to feed back; manufacturing information is missing, so designs get reworked.
- Origin story: hard-coded drone-frame configurators that only worked for one configuration.

### Product capabilities stated
- **"Compilability" of 3D models / models as code**: instead of generating points, they generate a **script that generates the model**. The script can be checked for errors, features extracted, metadata embedded for downstream simulation and other tools. The user never sees the code; it is edited and updated in the background.
- Own infrastructure and formats, but integrates with existing tools: **reads and writes Onshape; reads CATIA, NX, SolidWorks and Creo**; writing to those is in progress, launch date undetermined.
- Input styles: technical drawings or sketches; plain text description; a precise description such as an **Excel sheet with exact connection points and sizes**; reverse-engineering a part parametrically from drawings.
- Editing: keep editing through text; **highlight one part of an assembly and edit only that** (isolation so other parts do not change); change a number directly, e.g. make an L-bracket longer, press enter, updated in **under a second**.
- **DFM**: embedding DFM tests, first **3-axis milling, FDM, SLA, SLS**, then sheet metal and others. User picks a manufacturing method; the part is **altered to meet the checks**. Requirements split into **static** (must hold for the method at all, e.g. no sharp internal pocket corners in milling) and **dynamic** (subjective/cost, e.g. a radius that would need a new tool head). Checks are **rule-based**; pipeline integration is AI-based. Violations show a **pop-up recommendation**; example rule: minimum hole-to-edge distance about **1.5× hole diameter**. Rules can be **tuned by industry and by user**.
- Go-to-market: forward-deployed projects; they study customer processes before proposing.
- Use cases with images:
  1. Conceptual design in aviation: drone configuration exploration in minutes instead of weeks; develop once, change any parameter. Image "Parametric blended wing body aircraft design" (see demo parts).
  2. Asset generation: servo motor, connector, bracket for assemblies; a simple servo would take ~1.5 h by hand. Images "Custom bracket asset generation" (grid of 16 white brackets: L-angles with hole patterns, U-channels, T-plates, gusseted angle brackets, triple-rib gusset, perforated strip with standoff, ring with radial tabs, pedestal pipe mount with round top plate, lug/eye bracket) and "Custom flange asset generation" (grid of 16 white flanges: bolt-circle flanges with raised hubs, weld-neck style, square-plate flanges with spigot, rectangular frame flange, ring flanges).
  3. Design for non-designers: PCB enclosure, motor holder for quick 3D printing. Image "Custom enclosure generation".
- Users: from non-technical people to juniors and seniors.
- **Data privacy**: training own **small language models that run locally on customer machines**, no large GPU infrastructure; data never leaves. Once local, **fine-tune on the customer's legacy design archive**; they can parse, convert and fine-tune on legacy data.
- Pricing: licence/subscription tiers; separate enterprise offering for fine-tuning, local hosting, customisation; hobbyist-level pricing for pure generation.
- **API** besides the browser editor; example apps: STL of a tool → shadow box around it; jigs and fixtures from a part.
- Peers he recommends following: Bench AI (post-simulation model prep), nTop (design exploration), Synera (agentic workflows/integrations).

### Images in the interview (described)
- "Aircraft.png" (older editor UI, light-blue accents): header with back arrow, Kyrall logo, title "Blended Wing Body Aircraft", an "AI" toggle, user avatar, "Generate new" button. Left "Parameters" panel with an **"Apply instantly" toggle**; rows with slider + value: Dihedral Angle 5.0°, Root Chord 250.0 mm, Sweep Angle 20.0°, Tip Chord 120.0 mm, Wing Span 1000.0 mm (list scrolls). Centre: white blended-wing planform with **measurement overlay** labels 112.8 cm, 16.4 cm, 36.4 cm (bounding-box style). Right vertical toolbar: AI (suggestions), assembly/components, ruler, link, export. Bottom centre: history icon. Bottom right "Report a Bug". View cube with Front/Bottom.
- "Enclosure.png" (same older UI): title "Parametric Enclosure System"; Parameters (Apply instantly on): …, Lid Clearance 0.2 mm, Outer Height 50.0 mm, Outer Length 250.0 mm, Outer Width 100.0 mm (more rows above/below). Model: open rectangular box with corner screw bosses. A **history popover**: "Generate", prompt excerpt mentioning a standard warehouse part and four M3 screws, "Version 1 · 7d ago", a thumbnail of a closed box, button **"Restore this version"**. Bottom bar: history icon + two **version thumbnails** (timeline).
- "PH_Pic.png": the four homepage feature tiles (same as website).
- "Brackets_dataset.png", "Flange_dataset.png": described above.

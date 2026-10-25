# DFM checks on B-rep and open standard-part data

Researched 2026-10-25. **Verified** means it was prototyped today with build123d 0.13.0 / OCP 8.0.1 on Windows. The test was a 40×30×10 mm plate with a Ø6 hole 2 mm from an edge. The run took 0.08 s and reported hole radius 3.0, ligament 2.0 mm, ray-cast minimum thickness 2.0 mm, and the downward face correctly flagged.

## Checks computable from the B-rep with OCCT

| Check | Method (OCP classes) | Status | Notes and thresholds (defaults, overridable by rules) |
|---|---|---|---|
| **Hole-to-edge distance** | Classify faces with `BRepAdaptor_Surface.GetType()==GeomAbs_Cylinder` and concave orientation (hole), then `BRepExtrema_DistShapeShape(hole_face, boundary_face).Value()` against outer planar/side faces. Same for hole-to-hole | **verified** (2.000 mm) | CNC ≥ 1×D (soft); sheet metal ≥ 2×t; FDM ≥ 2 perimeters (0.8 mm) |
| **Min wall thickness** | Sample points per face on a UV grid (`BRepTools.UVBounds_s`, `BRepAdaptor_Surface.D1`, keep only in-face points with `BRepClass_FaceClassifier`). Cast a ray along the inward normal with `BRepIntCurveSurface_Inter`; the nearest hit gives the local thickness. Report the min and a heat-map on the mesh | **verified** (face centres) | FDM 0.8–1.2 mm; SLS PA12 0.8 mm; CNC Al 0.8 mm; injection 1–3 mm. Rays are cheap; ~10–50 samples per face is enough |
| **Min gap / slot width** | The same ray cast along the **outward** normal to the opposing face | method (not prototyped) | ≥ tool Ø for CNC; ≥ 0.5 mm FDM |
| **Draft angle** | For each face sample normal *n* and pull direction *d*: `draft = 90° − acos(|n·d|)`. Faces with `draft < min` that are not ⟂ *d* are flagged. v1 uses a single pull direction and parting plane | **verified** (0.0° on vertical walls) | injection ≥ 1° (textured ≥ 3°); casting ≥ 2° |
| **FDM overhang** | Tessellate (`BRepMesh_IncrementalMesh`, 0.1 mm deflection). Triangles with `n_z < −cos(45°)`, excluding the bed plane (z = zmin), give the overhang area. Face-level shortcut via `face.normal_at()` | **verified** (face-level) | 45° default; bridges ≤ 10 mm are allowed (needs an edge-span test) |
| **Sharp internal corners (milling)** | Concave edges: build123d 0.12+ exposes `Convexity` on edges, or use `BRepOffset_Analyse`. Flag concave **linear edges parallel to the tool axis** (no fillet, so unmachinable), and concave cylindrical faces with radius < min tool radius | method; `Convexity` API exists (0.12 release notes), not yet exercised | min internal radius ≥ ⅓ pocket depth or ≥ tool R (e.g. 1.5 mm for a Ø3 end mill) |
| **3-axis accessibility / undercuts** | Ray from each face sample along +tool axis; a hit on the part means inaccessible from that setup. Repeat for ±X/±Y/±Z setups | method | report the minimum number of setups |
| **Min feature size** | Smallest edge length (`GCPnts_AbscissaPoint.Length_s`), tiny faces (`area < ε`), thin ribs (thickness check), small holes (Ø < min) | method | FDM: feature ≥ 2× nozzle (0.8 mm); CNC: hole Ø ≥ 1 mm |
| **Hole depth : diameter** | Cylinder face height vs radius; blind vs through via ray | method | drilling ≤ 10:1 (warn > 4:1); taps ≤ 3×D thread depth |
| **Validity** | `BRepCheck_Analyzer` (`shape.is_valid`), closed shells, `ShapeFix_Shape` attempt, volume > 0, single solid per part | **verified** (`is_valid`) | hard gate before export |
| **Interference (assemblies)** | `BRepAlgoAPI_Common` volume between parts > ε; clearance via `BRepExtrema_DistShapeShape` | method | hard error unless a press-fit joint is declared |

Implementation notes:

- Run checks in the CAD worker subprocess after compile. Return a `DFMReport` with `{rule_id, metric, value, limit, severity, entity_refs (face/edge tags), location xyz}` so the UI can highlight faces in the GLB. Export GLB with per-face names, or keep a face-index map.
- The metric names are exactly the `DesignRule.metric` enum (see `doc-parsing.md`), so extracted rules plug in directly.
- Process profiles (`cnc_3axis`, `fdm`, `sls`, `sheet_metal`, `injection`) are YAML defaults that project rules override.

## Open data for standard hardware

| Source | Licence | Coverage | Verdict |
|---|---|---|---|
| **[bd_warehouse](https://github.com/gumyr/bd_warehouse) 0.4.0** (PyPI `bd_warehouse`) | **Apache-2.0** | **Verified contents:** socket head cap screws `iso4762` and `asme_b18.3`; hex nuts `iso4032`/`iso4033`/`iso4035`; button, cheese, countersunk, pan, set and shoulder screws, hex head; washers; heat-set nuts; `clearance_hole_sizes.csv`, `tap_hole_sizes.csv`, `drill_sizes.csv`, `nominal_screw_lengths.csv`; DIN 471/472 retaining rings; bearings (deep-groove, capped, angular-contact, cylindrical-roller, tapered-roller); O-rings with static/dynamic glands; threads (ISO, Whitworth, BSPP, ACME, metric trapezoidal, ASTM D2911/PCO1881 bottle); NPS pipes and flanges; gears; sprockets; shaft keys (ISO/DIN keyways); OpenBuilds parts (V-slot extrusions). `SocketHeadCapScrew('M6-1', 20, 'iso4762')` produced a valid solid | **Use as the standard-part library and lookup tables.** It is the same kernel as build123d |
| FreeCAD Fasteners Workbench | **GPL-2.0** (verified) | very broad ISO/DIN/ASME/GOST fasteners | Do not vendor its code or tables. Users can use it inside FreeCAD |
| BOLTS | LGPL-2.1+ / GPL-3.0 (library); data licence unclear | nuts, bolts, bearings, profiles | Avoid |
| ISO 273 (clearance holes fine/medium/coarse), ISO 2768-1 (general tolerances), ISO 286 (IT grades/fits), ISO 261/262 (metric threads) | The standards are copyrighted documents; the numeric values are facts | small tables | **Author our own CSVs** from public secondary sources, citing the standard number and not copying text. Check that bd_warehouse's clearance table matches ISO 273 (not verified) |
| Aluminium extrusions (Misumi HFS, Bosch Rexroth, item, 80/20) | Vendor CAD downloads are under vendor terms | slot profiles 20/30/40/45 mm | Ship parametric V-slot/T-slot profiles (OpenBuilds via bd_warehouse, plus our own generic 2020/3030/4040 model from public dimensions). Users import vendor STEP themselves |
| Bearing catalogues (SKF, NSK) | Catalogue terms; boundary dimensions per ISO 15 are standard facts | 6000/6200/6300 series etc. | Covered by bd_warehouse; extend with ISO 15 sizes |
| McMaster-Carr, TraceParts, 3DContentCentral | Terms prohibit scraping and redistribution | — | Never scrape. At most offer a "user imports a STEP" path |

Licence check for our Apache-2.0 project: bd_warehouse (Apache-2.0) is compatible. Our own fact tables should be released as CC0 or Apache-2.0 data and cite the standard.

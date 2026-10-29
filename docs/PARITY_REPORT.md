# Parity report

Generated from `docs/reference/PARITY_CHECKLIST.md` by `partwright-parity-report`; a row is done only with a passing
acceptance test and a recorded demo (D-030). Evidence paths are in each row's status.

**91 done, 46 in progress, 1 open, of 138 rows.**

| Area | done | in progress | open |
|---|---|---|---|
| Inputs | 9 | 8 | 0 |
| Context Manager / knowledge | 10 | 4 | 0 |
| Generation & output | 8 | 5 | 0 |
| Parameters & refinement | 8 | 2 | 0 |
| Verification & manufacturability | 9 | 1 | 0 |
| Assemblies | 3 | 1 | 0 |
| Export & interop | 7 | 0 | 1 |
| Workflow & platform | 12 | 3 | 0 |
| API & automation | 6 | 3 | 0 |
| Circular design / simulation hooks | 5 | 3 | 0 |
| Performance | 7 | 1 | 0 |
| Demo parts (eval cases) | 7 | 15 | 0 |

## In progress

| Row | Capability | Status |
|---|---|---|
| IN-2 | Text/spec file with exact specifications | in progress: live run on `partwright-ir:4b-s2` fails: size=200.000 x 120.000 x 5.000, holes=10, through_holes=10, max_centre_error_mm=25.0 (`parity-20261029-112255`) |
| IN-3 | Spreadsheet (CSV/Excel) with exact connection points and sizes | in progress: live run on `partwright-ir:4b-s2` fails: csv_size=200.000 x 120.000 x 5.000, csv_holes=10, csv_through_holes=10, csv_max_centre_error_mm=25.0, xlsx_size=200.000 x 120.000 x 5.000, xlsx_holes=10, xlsx_through_holes=10, xlsx_max_centre_error_mm=25.0, identical=True (`parity-20261029-112255`) |
| IN-4 | Hand-drawn sketch image | in progress: live run on `partwright-ir:4b-s2` fails: no valid part in 6 attempts; qwen3.5:4b (vision) reads the dimensions from the image, e.g. 120/40/4 on the IN-4 sketch, but its designs fail to build (`parity-20261029-112255`) |
| IN-5 | Photo/image of a part | in progress: live run on `partwright-ir:4b-s2` fails: no valid part in 6 attempts; qwen3.5:4b (vision) reads the dimensions from the image, e.g. 120/40/4 on the IN-4 sketch, but its designs fail to build (`parity-20261029-112255`) |
| IN-6 | Technical drawing (incl. legacy pre-CAD drawings) → parametric part | in progress: live run on `partwright-ir:4b-s2` fails: no valid part in 6 attempts; qwen3.5:4b (vision) reads the dimensions from the image, e.g. 120/40/4 on the IN-4 sketch, but its designs fail to build (`parity-20261029-112255`) |
| IN-9 | Existing CAD (STEP) / past designs as reference | in progress: live run on `partwright-ir:4b-s2` fails: source=5.000 x 40.000 x 80.000, output=40.000 x 70.000 x 120.000, length_ratio=1.5 (`parity-20261029-112255`) |
| IN-13 | Design rules and industry standards documents | in progress: live run on `partwright-ir:4b-s2` fails: built=False; no design was built (`parity-20261029-112255`) |
| IN-16 | Multiple inputs combined in one request ("upload as many inputs as you need") | in progress: live run on `partwright-ir:4b-s2` fails: inputs=prompt=used, sketch.png=used, plate_spec.md=used, spec_driven=plate_length, plate_thickness, plate_width, with_spec=ok, without_spec=ok (`parity-20261029-112255`) |
| CX-4 | Knowledge graph extracted from files, concepts and generated outputs | in progress: live run on `partwright-ir:4b-s2` fails: kmm28_related_to_m3=True, part_mentions_kmm28=True, part_mentions_m3=False, relations=47 (`parity-20261029-112255`) |
| CX-7 | Generation checks itself against uploaded inputs (every input considered) | in progress: live run on `partwright-ir:4b-s2` fails: constraints=10, evaluated=0, passed=0, repairs=5 (`parity-20261029-112255`) |
| CX-8 | Consistency with team conventions ("how you work", not only what) | in progress: live run on `partwright-ir:4b-s2` fails: built=False; no design was built (`parity-20261029-112255`) |
| CX-10 | Design intent captured and preserved | in progress: live run on `partwright-ir:4b-s2` fails: features=3, with_intent=0, feature_sources=prompt, params_citing_documents=5, byte_identical=True (`parity-20261029-112255`) |
| GE-5 | Functional assemblies with mates | in progress: live run on `partwright-ir:4b-s2` fails: built=False (`parity-20261029-112255`) |
| GE-6 | Whole-system assembly (drone: frame, control surfaces, mounts) | in progress: live run on `partwright-ir:4b-s2` fails: built=False (`parity-20261029-112255`) |
| GE-8 | Exact generation from specs and requirements | in progress: live run on `partwright-ir:4b-s2` fails: parts=30, dims_within_tolerance=98/152, share=0.6447; dims of parts that failed to build count as missed (`parity-20261029-132754`) |
| GE-11 | Accurate dimensions from imperfect inputs ("up to 90 %" of a part from drawing/photo) | in progress: live run on `partwright-ir:4b-s2` fails: plate_a=0/6, plate_b=4/6, plate_c=0/6, plate_d=5/6, flange_a=0/6, flange_b=5/6, flange_c=0/6, flange_d=5/6, recovered=19/48, share=0.3958 (`parity-20261029-132754`) |
| GE-13 | Generate mode / "Thinking level" selector | in progress: live run on `partwright-ir:4b-s2` fails: low_valid=3, high_valid=3, low_log=low with a 0 token reasoning budget / low with a 0 token reasoning budget, re-sampled because it repeated an earlier answer, high_log=high with a 8192 token reasoning budget / high with a 8192 token reasoning budget, re-sampl (`parity-20261029-132754`) |
| PR-5 | Targeted edit of a selected component/segment only | in progress: live run on `partwright-ir:4b-s2` fails: base_hash_before=13289bd4a3dca3a2, base_hash_after=07cab0d0c0ef1667, other_components_changed=base, lid_volume_removed_mm3=-4763.683, valid=True (`parity-20261029-112255`) |
| PR-7 | AI suggestions with Accept / Ignore, shown in 3D space | in progress: live run on `partwright-ir:4b-s2` fails: suggestions=0 (`parity-20261029-112255`) |
| VM-10 | Vision/visual critique of results (not claimed by reference; ours by design) | in progress: live run on `partwright-ir:4b-s2` fails: wrong_flagged=5/5, right_flagged=4/5; control: the correct parts must pass too, or a critic that rejects everything would meet the row (`parity-20261029-112255`) |
| AS-3 | Place generated asset directly into an existing assembly | in progress: live run on `partwright-ir:4b-s2` fails: built=False (`parity-20261029-112255`) |
| WP-6 | Real-time generation progress | in progress: live run on `partwright-ir:4b-s2` fails: step_events=14, progress=10, 40, 60, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 100, final=failed; API half; the bar is the web suite's (`parity-20261029-112255`) |
| WP-14 | Beginner flow: idea → printable part without CAD experience | in progress (M5): prompt, Generate, Download STL in 3 UI steps live with a slicer-clean STL, but only for "mounting plate 60 x 40 x 4 mm with two M3 holes 48 mm apart"; the checklist prompt "motor holder for 28 mm motor, 2 M3 screws" fails on partwright-ir:4b-s2 after 6 attempts (`parity-web-live-20261029-200716`) |
| WP-15 | Runs locally / on-prem with small local models (laptop-class) | in progress: live run on `partwright-ir:4b-s2` fails: prompts=10, completed=9, errors=b17-cup: gave up after 6 attempts, model_host=127.0.0.1; outbound sockets and name lookups to anything but loopback raise inside the run (`parity-20261029-132754`) |
| AP-2 | `generate` endpoint: prompt + optional image/mesh references | in progress: live run on `partwright-ir:4b-s2` fails: job_id=j7ae561da70d5, holes=2, angled_facet_mm2=1.4, angled_features=part.profile, title=Angle bracket (`parity-20261029-112255`) |
| AP-3 | `modify` endpoint: natural-language change to an existing model | in progress: live run on `partwright-ir:4b-s2` fails: before=5.0, after=10.0, job=done; seeded 5 mm plate; the change is the model's (`parity-20261029-112255`) |
| AP-7 | Batch processing | in progress: live run on `partwright-ir:4b-s2` fails: jobs=10, done=8, listed=10, failed=gave up after 6 attempts, gave up after 6 attempts (`parity-20261029-132754`) |
| CD-1 | Requirement/calculation change → geometry updates automatically | in progress: live run on `partwright-ir:4b-s2` fails: auto_job=params, job=failed, v1_span=650.0, versions=2, origin=context, trigger=beam_spec.md changed: beam_span 1000 -> 1100 mm; params job = cited parameter rebuilt without the model; refine job = the model was asked (`parity-20261029-112255`) |
| CD-3 | Simulation results flow back into design | in progress: live run on `partwright-ir:4b-s2` fails: allowable_mpa=138, safety_factor=2.0, ratio_before=1.4, load_n=193.2, proposal=[], thickness_after=4.0, stress_after_mpa=193.2; mock FEA: sigma = 6 F L / (w t^2) at mount_face, F fixed from the fixture result (`parity-20261029-112255`) |
| CD-5 | Manufacturing method change reshapes geometry | in progress: live run on `partwright-ir:4b-s2` fails: fdm_passes=True, milling_before=False, milling_after=False, corner_radii=0.000 x 0.000 x 0.000 x 0.000, diff_params=1, same_size=True (`parity-20261029-112255`) |
| PF-3 | Asset from drawing/photo, up to 90 % accurate, in < 1 min | in progress: live run on `partwright-ir:4b-s2` fails: IN-5_seconds=215.5, IN-5_built=False, IN-5_passed=False, IN-6_seconds=246.8, IN-6_built=False, IN-6_passed=False; time to a built model; accuracy is gated by IN-5 and IN-6 (`parity-20261029-112255`) |
| DP-1 | Quad frame ("White Quad Frame" / "Rendered Quad Frame") | in progress: live run on `partwright-ir:4b-s2` fails: checks=2/6, valid=True, failed=FC square 16: hole centre distances [128.0, 181.02]; sixteen M3 motor holes: 4 matching holes; all hole diameters [2.4, 2.4, 2.4, 2.4, 3.4, 3.4, 3.4, 3.4]; motor holes 16 apart: hole centre distances [32.0, 45.25]; motor holes 19 (`parity-20261029-112255`) |
| DP-2 | Flanged adapter: Adapter Height 60.0 mm, Base Bolt Dia 8.5 mm, Base Bolt Spacing X 85.0 mm, Base Bolt Spacing Y 60.0 mm | in progress: live run on `partwright-ir:4b-s2` fails: checks=1/4, valid=True, failed=4 bolt holes 8.5: 0 matching holes; all hole diameters [54.0]; spacing X 85: hole centre distances []; spacing Y 60: hole centre distances [] (`parity-20261029-112255`) |
| DP-4 | Glider / sailplane with refinement "Increase length to 450mm for higher fineness" | in progress: live run on `partwright-ir:4b-s2` fails: checks=0/2, valid=False, seconds=89.1 (`parity-20261029-112255`) |
| DP-6 | T-joint bracket for 2020 aluminium extrusion | in progress: live run on `partwright-ir:4b-s2` fails: checks=0/3, valid=False, seconds=136.8 (`parity-20261029-112255`) |
| DP-7 | Metal bracket with angled support and screw holes | in progress: live run on `partwright-ir:4b-s2` builds a valid bracket with holes but no angled support or gusset (`parity-20261029-112255`) |
| DP-8 | Greenhouse Hose Connector: Barb Base Diameter 16.0, Barb Length 30.0, Bore Diameter 12.0, Fitting Diameter 26.4 mm (more params hidden) | in progress: live run on `partwright-ir:4b-s2` fails: checks=0/1, valid=True, failed=bore 12: 0 holes; diameters [16.0], seconds=115.5 (`parity-20261029-112255`) |
| DP-12 | Hobby servo motor asset from datasheet drawing + photo → Onshape | in progress: live run on `partwright-ir:4b-s2` fails: no valid part in 6 attempts; qwen3.5:4b (vision) reads the dimensions from the image, e.g. 120/40/4 on the IN-4 sketch, but its designs fail to build; IN-5 plus tab holes 27.8 ±0.1 (`parity-20261029-112255`) |
| DP-13 | Fin-ray gripper finger, 3 versions with different rib counts | in progress: live run on `partwright-ir:4b-s2` fails: checks=2/2, valid=False, seconds=148.7 (`parity-20261029-112255`) |
| DP-14 | Bracket family (16 variants: L-angles, U-channels, T-plates, gussets, ring with tabs, pedestal mount, lug) | in progress: live run on `partwright-ir:4b-s2` fails: cases=16, passed=4, failed=dp14-long-angle, dp14-t-plate, dp14-single-gusset, dp14-double-gusset, dp14-ring-tabs, dp14-pedestal, dp14-z-bracket, dp14-corner-plate, dp14-clevis, dp14-shelf-bracket, dp14-pipe-saddle, dp14-hat-bracket; per-case checks in cases.json (`parity-20261029-132754`) |
| DP-15 | Flange family (16 variants: bolt-circle, weld-neck style, square-plate with spigot, rectangular frame, ring) | in progress: live run on `partwright-ir:4b-s2` fails: cases=16, passed=13, failed=dp15-weld-neck-dn50, dp15-weld-neck-dn80, dp15-iec-ff165; per-case checks in cases.json (`parity-20261029-132754`) |
| DP-16 | Drone assembly with frame, control surfaces, mounts; battery mount moved for CoG | in progress: live run on `partwright-ir:4b-s2` fails: GE-6_built=False, PR-8_cog_shift_x=-3.862, PR-8_predicted_shift_x=-3.862, PR-8_shift_error_mm=2.6645766811729078e-15, PR-8_frame_hole_moves_x=-20, -20, -20, -20, PR-8_holes_aligned=True; GE-6 (generated drone) and PR-8 (battery mount moved for CoG) (`parity-20261029-112255`) |
| DP-18 | Context-file parts: KMM-28 motor mount, KMP-30 motor plate, KSB-120 standard box, 10-hole plate 200×120, KFW-1200 fixed wing, aluminium profile types | in progress: live run on `partwright-ir:4b-s2` fails: cases=6, passed=5, failed=dp18-kmp-30; per-case checks in cases.json (`parity-20261029-112255`) |
| DP-20 | Robot arms, enclosures, brackets, jigs (claimed range) | in progress: live run on `partwright-ir:4b-s2` fails: cases=3, passed=1, failed=dp20-two-link-arm, dp20-pcb-enclosure; per-case checks in cases.json (`parity-20261029-112255`) |
| DP-21 | L-bracket concept (Length 120, Width 40, Thickness 4, Fillet 2 mm, Al 6061; constraints min wall ≥ 2, hole Ø ≥ 3, max length < 200; "7/7 checks") | in progress: live run on `partwright-ir:4b-s2` fails: checks=0/3, valid=False (`parity-20261029-112255`) |
| DP-22 | Air intake (timelapse video title) | in progress: live run on `partwright-ir:4b-s2` fails: checks=0/1, valid=True, failed=duct 40: 0 holes; diameters [38.0], seconds=16.5 (`parity-20261029-112255`) |

## Open

| Row | Capability | Status |
|---|---|---|
| EX-8 | Implicit/field geometry → B-rep connection | open |

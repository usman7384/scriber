Model: `scriber-ir:4b-s2`

| row | result | measured | note |
|---|---|---|---|
| DP-2 | FAIL | checks=1/4, valid=True, failed=4 bolt holes 8.5: 0 matching holes; all hole diameters [54.0]; spacing X 85: hole centre distances []; spacing Y 60: hole centre distances [] |  |
| DP-7 | FAIL | checks=1/1, valid=True, failed=, angled= |  |
| DP-21 | FAIL | checks=0/3, valid=False, failed= |  |
| DP-3 | pass | checks=3/3, valid=True, failed=, seconds=41.0 |  |
| DP-6 | FAIL | checks=0/3, valid=False, failed=, seconds=136.8 |  |
| DP-8 | FAIL | checks=0/1, valid=True, failed=bore 12: 0 holes; diameters [16.0], seconds=115.5 |  |
| DP-22 | FAIL | checks=0/1, valid=True, failed=duct 40: 0 holes; diameters [38.0], seconds=16.5 |  |
| DP-1 | FAIL | checks=2/6, valid=True, failed=FC square 16: hole centre distances [128.0, 181.02]; sixteen M3 motor holes: 4 matching holes; all hole diameters [2.4, 2.4, 2.4, 2.4, 3.4, 3.4, 3.4, 3.4]; motor holes 16 apart: hole centre distances [32.0, 45.25]; motor holes 19 apart: hole centre distances [32.0, 45.25], seconds=118.7, motor_pads=4, holes_per_pad=1, 1, 1, 1, arm_reach_spread=0.0 |  |
| DP-4 | FAIL | checks=0/2, valid=False, failed=, seconds=89.1 |  |
| DP-19 | pass | phone_width=75.0, source=phone width 75 mm, inner_width=75.5, expected=75.5, job=done | cut across the cradle at mid-depth, mid-lip height |
| IN-2 | FAIL | size=200.000 x 120.000 x 5.000, holes=10, through_holes=10, max_centre_error_mm=25.0 |  |
| IN-3 | FAIL | csv_size=200.000 x 120.000 x 5.000, csv_holes=10, csv_through_holes=10, csv_max_centre_error_mm=25.0, xlsx_size=200.000 x 120.000 x 5.000, xlsx_holes=10, xlsx_through_holes=10, xlsx_max_centre_error_mm=25.0, identical=True |  |
| IN-9 | FAIL | source=5.000 x 40.000 x 80.000, output=40.000 x 70.000 x 120.000, length_ratio=1.5 |  |
| IN-12 | pass | m6_clearance_holes=4, bores=1, valid=True, req_1_features=part/part/corner_holes, req_2_features=part/part/bore |  |
| IN-13 | FAIL | built=False | no design was built |
| IN-15 | pass | side_walls=3.200 x 3.200 x 3.200 x 3.200, params_citing_report=wall_t |  |
| DP-17 | pass | m6_clearance_holes=4, bores=1, valid=True, req_1_features=part/part/corner_holes, req_2_features=part/part/bore |  |
| CX-4 | FAIL | kmm28_related_to_m3=True, part_mentions_kmm28=True, part_mentions_m3=False, relations=47 |  |
| CX-7 | FAIL | constraints=10, evaluated=0, passed=0, repairs=5 |  |
| CX-8 | FAIL | built=False | no design was built |
| CX-10 | FAIL | features=3, with_intent=0, feature_sources=prompt, params_citing_documents=5, byte_identical=True |  |
| CX-11 | pass | req_3_features=plate/part/corner_holes, plate/part/plate, changed=req_3_plate_size_x, stale=plate |  |
| VM-2 | pass | milling_before=False, milling_after=True, corner_radii=3.000 x 3.000 x 3.000 x 3.000, diff_features=p.inside_corner, p.body_s, p.pocket, diff_params=7, same_size=True |  |
| VM-7 | pass | mounting-plate=0/10 evaluated, unevaluated: req_1_plate_size_x, req_1_plate_size_y, req_1_plate_size_z, req_2, req_3_centre_bore, req_4, req_5, req_6, req_7, req_8_sensor_bore, sensor-plate=5/5 evaluated, lid=3/4 evaluated, unevaluated: wall_thickness, gate=fail | lid-spec.md plants a wall thickness no check covers; the gate must fail on it |
| CD-5 | FAIL | fdm_passes=True, milling_before=False, milling_after=False, corner_radii=0.000 x 0.000 x 0.000 x 0.000, diff_features=, diff_params=1, same_size=True |  |
| IN-16 | FAIL | inputs=prompt=used, sketch.png=used, plate_spec.md=used, spec_driven=plate_length, plate_thickness, plate_width, changed_without_spec=, with_spec=ok, without_spec=ok |  |
| IN-17 | pass | status_code=202, job=done, photo_role=used, attachments=f48f33ea04a00, photo_id=f48f33ea04a00 | the image goes to the model with the change request; what the model makes of it is the live run's |
| AP-2 | FAIL | job_id=j7ae561da70d5, holes=2, angled_facet_mm2=1.4, angled_features=part.profile, title=Angle bracket |  |
| AP-3 | FAIL | before=5.0, after=10.0, job=done | seeded 5 mm plate; the change is the model's |
| CD-1 | FAIL | auto_job=params, job=failed, v1_span=650.0, new_span=None, versions=2, origin=context, trigger=beam_spec.md changed: beam_span 1000 -> 1100 mm | params job = cited parameter rebuilt without the model; refine job = the model was asked |
| CD-3 | FAIL | allowable_mpa=138, safety_factor=2.0, ratio_before=1.4, load_n=193.2, proposal=[], thickness_after=4.0, stress_after_mpa=193.2 | mock FEA: sigma = 6 F L / (w t^2) at mount_face, F fixed from the fixture result |
| PR-7 | FAIL | suggestions=0 |  |
| CX-3 | pass | job=done, recorded=f2ec50f71f67d, f3b09f4cd2e96, selected=f2ec50f71f67d, f3b09f4cd2e96, used_in={"f2ec50f71f67d": ["mbcb84332dfc9"], "f3b09f4cd2e96": ["mbcb84332dfc9"], "fc53f2acedcf1": []} | API half; the 'Used in' column is the web suite's |
| WP-6 | FAIL | step_events=14, progress=10, 40, 60, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 100, final=failed | API half; the bar is the web suite's |
| GE-9 | pass | variants=3, rib_counts=4, 6, 8, sweep=100, sweep_valid=100, sweep_seconds=65.7 | seeded base; the model plans the variants |
| DP-13 | FAIL | checks=2/2, valid=False, failed=, seconds=148.7 |  |
| AP-8 | pass | changed=bore_diameter 22 to 24, plate_thickness 6 to 10, calls=20, endpoints=POST documents, POST partstudios, POST partstudios/features, import_calls=0, features=plate_length (assignVariable), plate_width (assignVariable), plate_thickness (assignVariable), boss_diameter (assignVariable), boss_height (assignVariable), bore_diameter (assignVariable), hole_spacing_x (assignVariable), hole_spacing_y (assignVariable), plate_sketch (newSketch), Base plate (extrude), boss_sketch plane (cPlane), boss_sketch (newSketch), Motor boss (extrude), bore plane (cPlane), bore locations (newSketch), Motor bore (hole), mount_holes locations (newSketch), Mounting holes (hole), variables=plate_length=100.0 mm, plate_width=60.0 mm, plate_thickness=10.0 mm, boss_diameter=36.0 mm, boss_height=12.0 mm, bore_diameter=24.0 mm, hole_spacing_x=80.0 mm, hole_spacing_y=40.0 mm, linked=Base plate.depth=#plate_thickness, boss_sketch plane.offset=#plate_thickness, Motor boss.depth=#boss_height, bore plane.offset=#plate_thickness + #boss_height, Motor bore.holeDiameter=#bore_diameter, dangling_refs=0, volume_mm3=61311.615 | Onshape REST replayed from a recorded mock written from the public docs (no account, no network); bodies are the exporter's |
| PR-5 | FAIL | base_hash_before=13289bd4a3dca3a2, base_hash_after=07cab0d0c0ef1667, other_components_changed=base, slot_features=, lid_volume_removed_mm3=-4763.683, valid=True |  |
| AS-3 | FAIL | built=False |  |
| GE-5 | FAIL | built=False |  |
| GE-6 | FAIL | built=False |  |
| DP-11 | pass | checks=3/3, valid=True, failed=, seconds=85.0 |  |
| DP-16 | FAIL | GE-6_built=False, PR-8_cog_shift_x=-3.862, PR-8_predicted_shift_x=-3.862, PR-8_shift_error_mm=2.6645766811729078e-15, PR-8_frame_hole_moves_x=-20, -20, -20, -20, PR-8_holes_aligned=True, PR-8_broken_mates= | GE-6 (generated drone) and PR-8 (battery mount moved for CoG) |
| IN-4 | FAIL | built=False |  |
| IN-5 | FAIL | built=False |  |
| IN-6 | FAIL | built=False |  |
| DP-12 | FAIL | built=False | IN-5 plus tab holes 27.8 ±0.1 |
| VM-10 | FAIL | wrong_flagged=5/5, right_flagged=4/5 | control: the correct parts must pass too, or a critic that rejects everything would meet the row |
| PF-3 | FAIL | IN-5_seconds=215.5, IN-5_built=False, IN-5_passed=False, IN-6_seconds=246.8, IN-6_built=False, IN-6_passed=False | time to a built model; accuracy is gated by IN-5 and IN-6 |
| DP-18 | FAIL | cases=6, passed=5, failed=dp18-kmp-30 | per-case checks in cases.json |
| DP-20 | FAIL | cases=3, passed=1, failed=dp20-two-link-arm, dp20-pcb-enclosure | per-case checks in cases.json |

13/51 rows pass

Model: `scriber-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| AP-6 | pass | tool_vertices=12, tool_thickness=6.0, pocket_samples=1074, offset_min=0.9997, offset_max=1.0, job=done, documented=True | pocket section at half depth of the exported STL, vertices and chord midpoints, distance to the tool's mid-height outline |
| AP-9 | pass | solids=1, valid=True, span=1000.0, root_chord=250.036, tip_chord=120.017, sweep_deg=20.002, dihedral_deg=5.0, twist_deg=2.0, airfoil_deviation_pct_chord=0.015, origin=sizing, llm_calls=0, job=done | scriber_cli.pipe.pipe (the `scriber pipe` command) against the in-process API; IN-11 checks on the downloaded STEP |
| DP-19 | pass | phone_width=75.0, source=phone width 75 mm, inner_width=75.5, expected=75.5, job=done | cut across the cradle at mid-depth, mid-lip height |
| WP-10 | pass | author=alice, visible_to_bob=True, fork_project=True, forked_from=m72bbc5195572 v1 by alice, fork_versions=2, fork_thickness=8.0, original_thickness=5.0 | API half; the web Community tab is not built |
| WP-11 | pass | model_id=ma277bcd79171, version=1, text=the left hole is off by 2 mm, user=local, screenshot_bytes=1539, screenshot_matches=True | API half: the web dialog posts this shape (apps/web BugReport); no end-to-end browser run against the live API |
| WP-12 | pass | limit=3, alice_codes=202, 202, 202, 429, bob_code=202, alice_usage=3, default_limit=None, default_generations=11, default_done=11 | a user is the token's name; 11 > the reference's 10 free generations with no limit set |
| CD-7 | pass | plate dV/dthickness=9463.15222, plate dm/dthickness=74.28574, plate dV/dlength=400.0, plate dV/dhole_d=-207.34512, plate dbbox_x/dlength=1.0, plate dbbox_z/dthickness=1.0, tab dm/dthickness=6.48, tab dbbox_y/dwidth=1.0, max_rel_error=8.69e-12, unchanged dbbox_y/dlength=0.0 | central differences, 1e-3 relative step |
| CX-12 | pass | files=70, step=50, pdf=20, parsed=68, rate=0.9714, facts=95, failed=part-049.step: BuildError: part-049.step: ValueError: part-049.step: the STEP file holds no geometry; spec-019.pdf: PdfiumError: Failed to load document (PDFium: Data format error)., seconds=3.8 | one damaged STEP and one damaged PDF on purpose; report in ingest_report.json |
| CX-14 | pass | material=Aluminum 6061-T6, density_g_cm3=2.7, youngs_modulus_gpa=68.9, source=ASM Aerospace Specification Metals datasheet MA6061T6 (asm.matweb.com), mass_g=127.753, reference_mass_g=127.753, error_pct=0.0 | reference = analytic plate volume x 2.70 g/cm3 (ASM MA6061T6) |
| EX-5 | FAIL | schema=AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF, volume_drift=1.537745022366455e-16, bbox_drift=0.0, solids=1, valid=True, material=Aluminum 6061-T6, documented=True, freecad=not installed | OCCT round trip only; the FreeCAD half needs FreeCAD installed |

9/10 rows pass

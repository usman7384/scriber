Model: `partwright-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| CX-9 | pass | facts=5, bore=req_2_bore, mount=req_1_mount, sourced=True |  |
| VM-1 | pass | pocket_sharp=min_internal_corner_radius@milling_3axis, pocket_r4=PASS, overhang_70=max_overhang_angle@fdm, overhang_45=PASS |  |
| VM-3 | pass | min_hole_edge_ratio=static, min_internal_corner_radius@milling_3axis=static, max_overhang_angle@fdm=static, min_hole_diameter=dynamic, dynamic_only_problems=0, dynamic_only_warnings=min_hole_diameter, static_problems=1 |  |
| VM-5 | pass | aero_flags=1, default_flags=0, aero_measured_mm=18.0, aero_required_mm=20.0 |  |
| CD-8 | pass | params_kept=True, intents_kept=True, same_hash=True, volume_drift=1.0913936421275139e-11 |  |

5/5 rows pass

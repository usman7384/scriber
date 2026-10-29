Model: `partwright-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| IN-11 | pass | solids=1, valid=True, span=1000.0, root_chord=250.036, tip_chord=120.017, sweep_deg=20.002, dihedral_deg=5.0, twist_deg=2.0, airfoil_deviation_pct_chord=0.015 | sections cut at the root and tip stations; sweep and dihedral at the leading edge |
| CD-6 | pass | changed=wing_span: 1000 -> 1100, features_changed=0, new_span=1100.0, old_span=1000.0 | re-run is explicit; no file watcher yet |
| GE-4 | pass | features=root_airfoil, mid_airfoil, tip_airfoil, main_wing, winglet_root_airfoil, winglet_tip_airfoil, winglet, winglet_assembly, full_aircraft, build_order=root_airfoil, mid_airfoil, tip_airfoil, main_wing, winglet_root_airfoil, winglet_tip_airfoil, winglet, winglet_assembly, full_aircraft, solids=1 |  |
| DP-9 | pass | solids=1, valid=True, span=1000.0, root_chord=250.036, tip_chord=120.017, sweep_deg=20.002, dihedral_deg=5.0, twist_deg=0.0, airfoil_deviation_pct_chord=0.015, bbox_cm=46.6 / 100.0 / 18.4, tree=root_airfoil, mid_airfoil, tip_airfoil, main_wing, winglet_root_airfoil, winglet_tip_airfoil, winglet, winglet_assembly, full_aircraft | winglets sit inboard of the tips, so the bbox span is the wing span |
| DP-10 | pass | solids=1, valid=True, span=1000.0, root_chord=250.036, tip_chord=120.017, sweep_deg=20.002, dihedral_deg=5.0, twist_deg=2.0, airfoil_deviation_pct_chord=0.015, body_chord=420.032, body_deviation_pct_chord=0.0096, inner_volume_l=2.038, required_l=1.8 | control surfaces and performance fields are read but not modelled |

5/5 rows pass

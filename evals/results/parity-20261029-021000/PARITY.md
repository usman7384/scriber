Model: `scriber-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| GE-1 | pass | brep_solids=3, mesh_entities=0, valid=True, volume_drift=0.0 |  |
| GE-2 | pass | persisted=True, deterministic=True, error_feature=bad_hole, features=fuselage.body, wing.panel, tail.panel |  |
| PR-1 | pass | params=7, fields=max, min, name, provenance, unit, value | API half; the panel is WP rows in the web suite |
| VM-6 | pass | valid=True, solids=3, boundary_edges=0 |  |
| EX-1 | pass | schema=AP214, solids=3, volume_drift=0.0 |  |
| EX-2 | pass | watertight=True, chordal_deviation_mm=0.00839, triangles=1008 |  |
| EX-3 | pass | errors=0, warnings=0, mesh_nodes=Fuselage, Tailplane, Wing |  |

7/7 rows pass

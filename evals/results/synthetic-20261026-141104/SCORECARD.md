| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| partwright-ir:0.8b-s0b | 40/40 | 40/40 | 322/323 | 39/40 | 18 | 6.9 |
| qwen3.5:0.8b-q8_0 | 8/40 | 8/40 | 39/323 | 4/40 | 102 | 71.6 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| s0-block-001 | partwright-ir:0.8b-s0b | yes | 16/16 | 0 | 8.0 | - |
| s0-block-001 | qwen3.5:0.8b-q8_0 | no | 0/16 | 3 | 149.1 | gave up after 4 attempts |
| s0-block-005 | partwright-ir:0.8b-s0b | yes | 7/7 | 3 | 32.5 | - |
| s0-block-005 | qwen3.5:0.8b-q8_0 | no | 0/7 | 3 | 42.2 | gave up after 4 attempts |
| s0-block-009 | partwright-ir:0.8b-s0b | yes | 8/8 | 0 | 8.8 | - |
| s0-block-009 | qwen3.5:0.8b-q8_0 | no | 0/8 | 3 | 81.3 | gave up after 4 attempts |
| s0-block-013 | partwright-ir:0.8b-s0b | yes | 9/9 | 0 | 11.3 | - |
| s0-block-013 | qwen3.5:0.8b-q8_0 | no | 0/9 | 3 | 82.5 | gave up after 4 attempts |
| s0-block-017 | partwright-ir:0.8b-s0b | yes | 7/7 | 3 | 29.2 | - |
| s0-block-017 | qwen3.5:0.8b-q8_0 | no | 0/7 | 3 | 29.4 | gave up after 4 attempts |
| s0-block-021 | partwright-ir:0.8b-s0b | yes | 7/7 | 0 | 7.4 | - |
| s0-block-021 | qwen3.5:0.8b-q8_0 | no | 0/7 | 3 | 142.9 | gave up after 4 attempts |
| s0-block-025 | partwright-ir:0.8b-s0b | yes | 9/9 | 0 | 9.1 | - |
| s0-block-025 | qwen3.5:0.8b-q8_0 | yes | 6/9 | 0 | 75.7 | 4 counterbores: 2 found; 4 M4 mounting holes: 2 matching holes; all hole diameters [4.0, 4.5, 4.5, 8.0, 8.0, 10.25]; spacing 90: hole centre distances [12.25, 15.8, 16.68, 23.77, 28.34, 29.01, 30.0, 32.4] |
| s0-block-029 | partwright-ir:0.8b-s0b | yes | 16/16 | 3 | 36.3 | - |
| s0-block-029 | qwen3.5:0.8b-q8_0 | no | 0/16 | 3 | 69.1 | gave up after 4 attempts |
| s0-block-033 | partwright-ir:0.8b-s0b | yes | 18/18 | 0 | 10.2 | - |
| s0-block-033 | qwen3.5:0.8b-q8_0 | no | 0/18 | 3 | 122.1 | gave up after 4 attempts |
| s0-block-037 | partwright-ir:0.8b-s0b | yes | 8/8 | 0 | 11.5 | - |
| s0-block-037 | qwen3.5:0.8b-q8_0 | no | 0/8 | 3 | 118.5 | gave up after 4 attempts |
| s0-bracket-003 | partwright-ir:0.8b-s0b | yes | 12/12 | 0 | 7.0 | - |
| s0-bracket-003 | qwen3.5:0.8b-q8_0 | no | 0/12 | 3 | 143.4 | gave up after 4 attempts |
| s0-bracket-007 | partwright-ir:0.8b-s0b | yes | 6/6 | 0 | 6.8 | - |
| s0-bracket-007 | qwen3.5:0.8b-q8_0 | no | 0/6 | 3 | 39.8 | gave up after 4 attempts |
| s0-bracket-011 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 7.1 | - |
| s0-bracket-011 | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 74.2 | gave up after 4 attempts |
| s0-bracket-015 | partwright-ir:0.8b-s0b | yes | 11/11 | 0 | 6.8 | - |
| s0-bracket-015 | qwen3.5:0.8b-q8_0 | no | 0/11 | 3 | 73.1 | gave up after 4 attempts |
| s0-bracket-019 | partwright-ir:0.8b-s0b | yes | 9/9 | 0 | 6.0 | - |
| s0-bracket-019 | qwen3.5:0.8b-q8_0 | no | 0/9 | 3 | 156.2 | gave up after 4 attempts |
| s0-bracket-023 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 6.9 | - |
| s0-bracket-023 | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 74.5 | gave up after 4 attempts |
| s0-bracket-027 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 5.9 | - |
| s0-bracket-027 | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 66.0 | gave up after 4 attempts |
| s0-bracket-031 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 5.8 | - |
| s0-bracket-031 | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 71.6 | gave up after 4 attempts |
| s0-bracket-035 | partwright-ir:0.8b-s0b | yes | 6/6 | 0 | 6.8 | - |
| s0-bracket-035 | qwen3.5:0.8b-q8_0 | no | 0/6 | 3 | 68.4 | gave up after 4 attempts |
| s0-bracket-039 | partwright-ir:0.8b-s0b | yes | 11/11 | 0 | 6.7 | - |
| s0-bracket-039 | qwen3.5:0.8b-q8_0 | no | 0/11 | 3 | 74.3 | gave up after 4 attempts |
| s0-plate-000 | partwright-ir:0.8b-s0b | yes | 10/10 | 0 | 11.4 | - |
| s0-plate-000 | qwen3.5:0.8b-q8_0 | no | 0/10 | 3 | 39.9 | gave up after 4 attempts |
| s0-plate-004 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 6.6 | - |
| s0-plate-004 | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 35.7 | gave up after 4 attempts |
| s0-plate-008 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 6.9 | - |
| s0-plate-008 | qwen3.5:0.8b-q8_0 | yes | 3/5 | 3 | 34.5 | 4 M6 clearance holes: 0 matching holes; all hole diameters []; 34 mm pitch: hole centre distances [] |
| s0-plate-012 | partwright-ir:0.8b-s0b | yes | 13/13 | 0 | 7.9 | - |
| s0-plate-012 | qwen3.5:0.8b-q8_0 | yes | 7/13 | 0 | 74.3 | 4 M5 clearance holes: 1 matching holes; all hole diameters [5.5]; spacing 70: hole centre distances []; parameter hole_margin: missing; parameter pocket_length: missing; parameter pocket_width: missing; parameter pocket_depth: missing |
| s0-plate-016 | partwright-ir:0.8b-s0b | yes | 10/10 | 0 | 5.4 | - |
| s0-plate-016 | qwen3.5:0.8b-q8_0 | no | 0/10 | 3 | 22.2 | gave up after 4 attempts |
| s0-plate-020 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 6.2 | - |
| s0-plate-020 | qwen3.5:0.8b-q8_0 | yes | 5/5 | 3 | 31.1 | - |
| s0-plate-024 | partwright-ir:0.8b-s0b | yes | 10/10 | 0 | 5.5 | - |
| s0-plate-024 | qwen3.5:0.8b-q8_0 | no | 0/10 | 3 | 28.5 | gave up after 4 attempts |
| s0-plate-028 | partwright-ir:0.8b-s0b | yes | 12/12 | 0 | 6.2 | - |
| s0-plate-028 | qwen3.5:0.8b-q8_0 | no | 0/12 | 3 | 109.1 | gave up after 4 attempts |
| s0-plate-032 | partwright-ir:0.8b-s0b | yes | 4/4 | 0 | 4.4 | - |
| s0-plate-032 | qwen3.5:0.8b-q8_0 | yes | 4/4 | 0 | 77.2 | - |
| s0-plate-036 | partwright-ir:0.8b-s0b | yes | 3/3 | 0 | 4.3 | - |
| s0-plate-036 | qwen3.5:0.8b-q8_0 | no | 0/3 | 3 | 67.0 | gave up after 4 attempts |
| s0-turned-002 | partwright-ir:0.8b-s0b | yes | 4/4 | 0 | 4.5 | - |
| s0-turned-002 | qwen3.5:0.8b-q8_0 | yes | 4/4 | 0 | 72.8 | - |
| s0-turned-006 | partwright-ir:0.8b-s0b | yes | 5/5 | 0 | 7.7 | - |
| s0-turned-006 | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 24.4 | gave up after 4 attempts |
| s0-turned-010 | partwright-ir:0.8b-s0b | yes | 10/10 | 3 | 24.3 | - |
| s0-turned-010 | qwen3.5:0.8b-q8_0 | no | 0/10 | 3 | 43.6 | gave up after 4 attempts |
| s0-turned-014 | partwright-ir:0.8b-s0b | yes | 4/4 | 0 | 6.9 | - |
| s0-turned-014 | qwen3.5:0.8b-q8_0 | no | 0/4 | 3 | 68.4 | gave up after 4 attempts |
| s0-turned-018 | partwright-ir:0.8b-s0b | yes | 4/4 | 0 | 5.2 | - |
| s0-turned-018 | qwen3.5:0.8b-q8_0 | no | 0/4 | 3 | 22.8 | gave up after 4 attempts |
| s0-turned-022 | partwright-ir:0.8b-s0b | yes | 11/11 | 0 | 6.4 | - |
| s0-turned-022 | qwen3.5:0.8b-q8_0 | yes | 6/11 | 0 | 74.0 | diameter 20: bounding box 8.50 x 28.00 x 26.50 mm; 8 mm bore: 0 matching holes; all hole diameters []; wall 6: wall from outer size and holes []; parameter bore_diameter: missing; parameter edge_chamfer: missing |
| s0-turned-026 | partwright-ir:0.8b-s0b | yes | 9/9 | 3 | 21.0 | - |
| s0-turned-026 | qwen3.5:0.8b-q8_0 | no | 0/9 | 3 | 62.5 | gave up after 4 attempts |
| s0-turned-030 | partwright-ir:0.8b-s0b | yes | 13/13 | 0 | 7.8 | - |
| s0-turned-030 | qwen3.5:0.8b-q8_0 | no | 0/13 | 3 | 27.5 | gave up after 4 attempts |
| s0-turned-034 | partwright-ir:0.8b-s0b | yes | 4/4 | 0 | 6.7 | - |
| s0-turned-034 | qwen3.5:0.8b-q8_0 | yes | 4/4 | 0 | 71.7 | - |
| s0-turned-038 | partwright-ir:0.8b-s0b | yes | 1/2 | 3 | 14.8 | diameter 46: bounding box 37.00 x 37.00 x 69.00 mm |
| s0-turned-038 | qwen3.5:0.8b-q8_0 | no | 0/2 | 3 | 61.5 | gave up after 4 attempts |

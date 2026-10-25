| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| qwen2.5-coder:7b-instruct-q4_K_M | 9/10 | 8/10 | 22/35 | 3/10 | 27 | 172.5 |
| qwen3.5:4b | 7/10 | 7/10 | 22/35 | 4/10 | 21 | 145.0 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | qwen2.5-coder:7b-instruct-q4_K_M | yes | 1/4 | 3 | 240.6 | 4 bolt holes 8.5: 0 matching holes; all hole diameters []; spacing X 85: hole centre distances []; spacing Y 60: hole centre distances [] |
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 144.9 | gave up after 4 attempts |
| dp21-l-bracket | qwen2.5-coder:7b-instruct-q4_K_M | yes | 2/3 | 3 | 172.5 | four 6 mm holes: 1 matching holes; all hole diameters [6.0] |
| dp21-l-bracket | qwen3.5:4b | yes | 2/3 | 3 | 158.5 | four 6 mm holes: 0 matching holes; all hole diameters [] |
| dp3-dn50-flange | qwen2.5-coder:7b-instruct-q4_K_M | yes | 0/3 | 3 | 116.9 | outer diameter 165: bounding box 60.30 x 18.00 x 18.00 mm; 4 bolt holes 18: 0 matching holes; all hole diameters []; PCD 125 across: hole centre distances [] |
| dp3-dn50-flange | qwen3.5:4b | no | 0/3 | 3 | 172.7 | gave up after 4 attempts |
| dp5-hollow-cylinder | qwen2.5-coder:7b-instruct-q4_K_M | yes | 3/3 | 3 | 78.5 | - |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 3/3 | 1 | 82.9 | - |
| dp6-2020-t-plate | qwen2.5-coder:7b-instruct-q4_K_M | yes | 1/3 | 3 | 184.1 | five M5 clearance: 0 matching holes; all hole diameters []; 20 mm pitch: hole centre distances [] |
| dp6-2020-t-plate | qwen3.5:4b | no | 0/3 | 3 | 163.4 | gave up after 4 attempts |
| dp7-angled-bracket | qwen2.5-coder:7b-instruct-q4_K_M | no | 0/1 | 3 | 192.6 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:4b | yes | 1/1 | 1 | 83.2 | - |
| in2-ten-hole-plate | qwen2.5-coder:7b-instruct-q4_K_M | yes | 4/6 | 3 | 205.7 | ten 6.6 holes: 2 matching holes; all hole diameters [6.6, 6.6]; row distance 60: hole centre distances [40.0] |
| in2-ten-hole-plate | qwen3.5:4b | yes | 6/6 | 0 | 57.9 | - |
| m1-bracket | qwen2.5-coder:7b-instruct-q4_K_M | yes | 3/4 | 3 | 123.3 | 4x M6 clearance: 2 matching holes; all hole diameters [6.6, 6.6] |
| m1-bracket | qwen3.5:4b | yes | 4/4 | 1 | 89.2 | - |
| nema17-plate | qwen2.5-coder:7b-instruct-q4_K_M | yes | 5/5 | 0 | 54.6 | - |
| nema17-plate | qwen3.5:4b | yes | 4/5 | 3 | 172.3 | 31 mm square: hole centre distances [29.5, 41.72] |
| wp-open-box | qwen2.5-coder:7b-instruct-q4_K_M | yes | 3/3 | 3 | 113.5 | - |
| wp-open-box | qwen3.5:4b | yes | 2/3 | 3 | 145.0 | height 40: bounding box 100.00 x 60.00 x 24.00 mm |

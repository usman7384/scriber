| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| qwen3.5:4b | 7/10 | 7/10 | 21/35 | 2/10 | 26 | 117.4 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 117.4 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:4b | no | 0/3 | 3 | 132.5 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:4b | yes | 1/3 | 3 | 130.6 | 4 bolt holes 18: 0 matching holes; all hole diameters [60.3]; PCD 125 across: hole centre distances [] |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 3/3 | 3 | 61.4 | - |
| dp6-2020-t-plate | qwen3.5:4b | yes | 2/3 | 3 | 106.8 | five M5 clearance: 0 matching holes; all hole diameters [4.2, 4.2, 4.2] |
| dp7-angled-bracket | qwen3.5:4b | no | 0/1 | 3 | 150.7 | gave up after 4 attempts |
| in2-ten-hole-plate | qwen3.5:4b | yes | 6/6 | 1 | 80.1 | - |
| m1-bracket | qwen3.5:4b | yes | 3/4 | 3 | 137.8 | 4x M6 clearance: 0 matching holes; all hole diameters [] |
| nema17-plate | qwen3.5:4b | yes | 4/5 | 1 | 80.0 | centre hole 22: 0 matching holes; all hole diameters [3.4, 3.4, 3.4, 3.4] |
| wp-open-box | qwen3.5:4b | yes | 2/3 | 3 | 82.2 | height 40: bounding box 100.00 x 60.00 x 2.00 mm |

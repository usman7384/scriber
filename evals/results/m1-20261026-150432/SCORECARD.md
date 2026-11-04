| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| scriber-ir:0.8b-s0b | 3/10 | 3/10 | 3/35 | 0/10 | 30 | 19.1 |
| qwen3.5:0.8b-q8_0 | 2/10 | 1/10 | 6/35 | 1/10 | 30 | 39.1 |
| qwen3.5:4b | 5/10 | 5/10 | 15/35 | 4/10 | 20 | 68.3 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | scriber-ir:0.8b-s0b | yes | 0/4 | 3 | 84.1 | height 60: bounding box 508.00 x 508.00 x 236.00 mm; 4 bolt holes 8.5: 0 matching holes; all hole diameters [6.6, 6.6, 6.6, 6.6]; spacing X 85: hole centre distances []; spacing Y 60: hole centre distances [] |
| dp2-flanged-adapter | qwen3.5:0.8b-q8_0 | no | 0/4 | 3 | 114.0 | gave up after 4 attempts |
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 122.1 | gave up after 4 attempts |
| dp21-l-bracket | scriber-ir:0.8b-s0b | no | 0/3 | 3 | 17.7 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:0.8b-q8_0 | no | 0/3 | 3 | 32.1 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:4b | no | 0/3 | 3 | 88.5 | gave up after 4 attempts |
| dp3-dn50-flange | scriber-ir:0.8b-s0b | no | 0/3 | 3 | 16.4 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:0.8b-q8_0 | no | 0/3 | 3 | 28.5 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:4b | no | 0/3 | 3 | 99.8 | gave up after 4 attempts |
| dp5-hollow-cylinder | scriber-ir:0.8b-s0b | yes | 2/3 | 3 | 12.3 | wall 2: wall from outer size and holes [24.0] |
| dp5-hollow-cylinder | qwen3.5:0.8b-q8_0 | yes | 3/3 | 3 | 60.0 | - |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 3/3 | 0 | 12.2 | - |
| dp6-2020-t-plate | scriber-ir:0.8b-s0b | no | 0/3 | 3 | 19.1 | gave up after 4 attempts |
| dp6-2020-t-plate | qwen3.5:0.8b-q8_0 | no | 0/3 | 3 | 39.1 | gave up after 4 attempts |
| dp6-2020-t-plate | qwen3.5:4b | no | 0/3 | 3 | 68.3 | gave up after 4 attempts |
| dp7-angled-bracket | scriber-ir:0.8b-s0b | no | 0/1 | 3 | 20.3 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:0.8b-q8_0 | no | 0/1 | 3 | 65.5 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:4b | yes | 0/1 | 2 | 60.5 | has screw holes: 0 matching holes; all hole diameters [] |
| in2-ten-hole-plate | scriber-ir:0.8b-s0b | no | 0/6 | 3 | 21.4 | gave up after 4 attempts |
| in2-ten-hole-plate | qwen3.5:0.8b-q8_0 | no | 0/6 | 3 | 25.0 | gave up after 4 attempts |
| in2-ten-hole-plate | qwen3.5:4b | no | 0/6 | 3 | 92.6 | gave up after 4 attempts |
| m1-bracket | scriber-ir:0.8b-s0b | no | 0/4 | 3 | 26.6 | gave up after 4 attempts |
| m1-bracket | qwen3.5:0.8b-q8_0 | no | 0/4 | 3 | 20.9 | gave up after 4 attempts |
| m1-bracket | qwen3.5:4b | yes | 4/4 | 0 | 38.2 | - |
| nema17-plate | scriber-ir:0.8b-s0b | yes | 1/5 | 3 | 18.5 | thickness 5: bounding box 60.00 x 60.00 x 31.00 mm; four M3: 0 matching holes; all hole diameters []; 31 mm square: hole centre distances []; centre hole 22: 0 matching holes; all hole diameters [] |
| nema17-plate | qwen3.5:0.8b-q8_0 | no | 0/5 | 3 | 20.4 | gave up after 4 attempts |
| nema17-plate | qwen3.5:4b | yes | 5/5 | 0 | 26.0 | - |
| wp-open-box | scriber-ir:0.8b-s0b | no | 0/3 | 3 | 15.2 | gave up after 4 attempts |
| wp-open-box | qwen3.5:0.8b-q8_0 | yes | 3/3 | 3 | 66.9 | - |
| wp-open-box | qwen3.5:4b | yes | 3/3 | 3 | 64.1 | - |

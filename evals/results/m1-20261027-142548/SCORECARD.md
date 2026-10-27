| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| qwen3.5:4b | 5/10 | 5/10 | 15/35 | 4/10 | 17 | 67.4 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 117.2 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:4b | no | 0/3 | 3 | 82.9 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:4b | no | 0/3 | 3 | 97.8 | gave up after 4 attempts |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 3/3 | 0 | 11.8 | - |
| dp6-2020-t-plate | qwen3.5:4b | no | 0/3 | 3 | 67.4 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:4b | yes | 0/1 | 2 | 57.7 | has screw holes: 0 matching holes; all hole diameters [] |
| in2-ten-hole-plate | qwen3.5:4b | no | 0/6 | 3 | 90.4 | gave up after 4 attempts |
| m1-bracket | qwen3.5:4b | yes | 4/4 | 0 | 40.7 | - |
| nema17-plate | qwen3.5:4b | yes | 5/5 | 0 | 25.7 | - |
| wp-open-box | qwen3.5:4b | yes | 3/3 | 0 | 19.9 | - |

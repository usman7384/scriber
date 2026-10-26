| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| qwen3.5:4b | 5/10 | 5/10 | 16/35 | 4/10 | 23 | 132.8 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 95.7 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:4b | no | 0/3 | 3 | 202.4 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:4b | yes | 1/3 | 3 | 147.1 | 4 bolt holes 18: 0 matching holes; all hole diameters [17.5, 17.5, 17.5, 17.5, 60.3]; PCD 125 across: hole centre distances [] |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 3/3 | 2 | 62.6 | - |
| dp6-2020-t-plate | qwen3.5:4b | no | 0/3 | 3 | 182.0 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:4b | no | 0/1 | 3 | 132.8 | gave up after 4 attempts |
| in2-ten-hole-plate | qwen3.5:4b | no | 0/6 | 3 | 423.3 | gave up after 4 attempts |
| m1-bracket | qwen3.5:4b | yes | 4/4 | 0 | 29.3 | - |
| nema17-plate | qwen3.5:4b | yes | 5/5 | 0 | 34.3 | - |
| wp-open-box | qwen3.5:4b | yes | 3/3 | 3 | 88.7 | - |

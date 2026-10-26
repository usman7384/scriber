| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| qwen3.5:4b | 3/10 | 3/10 | 9/35 | 2/10 | 27 | 128.4 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 110.2 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:4b | no | 0/3 | 3 | 128.4 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:4b | no | 0/3 | 3 | 228.4 | gave up after 4 attempts |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 1/3 | 3 | 58.8 | wall 2: wall from outer size and holes []; one bore: 0 matching holes; all hole diameters [] |
| dp6-2020-t-plate | qwen3.5:4b | no | 0/3 | 3 | 279.0 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:4b | no | 0/1 | 3 | 129.0 | gave up after 4 attempts |
| in2-ten-hole-plate | qwen3.5:4b | no | 0/6 | 3 | 122.3 | gave up after 4 attempts |
| m1-bracket | qwen3.5:4b | no | 0/4 | 3 | 152.6 | gave up after 4 attempts |
| nema17-plate | qwen3.5:4b | yes | 5/5 | 0 | 52.6 | - |
| wp-open-box | qwen3.5:4b | yes | 3/3 | 3 | 95.8 | - |

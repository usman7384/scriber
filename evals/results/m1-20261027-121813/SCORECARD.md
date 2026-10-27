| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| qwen3.5:4b | 5/10 | 5/10 | 15/35 | 4/10 | 17 | 51.6 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | qwen3.5:4b | no | 0/4 | 3 | 56.7 | gave up after 4 attempts |
| dp21-l-bracket | qwen3.5:4b | no | 0/3 | 3 | 51.6 | gave up after 4 attempts |
| dp3-dn50-flange | qwen3.5:4b | no | 0/3 | 3 | 89.3 | gave up after 4 attempts |
| dp5-hollow-cylinder | qwen3.5:4b | yes | 3/3 | 0 | 6.0 | - |
| dp6-2020-t-plate | qwen3.5:4b | no | 0/3 | 3 | 63.1 | gave up after 4 attempts |
| dp7-angled-bracket | qwen3.5:4b | yes | 0/1 | 2 | 28.1 | has screw holes: 0 matching holes; all hole diameters [] |
| in2-ten-hole-plate | qwen3.5:4b | no | 0/6 | 3 | 80.9 | gave up after 4 attempts |
| m1-bracket | qwen3.5:4b | yes | 4/4 | 0 | 35.2 | - |
| nema17-plate | qwen3.5:4b | yes | 5/5 | 0 | 24.6 | - |
| wp-open-box | qwen3.5:4b | yes | 3/3 | 0 | 18.0 | - |

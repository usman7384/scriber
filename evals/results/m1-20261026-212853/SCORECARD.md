| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| scriber-ir:0.8b-s1 | 6/10 | 6/10 | 10/35 | 3/10 | 19 | 15.9 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| dp2-flanged-adapter | scriber-ir:0.8b-s1 | yes | 0/4 | 3 | 15.7 | height 60: bounding box 103.00 x 103.00 x 51.00 mm; 4 bolt holes 8.5: 0 matching holes; all hole diameters [4.5, 4.5, 4.5, 4.5, 60.0]; spacing X 85: hole centre distances []; spacing Y 60: hole centre distances [] |
| dp21-l-bracket | scriber-ir:0.8b-s1 | no | 0/3 | 3 | 19.7 | gave up after 4 attempts |
| dp3-dn50-flange | scriber-ir:0.8b-s1 | yes | 1/3 | 3 | 15.9 | 4 bolt holes 18: 0 matching holes; all hole diameters [17.5, 17.5, 17.5, 17.5, 60.3]; PCD 125 across: hole centre distances [] |
| dp5-hollow-cylinder | scriber-ir:0.8b-s1 | yes | 1/3 | 0 | 3.0 | wall 2: wall from outer size and holes []; one bore: 0 matching holes; all hole diameters [] |
| dp6-2020-t-plate | scriber-ir:0.8b-s1 | no | 0/3 | 3 | 15.7 | gave up after 4 attempts |
| dp7-angled-bracket | scriber-ir:0.8b-s1 | yes | 1/1 | 0 | 4.1 | - |
| in2-ten-hole-plate | scriber-ir:0.8b-s1 | no | 0/6 | 3 | 19.2 | gave up after 4 attempts |
| m1-bracket | scriber-ir:0.8b-s1 | yes | 4/4 | 1 | 19.3 | - |
| nema17-plate | scriber-ir:0.8b-s1 | no | 0/5 | 3 | 16.4 | gave up after 4 attempts |
| wp-open-box | scriber-ir:0.8b-s1 | yes | 3/3 | 0 | 3.6 | - |

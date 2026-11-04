Model: `scriber-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| IN-1 | pass | solids=1, valid=True, height=50.0, od=100.0, wall=2.0 |  |
| DP-5 | pass | solids=1, valid=True, height=50.0, od=100.0, wall=2.0 |  |
| PR-4 | pass | length=450.0, changed=length, parts=3, valid=True |  |
| DP-2 | FAIL | checks=1/4, valid=True, failed=4 bolt holes 8.5: 0 matching holes; all hole diameters [5.5, 5.5, 43.8]; spacing X 85: hole centre distances []; spacing Y 60: hole centre distances [] |  |
| DP-7 | FAIL | checks=1/1, valid=True, failed=, angled= |  |
| DP-21 | FAIL | checks=2/3, valid=True, failed=four 6 mm holes: 0 matching holes; all hole diameters [4.5, 4.5, 4.5, 4.5] |  |
| GE-10 | pass | titles=Hollow cylinder | Mounting bracket |  |
| GE-7 | pass | runs=5, distinct_ir=1, distinct_volumes=1, volume=23315.76112 |  |

5/8 rows pass

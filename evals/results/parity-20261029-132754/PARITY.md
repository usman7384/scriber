Model: `scriber-ir:4b-s2`

| row | result | measured | note |
|---|---|---|---|
| GE-13 | FAIL | low_valid=3, high_valid=3, low_log=low with a 0 token reasoning budget | low with a 0 token reasoning budget, re-sampled because it repeated an earlier answer, high_log=high with a 8192 token reasoning budget | high with a 8192 token reasoning budget, re-sampled because it repeated an earlier answer |  |
| AP-7 | FAIL | jobs=10, done=8, listed=10, failed=gave up after 6 attempts, gave up after 6 attempts |  |
| WP-15 | FAIL | prompts=10, completed=9, errors=b17-cup: gave up after 6 attempts, blocked=, model_host=127.0.0.1 | outbound sockets and name lookups to anything but loopback raise inside the run |
| PF-8 | pass | model=scriber-ir:4b-s2, eval_tokens=256, tokens_per_s=20.4, loaded_size_gib=2.76 | Ollama eval counters on this machine, not the reference laptop |
| GE-8 | FAIL | parts=30, dims_within_tolerance=98/152, share=0.6447 | dims of parts that failed to build count as missed |
| VM-8 | pass | reference_parts=30, references_failing_spec=, cases_scored=20/30, mean_param_accuracy=0.9174, median_hausdorff_mm=0.0 | per-case param accuracy and Hausdorff in ../benchmark.json; a case whose generation did not build has no Hausdorff |
| PF-1 | pass | cases=30, median_s=33.45, max_s=239.8 | measured on this machine, not the reference laptop of docs/HARDWARE.md |
| PF-7 | pass | p50_s=33.45, seconds_claim=met | single-part benchmark prompts; the 'seconds' claim (p50 under 60 s) is met |
| GE-11 | FAIL | plate_a=0/6, plate_b=4/6, plate_c=0/6, plate_d=5/6, flange_a=0/6, flange_b=5/6, flange_c=0/6, flange_d=5/6, recovered=19/48, share=0.3958 |  |
| DP-14 | FAIL | cases=16, passed=4, failed=dp14-long-angle, dp14-t-plate, dp14-single-gusset, dp14-double-gusset, dp14-ring-tabs, dp14-pedestal, dp14-z-bracket, dp14-corner-plate, dp14-clevis, dp14-shelf-bracket, dp14-pipe-saddle, dp14-hat-bracket | per-case checks in cases.json |
| DP-15 | FAIL | cases=16, passed=13, failed=dp15-weld-neck-dn50, dp15-weld-neck-dn80, dp15-iec-ff165 | per-case checks in cases.json |

4/11 rows pass

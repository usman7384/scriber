| model | built | valid | checks | all checks pass | repairs | median s |
|---|---|---|---|---|---|---|
| scriber-ir:0.8b-s0b | 0/2 | 0/2 | 0/29 | 0/2 | 6 | 81.3 |
| qwen3.5:4b | 0/2 | 0/2 | 0/29 | 0/2 | 6 | 378.6 |

| case | model | built | checks | repairs | s | failed checks |
|---|---|---|---|---|---|---|
| c01-manifold-challenge | scriber-ir:0.8b-s0b | no | 0/25 | 3 | 81.3 | gave up after 4 attempts |
| c01-manifold-challenge | qwen3.5:4b | no | 0/25 | 3 | 378.6 | gave up after 4 attempts |
| c02-manifold-short | scriber-ir:0.8b-s0b | no | 0/4 | 3 | 38.2 | gave up after 4 attempts |
| c02-manifold-short | qwen3.5:4b | no | 0/4 | 3 | 220.1 | gave up after 4 attempts |

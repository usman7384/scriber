Model: `partwright-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| AS-2 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| AS-4 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| PR-8 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| IN-7 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| IN-8 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| CD-4 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| PF-5 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| IN-14 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| PF-2 | FAIL |  | BuildError: NameError: name 'namespace' is not defined |
| PF-6 | pass | variants=1000, valid_single_solids=1000, distinct_volumes=1000, workers=8, elapsed_s=488.2, rebuild_p50_s=3.672, budget_s=600.0 | seeded +-10 % on every BWB param; compile and rebuild with validity and mass checks, no exports |

1/10 rows pass

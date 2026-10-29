from partwright_evals.parity_report import report, rows

CHECKLIST = """## Inputs

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| IN-1 | Prompt to part | S1 | agent | Gen(x) | done (M1): passes |
| IN-2 | Spec file | S2 | context | Gen(y) | in progress (M2): half |

## Export

| # | Capability | Evidence | Our deliverable | Acceptance test | Status |
|---|---|---|---|---|---|
| EX-1 | STEP | S3 | geometry | reload | open |
"""


def test_report_counts_rows_per_area_and_lists_unfinished_ones() -> None:
    found = rows(CHECKLIST)
    assert [(s, r) for s, r, *_ in found] == [("Inputs", "IN-1"), ("Inputs", "IN-2"), ("Export", "EX-1")]
    text = report(found)
    assert "**1 done, 1 in progress, 1 open, of 3 rows.**" in text
    assert "| Inputs | 1 | 1 | 0 |" in text and "| Export | 0 | 0 | 1 |" in text
    assert "| IN-2 | Spec file | in progress (M2): half |" in text and "| IN-1 |" not in text

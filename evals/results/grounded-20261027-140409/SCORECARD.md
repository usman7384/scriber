## Extraction and retrieval

- Facts: P 0.93 / R 0.95 (55 tp, 4 fp, 3 fn)
- Rules: P 1.00 / R 0.86 (6 tp, 0 fp, 1 fn)
- Retrieval: 1.00 of extracted labelled facts reach the context pack (9 cases)

## Generation: prompt-only vs grounded

| mode | fully passing | built | checks | rule errors | params cited (correct / cited / all) | median s |
|---|---|---|---|---|---|---|
| prompt | 4/10 | 9/10 | 34/45 | 8 | 0 / 0 / 42 | 27 |
| grounded | 3/10 | 10/10 | 27/45 | 9 | 24 / 34 / 48 | 32 |

| case | facts P/R | rules | retrieval | prompt | grounded |
|---|---|---|---|---|---|
| g01-sensor-plate | 6/7 found, 0 missed | 2/2 | 1.00 | PASS 5/5, cited 0/5 | PASS 5/5, cited 4/5 |
| g02-nema23-docx | 7/7 found, 0 missed | 0/0 | 1.00 | fail 4/5, cited 0/5 | fail 0/5, cited 0/4 |
| g03-hole-table-xlsx | 13/13 found, 0 missed | 0/0 | 1.00 | not built (4 attempts) | fail 4/6, cited 3/5 |
| g04-enclosure-yaml | 4/6 found, 0 missed | 1/1 | 1.00 | PASS 3/3, cited 0/4 | PASS 3/3, cited 4/4 |
| g05-flange-pdf | 6/6 found, 0 missed | 1/1 | 1.00 | fail 3/5, cited 0/5 | fail 3/5, cited 4/5 |
| g06-base-plate-txt | 6/6 found, 0 missed | 0/0 | 1.00 | fail 6/6, 4 rule errors, cited 0/4 | fail 4/6, cited 4/5 |
| g07-spacer-csv | 0/0 found, 3 missed | 0/0 | - | PASS 3/3, cited 0/3 | fail 0/3, cited 0/3 |
| g08-milled-pocket | 7/8 found, 0 missed | 1/1 | 1.00 | fail 3/3, 4 rule errors, cited 0/7 | fail 0/3, 9 rule errors, cited 0/7 |
| g09-previous-step | 1/1 found, 0 missed | 0/0 | 1.00 | fail 2/4, cited 0/4 | fail 3/4, cited 1/5 |
| g10-fdm-bracket | 5/5 found, 0 missed | 1/2 | 1.00 | PASS 5/5, cited 0/5 | PASS 5/5, cited 4/5 |

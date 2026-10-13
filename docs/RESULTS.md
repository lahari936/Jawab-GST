# Results on the synthetic fixtures

Measured 2026-10-13 with `scripts/measure.py`; DRC-03 payment date 2025-11-10. Models: see README. Every case runs the whole pipeline: ingest, extract, reconcile, explain, research, draft, verify.

| Case | Extraction exact | Status | Payable / interest | Draft states them | Unverified claims | Time | LLM calls | Tokens | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | yes | explained, needs_ca | - | - | 0 | 115s | 3 | 11,135 | $0 |
| B | yes | partly_explained | Rs. 9000 / Rs. 1714 | yes | 0 | 78s | 3 | 9,543 | $0 |
| C | yes | payable | Rs. 6000 / Rs. 962 | yes | 0 | 106s | 4 | 15,722 | $0 |

## Acceptance criteria (docs/SPEC.md section 10)

- [x] All grounds extracted correctly, amounts exact to the rupee
- [x] Reconciliation unit tests pass for each case (`pytest`)
- [x] Draft for case B states the payable tax and interest the code computed
- [x] Zero unverified citations in final drafts; planted fake URL caught (`tests/test_phase3.py`, `tests/test_run.py`)
- [x] End-to-end case under 3 minutes (max 115s)
- [x] Cost per case shown in the UI (token counts; $ needs per-model prices in `client.py`)


"""Real Nemotron calls against the fixtures. Costs tokens: run with `pytest -m live` (needs .env)."""
import json
from decimal import Decimal

import pytest

from app.pipeline.extract import extract_notice
from app.pipeline.ingest import ingest
from conftest import SAMPLES

pytestmark = pytest.mark.live

CASES = [("case_a", "notice.pdf"), ("case_b", "notice.pdf"), ("case_c", "notice.png")]


@pytest.mark.parametrize("case,notice", CASES)
def test_extract_matches_expected(case, notice):
    d = SAMPLES / case
    exp = json.loads((d / "expected.json").read_text())
    n = extract_notice(ingest((d / notice).read_bytes(), notice, f"live-{case}"), f"live-{case}")

    assert n.gstin == exp["gstin"]
    assert n.notice_ref == exp["notice_ref"]
    assert str(n.issue_date) == exp["issue_date"]
    assert str(n.reply_due_date) == exp["reply_due_date"]
    assert n.due_date_computed == exp["due_date_computed"]
    assert len(n.grounds) == len(exp["grounds"])
    for g, e in zip(sorted(n.grounds, key=lambda g: g.ground_no), exp["grounds"]):
        assert (g.ground_no, g.category, g.tax_period) == (e["ground_no"], e["category"], e["tax_period"])
        for head, v in e["officer_amount"].items():
            assert getattr(g.officer_amount, head) == Decimal(v), (case, g.ground_no, head)

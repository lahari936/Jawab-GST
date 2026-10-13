from datetime import date

from app.domain.interest import interest, payment_due_date
from app.domain.reconcile import assess
from app.models import Ground, TaxAmount
from app.pipeline import research as research_mod
from app.pipeline.draft import GroundReply, render
from app.pipeline.verify import allowed_amounts, verify
from app.research import tavily
from app.research.tavily import case_sources
from test_reconcile import amt, run


def test_payment_due_date_rolls_year():
    assert payment_due_date("2024-09") == date(2024, 10, 20)
    assert payment_due_date("2024-12") == date(2025, 1, 20)


def test_interest_case_b():
    # 4500 * 18% * 386 days / 365 = 856.60 -> 857
    i = interest(amt(cgst=4500, sgst=4500), "2024-09", date(2025, 11, 10))
    assert i == amt(cgst=857, sgst=857)
    assert interest(amt(cgst=4500), "2024-09", date(2024, 10, 1)) == TaxAmount()  # paid before due date


def test_assess_and_evidence():
    a, b, c = run("case_a"), run("case_b"), run("case_c")
    assert assess(a) == ("explained", None)
    assert assess(b) == ("partly_explained", amt(cgst=4500, sgst=4500))
    assert assess(c) == ("payable", amt(cgst=3000, sgst=3000))
    assert "KT/CN/07" in a.evidence[0].text and a.evidence[0].amount == amt(igst=18000)
    assert "QL/118" in b.evidence[0].text and b.evidence[0].amount == amt(cgst=1500, sgst=1500)
    assert c.evidence == []


def test_research_stores_sources(monkeypatch):
    fake = {"results": [{"title": "Circular 183", "url": "https://cbic-gst.gov.in/c183.pdf", "content": "ITC ..."}]}
    calls = []
    monkeypatch.setattr(tavily, "_tv", lambda: type("T", (), {"search": lambda self, **kw: calls.append(kw) or fake})())
    ground = Ground(ground_no=1, category="itc_2b_vs_3b", description="d", tax_period="2024-09", officer_amount=TaxAmount())
    rows = research_mod.research("case-research", ground)
    assert rows[0].id and rows[0].url == "https://cbic-gst.gov.in/c183.pdf"
    assert calls[0]["include_domains"] == tavily.GST_DOMAINS
    assert [s.id for s in case_sources("case-research")] == [rows[0].id]


def test_verifier_flags_planted_url_number_and_citation(monkeypatch):
    monkeypatch.setattr(tavily, "_tv", lambda: type("T", (), {"search": lambda self, **kw: {"results": [
        {"title": "Rule 99", "url": "https://cbic-gst.gov.in/rule99.html", "content": "..."}]}})())
    ground = Ground(ground_no=1, category="itc_2b_vs_3b", description="d", tax_period="2024-09", officer_amount=TaxAmount())
    src = research_mod.research("case-verify", ground)[0]
    rec = run("case_b")
    payable = amt(cgst=4500, sgst=4500)
    allowed = allowed_amounts(rec, payable, amt(cgst=857, sgst=857))

    good = f"ITC of Rs. 4,500 each was paid with interest of Rs. 857 [S{src.id}]. Total Rs. 9,000. See {src.url}."
    assert verify(good, allowed, case_sources("case-verify")) == []

    bad = good + " Also Rs. 9,999 per https://fake-gst-circular.example/c999 [S99999]."
    issues = verify(bad, allowed, case_sources("case-verify"))
    assert {(i.kind, i.value) for i in issues} == {
        ("number", "Rs. 9,999"), ("url", "https://fake-gst-circular.example/c999"), ("citation", "[S99999]")}
    assert all(bad[i.start:i.end] == i.value for i in issues)


def test_render_has_banner_and_needs_ca():
    import json
    from app.models import Notice
    from conftest import SAMPLES
    exp = json.loads((SAMPLES / "case_a" / "expected.json").read_text())
    for g in exp["grounds"]:
        g["description"] = "x"
    n = Notice.model_validate(exp)
    text = render(n, [GroundReply(ground_no=1, text="Explained by credit note.")], [n.grounds[1]], date(2025, 11, 1))
    assert text.count("NOT LEGAL ADVICE") == 2
    assert "Ground 1:\nExplained by credit note." in text
    assert "Ground 2:\nThis ground is under review" in text

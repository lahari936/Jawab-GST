"""Whole case lifecycle on case B with LLM and Tavily faked."""
import json
from datetime import date

from app.llm import client
from app.pipeline import case
from app.research import tavily
from conftest import SAMPLES


def fake_llm(monkeypatch, draft_text="Rs. 4,500 paid with interest Rs. 857 [S{sid}]. Rs. 1,234 extra."):
    exp = json.loads((SAMPLES / "case_b" / "expected.json").read_text())
    exp["grounds"][0]["description"] = "ITC in 3B exceeds 2B"
    exp["reply_due_date"] = None
    seen = {}

    def fake_chat(tier, messages, case_id, **kw):
        if tier == "fast":
            return json.dumps(exp)
        if tier == "agent":
            return json.dumps({"causes": [{"cause": "timing_difference", "why": "Supplier filed late.",
                                           "proof_document": "GSTR-2B Oct"}]})
        seen["draft_input"] = json.loads(messages[1]["content"])
        sid = seen["draft_input"][0]["sources"][0]["id"]
        return json.dumps({"grounds": [{"ground_no": 1, "text": draft_text.format(sid=sid)}]})

    monkeypatch.setattr(client, "_chat", fake_chat)
    monkeypatch.setattr(tavily, "_tv", lambda: type("T", (), {"search": lambda self, **kw: {"results": [
        {"title": "Circular", "url": "https://cbic-gst.gov.in/x.pdf", "content": "..."}]}})())
    return seen


def test_run_case_b_offline(monkeypatch):
    fake_llm(monkeypatch)
    c = case.run(SAMPLES / "case_b", date(2025, 11, 10), case_id="offline-b")
    g = c.grounds[0]
    assert g.status == "partly_explained" and g.interest_total == 1714 and g.payable_total == 9000
    assert c.notice.due_date_computed
    assert "Ground 1:\nRs. 4,500" in c.draft
    assert [(i.kind, i.value) for i in c.issues] == [("number", "Rs. 1,234")]
    assert case.load("offline-b").issues == c.issues  # persisted


def test_ui_flow_only_confirmed_facts_reach_draft(monkeypatch):
    seen = fake_llm(monkeypatch)
    d = SAMPLES / "case_b"
    c = case.create((d / "notice.pdf").read_bytes(), "notice.pdf", d / "gstr1.csv", d / "gstr3b.csv",
                    d / "gstr2b.csv", case_id="ui-b")
    assert c.grounds[0].confirmed and "QL/118" in c.grounds[0].confirmed[0]  # evidence pre-confirmed
    c = case.analyse(c, 1)
    assert c.grounds[0].causes[0].why == "Supplier filed late." and c.grounds[0].source_ids
    c = case.confirm(c, 1, ["User fact only"])
    c = case.make_draft(c, date(2025, 11, 10))
    assert seen["draft_input"][0]["confirmed_facts"] == ["User fact only"]

    c = case.reverify(c, c.draft.replace("Rs. 1,234 extra.", "See https://fake.example/x."))
    assert [(i.kind, i.value) for i in c.issues] == [("url", "https://fake.example/x")]

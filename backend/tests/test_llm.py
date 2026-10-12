"""LLM client, ingest and extract with the API faked. Live checks are in test_live.py (pytest -m live)."""
import json
from datetime import date
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm import client
from app.models import LlmCall, engine
from app.pipeline import extract, ingest
from conftest import SAMPLES

NOTICE_JSON = {
    "gstin": "27ZZZMB0002B1Z2", "notice_ref": "R1", "form": "ASMT-10", "issue_date": "2025-10-20",
    "reply_due_date": None, "financial_year": "2024-25",
    "grounds": [{"ground_no": 1, "category": "itc_2b_vs_3b", "description": "d", "tax_period": "2024-09",
                 "officer_amount": {"cgst": 6000, "sgst": 6000}}],
}


class FakeAPI:
    """Returns queued message objects; records requests."""

    def __init__(self, *messages):
        self.messages, self.requests = list(messages), []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kw):
        self.requests.append(kw)
        return NS(choices=[NS(message=self.messages.pop(0))], usage=NS(prompt_tokens=10, completion_tokens=5))


@pytest.fixture
def fake(monkeypatch):
    for t in ("VISION", "FAST", "AGENT", "REASON"):
        monkeypatch.setenv(f"MODEL_{t}", f"m-{t.lower()}")

    def install(*messages):
        api = FakeAPI(*messages)
        monkeypatch.setattr(client, "_client", lambda: api)
        return api
    return install


def msg(content=None, reasoning_content=None):
    return NS(content=content, reasoning_content=reasoning_content)


def test_reasoning_field_fallback_and_fences(fake):
    fake(msg(None, "thinking...\n```json\n" + json.dumps(NOTICE_JSON) + "\n```"))
    n = extract.extract_notice("text", "case-x")
    assert n.gstin == "27ZZZMB0002B1Z2"


def test_due_date_computed_when_missing(fake):
    fake(msg(json.dumps(NOTICE_JSON)))
    n = extract.extract_notice("text", "case-x")
    assert n.reply_due_date == date(2025, 11, 19) and n.due_date_computed


def test_retry_once_then_fail(fake):
    api = fake(msg("{}"), msg(json.dumps(NOTICE_JSON)))
    assert extract.extract_notice("text", "case-retry").gstin
    assert "failed validation" in api.requests[1]["messages"][1]["content"]

    fake(msg("{}"), msg("not json"))
    with pytest.raises(RuntimeError):
        extract.extract_notice("text", "case-retry")


def test_usage_logged(fake):
    fake(msg(json.dumps(NOTICE_JSON)))
    extract.extract_notice("text", "case-log")
    with Session(engine) as s:
        rows = s.scalars(select(LlmCall).where(LlmCall.case_id == "case-log")).all()
    assert [(r.tier, r.model, r.input_tokens, r.output_tokens) for r in rows] == [("fast", "m-fast", 10, 5)]


def test_ingest_digital_pdf_skips_llm(fake):
    api = fake()
    text = ingest.ingest((SAMPLES / "case_a" / "notice.pdf").read_bytes(), "notice.pdf", "c")
    assert "29ZZZKT0001A1Z1" in text and "18,000.00" in text
    assert api.requests == []


def test_ingest_image_uses_vision(fake):
    api = fake(msg("TRANSCRIBED"))
    assert ingest.ingest((SAMPLES / "case_c" / "notice.png").read_bytes(), "notice.png", "c") == "TRANSCRIBED"
    req = api.requests[0]
    assert req["model"] == "m-vision"
    assert req["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_ingest_rejects_unknown_type():
    with pytest.raises(ValueError):
        ingest.ingest(b"x", "notice.docx", "c")

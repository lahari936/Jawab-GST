import json
from typing import Literal

from pydantic import BaseModel

from app.domain.reconcile import ReconResult
from app.llm.client import call_json
from app.models import Ground


class Cause(BaseModel):
    cause: Literal["timing_difference", "credit_note", "amendment_later_period", "itc_reversed", "genuine_short_payment"]
    why: str                 # one sentence tied to the data given; no new numbers
    proof_document: str      # document that would prove it


class Explanation(BaseModel):
    causes: list[Cause]


SYSTEM = """You are a GST practitioner. You get one ASMT-10 ground: the officer's figure, our figure and the
reconciliation computed by code, including later-period documents. From the allowed cause list, pick those
consistent with the data and say what document would prove each. Do not compute numbers or introduce new ones.
If code says part of the amount is payable, include genuine_short_payment."""


def explain(g: Ground, r: ReconResult, status: str, case_id: str) -> Explanation:
    user = json.dumps({"ground": g.model_dump(mode="json"), "reconciliation": r.model_dump(mode="json"),
                       "status_from_code": status}, indent=1)
    return call_json("agent", SYSTEM, user, Explanation, case_id)

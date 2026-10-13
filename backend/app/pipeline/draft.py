import json
from datetime import date

from pydantic import BaseModel

from app.llm.client import call_json
from app.models import Ground, Notice

BANNER = "DRAFT FOR REVIEW BY YOU OR A CA. NOT LEGAL ADVICE. NOT FILED."


class GroundReply(BaseModel):
    ground_no: int
    text: str


class DraftOut(BaseModel):
    grounds: list[GroundReply]


SYSTEM = """Write the reply to each ground for Form GST ASMT-11. Use only the facts, numbers and sources given.
Write every amount as "Rs. 12,345" using only amounts that appear in the input. Do not add, subtract or total amounts yourself.
Cite sources only as [S<id>] using the ids given; never write URLs. Plain, formal English, point-wise, 80-180 words per ground.
If status is payable or partly_explained, state that the tax and interest given were paid via Form GST DRC-03 on the payment date given."""


def _json(o):
    return o.model_dump(mode="json") if isinstance(o, BaseModel) else str(o)


def draft(items: list[dict], case_id: str) -> DraftOut:
    return call_json("reason", SYSTEM, json.dumps(items, indent=1, default=_json), DraftOut, case_id)


def render(n: Notice, replies: list[GroundReply], needs_ca: list[Ground], today: date) -> str:
    """Code owns header, footer and needs-CA grounds; the model writes only ground replies."""
    body = {r.ground_no: r.text.strip() for r in replies}
    for g in needs_ca:
        body[g.ground_no] = ("This ground is under review with our tax consultant. "
                             "A detailed reply with supporting documents will be furnished separately.")
    lines = [
        f"[{BANNER}]", "", "FORM GST ASMT-11", "[See rule 99(2)]",
        "Reply to the notice issued under section 61 intimating discrepancies in the return", "",
        f"GSTIN: {n.gstin}", f"Reference No. of notice: {n.notice_ref}",
        f"Date of notice: {n.issue_date:%d/%m/%Y}", f"Financial year: {n.financial_year}", f"Date: {today:%d/%m/%Y}", "",
        "Reply to the discrepancies:", "",
    ]
    for no in sorted(body):
        lines += [f"Ground {no}:", body[no], ""]
    lines += ["We request that the proceedings be dropped in view of the above.", "",
              "Authorised Signatory", "", f"[{BANNER}]"]
    return "\n".join(lines)

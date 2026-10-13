"""Case lifecycle shared by the API and the CLI: create -> analyse grounds -> confirm facts -> draft -> (edit) verify.

CLI, from backend/:  python -m app.pipeline.case ../samples/jawab/case_b --paid-on 2025-11-10
"""
import argparse
import time
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, computed_field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.interest import interest
from app.domain.reconcile import ReconResult, assess, reconcile_ground
from app.domain.returns import load_gstr1, load_gstr2b, load_gstr3b
from app.models import HEADS, Case, Ground, LlmCall, Notice, TaxAmount, engine, init_db
from app.pipeline.draft import draft, render
from app.pipeline.explain import Cause, explain
from app.pipeline.extract import extract_notice
from app.pipeline.ingest import ingest
from app.pipeline.research import research
from app.pipeline.verify import Issue, allowed_amounts, verify
from app.research.tavily import case_sources


def _total(a: TaxAmount | None) -> Decimal | None:
    return sum(getattr(a, h) for h in HEADS) if a else None


class GroundState(BaseModel):
    ground: Ground
    status: Literal["explained", "partly_explained", "payable", "needs_ca"]
    recon: ReconResult | None = None
    payable: TaxAmount | None = None
    interest: TaxAmount | None = None
    analysed: bool = False
    causes: list[Cause] = []         # suggestions from the agent
    confirmed: list[str] = []        # facts the user confirmed; only these reach the draft
    source_ids: list[int] = []

    @computed_field
    def payable_total(self) -> Decimal | None:
        return _total(self.payable)

    @computed_field
    def interest_total(self) -> Decimal | None:
        return _total(self.interest)


class CaseState(BaseModel):
    id: str
    notice: Notice
    grounds: list[GroundState]
    paid_on: date | None = None
    draft: str | None = None
    issues: list[Issue] = []


# ---------- storage ----------

def save(c: CaseState) -> CaseState:
    init_db()
    with Session(engine) as s:
        s.merge(Case(id=c.id, data=c.model_dump_json()))
        s.commit()
    return c


def load(case_id: str) -> CaseState:
    init_db()
    with Session(engine) as s:
        row = s.get(Case, case_id)
    if row is None:
        raise KeyError(case_id)
    return CaseState.model_validate_json(row.data)


def list_cases() -> list[CaseState]:
    init_db()
    with Session(engine) as s:
        return [CaseState.model_validate_json(d) for d in s.scalars(select(Case.data).order_by(Case.created_at.desc()))]


def cost(case_id: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.execute(select(LlmCall.tier, func.count(), func.sum(LlmCall.input_tokens),
                                func.sum(LlmCall.output_tokens), func.sum(LlmCall.cost))
                         .where(LlmCall.case_id == case_id).group_by(LlmCall.tier)).all()
    return [{"tier": t, "calls": n, "input_tokens": i, "output_tokens": o, "cost": c} for t, n, i, o, c in rows]


# ---------- steps ----------

def create(notice_bytes: bytes, notice_name: str, gstr1, gstr3b, gstr2b, case_id: str | None = None) -> CaseState:
    case_id = case_id or uuid.uuid4().hex[:10]
    r1, b3, b2 = load_gstr1(gstr1), load_gstr3b(gstr3b), load_gstr2b(gstr2b)  # fail fast on bad CSVs
    notice = extract_notice(ingest(notice_bytes, notice_name, case_id), case_id)
    grounds = []
    for g in notice.grounds:
        rec = reconcile_ground(g, r1, b3, b2)
        if rec is None:
            grounds.append(GroundState(ground=g, status="needs_ca"))
            continue
        status, payable = assess(rec)
        grounds.append(GroundState(ground=g, status=status, recon=rec, payable=payable,
                                   confirmed=[e.text for e in rec.evidence]))  # document facts from returns
    return save(CaseState(id=case_id, notice=notice, grounds=grounds))


def _ground(c: CaseState, n: int) -> GroundState:
    gs = next((g for g in c.grounds if g.ground.ground_no == n), None)
    if gs is None or gs.recon is None:
        raise KeyError(f"ground {n} not found or needs CA review")
    return gs


def analyse(c: CaseState, n: int) -> CaseState:
    gs = _ground(c, n)
    gs.causes = explain(gs.ground, gs.recon, gs.status, c.id).causes
    gs.source_ids = [s.id for s in research(c.id, gs.ground)]
    gs.analysed = True
    return save(c)


def confirm(c: CaseState, n: int, facts: list[str]) -> CaseState:
    _ground(c, n).confirmed = facts
    return save(c)


def make_draft(c: CaseState, paid_on: date) -> CaseState:
    for gs in c.grounds:
        if gs.recon and not gs.analysed:
            analyse(c, gs.ground.ground_no)
    sources = {s.id: s for s in case_sources(c.id)}
    c.paid_on, items = paid_on, []
    for gs in c.grounds:
        if gs.recon is None:
            continue
        gs.interest = interest(gs.payable, gs.ground.tax_period, paid_on) if gs.payable else None
        items.append({
            "ground_no": gs.ground.ground_no, "officer_wording": gs.ground.description,
            "tax_period": gs.ground.tax_period, "status": gs.status, "officer_amount": gs.ground.officer_amount,
            "our_amount": gs.recon.our_amount, "net_over_financial_year": gs.recon.fy_net,
            "confirmed_facts": gs.confirmed, "payable_tax": gs.payable, "payable_total": gs.payable_total,
            "interest_section_50": gs.interest, "interest_total": gs.interest_total,
            "payment_date": paid_on if gs.payable else None,
            "sources": [{"id": i, "title": sources[i].title, "snippet": sources[i].content[:600]} for i in gs.source_ids],
        })
    replies = draft(items, c.id).grounds if items else []
    c.draft = render(c.notice, replies, [gs.ground for gs in c.grounds if gs.recon is None], date.today())
    return reverify(c, c.draft)


def reverify(c: CaseState, text: str) -> CaseState:
    c.draft = text
    allowed = allowed_amounts(c.notice, *[[g.recon, g.payable, g.interest, g.payable_total, g.interest_total]
                                          for g in c.grounds])
    c.issues = verify(text, allowed, case_sources(c.id))
    return save(c)


def run(case_dir: Path, paid_on: date, case_id: str | None = None) -> CaseState:
    """Whole case, auto-confirming every suggested cause (CLI and tests; the UI confirms per fact)."""
    notice = next(p for p in case_dir.iterdir() if p.stem == "notice" and p.suffix != ".txt")
    c = create(notice.read_bytes(), notice.name, case_dir / "gstr1.csv", case_dir / "gstr3b.csv",
               case_dir / "gstr2b.csv", case_id)
    for gs in c.grounds:
        if gs.recon:
            analyse(c, gs.ground.ground_no)
            gs.confirmed += [x.why for x in gs.causes]
    return make_draft(c, paid_on)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir", type=Path)
    ap.add_argument("--paid-on", type=date.fromisoformat, default=date.today(), help="DRC-03 payment date")
    a = ap.parse_args()
    t = time.time()
    c = run(a.case_dir, a.paid_on)
    print(c.draft)
    print("\n--- grounds")
    for g in c.grounds:
        print(f"  {g.ground.ground_no}: {g.status} payable={g.payable_total} interest={g.interest_total}")
    print(f"--- verifier: {len(c.issues)} issue(s)")
    for i in c.issues:
        print(f"  {i.kind}: {i.value}")
    print(f"--- case {c.id}: {cost(c.id)}, {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()

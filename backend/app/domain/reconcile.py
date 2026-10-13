"""Deterministic reconciliation. Discrepancy sign matches the officer's: positive = against the taxpayer."""
from decimal import Decimal

import pandas as pd
from pydantic import BaseModel

from app.models import HEADS, Ground, TaxAmount


class Evidence(BaseModel):
    text: str                      # document-level fact from the returns, no amounts
    amount: TaxAmount


class ReconResult(BaseModel):
    ground_no: int
    our_amount: TaxAmount          # discrepancy recomputed from the returns
    difference: TaxAmount          # officer_amount - our_amount
    fy_net: TaxAmount              # discrepancy netted over the FY (timing differences cancel out)
    periods: list[dict]            # per-month discrepancy for the FY, for the UI and the explain step
    evidence: list[Evidence]       # later-period documents that offset this period


def fy_of(period: str) -> str:
    y, m = map(int, period.split("-"))
    start = y if m >= 4 else y - 1
    return f"FY{start}-{str(start + 1)[2:]}"


def _by_period(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("period")[list(HEADS)].sum()


def discrepancy(category: str, r1, b3, b2) -> pd.DataFrame:
    if category == "output_tax_r1_vs_3b":
        a, b = _by_period(r1), _by_period(b3[b3.section == "output"])
    elif category == "itc_2b_vs_3b":
        a, b = _by_period(b3[b3.section == "itc"]), _by_period(b2)
    else:
        raise ValueError(category)
    return a.sub(b, fill_value=Decimal(0)).sort_index()


def _amt(row, sign: int = 1) -> TaxAmount:
    return TaxAmount(**{h: sign * Decimal(str(row[h])) for h in HEADS})


def _evidence(g: Ground, r1, b2) -> list[Evidence]:
    fy = fy_of(g.tax_period)
    later = lambda df: df[(df.period > g.tax_period) & (df.period.map(fy_of) == fy)]
    if g.category == "output_tax_r1_vs_3b":
        return [Evidence(text=f"Credit note {r.doc_no} dated {r.doc_date} reported in GSTR-1 for {r.period}",
                         amount=_amt(r._asdict(), -1))  # stored negative by load_gstr1
                for r in later(r1[r1.doc_type == "CRN"]).itertuples()]
    return [Evidence(text=f"Invoice {r.invoice_no} dated {r.invoice_date} from supplier {r.supplier_gstin} "
                          f"appears in GSTR-2B for {r.period} (supplier filed late)", amount=_amt(r._asdict()))
            for r in later(b2[b2.invoice_date.str.startswith(g.tax_period)]).itertuples()]


def reconcile_ground(g: Ground, r1, b3, b2) -> ReconResult | None:
    if g.category == "other":
        return None
    is_fy = g.tax_period.startswith("FY")
    fy = g.tax_period if is_fy else fy_of(g.tax_period)
    d = discrepancy(g.category, r1, b3, b2)
    d = d[[fy_of(p) == fy for p in d.index]]
    fy_net = _amt(d.sum()) if len(d) else TaxAmount()
    if is_fy:
        ours = fy_net
    else:
        ours = _amt(d.loc[g.tax_period]) if g.tax_period in d.index else TaxAmount()
    return ReconResult(
        ground_no=g.ground_no, our_amount=ours, difference=g.officer_amount - ours, fy_net=fy_net,
        periods=[{"period": p, **_amt(r).model_dump()} for p, r in d.iterrows()],
        evidence=[] if is_fy else _evidence(g, r1, b2),
    )


def assess(r: ReconResult) -> tuple[str, TaxAmount | None]:
    """Status and payable tax. Payable = what stays unexplained after the FY nets out, capped at our figure."""
    pos = lambda a, h: max(getattr(a, h), Decimal(0))
    payable = TaxAmount(**{h: min(pos(r.fy_net, h), pos(r.our_amount, h)) for h in HEADS})
    if payable == TaxAmount():
        return "explained", None
    if payable == TaxAmount(**{h: pos(r.our_amount, h) for h in HEADS}):
        return "payable", payable
    return "partly_explained", payable

"""Deterministic reconciliation. Discrepancy sign matches the officer's: positive = against the taxpayer."""
from decimal import Decimal

import pandas as pd
from pydantic import BaseModel

from app.models import HEADS, Ground, TaxAmount


class ReconResult(BaseModel):
    ground_no: int
    our_amount: TaxAmount          # discrepancy recomputed from the returns
    difference: TaxAmount          # officer_amount - our_amount
    fy_net: TaxAmount              # discrepancy netted over the FY (timing differences cancel out)
    periods: list[dict]            # per-month discrepancy for the FY, for the UI and the explain step


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


def _amt(row) -> TaxAmount:
    return TaxAmount(**{h: Decimal(str(row[h])) for h in HEADS})


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
    )

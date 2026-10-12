"""Load GSTR-1, GSTR-3B and GSTR-2B CSV templates (see samples/jawab)."""
from decimal import Decimal

import pandas as pd

from app.models import HEADS

COLUMNS = {
    "gstr1": ["period", "doc_type", "doc_no", "doc_date", *HEADS],
    "gstr3b": ["period", "section", *HEADS],
    "gstr2b": ["period", "supplier_gstin", "invoice_no", "invoice_date", *HEADS],
}


def _load(src, kind: str) -> pd.DataFrame:
    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    missing = set(COLUMNS[kind]) - set(df.columns)
    if missing:
        raise ValueError(f"{kind}: missing columns {sorted(missing)}")
    for h in HEADS:
        df[h] = df[h].map(lambda v: Decimal(v.replace(",", "") or "0"))
    return df


def load_gstr1(src) -> pd.DataFrame:
    df = _load(src, "gstr1")
    bad = set(df.doc_type) - {"INV", "CRN", "DBN"}
    if bad:
        raise ValueError(f"gstr1: unknown doc_type {sorted(bad)}")
    crn = df.doc_type == "CRN"  # credit notes are entered positive and reduce tax
    for h in HEADS:
        df.loc[crn, h] = df.loc[crn, h].map(lambda v: -v)
    return df


def load_gstr3b(src) -> pd.DataFrame:
    df = _load(src, "gstr3b")
    bad = set(df.section) - {"output", "itc"}
    if bad:
        raise ValueError(f"gstr3b: unknown section {sorted(bad)}")
    return df


def load_gstr2b(src) -> pd.DataFrame:
    return _load(src, "gstr2b")

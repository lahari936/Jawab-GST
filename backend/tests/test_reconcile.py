import json
from decimal import Decimal

import pytest

from app.domain.reconcile import fy_of, reconcile_ground
from app.domain.returns import load_gstr1, load_gstr2b, load_gstr3b
from app.models import Notice, TaxAmount
from conftest import SAMPLES


def run(case: str, ground_no: int = 1):
    d = SAMPLES / case
    exp = json.loads((d / "expected.json").read_text())
    for g in exp["grounds"]:
        g["description"] = "x"
    g = next(g for g in Notice.model_validate(exp).grounds if g.ground_no == ground_no)
    return reconcile_ground(g, load_gstr1(d / "gstr1.csv"), load_gstr3b(d / "gstr3b.csv"), load_gstr2b(d / "gstr2b.csv"))


def amt(**kw):
    return TaxAmount(**{k: Decimal(v) for k, v in kw.items()})


def test_fy_of():
    assert fy_of("2024-04") == "FY2024-25"
    assert fy_of("2025-03") == "FY2024-25"


def test_case_a_credit_note_timing():
    r = run("case_a")
    assert r.our_amount == amt(igst=18000)
    assert r.difference == TaxAmount()
    assert r.fy_net == TaxAmount()  # August credit note offsets July fully
    assert [p["period"] for p in r.periods] == ["2024-07", "2024-08", "2024-09"]
    assert r.periods[1]["igst"] == Decimal(-18000)


def test_case_a_other_ground_not_reconciled():
    assert run("case_a", 2) is None


def test_case_b_itc_partly_genuine():
    r = run("case_b")
    assert r.our_amount == amt(cgst=6000, sgst=6000)
    assert r.difference == TaxAmount()
    assert r.fy_net == amt(cgst=4500, sgst=4500)  # late filer offsets 1500; non-filer 4500 stays


def test_case_c_genuine_short_payment():
    r = run("case_c")
    assert r.our_amount == amt(cgst=3000, sgst=3000)
    assert r.fy_net == amt(cgst=3000, sgst=3000)


def test_bad_csv_rejected(tmp_path):
    p = tmp_path / "r1.csv"
    p.write_text("period,igst\n2024-07,1\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_gstr1(p)

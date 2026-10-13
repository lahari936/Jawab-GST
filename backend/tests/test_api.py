from fastapi.testclient import TestClient

from app.main import app
from conftest import SAMPLES
from test_run import fake_llm

api = TestClient(app)


def test_upload_flow(monkeypatch):
    fake_llm(monkeypatch)
    d = SAMPLES / "case_b"
    files = {k: (f"{k}.csv", (d / f"{k}.csv").read_bytes()) for k in ("gstr1", "gstr3b", "gstr2b")}
    files["notice"] = ("notice.pdf", (d / "notice.pdf").read_bytes())
    r = api.post("/cases", files=files)
    assert r.status_code == 200, r.text
    cid = r.json()["case"]["id"]

    v = api.post(f"/cases/{cid}/grounds/1/analyse").json()
    assert v["sources"][0]["url"] == "https://cbic-gst.gov.in/x.pdf"
    api.put(f"/cases/{cid}/grounds/1/confirmed", json={"facts": ["Supplier filed late."]})
    v = api.post(f"/cases/{cid}/draft", json={"paid_on": "2025-11-10"}).json()
    assert v["case"]["grounds"][0]["interest_total"] == "1714"
    assert [i["value"] for i in v["case"]["issues"]] == ["Rs. 1,234"]

    row = next(c for c in api.get("/cases").json() if c["id"] == cid)
    assert row["issues"] == 1 and row["has_draft"]


def test_errors():
    assert api.get("/cases/nope").status_code == 404
    assert api.post("/cases/sample/../../etc").status_code == 404
    d = SAMPLES / "case_b"
    bad = {"notice": ("n.pdf", (d / "notice.pdf").read_bytes()), "gstr1": ("g.csv", b"period,igst\n2024-07,1\n"),
           "gstr3b": ("g.csv", (d / "gstr3b.csv").read_bytes()), "gstr2b": ("g.csv", (d / "gstr2b.csv").read_bytes())}
    r = api.post("/cases", files=bad)
    assert r.status_code == 400 and "missing columns" in r.text

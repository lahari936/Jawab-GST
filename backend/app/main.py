import io
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.pipeline import case
from app.research.tavily import case_sources

SAMPLES = Path(os.environ.get("SAMPLES_DIR", Path(__file__).resolve().parents[2] / "samples" / "jawab"))
MAX_UPLOAD = 10 * 1024 * 1024

app = FastAPI(title="Jawab")
# ponytail: open CORS, no auth; lock to the frontend origin before real users.
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


def _view(c: case.CaseState) -> dict:
    srcs = case_sources(c.id)
    return {"case": c.model_dump(mode="json"),
            "sources": [{"id": s.id, "ground_no": s.ground_no, "title": s.title, "url": s.url,
                         "snippet": s.content[:400]} for s in srcs],
            "cost": case.cost(c.id)}


def _load(case_id: str) -> case.CaseState:
    try:
        return case.load(case_id)
    except KeyError:
        raise HTTPException(404, "case not found")


def _step(fn, *args):
    try:
        return _view(fn(*args))
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.get("/cases")
def list_cases():
    today = date.today()
    return [{"id": c.id, "gstin": c.notice.gstin, "notice_ref": c.notice.notice_ref,
             "reply_due_date": c.notice.reply_due_date, "days_left": (c.notice.reply_due_date - today).days,
             "statuses": [g.status for g in c.grounds], "has_draft": c.draft is not None,
             "issues": len(c.issues), "cost": sum(r["cost"] or 0 for r in case.cost(c.id))}
            for c in case.list_cases()]


async def _read(f: UploadFile) -> bytes:
    data = await f.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, f"{f.filename} is over 10 MB")
    return data


@app.post("/cases")
async def create_case(notice: UploadFile, gstr1: UploadFile, gstr3b: UploadFile, gstr2b: UploadFile):
    files = [await _read(f) for f in (notice, gstr1, gstr3b, gstr2b)]
    return _step(case.create, files[0], notice.filename or "", *(io.BytesIO(b) for b in files[1:]))


@app.post("/cases/sample/{name}")
def create_sample(name: str):
    d = SAMPLES / name
    if name not in {"case_a", "case_b", "case_c"} or not d.is_dir():
        raise HTTPException(404, "unknown sample")
    notice = next(p for p in d.iterdir() if p.stem == "notice" and p.suffix != ".txt")
    return _step(case.create, notice.read_bytes(), notice.name, d / "gstr1.csv", d / "gstr3b.csv", d / "gstr2b.csv")


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    return _view(_load(case_id))


@app.post("/cases/{case_id}/grounds/{n}/analyse")
def analyse(case_id: str, n: int):
    return _step(case.analyse, _load(case_id), n)


class Facts(BaseModel):
    facts: list[str]


@app.put("/cases/{case_id}/grounds/{n}/confirmed")
def confirm(case_id: str, n: int, body: Facts):
    return _step(case.confirm, _load(case_id), n, body.facts)


class DraftReq(BaseModel):
    paid_on: date


@app.post("/cases/{case_id}/draft")
def make_draft(case_id: str, body: DraftReq):
    return _step(case.make_draft, _load(case_id), body.paid_on)


class DraftText(BaseModel):
    text: str


@app.put("/cases/{case_id}/draft")
def edit_draft(case_id: str, body: DraftText):
    return _step(case.reverify, _load(case_id), body.text)

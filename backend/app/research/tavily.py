import os
from functools import cache

from sqlalchemy import select
from sqlalchemy.orm import Session
from tavily import TavilyClient

from app.models import Source, engine, init_db

GST_DOMAINS = ["cbic-gst.gov.in", "gst.gov.in", "indiacode.nic.in"]


@cache
def _tv() -> TavilyClient:
    return TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def search_official(query: str, domains: list[str] = GST_DOMAINS) -> list[dict]:
    res = _tv().search(query=query, include_domains=domains, search_depth="advanced", max_results=5)
    return [{"title": r["title"], "url": r["url"], "content": r["content"]} for r in res["results"]]


def save_sources(case_id: str, ground_no: int, query: str, results: list[dict]) -> list[Source]:
    init_db()
    with Session(engine, expire_on_commit=False) as s:
        rows = [Source(case_id=case_id, ground_no=ground_no, query=query, **r) for r in results]
        s.add_all(rows)
        s.commit()
    return rows


def case_sources(case_id: str) -> list[Source]:
    init_db()
    with Session(engine) as s:
        return list(s.scalars(select(Source).where(Source.case_id == case_id)))

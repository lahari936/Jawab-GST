"""Code-only verifier: every amount must come from computed output, every citation and URL from the sources table."""
import re
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel

from app.models import HEADS, Source, TaxAmount

AMOUNT = re.compile(r"(?:Rs\.?|₹|INR)\s*([\d,]+(?:\.\d+)?)")
CITE = re.compile(r"\[S(\d+)\]")
URL = re.compile(r"https?://[^\s\])>,;]*[^\s\])>,;.]")  # no trailing "."


class Issue(BaseModel):
    kind: Literal["number", "citation", "url"]
    value: str
    start: int
    end: int


def allowed_amounts(*objs) -> set[Decimal]:
    """Every amount in the given computed output (nested TaxAmount/dict/list/Decimal), its abs value and head totals."""
    out: set[Decimal] = set()

    def walk(o):
        if isinstance(o, TaxAmount):
            out.add(abs(sum(getattr(o, h) for h in HEADS)))
            o = o.model_dump()
        if isinstance(o, dict):
            o = list(o.values())
        if isinstance(o, (list, tuple)):
            for x in o:
                walk(x)
        elif isinstance(o, Decimal):
            out.add(abs(o))
        elif hasattr(o, "model_dump"):
            walk(o.__dict__)

    for o in objs:
        walk(o)
    return out


def verify(text: str, allowed: set[Decimal], sources: list[Source]) -> list[Issue]:
    issues = []
    for m in AMOUNT.finditer(text):
        try:
            ok = Decimal(m.group(1).replace(",", "").rstrip(".")) in allowed
        except InvalidOperation:
            ok = False
        if not ok:
            issues.append(Issue(kind="number", value=m.group(0), start=m.start(), end=m.end()))
    ids = {s.id for s in sources}
    issues += [Issue(kind="citation", value=m.group(0), start=m.start(), end=m.end())
               for m in CITE.finditer(text) if int(m.group(1)) not in ids]
    urls = {s.url for s in sources}
    issues += [Issue(kind="url", value=m.group(0), start=m.start(), end=m.end())
               for m in URL.finditer(text) if m.group(0) not in urls]
    return issues

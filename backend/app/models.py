import os
from datetime import date, datetime
from decimal import Decimal
from functools import cache
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, Numeric, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------- Pydantic (LLM outputs and domain) ----------

HEADS = ("igst", "cgst", "sgst", "cess")


class TaxAmount(BaseModel):
    igst: Decimal = Decimal(0)
    cgst: Decimal = Decimal(0)
    sgst: Decimal = Decimal(0)
    cess: Decimal = Decimal(0)

    def __sub__(self, other: "TaxAmount") -> "TaxAmount":
        return TaxAmount(**{h: getattr(self, h) - getattr(other, h) for h in HEADS})


class Ground(BaseModel):
    ground_no: int
    category: Literal["output_tax_r1_vs_3b", "itc_2b_vs_3b", "other"]
    description: str          # officer's wording, verbatim
    tax_period: str           # "2024-04" or "FY2024-25"
    officer_amount: TaxAmount


class Notice(BaseModel):
    gstin: str
    notice_ref: str
    form: Literal["ASMT-10"]
    issue_date: date
    reply_due_date: date | None   # if missing, code computes issue_date + 30 days and flags it
    due_date_computed: bool = False
    financial_year: str
    grounds: list[Ground]


# ---------- SQLAlchemy ----------

engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///jawab.db"))


class Base(DeclarativeBase):
    pass


class LlmCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    tier: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Source(Base):
    """A Tavily result. Drafts may cite only rows from this table, as [S<id>]."""
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String, index=True)
    ground_no: Mapped[int] = mapped_column(Integer)
    query: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Case(Base):
    """Whole case state (app.pipeline.case.CaseState) as JSON; small enough per case to not need columns."""
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


@cache
def init_db():
    Base.metadata.create_all(engine)

"""Interest under Section 50 CGST Act. Verify rate and method against the Act before the demo."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.models import HEADS, TaxAmount

RATE = Decimal("0.18")  # 50(1) late payment; 50(3) ITC wrongly availed and utilised is also 18%


def payment_due_date(period: str) -> date:
    # ponytail: monthly filer, GSTR-3B due 20th of next month; QRMP filers (22nd/24th) not handled.
    # For ITC this also assumes the credit was utilised on that date (rule 88B(3) allows a later date).
    y, m = map(int, period.split("-"))
    return date(y + m // 12, m % 12 + 1, 20)


def interest(tax: TaxAmount, period: str, paid_on: date) -> TaxAmount:
    days = max((paid_on - payment_due_date(period)).days, 0)
    return TaxAmount(**{
        h: (getattr(tax, h) * RATE * days / 365).quantize(Decimal(1), ROUND_HALF_UP) for h in HEADS
    })

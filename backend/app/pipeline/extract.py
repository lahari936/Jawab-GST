from datetime import timedelta

from app.llm.client import call_json
from app.models import Notice

SYSTEM = """You read Indian GST notices. Extract each discrepancy ground exactly as the officer wrote it.
Copy amounts digit for digit as plain numbers without commas or currency symbols. If a field is not in the text, use null. Do not infer.
category: "output_tax_r1_vs_3b" if tax in GSTR-1 exceeds GSTR-3B; "itc_2b_vs_3b" if ITC in GSTR-3B exceeds GSTR-2B; otherwise "other".
tax_period: "YYYY-MM" for a month, "FY2024-25" style for a whole year. financial_year: "2024-25" style. Dates: YYYY-MM-DD."""


def extract_notice(text: str, case_id: str) -> Notice:
    n = call_json("fast", SYSTEM, text, Notice, case_id)
    n.due_date_computed = n.reply_due_date is None
    if n.due_date_computed:
        n.reply_due_date = n.issue_date + timedelta(days=30)
    return n

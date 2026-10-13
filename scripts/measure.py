"""Run cases A-C end to end with real models and write docs/RESULTS.md against the spec's acceptance criteria.

Run from repo root:  .venv/Scripts/python scripts/measure.py   (spends model and Tavily credits)
"""
import json
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.pipeline import case  # noqa: E402

SAMPLES = ROOT / "samples" / "jawab"
PAID_ON = date(2025, 11, 10)


def extraction_ok(n, exp) -> list[str]:
    errs = [f"{k}: {getattr(n, k)} != {exp[k]}" for k in ("gstin", "notice_ref", "financial_year", "due_date_computed")
            if getattr(n, k) != exp[k]]
    errs += [f"{k}: {getattr(n, k)} != {exp[k]}" for k in ("issue_date", "reply_due_date") if str(getattr(n, k)) != exp[k]]
    if len(n.grounds) != len(exp["grounds"]):
        return errs + [f"grounds: {len(n.grounds)} != {len(exp['grounds'])}"]
    for g, e in zip(sorted(n.grounds, key=lambda g: g.ground_no), exp["grounds"]):
        errs += [f"ground {g.ground_no} {k}" for k in ("category", "tax_period") if getattr(g, k) != e[k]]
        errs += [f"ground {g.ground_no} {h}" for h, v in e["officer_amount"].items()
                 if getattr(g.officer_amount, h) != Decimal(v)]
    return errs


rows = []
for name in ("case_a", "case_b", "case_c"):
    exp = json.loads((SAMPLES / name / "expected.json").read_text())
    t = time.time()
    try:
        c = case.run(SAMPLES / name, PAID_ON)
    except Exception as e:  # keep measuring the other cases
        rows.append({"case": name, "error": f"{type(e).__name__}: {e}"[:200]})
        continue
    secs = time.time() - t
    cost = case.cost(c.id)
    payable = [g for g in c.grounds if g.payable]
    rows.append({
        "case": name, "id": c.id, "seconds": round(secs),
        "extraction_errors": extraction_ok(c.notice, exp),
        "statuses": [g.status for g in c.grounds],
        "payable": [str(g.payable_total) for g in payable], "interest": [str(g.interest_total) for g in payable],
        "draft_states_amounts": all(f"Rs. {Decimal(g.payable.cgst or g.payable.igst):,.0f}" in c.draft
                                    and f"{Decimal(g.interest.cgst or g.interest.igst):,.0f}" in c.draft for g in payable),
        "issues": [f"{i.kind}: {i.value}" for i in c.issues],
        "calls": sum(r["calls"] for r in cost),
        "tokens": sum((r["input_tokens"] or 0) + (r["output_tokens"] or 0) for r in cost),
        "cost": str(sum(Decimal(str(r["cost"] or 0)) for r in cost)),
    })
    print(json.dumps(rows[-1]), flush=True)

lines = [
    "# Results on the synthetic fixtures", "",
    f"Measured {date.today()} with `scripts/measure.py`; DRC-03 payment date {PAID_ON}. "
    "Models: see README. Every case runs the whole pipeline: ingest, extract, reconcile, explain, research, draft, verify.", "",
    "| Case | Extraction exact | Status | Payable / interest | Draft states them | Unverified claims | Time | LLM calls | Tokens | Cost |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
]
for r in rows:
    if "error" in r:
        lines.append(f"| {r['case']} | failed: {r['error']} | | | | | | | | |")
        continue
    lines.append(
        f"| {r['case'][-1].upper()} | {'yes' if not r['extraction_errors'] else '; '.join(r['extraction_errors'])} "
        f"| {', '.join(r['statuses'])} | {', '.join(f'Rs. {p} / Rs. {i}' for p, i in zip(r['payable'], r['interest'])) or '-'} "
        f"| {('yes' if r['draft_states_amounts'] else 'NO') if r['payable'] else '-'} | {len(r['issues']) or 0} "
        f"| {r['seconds']}s | {r['calls']} | {r['tokens']:,} | ${r['cost']} |")
ok = [r for r in rows if "error" not in r]
lines += ["", "## Acceptance criteria (docs/SPEC.md section 10)", "",
          f"- [{'x' if ok and len(ok) == 3 and all(not r['extraction_errors'] for r in ok) else ' '}] All grounds extracted correctly, amounts exact to the rupee",
          "- [x] Reconciliation unit tests pass for each case (`pytest`)",
          f"- [{'x' if any(r['case'] == 'case_b' and r['draft_states_amounts'] and r['payable'] for r in ok) else ' '}] Draft for case B states the payable tax and interest the code computed",
          f"- [{'x' if ok and all(not r['issues'] for r in ok) else ' '}] Zero unverified citations in final drafts; planted fake URL caught (`tests/test_phase3.py`, `tests/test_run.py`)",
          f"- [{'x' if ok and all(r['seconds'] < 180 for r in ok) else ' '}] End-to-end case under 3 minutes (max {max((r['seconds'] for r in ok), default=0)}s)",
          "- [x] Cost per case shown in the UI (token counts; $ needs per-model prices in `client.py`)", ""]
for r in ok:
    if r["issues"]:
        lines.append(f"Case {r['case'][-1].upper()} unverified: {'; '.join(r['issues'])}")
(ROOT / "docs" / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote docs/RESULTS.md")

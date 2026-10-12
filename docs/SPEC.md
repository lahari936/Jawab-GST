# Jawab — GST Notice Responder: Implementation Spec

Hackathon: Nebius x NVIDIA Global AI Hackathon · Track: Best Apps and Agents (+ Best Use of Tavily)
Deadline: 30 Oct 2026, 10:30 pm IST

Jawab turns an ASMT-10 scrutiny notice plus the business's return data into a reviewed, cited ASMT-11 reply.
Hackathon scope: ASMT-10 only, and the two most common grounds (output tax mismatch, ITC mismatch). Anything else is marked "needs CA review".

---

## 1. How to use this with Claude Code

1. Save this file in an empty repo as `docs/SPEC.md`.
2. Create `CLAUDE.md` at the repo root with the block below.
3. Run Claude Code phase by phase using the prompts in section 8. Review and commit after each phase.

```markdown
# CLAUDE.md
Read docs/SPEC.md before any task. Project: Jawab (GST Notice Responder).
Rules:
- All LLM calls go through backend/app/llm/client.py; never call the API directly elsewhere.
- Arithmetic and date maths happen in Python, never in an LLM prompt.
- Every citation in generated text must come from a Tavily result stored in the sources table.
- Pydantic models for every LLM output; validate and retry once on failure.
- Write tests with each module. Run `pytest` before saying a phase is done.
- Never commit .env or real documents. Sample files go in /samples and must be synthetic.
```

---

## 2. Stack

| Layer | Choice | Why |
| --- | --- | --- |
| LLM | Nemotron on Nebius Token Factory (OpenAI-compatible API) | Hackathon requirement |
| Web research | Tavily Search API | Live official sources; Tavily prize |
| Backend | Python 3.12, FastAPI, Pydantic v2, pandas | Typed LLM outputs; deterministic reconciliation |
| Document input | PyMuPDF for digital PDFs; Nemotron 3 Nano Omni for scans/photos | No separate OCR service |
| Database | PostgreSQL | Cases, grounds, sources, LLM call log |
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui | Polished UI for the Design score |
| Deploy | Backend container on Nebius Serverless Endpoints; frontend on Vercel | Shows Nebius beyond Token Factory |

## 3. Model routing

Check these IDs against your Token Factory catalog before coding; the catalog changes.

| Tier | Step | Model ID |
| --- | --- | --- |
| vision | Read scanned notices, photos | `nvidia/Nemotron-3-Nano-Omni` (confirm image input) |
| fast | Extract notice fields, classify grounds, verify | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| agent | Explain grounds, research tool calls | `nvidia/nemotron-3-super-120b-a12b` |
| reason | Draft the ASMT-11 reply | `nvidia/Nemotron-3-Ultra-550b-a55b` |

**Known catch:** Nemotron models on Token Factory are reasoning models. Clients that read only `message.content` can get empty output (reported in a Nebius GitHub issue, May 2026). Log the raw response on day 1 and handle both fields.

## 4. Shared code

### LLM client (the only place that calls the API)

```python
# backend/app/llm/client.py
import os
from openai import OpenAI
from pydantic import BaseModel, ValidationError

client = OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])

MODELS = {
    "vision": os.environ["MODEL_VISION"],
    "fast": os.environ["MODEL_FAST"],
    "agent": os.environ["MODEL_AGENT"],
    "reason": os.environ["MODEL_REASON"],
}

def _text(msg) -> str:
    # Reasoning models may leave content empty; fall back to the reasoning field.
    return msg.content or getattr(msg, "reasoning_content", None) or ""

def call_json(tier: str, system: str, user: str, schema: type[BaseModel], case_id: str):
    for _ in range(2):
        r = client.chat.completions.create(
            model=MODELS[tier],
            messages=[{"role": "system", "content": system + "\nReturn only JSON matching the schema."},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        log_usage(case_id, tier, r.usage)  # writes tokens and cost to llm_calls
        try:
            return schema.model_validate_json(_text(r.choices[0].message))
        except ValidationError as e:
            user += f"\n\nYour last output failed validation: {e}. Fix it."
    raise RuntimeError("LLM output invalid after retry")
```

The `llm_calls` table (case_id, tier, model, input_tokens, output_tokens, cost) feeds a "cost per case" panel. Show it in the video.

### Research helper

```python
# backend/app/research/tavily.py
import os
from tavily import TavilyClient
tv = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

GST_DOMAINS = ["cbic-gst.gov.in", "gst.gov.in", "indiacode.nic.in"]

def search_official(query: str, domains: list[str] = GST_DOMAINS) -> list[dict]:
    res = tv.search(query=query, include_domains=domains, search_depth="advanced", max_results=5)
    return [{"title": r["title"], "url": r["url"], "content": r["content"]} for r in res["results"]]
```

Store every result in the `sources` table linked to the case. The drafting step may cite only rows from that table.

### Repo layout

```
repo/
  CLAUDE.md  LICENSE (MIT)  README.md  docker-compose.yml  .env.example
  docs/SPEC.md
  backend/app/
    main.py            # FastAPI routes
    llm/client.py
    research/tavily.py
    pipeline/          # ingest, extract, explain, research, draft, verify
    domain/            # returns.py, reconcile.py, interest.py
    models.py          # Pydantic + SQLAlchemy
  backend/tests/
  frontend/            # Next.js app
  samples/jawab/       # synthetic demo files only
```

### Environment variables

`NEBIUS_BASE_URL`, `NEBIUS_API_KEY`, `MODEL_VISION`, `MODEL_FAST`, `MODEL_AGENT`, `MODEL_REASON`, `TAVILY_API_KEY`, `DATABASE_URL`, `NEXT_PUBLIC_API_URL`.

Base URL: use the one in your Nebius console (e.g. `https://api.tokenfactory.nebius.com/v1/` or `https://api.tokenfactory.us-central1.nebius.com/v1/`).

---

## 5. Pipeline

1. **Ingest** (`pipeline/ingest.py`): digital PDF → PyMuPDF text. Scan or photo → Nano Omni, prompt "transcribe this notice verbatim".
2. **Extract notice** (`pipeline/extract.py`, fast): text → `Notice` schema.
3. **Load returns** (`domain/returns.py`, code only): parse uploaded GSTR-1, GSTR-3B and GSTR-2B files. Start with the CSV templates in `/samples/jawab`; add portal JSON/Excel later if time allows.
4. **Reconcile** (`domain/reconcile.py`, code only): per tax period and tax head, compute GSTR-1 vs 3B output tax and GSTR-2B vs 3B ITC. Match each ground to its rows and compute the difference.
5. **Explain** (`pipeline/explain.py`, agent): for each ground, propose likely causes from a fixed list (timing difference, credit note, amendment in a later period, ITC reversed, genuine short payment). The user confirms or adds facts in the UI.
6. **Research** (`pipeline/research.py`, agent + Tavily): one query per ground on the GST domains.
7. **Compute payable** (`domain/interest.py`, code only): for grounds the user accepts, tax plus interest under Section 50 to the payment date. Verify the rate and method against the Act before the demo.
8. **Draft** (`pipeline/draft.py`, reason): the ASMT-11 reply, point-wise, citing only stored sources and computed numbers.
9. **Verify** (`pipeline/verify.py`, code + fast): every number in the draft must exist in the reconciliation output; every URL must exist in `sources`. Failures are highlighted red in the UI.

## 6. Data schemas

```python
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel

class TaxAmount(BaseModel):
    igst: Decimal = 0
    cgst: Decimal = 0
    sgst: Decimal = 0
    cess: Decimal = 0

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
    financial_year: str
    grounds: list[Ground]

class GroundResult(BaseModel):
    ground_no: int
    our_amount: TaxAmount
    difference: TaxAmount
    status: Literal["explained", "partly_explained", "payable", "needs_ca"]
    explanation_facts: list[str]   # confirmed by the user
    source_ids: list[int]
    payable: TaxAmount | None
    interest: Decimal | None
```

## 7. Prompts (starting points)

- **Extract (fast):** "You read Indian GST notices. Extract each discrepancy ground exactly as the officer wrote it. Copy amounts digit for digit. If a field is not in the text, use null. Do not infer."
- **Explain (agent):** "Here is ground N, the officer's figure, our figure and the difference from code. From this list of standard causes, pick those consistent with the data and say what document would prove each. Do not compute numbers."
- **Draft (reason):** "Write the reply to ground N for Form ASMT-11. Use only the facts, numbers and sources given. Cite each source by its id. Plain, formal English. If the status is payable, state that tax and interest were paid via DRC-03 with the amounts given."

## 8. UI screens

1. **New case:** upload notice + return files; GSTIN auto-filled from the notice.
2. **Grounds:** table of grounds with officer amount, our amount, difference and status chips.
3. **Ground detail:** reconciliation table, suggested causes with confirm buttons, sources found.
4. **Draft reply:** editable text, citations as hover cards, red highlights for unverified claims, export to PDF/DOCX.
5. **Dashboard:** all notices, days to deadline, cost per case.

Banner on every draft: "Draft for review by you or a CA. Not legal advice." Nothing is filed automatically.

## 9. Test fixtures

Create 3 synthetic cases in `/samples/jawab/` (fake GSTINs, invented business names):

- **Case A:** output tax mismatch fully explained by a credit note in the next month.
- **Case B:** ITC mismatch, partly genuine (one supplier didn't file) → payable plus interest.
- **Case C:** a scanned photo of a notice, to show Nano Omni.

## 10. Acceptance criteria

- [ ] All grounds extracted correctly from cases A–C, amounts exact to the rupee
- [ ] Reconciliation unit tests pass for each case
- [ ] Draft for case B states the payable tax and interest the code computed
- [ ] Zero unverified citations in final drafts; a planted fake URL is caught by the verifier
- [ ] End-to-end case runs in under 3 minutes
- [ ] Cost per case shown in the UI

---

## 11. Build plan (Oct 12–30) with Claude Code prompts

Feature work stops on 27 Oct. Don't start a phase until the previous gate passes.

1. **Setup + model check (Oct 12–13).** Claim Nebius Builder Program credits; get Nebius and Tavily keys.
   - Prompt: "Read docs/SPEC.md. Scaffold the repo exactly as in 'Repo layout': docker-compose with Postgres, FastAPI health route, Next.js app, .env.example, MIT LICENSE. Then write scripts/smoke_models.py that calls each of the four MODEL_* env vars with a one-line prompt and prints both the content and any reasoning field."
   - Gate: all four models respond and you know which field holds the answer.
2. **Core pipeline (Oct 14–18).**
   - Prompt: "Create the synthetic fixtures in section 9, including CSV templates for GSTR-1, GSTR-3B and GSTR-2B. Then implement llm/client.py with the llm_calls table, pipeline/ingest.py, pipeline/extract.py, domain/returns.py and domain/reconcile.py with pytest tests against the fixtures."
   - Gate: extraction and reconciliation tests pass on every fixture.
3. **Reasoning + verify (Oct 19–22).**
   - Prompt: "Implement research/tavily.py with a sources table, then explain.py, research.py, domain/interest.py, draft.py and verify.py in spec order. Add a test that plants a fake URL and a wrong number in a draft and asserts the verifier flags both."
   - Gate: one full case runs end to end from the command line.
4. **Frontend (Oct 21–25).**
   - Prompt: "Build the UI screens in section 8 with Next.js, Tailwind and shadcn/ui. Wire them to the FastAPI routes. Unverified claims show red; citations show as hover cards; add the cost-per-case panel."
   - Gate: a case runs fully through the browser.
5. **Deploy + polish (Oct 26–27).**
   - Prompt: "Containerise the backend and document deployment to Nebius Serverless Endpoints in the README. Write the README sections the hackathon requires: setup, running, Nemotron models used, where Token Factory helped, other Nebius services used."
   - Gate: the public URL works from a phone. If behind schedule, cut portal file formats and the dashboard first.
6. **Video, README, submit (Oct 28–29).** Measure results on the fixtures, record the video, fill in the Devpost placeholders, submit by the night of 29 Oct. 30 Oct is buffer.

## 12. Risks and guardrails

| Risk | Guardrail |
| --- | --- |
| Made-up circular | Drafts cite only stored source ids; verifier rejects anything else |
| Wrong numbers | All maths in code; verifier matches every number to computed output |
| Reads as legal advice | Banner on every draft; nothing filed automatically |
| Real data in repo/demo | Synthetic samples only; fake GSTINs |
| Reasoning-model output parsing | Handle empty `content`; log raw responses in week 1 |
| Ultra latency / credits | Ultra only for drafting; cache per case; budget alert in cost panel |
| Model IDs change | IDs in env vars, not code |
| Running out of time | Pre-decided cuts: portal file formats, dashboard, multilingual output |

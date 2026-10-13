# Submission kit

Fill the `[brackets]` from `docs/RESULTS.md` after running `scripts/measure.py`. Check every claim against what actually happened.

## Links

- Live app: https://frontend-woad-gamma-hzt3uxjv46.vercel.app (API: https://jawab-api.onrender.com, free tier sleeps; open it a few minutes before judging)
- Code: https://github.com/lahari936/Jawab-GST (MIT)

## Devpost

**Tagline:** Turns a GST scrutiny notice and your returns into a cited, checked reply draft.

**Inspiration.** Small Indian businesses get ASMT-10 scrutiny notices when their GSTR-1, GSTR-3B and GSTR-2B don't agree. The reply (ASMT-11) is due in 30 days. Most of the work is reconciling numbers and finding the rule that explains the gap, and it usually means paying a consultant for a reply that often comes down to "a credit note landed in the next month".

**What it does.**
- Upload the notice (PDF, or a phone photo) and three return files.
- Jawab reads the notice and reconciles each ground month by month in code, and finds the documents that explain the gap.
- It suggests causes, which you confirm, and searches official GST sites for supporting circulars.
- It drafts the ASMT-11 reply with citations and computes any tax and Section 50 interest payable.
- Every amount and citation in the draft is checked against computed figures and stored sources; anything unverified shows in red.

**How we built it.**
- **Four Nemotron sizes, each on the job it fits:**
  - Nano Omni reads scanned or photographed notices.
  - A 30B model extracts the notice fields.
  - Super 120B suggests causes.
  - Ultra 550B writes the reply.
- **Tavily** searches only cbic-gst.gov.in, gst.gov.in and indiacode.nic.in; every result is stored and given an id.
- **Code owns the arithmetic:** pandas reconciles the returns, Python computes status, tax payable and interest, and a code-only verifier checks the draft.
- **Stack:** FastAPI + Pydantic + Postgres, and Next.js + shadcn/ui.

**Challenges.**
- Reasoning models put their thinking in a separate field, so the client reads the answer field and falls back to the reasoning field if it's empty.
- The vision model misread a `Z` as `2` on a low-resolution photo.
- Models sometimes return invalid JSON. Pydantic validation plus one retry fixes most cases, and the error keeps the raw output for debugging.
- [Add anything from the build week you want to mention.]

**Accomplishments.**
- On three synthetic cases: every notice field and amount extracted exactly (including from a tilted phone photo), 0 unverified claims in final drafts, 78–115 seconds per case end to end on free-tier endpoints (`docs/RESULTS.md`).
- The verifier catches a planted fake URL, a wrong number and a fake citation.

**What's next.**
- Portal JSON and Excel imports for the returns.
- More ground types.
- Agent-written search queries.
- Multilingual output.
- DRC-03 helper.

**Built with:** nemotron, nvidia-api-catalog, tavily, python, fastapi, pydantic, pandas, postgresql, next.js, typescript, tailwind, shadcn-ui, vercel, render

> Inference runs on the NVIDIA API Catalog (free tier). Say so plainly in the submission.

## Video script (about 3 minutes)

| Time | Show | Say |
| --- | --- | --- |
| 0:00 | Dashboard | "A GST scrutiny notice gives a small business 30 days to explain why its returns don't match. Jawab drafts that reply." |
| 0:15 | New case → Case B | "Upload the notice and your GSTR-1, 3B and 2B. Here's a synthetic sample." |
| 0:30 | Case page: grounds table | "Nemotron read the notice. The reply date wasn't stated, so code computed it. Officer says ₹6,000 + ₹6,000 excess ITC; our reconciliation agrees for September…" |
| 0:50 | Month table | "…but netted over the year, ₹1,500 per head came back in October from a supplier who filed late. ₹4,500 per head is genuinely payable." |
| 1:10 | Suggest causes & find sources | "Nemotron Super suggests causes; Tavily finds the CBIC circulars. Only facts I tick reach the draft. This 'amendment' suggestion is wrong for this data, so I leave it unticked." |
| 1:40 | Draft: set payment date, generate | "Nemotron Ultra writes the reply. Tax and Section 50 interest are computed in Python, never by the model." |
| 2:05 | Hover a citation | "Every citation is a stored source; hover to see it." |
| 2:15 | Edit: add 'Rs. 9,999' and a fake URL, re-verify | "If anyone, model or human, adds a number or source we can't back up, it turns red." |
| 2:35 | Cost panel; Case C photo | "Cost and tokens per case. And it reads phone photos of notices too." |
| 2:50 | Banner | "It's a draft for you or your CA. Nothing is filed automatically." |

Record at 1280×800 and pre-run Case B (Render free tier and the model free tier are slow). Cut the waiting out.

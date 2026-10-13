# Jawab: GST notice responder

Jawab turns an ASMT-10 scrutiny notice and the business's return data into a reviewed, cited ASMT-11 reply draft.

> Draft for review by you or a CA. Not legal advice. Nothing is filed automatically.

Built for the Nebius x NVIDIA Global AI Hackathon (Best Apps and Agents, Best Use of Tavily), using NVIDIA Nemotron models. Full spec: [`docs/SPEC.md`](docs/SPEC.md).

## What it does

1. **Reads the notice.** Digital PDFs are parsed locally with PyMuPDF. A scan or phone photo goes to Nemotron Nano Omni for transcription.
2. **Extracts the grounds.** A fast Nemotron model turns the text into a typed `Notice` (Pydantic, validated, one retry).
3. **Reconciles in code.** pandas compares GSTR-1 with GSTR-3B (output tax) and GSTR-2B with GSTR-3B (ITC), month by month and netted over the year. It also lists the later documents that offset a gap, such as a credit note or a late-filed supplier invoice. Status, tax payable and Section 50 interest are all computed in Python.
4. **Explains.** An agent model suggests likely causes from a fixed list. The user ticks only the facts they can prove.
5. **Researches.** Tavily searches cbic-gst.gov.in, gst.gov.in and indiacode.nic.in. Every result is stored in a `sources` table.
6. **Drafts.** Nemotron Ultra writes the reply to each ground, using only confirmed facts and computed numbers, and cites sources as `[S<id>]`.
7. **Verifies in code.** Every `Rs.` amount must match a computed figure, and every citation and URL must match a stored source. Anything else is highlighted red in the UI.

Scope: ASMT-10 notices, with two ground types (output tax R1 vs 3B, ITC 2B vs 3B). Any other ground is marked "needs CA review".

## Run it locally

Needs Python 3.12+, Node 20+ and Docker.

```bash
cp .env.example .env                      # add your LLM and Tavily keys
docker compose up -d db                   # Postgres on host port 5433
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt   # bin/ on macOS/Linux
python scripts/smoke_models.py            # check all four model tiers respond
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010
cd frontend && npm install && npm run dev # http://localhost:3000
```

Open http://localhost:3000, click **New case**, then pick one of the synthetic samples (cases A–C). Or upload your own notice plus the three CSVs, using the templates in `samples/jawab/`.

**Command-line run of one whole case:**

```bash
cd backend && ../.venv/Scripts/python -m app.pipeline.case ../samples/jawab/case_b --paid-on 2025-11-10
```

**Tests:**

```bash
cd backend && ../.venv/Scripts/python -m pytest          # offline: LLM and Tavily faked
cd backend && ../.venv/Scripts/python -m pytest -m live  # real model calls against the three fixtures
```

### Sample cases (synthetic: fake GSTINs and invented businesses)

| Case | Notice | What it shows |
| --- | --- | --- |
| A | digital PDF | July output tax gap fully offset by an August credit note; a second e-way bill ground is routed to a CA |
| B | digital PDF, no reply date | ITC gap: Rs. 1,500 per head from a late-filed supplier, Rs. 4,500 per head payable with interest |
| C | tilted phone photo | Read by the vision model; genuine short payment |

## Nemotron models used

Model IDs live in `.env`, not in code. The only file that calls the API is `backend/app/llm/client.py`.

| Tier | Job | Model |
| --- | --- | --- |
| vision | Transcribe scanned or photographed notices | Nemotron 3 Nano Omni (30B-A3B, reasoning) |
| fast | Extract notice fields into JSON | Nemotron 3.5 Lightning 30B-A3B |
| agent | Suggest causes for each ground | Nemotron 3 Super 120B-A12B |
| reason | Write the ASMT-11 reply | Nemotron 3 Ultra 550B-A55B |

All four are reasoning models. Their answer arrives in `content` and their thinking in `reasoning_content`. The client reads `content`, falls back to the reasoning field if `content` is empty, and strips `<think>` blocks and code fences before validating JSON.

Each call is logged to `llm_calls` (tier, model, tokens, cost). The UI shows this as the per-case cost panel.

## Inference

All four models run on the **NVIDIA API Catalog** (`https://integrate.api.nvidia.com/v1`, OpenAI-compatible, free tier).
One endpoint serves every Nemotron size, so routing each step to the size it needs is one env var per tier.
Any other OpenAI-compatible host for the same models is a `.env` change: `LLM_BASE_URL`, `LLM_API_KEY` and the four `MODEL_*` IDs.

Free-tier notes: the endpoint sometimes returns 503 "ResourceExhausted" when busy, so the client retries up to five times with backoff.
Cost per case shows $0 because the free tier is free; token counts per tier are real.

## Deployment

**Backend (container).** Build from the repo root so the synthetic samples ship with the image:

```bash
docker build -f backend/Dockerfile -t jawab-api .
docker run -p 8010:8000 --env-file .env -e DATABASE_URL=sqlite:////tmp/jawab.db jawab-api
```

The container listens on `$PORT` (default 8000). Set these variables wherever it runs:

- `LLM_BASE_URL`, `LLM_API_KEY`
- `MODEL_VISION`, `MODEL_FAST`, `MODEL_AGENT`, `MODEL_REASON`
- `TAVILY_API_KEY`
- `DATABASE_URL`: a managed Postgres, or the SQLite path above for a throwaway demo
- `CORS_ORIGINS`: the frontend URL; defaults to `*`

**Live deployment:** the API runs on Render from [`render.yaml`](render.yaml) (Dashboard → New → Blueprint; it asks for `LLM_API_KEY`, `TAVILY_API_KEY` and `DATABASE_URL`). The frontend is on Vercel.

**Frontend (Vercel).** Import the repo, set the root directory to `frontend`, and set `NEXT_PUBLIC_API_URL` to the backend's public URL.

To run the API container alongside Postgres:

```bash
docker compose --profile api up
```

The API is then on http://localhost:8010.

## Guardrails

- **Maths:** all arithmetic and date maths happen in Python; prompts tell the models not to compute.
- **Citations:** drafts may cite only rows stored in `sources`. The verifier rejects anything else, including URLs.
- **Facts:** only facts the user ticks reach the drafting model.
- **Fixed text:** the header, the banner and the text for grounds that need a CA are written by code, not the model.
- **Data:** samples are synthetic, and `.env` is gitignored.

## Known limits

- Interest assumes a monthly filer (3B due on the 20th of the next month) and, for ITC, that the credit was used on that date. Check the rate and method against Section 50 and rule 88B before relying on it.
- Each ground type has one fixed Tavily query.
- Returns load from CSV templates only; portal JSON and Excel are not supported yet.
- Export to PDF is done with the browser's print dialog; there is no DOCX export.

## License

MIT

# Jawab — GST Notice Responder

Turns an ASMT-10 scrutiny notice plus return data into a reviewed, cited ASMT-11 reply draft.
Draft for review by you or a CA. Not legal advice. See `docs/SPEC.md`.

## Setup

```bash
cp .env.example .env          # fill in keys
docker compose up -d db
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8010
cd frontend && npm install && npm run dev
python scripts/smoke_models.py  # check all four Nemotron tiers
```

Tests: `cd backend && pytest` (offline). Live Nemotron extraction on the fixtures: `pytest -m live`.
One case end to end from the CLI: `cd backend && python -m app.pipeline.case ../samples/jawab/case_b --paid-on 2025-11-10`.
API on port 8010 (`uvicorn app.main:app --port 8010` from backend/), web on 3000. Postgres on host port 5433.
Regenerate sample notices: `python scripts/make_samples.py`.

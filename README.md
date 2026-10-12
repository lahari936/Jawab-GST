# Jawab — GST Notice Responder

Turns an ASMT-10 scrutiny notice plus return data into a reviewed, cited ASMT-11 reply draft.
Draft for review by you or a CA. Not legal advice. See `docs/SPEC.md`.

## Setup

```bash
cp .env.example .env          # fill in keys
docker compose up -d db
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
python scripts/smoke_models.py  # check all four Nemotron tiers
```

Tests: `cd backend && pytest`

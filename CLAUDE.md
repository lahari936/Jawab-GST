# CLAUDE.md
Read docs/SPEC.md before any task. Project: Jawab (GST Notice Responder).
Rules:
- All LLM calls go through backend/app/llm/client.py; never call the API directly elsewhere.
- Arithmetic and date maths happen in Python, never in an LLM prompt.
- Every citation in generated text must come from a Tavily result stored in the sources table.
- Pydantic models for every LLM output; validate and retry once on failure.
- Write tests with each module. Run `pytest` before saying a phase is done.
- Never commit .env or real documents. Sample files go in /samples and must be synthetic.

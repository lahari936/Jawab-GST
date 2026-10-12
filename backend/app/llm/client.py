"""The only module that calls the LLM API."""
import base64
import json
import os
import re
from decimal import Decimal
from functools import cache

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.models import LlmCall, engine, init_db

# USD per 1M tokens (input, output).
# ponytail: zeros until filled from the Token Factory pricing page; cost panel shows 0 till then.
PRICES = {t: (Decimal(0), Decimal(0)) for t in ("vision", "fast", "agent", "reason")}


@cache
def _client() -> OpenAI:
    return OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])


def _model(tier: str) -> str:
    return os.environ[f"MODEL_{tier.upper()}"]


def _text(msg) -> str:
    # Reasoning models may leave content empty; fall back to the reasoning fields.
    return msg.content or getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""


def _json_slice(text: str) -> str:
    # Drop <think> blocks and code fences: keep the outermost {...}.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 else text


def log_usage(case_id: str, tier: str, model: str, usage) -> None:
    init_db()
    inp = getattr(usage, "prompt_tokens", 0) or 0
    out = getattr(usage, "completion_tokens", 0) or 0
    p_in, p_out = PRICES[tier]
    cost = (inp * p_in + out * p_out) / 1_000_000
    with Session(engine) as s:
        s.add(LlmCall(case_id=case_id, tier=tier, model=model, input_tokens=inp, output_tokens=out, cost=cost))
        s.commit()


def _chat(tier: str, messages: list[dict], case_id: str, **kw) -> str:
    model = _model(tier)
    r = _client().chat.completions.create(model=model, messages=messages, **kw)
    log_usage(case_id, tier, model, r.usage)
    return _text(r.choices[0].message)


def call_json(tier: str, system: str, user: str, schema: type[BaseModel], case_id: str):
    system += ("\nReturn only JSON matching this JSON schema:\n"
               + json.dumps(schema.model_json_schema()))
    for _ in range(2):
        out = _chat(tier, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    case_id, response_format={"type": "json_object"}, temperature=0.1)
        try:
            return schema.model_validate_json(_json_slice(out))
        except ValidationError as e:
            user += f"\n\nYour last output failed validation: {e}. Fix it."
    raise RuntimeError("LLM output invalid after retry")


def transcribe(image: bytes, mime: str, prompt: str, case_id: str) -> str:
    url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    return _chat("vision", [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": url}},
    ]}], case_id, temperature=0)

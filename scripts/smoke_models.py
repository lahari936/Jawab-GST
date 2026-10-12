"""Ping each MODEL_* tier and print both content and reasoning fields.

Run from repo root: python scripts/smoke_models.py
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])

for tier in ("VISION", "FAST", "AGENT", "REASON"):
    model = os.environ[f"MODEL_{tier}"]
    print(f"\n=== {tier}: {model}")
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
            max_tokens=512,
        )
        msg = r.choices[0].message
        print("content          :", repr(msg.content))
        print("reasoning_content:", repr(getattr(msg, "reasoning_content", None)))
        print("reasoning        :", repr(getattr(msg, "reasoning", None)))
        print("usage            :", r.usage)
    except Exception as e:
        print("ERROR:", e)

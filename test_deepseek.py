"""Test DeepSeek API using settings from .env"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

key = os.getenv("OPENAI_API_KEY", "").strip()
base = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com").strip() or "https://api.deepseek.com"
model = os.getenv("OPENAI_MODEL", "deepseek-chat").strip() or "deepseek-chat"

print("base_url:", base)
print("model:", model)
print("key:", (key[:8] + "...") if key else "(empty)")

if not key:
    print("FAIL: OPENAI_API_KEY is empty in .env")
    sys.exit(1)

try:
    client = OpenAI(api_key=key, base_url=base)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "reply OK"}],
        max_tokens=10,
    )
    print("OK reply:", resp.choices[0].message.content)
except Exception as e:
    print("FAIL:", e)
    sys.exit(1)

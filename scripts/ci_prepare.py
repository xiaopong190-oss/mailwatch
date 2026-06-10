"""GitHub Actions: build .env and accounts.json from repository secrets."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"ERROR: missing secret/env {name}")
        sys.exit(1)
    return val


def main() -> None:
    accounts_raw = require("ACCOUNTS_JSON")
    try:
        data = json.loads(accounts_raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: ACCOUNTS_JSON is not valid JSON: {e}")
        sys.exit(1)
    if not data.get("accounts"):
        print("ERROR: ACCOUNTS_JSON.accounts is empty")
        sys.exit(1)

    ROOT.joinpath("accounts.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    env = {
        "AI_PROVIDER": os.getenv("AI_PROVIDER", "deepseek").strip() or "deepseek",
        "OPENAI_API_KEY": require("OPENAI_API_KEY"),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com").strip(),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "deepseek-chat").strip(),
        "DINGTALK_WEBHOOK": os.getenv("DINGTALK_WEBHOOK", "").strip(),
        "DINGTALK_SECRET": os.getenv("DINGTALK_SECRET", "").strip(),
    }
    lines = [f"{k}={v}" for k, v in env.items()]
    ROOT.joinpath(".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("OK: wrote accounts.json and .env for CI")


if __name__ == "__main__":
    main()

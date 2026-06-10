"""
每日自动任务：拉邮件 → 过滤亚马逊 → DeepSeek/OpenAI 分类 → 本地报告 → 钉钉
用法: python daily_run.py
"""

import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from main import (
    AccountConfig,
    analyze_with_gpt,
    enrich_report,
    fetch_today_emails,
    filter_amazon_emails,
    load_accounts_store,
)
from report_util import push_dingtalk, report_to_markdown


def run_daily() -> Path:
    cfg = load_accounts_store()
    accounts = [
        AccountConfig(
            type=a["type"],
            email=a["email"],
            password=a["password"],
            name=a.get("name", ""),
        )
        for a in cfg.get("accounts", [])
    ]
    if not accounts:
        print("ERROR: 请先在网页「邮箱管理」添加邮箱")
        sys.exit(1)

    focus = cfg.get("focus", "亚马逊运营相关邮件")
    amazon_only = cfg.get("amazon_only", True)

    all_emails = []
    for acc in accounts:
        print(f"读取: {acc.name or acc.email}")
        all_emails.extend(fetch_today_emails(acc))

    fetched = len(all_emails)
    filtered = filter_amazon_emails(all_emails) if amazon_only else all_emails
    print(f"拉取 {fetched} 封，分析 {len(filtered)} 封")

    if not filtered:
        result = enrich_report({
            "date": date.today().isoformat(),
            "insight": "今日无亚马逊相关邮件",
            "emails": [],
        }, raw_total=fetched)
    else:
        result = analyze_with_gpt(filtered, focus)
        result["total"] = fetched

    meta = {"fetched": fetched, "amazon_filtered": len(filtered)}
    md = report_to_markdown(result, meta)

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out = reports_dir / f"{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"报告已保存: {out}")

    webhook = __import__("os").getenv("DINGTALK_WEBHOOK", "").strip()
    secret = __import__("os").getenv("DINGTALK_SECRET", "").strip()
    if webhook:
        title = f"MailWatch 重要邮件 {date.today().isoformat()}"
        ding_md = report_to_markdown(result, meta, important_only=True)
        push_dingtalk(webhook, title, ding_md, secret=secret)
        print("已推送到钉钉（仅重要邮件）")
    else:
        print("未配置 DINGTALK_WEBHOOK，跳过钉钉推送")

    return out


if __name__ == "__main__":
    try:
        run_daily()
    except Exception as e:
        detail = getattr(e, "detail", None)
        print(f"FAILED: {detail or e}")
        sys.exit(1)

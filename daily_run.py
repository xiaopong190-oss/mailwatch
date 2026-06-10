"""
每日自动任务：拉邮件 → 过滤亚马逊 → DeepSeek/OpenAI 分类 → 本地报告 → 钉钉
用法: python daily_run.py

默认统计窗口：昨日 08:00 ~ 今日 08:00（滚动 24 小时，适合每天 8:30 推送）
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

from main import (
    AccountConfig,
    analyze_with_gpt,
    enrich_report,
    fetch_emails_for_window,
    filter_amazon_emails,
    format_window_label,
    load_accounts_store,
    resolve_rolling_report_window,
)
from report_util import push_dingtalk, report_to_markdown


def resolve_window_bounds():
    end_hour = int(os.getenv("MAILWATCH_WINDOW_END_HOUR", "8"))
    end_minute = int(os.getenv("MAILWATCH_WINDOW_END_MINUTE", "0"))
    return resolve_rolling_report_window(end_hour, end_minute)


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
    window_start, window_end = resolve_window_bounds()
    period_label = format_window_label(window_start, window_end)

    all_emails = []
    for acc in accounts:
        print(f"读取 {period_label}: {acc.name or acc.email}")
        all_emails.extend(fetch_emails_for_window(acc, window_start, window_end))

    fetched = len(all_emails)
    filtered = filter_amazon_emails(all_emails) if amazon_only else all_emails
    print(f"窗口内拉取 {fetched} 封，分析 {len(filtered)} 封")

    if not filtered:
        result = enrich_report({
            "date": window_end.date().isoformat(),
            "day": "rolling_24h",
            "insight": f"{period_label} 无亚马逊相关邮件",
            "emails": [],
        }, raw_total=fetched)
    else:
        result = analyze_with_gpt(
            filtered,
            focus,
            report_date=window_end.date(),
            period_label=f"统计时段 {period_label}",
        )
        result["total"] = fetched
        result["day"] = "rolling_24h"

    meta = {
        "fetched": fetched,
        "amazon_filtered": len(filtered),
        "report_period": period_label,
    }
    md = report_to_markdown(result, meta)

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out = reports_dir / f"{window_end.date().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"报告已保存: {out}")

    webhook = os.getenv("DINGTALK_WEBHOOK", "").strip()
    secret = os.getenv("DINGTALK_SECRET", "").strip()
    if webhook:
        title = f"MailWatch 重要邮件 {window_end.date().isoformat()}"
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

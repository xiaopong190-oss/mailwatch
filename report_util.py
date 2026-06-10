"""报告生成与钉钉推送"""

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from typing import Optional

# 钉钉只推送这些分类（不含广告通知、配送汇总）
DINGTALK_CATEGORIES = ("风险邮件", "账号警告", "待处理", "重要邮件")


def filter_important_report(data: dict) -> dict:
    emails = [
        em
        for em in (data.get("emails") or [])
        if not em.get("grouped") and (em.get("category") or "") in DINGTALK_CATEGORIES
    ]
    stats = {cat: 0 for cat in DINGTALK_CATEGORIES}
    for em in emails:
        cat = em.get("category") or "重要邮件"
        if cat in stats:
            stats[cat] += 1
    out = dict(data)
    out["emails"] = emails
    out["categoryStats"] = stats
    out["urgent"] = stats["风险邮件"] + stats["账号警告"]
    out["needReply"] = stats["待处理"]
    out["handled"] = 0
    return out


def report_to_markdown(
    data: dict, meta: Optional[dict] = None, important_only: bool = False
) -> str:
    if important_only:
        data = filter_important_report(data)
    meta = meta or {}
    cs = data.get("categoryStats") or {}
    title = "亚马逊邮件重要提醒" if important_only else "亚马逊邮件日报"
    lines = [
        f"# {title} — {data.get('date', '')}",
        "",
        f"- 拉取邮件：{meta.get('fetched', data.get('total', 0))} 封",
    ]
    if important_only:
        lines.append(f"- 需关注：{len(data.get('emails') or [])} 封（风险/警告/待处理/重要）")
    if meta.get("amazon_filtered") is not None:
        lines.append(f"- 亚马逊相关：{meta.get('amazon_filtered')} 封")
    if data.get("deliveryGrouped"):
        lines.append(f"- 配送已汇总：{data['deliveryGrouped']} 封")

    lines.extend([
        f"- 风险：{cs.get('风险邮件', 0)} | 账号警告：{cs.get('账号警告', 0)} | 待处理：{cs.get('待处理', 0)}",
        f"- 重要：{cs.get('重要邮件', 0)} | 广告：{cs.get('广告通知', 0)}",
        "",
    ])

    if data.get("insight"):
        lines.extend([f"**洞察：** {data['insight']}", ""])

    if important_only and not (data.get("emails") or []):
        lines.extend(["", "**今日无重要邮件需处理**（无风险、警告、待处理或重要类邮件）", ""])
        return "\n".join(lines).strip()

    by_account: dict = {}
    for em in data.get("emails") or []:
        acct = em.get("account") or "默认邮箱"
        by_account.setdefault(acct, []).append(em)

    for acct, items in sorted(by_account.items()):
        lines.append(f"## {acct}")
        lines.append("")
        for i, em in enumerate(items, 1):
            if em.get("grouped"):
                lines.append(f"{i}. **[配送汇总]** {em.get('groupCount', 0)} 封 — {em.get('summary', '')}")
            else:
                cat = em.get("category", "")
                pri = em.get("priority", "")
                lines.append(f"{i}. **[{cat}]** {em.get('from', '')} {em.get('time', '')}")
                lines.append(f"   - 主题：{em.get('subject', '')}")
                lines.append(f"   - 摘要：{em.get('summary', '')}")
                tags = ", ".join(em.get("tags") or [])
                if tags:
                    lines.append(f"   - 标签：{tags}（{pri}优先）")
            lines.append("")

    return "\n".join(lines).strip()


def dingtalk_signed_url(webhook: str, secret: str = "") -> str:
    secret = (secret or "").strip()
    if not secret:
        return webhook
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    sep = "&" if "?" in webhook else "?"
    return f"{webhook}{sep}timestamp={timestamp}&sign={sign}"


def push_dingtalk(
    webhook: str, title: str, markdown: str, secret: str = ""
) -> None:
    if not webhook or "access_token=" not in webhook:
        raise ValueError("未配置有效的 DINGTALK_WEBHOOK")

    # 钉钉 markdown 有长度限制，截断；标题/正文需含关键词 MailWatch（若机器人启用了关键词）
    text = markdown[:18000]
    if "MailWatch" not in title and "MailWatch" not in text:
        text = f"**MailWatch**\n\n{text}"
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }
    req = urllib.request.Request(
        dingtalk_signed_url(webhook, secret),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        if body.get("errcode") != 0:
            raise RuntimeError(f"钉钉推送失败: {body.get('errmsg', body)}")

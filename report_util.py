"""报告生成与钉钉推送"""

import json
import urllib.request
from typing import Optional


def report_to_markdown(data: dict, meta: Optional[dict] = None) -> str:
    meta = meta or {}
    cs = data.get("categoryStats") or {}
    lines = [
        f"# 亚马逊邮件日报 — {data.get('date', '')}",
        "",
        f"- 拉取邮件：{meta.get('fetched', data.get('total', 0))} 封",
    ]
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


def push_dingtalk(webhook: str, title: str, markdown: str) -> None:
    if not webhook or "access_token=" not in webhook:
        raise ValueError("未配置有效的 DINGTALK_WEBHOOK")

    # 钉钉 markdown 有长度限制，截断
    text = markdown[:18000]
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        if body.get("errcode") != 0:
            raise RuntimeError(f"钉钉推送失败: {body.get('errmsg', body)}")

"""
MailWatch 后端服务
双击「启动 MailWatch.bat」即可，无需其他操作
"""

import imaplib
import email
import json
import os
import re
import threading
import time
import webbrowser
from datetime import datetime, date, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ACCOUNTS_PATH = ROOT / "accounts.json"
os.chdir(ROOT)
load_dotenv(ENV_PATH)

app = FastAPI(title="MailWatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if (ROOT / "static").exists():
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/")
def serve_frontend():
    index = ROOT / "static" / "index.html"
    if index.exists():
        return FileResponse(
            str(index),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return {"message": "MailWatch API 运行中", "docs": "/docs"}


class AccountConfig(BaseModel):
    type: str
    email: str
    password: str
    name: str = ""


class AccountCreate(BaseModel):
    type: str
    email: str
    password: str
    name: str = ""


def load_accounts_store() -> dict:
    if not ACCOUNTS_PATH.exists():
        return {"focus": "亚马逊运营相关邮件", "amazon_only": True, "accounts": []}
    return json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))


def save_accounts_store(data: dict) -> None:
    ACCOUNTS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


@app.get("/api/accounts")
def get_accounts():
    return load_accounts_store()


@app.post("/api/accounts")
def add_account(item: AccountCreate):
    data = load_accounts_store()
    email = item.email.strip().lower()
    for acc in data.get("accounts", []):
        if acc.get("email", "").lower() == email:
            raise HTTPException(status_code=400, detail="该邮箱已存在")
    account = {
        "id": int(time.time() * 1000),
        "type": item.type,
        "email": item.email.strip(),
        "password": item.password,
        "name": item.name.strip() or item.email.split("@")[0],
    }
    data.setdefault("accounts", []).append(account)
    save_accounts_store(data)
    return account


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int):
    data = load_accounts_store()
    before = len(data.get("accounts", []))
    data["accounts"] = [a for a in data.get("accounts", []) if a.get("id") != account_id]
    if len(data["accounts"]) == before:
        raise HTTPException(status_code=404, detail="邮箱不存在")
    save_accounts_store(data)
    return {"ok": True}


class AnalyzeRequest(BaseModel):
    accounts: List[AccountConfig]
    focus: str = "亚马逊运营相关邮件"
    system_prompt: Optional[str] = None
    max_emails: int = 50
    day: str = "today"  # today | yesterday


OPENAI_DEFAULTS = {
    "model": "gpt-4o-mini",
    "base_url": "",
}
DEEPSEEK_DEFAULTS = {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
}
VALID_PROVIDERS = ("deepseek", "openai")
PLACEHOLDER_KEYS = {"", "hermes", "sk-your-key-here", "sk-...", "your-deepseek-api-key"}
PROVIDERS_WITH_BASE_URL = ("deepseek",)


class ConfigRequest(BaseModel):
    provider: str = "deepseek"  # deepseek | openai
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


class DingTalkRequest(BaseModel):
    webhook: Optional[str] = None
    secret: Optional[str] = None


def get_provider() -> str:
    provider = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
    if provider in ("hermes", "nous"):
        return "deepseek"
    return provider if provider in VALID_PROVIDERS else "deepseek"


def normalize_deepseek_base_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base or "127.0.0.1" in base or "localhost" in base or ":8645" in base:
        return DEEPSEEK_DEFAULTS["base_url"]
    if "deepseek.com" not in base:
        return DEEPSEEK_DEFAULTS["base_url"]
    return base


def normalize_deepseek_model(model: str) -> str:
    model = (model or "").strip()
    if not model or "stepfun/" in model or model.startswith("Hermes-") or model.startswith("gpt-"):
        return DEEPSEEK_DEFAULTS["model"]
    return model


def reload_env() -> None:
    load_dotenv(ENV_PATH, override=True)


def resolve_ai_settings() -> dict:
    reload_env()
    provider = get_provider()
    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "api_key": os.getenv("OPENAI_API_KEY", DEEPSEEK_DEFAULTS["api_key"]).strip(),
            "base_url": normalize_deepseek_base_url(
                os.getenv("OPENAI_BASE_URL", DEEPSEEK_DEFAULTS["base_url"]).strip()
                or DEEPSEEK_DEFAULTS["base_url"]
            ),
            "model": normalize_deepseek_model(
                os.getenv("OPENAI_MODEL", DEEPSEEK_DEFAULTS["model"]).strip()
                or DEEPSEEK_DEFAULTS["model"]
            ),
        }
    return {
        "provider": "openai",
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "base_url": "",
        "model": os.getenv("OPENAI_MODEL", OPENAI_DEFAULTS["model"]).strip()
        or OPENAI_DEFAULTS["model"],
    }


def extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    def _loads(candidate: str) -> dict:
        data = json.loads(candidate)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("root must be object", candidate, 0)
        return data

    try:
        return _loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        chunk = text[start : end + 1]
        try:
            return _loads(chunk)
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*([}\]])", r"\1", chunk)
            return _loads(fixed)

    raise json.JSONDecodeError("no json object found", text, 0)


def chat_completion_json(client: OpenAI, model: str, messages: list, max_tokens: int = 4096):
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    try:
        return client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        return client.chat.completions.create(**kwargs)


def parse_ai_json_response(raw: str, client: OpenAI, model: str) -> dict:
    try:
        return extract_json_object(raw)
    except json.JSONDecodeError:
        fix_resp = chat_completion_json(
            client,
            model,
            [
                {
                    "role": "user",
                    "content": (
                        "将以下内容修正为合法 JSON 对象，只输出 JSON，不要 markdown 或其它文字：\n"
                        + raw[:8000]
                    ),
                }
            ],
            max_tokens=4096,
        )
        return extract_json_object(fix_resp.choices[0].message.content.strip())


def ai_error_hint(provider: str, err: str) -> str:
    err_l = err.lower()
    if provider == "deepseek":
        base = resolve_ai_settings()["base_url"]
        if "127.0.0.1" in base or ":8645" in base:
            return "API 地址错误，仍指向 Hermes Proxy。请在设置里改回 https://api.deepseek.com 并保存"
        if "401" in err or "403" in err:
            return "DeepSeek API Key 无效，请到 platform.deepseek.com 创建 Key"
        if "402" in err or "quota" in err_l or "balance" in err_l or "insufficient" in err_l:
            return "DeepSeek 余额不足，请到 platform.deepseek.com 充值"
        if "502" in err or "connection" in err_l or "connect" in err_l:
            return f"无法连接 {base}，请检查网络；确认模型为 deepseek-chat"
        return "确认 API 地址为 https://api.deepseek.com，模型为 deepseek-chat"
    if "401" in err:
        return "OpenAI API Key 无效"
    if "429" in err or "quota" in err_l:
        return "OpenAI 额度不足，可改用 DeepSeek"
    return ""


def get_ai_client(cfg: Optional[dict] = None) -> OpenAI:
    cfg = cfg or resolve_ai_settings()
    kwargs = {"api_key": cfg["api_key"]}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def resolve_ai_settings_from_request(req: ConfigRequest) -> dict:
    provider = req.provider.strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail="provider 只能是 deepseek 或 openai")
    if provider == "deepseek":
        reload_env()
        key = (req.api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        if not key or key in PLACEHOLDER_KEYS:
            raise HTTPException(status_code=400, detail="DeepSeek 需填写 API Key")
        return {
            "provider": "deepseek",
            "api_key": key,
            "base_url": normalize_deepseek_base_url(req.base_url or DEEPSEEK_DEFAULTS["base_url"]),
            "model": normalize_deepseek_model(req.model or DEEPSEEK_DEFAULTS["model"]),
        }
    key = (req.api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not key.startswith("sk-"):
        raise HTTPException(status_code=400, detail="OpenAI 需填写 sk- 开头的 API Key")
    return {
        "provider": "openai",
        "api_key": key,
        "base_url": "",
        "model": (req.model or OPENAI_DEFAULTS["model"]).strip(),
    }


def is_api_configured() -> bool:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(key) and key.startswith("sk-") and key not in PLACEHOLDER_KEYS


def write_env(
    provider: str,
    api_key: str,
    model: str,
    base_url: str = "",
) -> None:
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    updated = {
        "AI_PROVIDER": provider,
        "OPENAI_API_KEY": api_key,
        "OPENAI_MODEL": model,
        "OPENAI_BASE_URL": base_url if provider in PROVIDERS_WITH_BASE_URL else "",
    }
    new_lines = []
    seen = set()
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in updated:
            new_lines.append(f"{key}={updated[key]}")
            seen.add(key)
        else:
            new_lines.append(line)
    for key, val in updated.items():
        if key not in seen:
            new_lines.append(f"{key}={val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    for key, val in updated.items():
        os.environ[key] = val
    load_dotenv(ENV_PATH, override=True)


def write_env_var(key: str, value: str) -> None:
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    new_lines = []
    seen = False
    for line in lines:
        k = line.split("=", 1)[0].strip() if "=" in line else ""
        if k == key:
            new_lines.append(f"{key}={value}")
            seen = True
        else:
            new_lines.append(line)
    if not seen:
        new_lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ[key] = value
    load_dotenv(ENV_PATH, override=True)


def get_dingtalk_webhook() -> str:
    reload_env()
    return os.getenv("DINGTALK_WEBHOOK", "").strip()


def get_dingtalk_secret() -> str:
    reload_env()
    return os.getenv("DINGTALK_SECRET", "").strip()


def is_dingtalk_configured() -> bool:
    wh = get_dingtalk_webhook()
    return bool(wh and "access_token=" in wh)


def repair_stale_env() -> None:
    """Fix .env left over from Hermes/Nous when user switched to DeepSeek."""
    if not ENV_PATH.exists():
        return
    provider = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
    if provider in ("hermes", "nous"):
        provider = "deepseek"
    if provider != "deepseek":
        return
    raw_base = os.getenv("OPENAI_BASE_URL", "").strip()
    raw_model = os.getenv("OPENAI_MODEL", "").strip()
    fixed_base = normalize_deepseek_base_url(raw_base) if raw_base else DEEPSEEK_DEFAULTS["base_url"]
    fixed_model = normalize_deepseek_model(raw_model) if raw_model else DEEPSEEK_DEFAULTS["model"]
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if (
        provider != os.getenv("AI_PROVIDER", "").strip().lower()
        or fixed_base != raw_base
        or fixed_model != raw_model
    ):
        write_env(provider, key, fixed_model, fixed_base)


repair_stale_env()


@app.get("/config/status")
def config_status():
    cfg = resolve_ai_settings()
    return {
        "configured": is_api_configured(),
        "provider": cfg["provider"],
        "model": cfg["model"],
        "base_url": cfg["base_url"],
        "api_key_hint": "sk-..." if cfg["api_key"] else "sk-...",
        "dingtalk_configured": is_dingtalk_configured(),
        "dingtalk_secret_configured": bool(get_dingtalk_secret()),
    }


@app.post("/config/dingtalk")
def save_dingtalk(req: DingTalkRequest):
    reload_env()
    webhook = (req.webhook or "").strip() or get_dingtalk_webhook()
    secret = (req.secret or "").strip() or get_dingtalk_secret()
    if not webhook:
        raise HTTPException(status_code=400, detail="请填写钉钉群机器人 Webhook")
    if "access_token=" not in webhook:
        raise HTTPException(status_code=400, detail="Webhook 需包含 access_token=...")
    if secret and not secret.startswith("SEC"):
        raise HTTPException(status_code=400, detail="加签 Secret 通常以 SEC 开头")
    write_env_var("DINGTALK_WEBHOOK", webhook)
    if (req.secret or "").strip():
        write_env_var("DINGTALK_SECRET", (req.secret or "").strip())
    return {"ok": True}


@app.post("/config/dingtalk/test")
def test_dingtalk():
    from report_util import push_dingtalk

    webhook = get_dingtalk_webhook()
    secret = get_dingtalk_secret()
    if not webhook:
        raise HTTPException(status_code=400, detail="请先在「定时设置」配置钉钉 Webhook")
    try:
        push_dingtalk(
            webhook,
            "MailWatch 测试",
            "**MailWatch** 钉钉连接正常 ✓\n\n每天 8:30 会自动推送风险/警告/待处理/重要邮件。",
            secret=secret,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"钉钉推送失败: {e}") from e


@app.post("/config")
def save_config(req: ConfigRequest):
    provider = req.provider.strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail="provider 只能是 deepseek 或 openai")

    if provider == "deepseek":
        reload_env()
        key = (req.api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        if not key or key in PLACEHOLDER_KEYS:
            raise HTTPException(
                status_code=400,
                detail="DeepSeek 需填写 API Key（platform.deepseek.com 创建）",
            )
        if not key.startswith("sk-"):
            raise HTTPException(status_code=400, detail="DeepSeek API Key 通常以 sk- 开头")
        base = normalize_deepseek_base_url(req.base_url or DEEPSEEK_DEFAULTS["base_url"])
        model = normalize_deepseek_model(req.model or DEEPSEEK_DEFAULTS["model"])
    else:
        reload_env()
        key = (req.api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        if not key or not key.startswith("sk-"):
            raise HTTPException(status_code=400, detail="OpenAI 需填写 sk- 开头的 API Key")
        base = ""
        model = (req.model or OPENAI_DEFAULTS["model"]).strip()

    write_env(provider, key, model, base)
    return {"ok": True, "provider": provider}


@app.post("/config/test")
def test_config(req: Optional[ConfigRequest] = Body(None)):
    cfg = resolve_ai_settings_from_request(req) if req and req.provider else resolve_ai_settings()
    try:
        client = get_ai_client(cfg)
        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": "回复 OK"}],
            max_tokens=5,
        )
        reply = response.choices[0].message.content.strip()
        return {
            "ok": True,
            "provider": cfg["provider"],
            "model": cfg["model"],
            "base_url": cfg["base_url"],
            "reply": reply,
        }
    except Exception as e:
        err = str(e)
        hint = ai_error_hint(cfg["provider"], err)
        label = {"openai": "OpenAI", "deepseek": "DeepSeek"}[cfg["provider"]]
        raise HTTPException(
            status_code=502,
            detail=f"{label} 连接失败: {err}{('。' + hint) if hint else ''}",
        )


AMAZON_HINTS = (
    "amazon", "amz", "fba", "seller central", "sellercentral", "a-to-z", "atoz",
    "listing", "asin", "brand registry", "advertising", "sponsored products",
    "买家", "亚马逊", "amazon.com", "amazon.co", "fba@", "inventory", "fulfillment",
)


def filter_amazon_emails(emails: List[dict]) -> List[dict]:
    result = []
    for em in emails:
        blob = f"{em.get('subject', '')} {em.get('from', '')} {em.get('body', '')}".lower()
        if any(h in blob for h in AMAZON_HINTS):
            result.append(em)
    return result


IMAP_SERVERS = {
    "163": ("imap.163.com", 993),
    "126": ("imap.126.com", 993),
    "yeah": ("imap.yeah.net", 993),
    "gmail": ("imap.gmail.com", 993),
}

NETEASE_TYPES = {"163", "126", "yeah"}

if "ID" not in imaplib.Commands:
    imaplib.Commands["ID"] = ("AUTH",)


def send_netease_imap_id(mail) -> None:
    """网易邮箱要求 login 后、select 前声明客户端 ID。"""
    tag = mail._new_tag()
    mail.send(tag + b' ID ("name" "MailWatch" "version" "1.0" "vendor" "MailWatch")\r\n')
    typ, data = mail._get_tagged_response(tag)
    if typ != "OK":
        err = ""
        if data:
            err = data[0].decode(errors="replace") if isinstance(data[0], bytes) else str(data[0])
        raise Exception(f"IMAP ID 被拒绝: {err or typ}")


def select_inbox(mail) -> None:
    status, data = mail.select("INBOX")
    if status == "OK":
        return
    detail = ""
    if data:
        detail = data[0].decode(errors="replace") if isinstance(data[0], bytes) else str(data[0])
    raise Exception(detail or "无法选择收件箱")


def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                result.append(part.decode("gbk", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def get_email_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            pass
    return body[:500].strip()


CATEGORY_ORDER = ["风险邮件", "账号警告", "待处理", "重要邮件", "广告通知"]

DELIVERY_INCLUDE = (
    "已发货", "发货通知", "配送", "送达", "delivered", "shipped", "out for delivery",
    "tracking", "包裹", "运单", "快递", "物流更新", "delivery update", "on its way",
    "预计送达", "carrier", "in transit", "dispatch", "your order has",
)
DELIVERY_EXCLUDE = (
    "丢失", "损坏", "差异", "discrepancy", "lost", "damaged", "problem", "issue",
    "missing", "reimbursement", "调查", "claim", "投诉", "异常", "拒收", "退回",
    "fba货件问题", "inbound problem", "shortage", "overage",
)


def _email_text_blob(em: dict) -> str:
    return f"{em.get('subject', '')} {em.get('from', '')} {em.get('body', '')}".lower()


def is_routine_delivery(em: dict) -> bool:
    blob = _email_text_blob(em)
    if any(k.lower() in blob for k in DELIVERY_EXCLUDE):
        return False
    return any(k.lower() in blob for k in DELIVERY_INCLUDE)


def split_delivery_emails(emails: List[dict]):
    delivery, others = [], []
    for em in emails:
        (delivery if is_routine_delivery(em) else others).append(em)
    return others, delivery


def build_delivery_summaries(delivery: List[dict]) -> List[dict]:
    if not delivery:
        return []

    by_account: dict = {}
    for em in delivery:
        acct = em.get("account") or "默认邮箱"
        by_account.setdefault(acct, []).append(em)

    summaries = []
    for account, items in sorted(by_account.items()):
        shipped = delivered = 0
        for em in items:
            blob = _email_text_blob(em)
            if any(k in blob for k in ("送达", "delivered", "签收", "已收到")):
                delivered += 1
            elif any(k in blob for k in ("发货", "shipped", "dispatch", "on its way", "已发出")):
                shipped += 1

        in_transit = max(0, len(items) - shipped - delivered)
        parts = []
        if shipped:
            parts.append(f"发货 {shipped} 封")
        if delivered:
            parts.append(f"签收/送达 {delivered} 封")
        if in_transit:
            parts.append(f"在途更新 {in_transit} 封")
        if not parts:
            parts.append(f"物流通知 {len(items)} 封")

        summaries.append({
            "grouped": True,
            "groupType": "配送汇总",
            "account": account,
            "from": "配送物流",
            "time": items[0].get("time", "--:--"),
            "subject": f"配送通知汇总 · {len(items)} 封",
            "summary": f"该邮箱今日 {len(items)} 封配送类邮件：{'，'.join(parts)}。常规物流通知，无需逐封处理。",
            "category": "重要邮件",
            "tags": ["配送汇总"],
            "priority": "低",
            "groupCount": len(items),
        })
    return summaries


def enrich_report(result: dict, raw_total: Optional[int] = None) -> dict:
    stats = {cat: 0 for cat in CATEGORY_ORDER}
    emails = result.get("emails") or []
    for em in emails:
        cat = em.get("category") or "重要邮件"
        if cat not in stats:
            cat = "重要邮件"
            em["category"] = cat
        stats[cat] += 1
    result["categoryStats"] = stats
    result["urgent"] = stats["风险邮件"] + stats["账号警告"]
    result["needReply"] = stats["待处理"]
    result["handled"] = stats["广告通知"]
    order = {cat: i for i, cat in enumerate(CATEGORY_ORDER)}
    result["emails"] = sorted(
        emails,
        key=lambda e: (
            e.get("account") or "",
            1 if e.get("grouped") else 0,
            order.get(e.get("category"), 99),
        ),
    )
    if raw_total is not None:
        result["total"] = raw_total
    grouped = sum(e.get("groupCount", 1) for e in emails if e.get("grouped"))
    if grouped:
        result["deliveryGrouped"] = grouped
    return result


def resolve_target_date(day: str) -> date:
    if day == "yesterday":
        return date.today() - timedelta(days=1)
    return date.today()


def fetch_emails_for_day(
    account: AccountConfig, day: str = "today", max_emails: int = 50
) -> List[dict]:
    server_host, server_port = IMAP_SERVERS.get(account.type, ("", 0))
    if not server_host:
        raise ValueError(f"不支持的邮箱类型: {account.type}")

    emails = []
    try:
        mail = imaplib.IMAP4_SSL(server_host, server_port)
        mail.login(account.email, account.password)

        if account.type in NETEASE_TYPES:
            send_netease_imap_id(mail)

        select_inbox(mail)

        target = resolve_target_date(day)
        since_str = target.strftime("%d-%b-%Y")
        before_str = (target + timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = mail.search(None, "SINCE", since_str, "BEFORE", before_str)

        if status != "OK" or not data[0]:
            mail.logout()
            return []

        ids = data[0].split()[-max_emails:]

        for uid in reversed(ids):
            try:
                _, msg_data = mail.fetch(uid, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = decode_str(msg.get("Subject", "（无主题）"))
                from_addr = decode_str(msg.get("From", ""))
                body = get_email_body(msg)

                try:
                    dt = parsedate_to_datetime(msg.get("Date", ""))
                    time_str = dt.strftime("%H:%M")
                except Exception:
                    time_str = "--:--"

                emails.append({
                    "account": account.name or account.email,
                    "from": from_addr,
                    "time": time_str,
                    "subject": subject,
                    "body": body,
                })
            except Exception as e:
                print(f"解析邮件出错: {e}")
                continue

        mail.logout()
    except imaplib.IMAP4.error as e:
        msg = str(e)
        hint = ""
        if account.type in NETEASE_TYPES:
            hint = "。请确认：1) 已开启 IMAP  2) 使用的是授权码而非登录密码  3) 163 网页版设置里允许第三方客户端"
        raise HTTPException(
            status_code=400,
            detail=f"{account.email} 登录失败：{msg}{hint}",
        )
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        hint = ""
        if account.type in NETEASE_TYPES and ("Unsafe Login" in msg or "收件箱" in msg or "SELECT" in msg):
            hint = "。网易邮箱需使用 IMAP 授权码，并在网页版 设置→POP3/SMTP/IMAP 中开启 IMAP"
        raise HTTPException(status_code=500, detail=f"{account.email} 读取失败：{msg}{hint}")

    return emails


def fetch_today_emails(account: AccountConfig, max_emails: int = 50) -> List[dict]:
    return fetch_emails_for_day(account, "today", max_emails)


def analyze_with_gpt(
    emails: List[dict],
    focus: str,
    system_prompt: str = None,
    report_date: Optional[date] = None,
) -> dict:
    if not is_api_configured():
        raise HTTPException(status_code=400, detail="请先在「设置」配置 AI 分析引擎（推荐 DeepSeek）")

    report_date = report_date or date.today()
    day_label = "昨日" if report_date < date.today() else "今日"

    raw_total = len(emails)
    others, delivery = split_delivery_emails(emails)
    delivery_summaries = build_delivery_summaries(delivery)

    client = get_ai_client()

    email_text = ""
    for i, em in enumerate(others, 1):
        email_text += f"\n【邮件{i}】来自邮箱:{em['account']} | 发件人:{em['from']} | 时间:{em['time']}\n"
        email_text += f"主题：{em['subject']}\n"
        if em.get("body"):
            email_text += f"正文摘录：{em['body'][:200]}\n"

    delivery_note = ""
    if delivery:
        delivery_note = f"\n另有 {len(delivery)} 封常规配送/物流通知邮件已由系统自动汇总，请勿在 emails 数组中逐封列出。\n"

    if not others:
        result = {
            "date": report_date.isoformat(),
            "insight": f"{day_label}共 {raw_total} 封邮件，均为配送通知，无异常需处理。",
            "emails": delivery_summaries,
        }
        return enrich_report(result, raw_total=raw_total)

    default_system = """你是亚马逊跨境电商运营邮件分析助手。对每封邮件必须归类到且仅归类到一个主分类，并给出1-2个具体子标签。

【五大主分类 — category 字段只能填以下之一】

1. 风险邮件（最高优先级，需立即处理）
   适用：差评、1-3星Review、A-to-Z索赔、Chargeback拒付、买家威胁差评、恶意投诉、侵权下架通知、假冒商品警告、账号被限制销售/暂停/listing被移除
   子标签示例：差评预警、A-to-Z索赔、Chargeback、侵权下架、Listing移除、恶意投诉

2. 账号警告（高优先级，24小时内处理）
   适用：账号健康度通知、ODR/迟发率/取消率超标、客服响应超时、政策合规警告、账号审核/KYC、身份验证、Brand Registry问题、跟卖投诉处理结果
   子标签示例：账号健康、ODR超标、迟发率警告、政策违规、账号审核、身份验证

3. 待处理（中优先级，需回复或操作）
   适用：买家站内信、退货/退款请求、换货、FBA货件差异/丢失/损坏、Inbound问题、Case需回复、发票/税号请求、亚马逊调查问卷需回复
   子标签示例：买家消息、退货退款、FBA货件、Case待回复、发票请求

4. 重要邮件（中低优先级，需知晓但不必立刻回复）
   适用：FBA库存低/断货预警、补货提醒、物流签收/到仓、付款成功/失败、月结账单、仓储费、长期仓储费、VAT/GST税务、供应商/货代通知、银行到账
   子标签示例：库存预警、物流到仓、付款账单、仓储费用、税务通知、供应链

5. 广告通知（低优先级，可批量处理或忽略）
   适用：SP/SB/SD广告报告、广告账单、Budget耗尽、Coupon/Lightning Deal邀请、促销到期、Amazon Ads政策、Brand Analytics报告
   子标签示例：SP广告、SB/SD广告、广告账单、促销邀请、Coupon到期

【优先级 priority 映射】
- 风险邮件、账号警告 → 高
- 待处理、重要邮件 → 中
- 广告通知 → 低

【tags 规则】
- 从上述子标签中选1-2个最匹配的，用简短中文（4-8字）
- 不要发明新主分类名称

【配送邮件汇总规则】
- 常规发货/配送/签收/在途更新类邮件不要逐封输出
- 这类邮件由系统自动汇总，你只需分析非配送类邮件"""

    final_system = system_prompt.strip() if system_prompt and system_prompt.strip() else default_system

    user_prompt = f"""分析重点：{focus}
{delivery_note}
以下是需要逐封分析的非配送类邮件（共 {len(others)} 封）：
{email_text if others else "（无，仅配送汇总）"}

请严格按以下 JSON 格式返回（只输出 JSON，total/urgent/needReply/handled 必须是整数）：
{{
  "date": "{report_date.isoformat()}",
  "total": 0,
  "urgent": 0,
  "needReply": 0,
  "handled": 0,
  "insight": "50字以内整体运营洞察，说明{day_label}最需要关注什么",
  "emails": [
    {{
      "account": "来自哪个邮箱备注名",
      "from": "发件人名称（简化）",
      "time": "HH:MM",
      "subject": "邮件主题",
      "summary": "60字以内摘要，提炼运营关键信息",
      "category": "风险邮件|账号警告|待处理|重要邮件|广告通知 之一",
      "tags": ["具体子标签1", "具体子标签2"],
      "priority": "高/中/低"
    }}
  ]
}}"""

    cfg = resolve_ai_settings()
    model = cfg["model"]
    messages = [
        {"role": "system", "content": final_system},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = chat_completion_json(client, model, messages, max_tokens=4096)
    except Exception as e:
        err = str(e)
        hint = ai_error_hint(cfg["provider"], err)
        raise HTTPException(
            status_code=500,
            detail=f"AI 调用失败: {err}{('。' + hint) if hint else ''}",
        )

    raw = response.choices[0].message.content.strip()
    try:
        parsed = parse_ai_json_response(raw, client, model)
    except (json.JSONDecodeError, ValueError) as e:
        snippet = raw[:160].replace("\n", " ")
        raise HTTPException(
            status_code=500,
            detail=f"AI 返回格式无法解析，请重试。{snippet}",
        ) from e

    emails_out = parsed.get("emails") or []
    emails_out.extend(delivery_summaries)
    parsed["emails"] = emails_out
    parsed["date"] = report_date.isoformat()
    parsed["day"] = "yesterday" if report_date < date.today() else "today"
    return enrich_report(parsed, raw_total=raw_total)


@app.post("/analyze")
def analyze_emails(req: AnalyzeRequest):
    try:
        day = req.day if req.day in ("today", "yesterday") else "today"
        report_date = resolve_target_date(day)
        all_emails = []

        for account in req.accounts:
            emails = fetch_emails_for_day(account, day, req.max_emails)
            all_emails.extend(emails)

        day_label = "昨日" if day == "yesterday" else "今日"
        if not all_emails:
            return enrich_report({
                "date": report_date.isoformat(),
                "day": day,
                "insight": f"{day_label}暂无邮件",
                "emails": [],
            }, raw_total=0)

        result = analyze_with_gpt(all_emails, req.focus, req.system_prompt, report_date)
        result["day"] = day
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"analyze error: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


def _is_mailwatch_running(port: int) -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _pick_port() -> int:
    import socket

    env_port = os.getenv("MAILWATCH_PORT", "").strip()
    if env_port:
        return int(env_port)

    for port in range(8000, 8011):
        if _is_mailwatch_running(port):
            print(f"\n MailWatch already running on port {port}")
            print(f"   http://127.0.0.1:{port}")
            if os.getenv("MAILWATCH_NO_BROWSER") != "1":
                webbrowser.open(f"http://127.0.0.1:{port}")
            print("   Close the existing window to stop.\n")
            raise SystemExit(0)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue

    raise SystemExit("ERROR: ports 8000-8010 are all in use. Close other apps and retry.")


if __name__ == "__main__":
    port = _pick_port()

    def open_browser():
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    if os.getenv("MAILWATCH_NO_BROWSER") != "1":
        threading.Thread(target=open_browser, daemon=True).start()

    print("\n MailWatch running")
    print(f"   http://127.0.0.1:{port}")
    print("   Close this window to stop\n")
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)

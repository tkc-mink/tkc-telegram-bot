# set_webhook.py
# -*- coding: utf-8 -*-
"""
Safe Telegram Webhook manager:
- set:    ตั้งค่า webhook (POST) + รองรับ secret_token / allowed_updates / drop_pending_updates
- get:    ดูสถานะ webhook ปัจจุบัน
- delete: ยกเลิก webhook

ENV ที่ใช้:
  TELEGRAM_BOT_TOKEN         (จำเป็น)
  WEBHOOK_URL                (จำเป็นสำหรับ set)
  TELEGRAM_SECRET_TOKEN      (ออปชัน แนะนำ) — จะถูกส่งใน header X-Telegram-Bot-Api-Secret-Token
  TELEGRAM_ALLOWED_UPDATES   (ออปชัน CSV, เช่น: message,edited_message,callback_query)
  DROP_PENDING_UPDATES       (ดีฟอลต์: 1)
  REQ_TIMEOUT_SEC            (ดีฟอลต์: 15)
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import requests

API_BASE = "https://api.telegram.org"

def _truthy(s: str | None, default: bool = False) -> bool:
    if s is None: return default
    s = s.strip().lower()
    return s in {"1", "true", "yes", "on"}

def _env_csv(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default or []
    return [x.strip() for x in raw.split(",") if x.strip()]

def _timeout() -> float:
    try:
        return float(os.getenv("REQ_TIMEOUT_SEC", "15"))
    except Exception:
        return 15.0

def _api(method: str, token: str, *, params: dict | None = None, json_body: dict | None = None, http="get"):
    url = f"{API_BASE}/bot{token}/{method}"
    try:
        if http.lower() == "post":
            r = requests.post(url, params=params, json=json_body, timeout=_timeout())
        else:
            r = requests.get(url, params=params, timeout=_timeout())
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        try:
            data = e.response.json()
        except Exception:
            data = {"ok": False, "description": str(e)}
        return data
    except Exception as e:
        return {"ok": False, "description": f"request error: {e}"}

def set_webhook():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    url   = os.getenv("WEBHOOK_URL")
    if not token or not url:
        print("❌ ต้องตั้ง ENV TELEGRAM_BOT_TOKEN และ WEBHOOK_URL ก่อน", file=sys.stderr)
        sys.exit(1)

    secret = os.getenv("TELEGRAM_SECRET_TOKEN")  # แนะนำให้ตั้งเป็นสตริงสุ่มยาวๆ
    allowed = _env_csv("TELEGRAM_ALLOWED_UPDATES", ["message","edited_message","callback_query"])
    drop = _truthy(os.getenv("DROP_PENDING_UPDATES", "1"), True)

    body = {
        "url": url,
        "allowed_updates": allowed,
        "drop_pending_updates": drop,
    }
    if secret:
        body["secret_token"] = secret  # Telegram จะส่ง header ตรวจสอบกลับมา

    # หมายเหตุ: ถ้าใช้ self-signed cert ต้องอัปโหลด certificate (ไม่ได้ทำในตัวอย่างนี้)
    res = _api("setWebhook", token, json_body=body, http="post")
    print(json.dumps(res, ensure_ascii=False, indent=2))

def get_info():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ ต้องตั้ง ENV TELEGRAM_BOT_TOKEN ก่อน", file=sys.stderr)
        sys.exit(1)
    res = _api("getWebhookInfo", token)
    print(json.dumps(res, ensure_ascii=False, indent=2))

def delete_webhook():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ ต้องตั้ง ENV TELEGRAM_BOT_TOKEN ก่อน", file=sys.stderr)
        sys.exit(1)
    drop = _truthy(os.getenv("DROP_PENDING_UPDATES", "1"), True)
    res = _api("deleteWebhook", token, params={"drop_pending_updates": "true" if drop else "false"})
    print(json.dumps(res, ensure_ascii=False, indent=2))

def main():
    p = argparse.ArgumentParser(description="Telegram Webhook Manager")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("set")
    sub.add_parser("get")
    sub.add_parser("delete")
    args = p.parse_args()

    if args.cmd == "set":
        set_webhook()
    elif args.cmd == "get":
        get_info()
    elif args.cmd == "delete":
        delete_webhook()

if __name__ == "__main__":
    main()

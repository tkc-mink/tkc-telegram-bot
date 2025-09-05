# check_models.py
# -*- coding: utf-8 -*-
"""
สคริปต์ทดสอบการเชื่อมต่อ OpenAI SDK v1.x
- แสดงรายการโมเดลที่เข้าถึงได้ (ตัด 50 รายการแรก)
- ทดสอบแชทสั้น ๆ (รองรับทั้ง utils.openai_client และ fallback SDK ตรง)
รัน:
  python check_models.py
  python check_models.py --model gpt-4o-mini
  python check_models.py --stream
"""

from __future__ import annotations
import os
import sys
import argparse
from typing import List, Dict, Any

# ===== Helpers =====
def _mask(s: str | None) -> str:
    if not s:
        return ""
    s = str(s)
    return s if len(s) <= 8 else f"{s[:4]}…{s[-4:]}"

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)

# ===== Try project client first; fallback to SDK =====
_USING_PROJECT_CLIENT = False
client = None

def _init_client():
    global client, _USING_PROJECT_CLIENT
    try:
        # โปรเจ็กต์ของคุณมี wrapper เอง
        from utils.openai_client import client as _client  # type: ignore
        client = _client
        _USING_PROJECT_CLIENT = True
        return
    except Exception:
        pass

    # Fallback: ใช้ OpenAI SDK v1.x ตรง ๆ
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        print(f"❌ ไม่พบไลบรารี openai: {e}\nโปรดติดตั้งด้วย: pip install openai>=1.0.0")
        sys.exit(1)

    api_key = _env("OPENAI_API_KEY")
    if not api_key:
        print("❌ ไม่พบ OPENAI_API_KEY ใน Environment")
        sys.exit(1)

    # timeout อ่านจาก ENV ถ้าให้ไว้
    timeout_sec = float(_env("OPENAI_TIMEOUT_SEC", "30") or "30")
    try:
        client = OpenAI(api_key=api_key, timeout=timeout_sec)
    except TypeError:
        # สำหรับเวอร์ชัน client ที่ไม่รับ timeout ใน constructor
        client = OpenAI(api_key=api_key)

def list_models(limit: int = 50) -> List[str]:
    try:
        resp = client.models.list()
        data = getattr(resp, "data", []) or []
        ids = [getattr(m, "id", None) for m in data]
        ids = [i for i in ids if i][:limit]
        if not ids:
            print("⚠️ ไม่พบโมเดลที่เข้าถึงได้ด้วย API key นี้")
        else:
            print("🔍 โมเดลที่ API key นี้เรียกได้ (บางส่วน):")
            for mid in ids:
                print("-", mid)
        return ids
    except Exception as e:
        print(f"❌ ดึงรายการโมเดลไม่สำเร็จ: {e}")
        return []

def _sdk_chat_completion(messages: List[Dict[str, str]], model: str, stream: bool = False) -> str:
    """
    ใช้เมื่อ fallback ไป SDK ตรง ๆ (openai>=1.x)
    """
    try:
        if stream:
            chunks = client.chat.completions.create(model=model, messages=messages, stream=True)
            out = []
            for ev in chunks:
                delta = (ev.choices[0].delta.content or "") if hasattr(ev.choices[0], "delta") else ""
                if delta:
                    out.append(delta)
                    # พิมพ์สด ๆ ให้เห็น (ไม่ขึ้นบรรทัดใหม่จนกว่าจะจบ)
                    print(delta, end="", flush=True)
            if out:
                print()  # ปิดบรรทัด
            return "".join(out).strip()
        else:
            resp = client.chat.completions.create(model=model, messages=messages)
            return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        raise RuntimeError(f"chat.completions.create error: {e}")

def quick_chat_test(model: str, stream: bool = False) -> str:
    """
    ทดสอบแชทสั้น ๆ ให้ตอบคำว่า 'pong' ภาษาไทย
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant that replies in Thai."},
        {"role": "user", "content": "ทดสอบตอบสั้น ๆ คำว่า 'pong' หน่อย"},
    ]

    if _USING_PROJECT_CLIENT:
        # ใช้ wrapper ของโปรเจ็กต์ถ้ามี
        try:
            from utils.openai_client import chat_completion  # type: ignore
        except Exception as e:
            raise RuntimeError(f"ไม่พบ utils.openai_client.chat_completion: {e}")

        # wrapper ของโปรเจ็กต์ไม่รองรับ stream โดยตรง จึงเรียกแบบ non-stream
        return chat_completion(messages, model=model)

    # Fallback: SDK ตรง ๆ
    return _sdk_chat_completion(messages, model=model, stream=stream)

def main():
    _init_client()

    parser = argparse.ArgumentParser(description="OpenAI connectivity check (models + quick chat)")
    parser.add_argument("--model", type=str, default=_env("OPENAI_MODEL", "gpt-4o-mini"),
                        help="โมเดลสำหรับทดสอบแชท (ดีฟอลต์อ่านจาก OPENAI_MODEL หรือ gpt-4o-mini)")
    parser.add_argument("--stream", action="store_true", help="ทดสอบแบบสตรีม (ใช้ได้เฉพาะโหมด SDK ตรง)")
    args = parser.parse_args()

    print("== OpenAI Connectivity Check ==")
    print("• Using project client:", "yes" if _USING_PROJECT_CLIENT else "no")
    print("• OPENAI_API_KEY:", _mask(_env("OPENAI_API_KEY")))
    print("• Model for chat test:", args.model)
    if args.stream and _USING_PROJECT_CLIENT:
        print("  (ℹ️ โหมด stream ใช้ได้เฉพาะเมื่อ fallback ไป SDK ตรง)")

    # 1) list models
    list_models(limit=50)

    # 2) quick chat test
    try:
        print("\n== Quick Chat Test ==")
        reply = quick_chat_test(args.model, stream=args.stream and not _USING_PROJECT_CLIENT)
        print("💬 Reply:", reply)
    except Exception as e:
        print(f"❌ ทดสอบแชทไม่สำเร็จ: {e}")
        sys.exit(2)

    print("\n✅ เสร็จสิ้นการทดสอบ")

if __name__ == "__main__":
    main()

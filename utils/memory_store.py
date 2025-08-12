# utils/memory_store.py
# -*- coding: utf-8 -*-
"""
Simple persistent conversation memory per user (JSON file based)

- เก็บ messages ของแต่ละ chat_id (role/user/assistant + ts)
- เก็บ summary บทสนทนา (ย่อหน้าเดียว) เพื่อลด token
- ดึงบริบทล่าสุด (recent context) ให้ LLM ใช้ตอบต่อเนื่อง
- มีการสรุปอัตโนมัติเมื่อประวัติเยอะเกิน (prune & summarize)

NOTE:
- ใช้คู่กับ summarize_text_with_gpt จาก function_calling (ไม่มีวงวน import)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import os, json, time

# ที่เก็บความจำ
MEMORY_DIR  = os.getenv("MEMORY_DIR", "data")
MEMORY_PATH = os.path.join(MEMORY_DIR, "memory_store.json")

# ขีดจำกัด/เงื่อนไขสรุป
MAX_HISTORY_ITEMS   = int(os.getenv("MEMORY_MAX_HISTORY_ITEMS", "40"))   # เก็บสดสูงสุดกี่รายการ ก่อนสรุป
KEEP_TAIL_AFTER_SUM = int(os.getenv("MEMORY_KEEP_TAIL_AFTER_SUM", "8"))  # หลังสรุปเก็บท้ายไว้กี่รายการ
CTX_MAX_ITEMS       = int(os.getenv("MEMORY_CTX_MAX_ITEMS", "12"))       # ส่งให้ LLM กี่ข้อความล่าสุด
CTX_MAX_CHARS       = int(os.getenv("MEMORY_CTX_MAX_CHARS", "6000"))     # จำกัดตัวอักษรบริบทรวม

def _ensure_file():
    os.makedirs(MEMORY_DIR, exist_ok=True)
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False)

def _load() -> Dict[str, Any]:
    _ensure_file()
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(db: Dict[str, Any]) -> None:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)

def _now() -> int:
    return int(time.time())

def _get_bucket(db: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    b = db.get(user_id)
    if not b:
        b = {"messages": [], "summary": ""}
        db[user_id] = b
    return b

def append_message(user_id: str, role: str, content: str) -> None:
    db = _load()
    b = _get_bucket(db, user_id)
    b["messages"].append({"role": role, "content": (content or "").strip(), "ts": _now()})
    _save(db)

def get_summary(user_id: str) -> str:
    db = _load()
    b = _get_bucket(db, user_id)
    return b.get("summary", "")

def set_summary(user_id: str, summary: str) -> None:
    db = _load()
    b = _get_bucket(db, user_id)
    b["summary"] = (summary or "").strip()
    _save(db)

def get_recent_context(user_id: str, max_items: int = CTX_MAX_ITEMS, max_chars: int = CTX_MAX_CHARS) -> List[Dict[str, str]]:
    db = _load()
    b = _get_bucket(db, user_id)
    msgs = list(b.get("messages", []))[-max_items:]

    # ตัดความยาวรวมโดยวิธีย้อนจากท้าย
    out: List[Dict[str, str]] = []
    total = 0
    for m in reversed(msgs):
        c = (m.get("content") or "")
        total += len(c)
        if total > max_chars:
            break
        out.append({"role": m.get("role", "user"), "content": c})
    return list(reversed(out))

def prune_and_maybe_summarize(user_id: str) -> None:
    """
    ถ้าประวัติเยอะเกิน: สรุปส่วนต้น แล้วคงท้ายไว้ KEEP_TAIL_AFTER_SUM รายการ
    """
    from function_calling import summarize_text_with_gpt  # นำเข้าเฉพาะตอนเรียกใช้ เพื่อกันวงวน import
    db = _load()
    b = _get_bucket(db, user_id)
    msgs = b.get("messages", [])

    if len(msgs) <= MAX_HISTORY_ITEMS:
        return

    # รวมเป็นข้อความเดียวเพื่อสรุป
    joined = []
    for m in msgs[:-KEEP_TAIL_AFTER_SUM]:
        r = m.get("role", "user")
        c = (m.get("content") or "").replace("\n", " ").strip()
        if not c:
            continue
        if r == "user":
            joined.append(f"[ผู้ใช้] {c}")
        else:
            joined.append(f"[ผู้ช่วย] {c}")
    long_text = " ".join(joined).strip()
    if long_text:
        prev = (b.get("summary") or "").strip()
        new_sum = summarize_text_with_gpt(
            ("สรุปบทสนทนาแบบย่อ กระชับ สำหรับเก็บเป็นบริบทระยะยาว (ภาษาไทย):\n"
             f"{('[สรุปเดิม] ' + prev) if prev else ''}\n[เนื้อหาใหม่] {long_text}")
        )
        b["summary"] = new_sum.strip()

    # เก็บท้ายไว้
    b["messages"] = msgs[-KEEP_TAIL_AFTER_SUM:]
    _save(db)

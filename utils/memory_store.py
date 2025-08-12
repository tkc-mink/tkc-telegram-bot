# utils/memory_store.py
# -*- coding: utf-8 -*-
"""
Simple persistent conversation memory per user (JSON file based)
- Stores messages and a running summary for each user.
- Prunes history and updates summary when conversations get too long.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
import os
import json
import time

# --- Configuration ---
MEMORY_DIR = os.getenv("MEMORY_DIR", "data")
MEMORY_PATH = os.path.join(MEMORY_DIR, "memory_store.json")
MAX_HISTORY_ITEMS = int(os.getenv("MEMORY_MAX_HISTORY_ITEMS", "40"))
KEEP_TAIL_AFTER_SUM = int(os.getenv("MEMORY_KEEP_TAIL_AFTER_SUM", "8"))
CTX_MAX_ITEMS = int(os.getenv("MEMORY_CTX_MAX_ITEMS", "12"))
CTX_MAX_CHARS = int(os.getenv("MEMORY_CTX_MAX_CHARS", "6000"))

# --- Private Helper Functions ---
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
        json.dump(db, f, ensure_ascii=False, indent=2)

def _now() -> int:
    return int(time.time())

def _get_bucket(db: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    return db.setdefault(user_id, {"messages": [], "summary": ""})

# --- Public API Functions ---
def append_message(user_id: str, role: str, content: str) -> None:
    """Adds a new message to a user's conversation history."""
    db = _load()
    b = _get_bucket(db, user_id)
    b["messages"].append({"role": role, "content": (content or "").strip(), "ts": _now()})
    _save(db)

def get_summary(user_id: str) -> str:
    """Retrieves the current conversation summary for a user."""
    db = _load()
    b = _get_bucket(db, user_id)
    return b.get("summary", "")

def set_summary(user_id: str, summary: str) -> None:
    """Manually sets the conversation summary for a user."""
    db = _load()
    b = _get_bucket(db, user_id)
    b["summary"] = (summary or "").strip()
    _save(db)

def get_recent_context(user_id: str, max_items: int = CTX_MAX_ITEMS, max_chars: int = CTX_MAX_CHARS) -> List[Dict[str, str]]:
    """Gets the most recent messages for context, respecting character limits."""
    db = _load()
    b = _get_bucket(db, user_id)
    msgs = list(b.get("messages", []))[-max_items:]

    out: List[Dict[str, str]] = []
    total_chars = 0
    for m in reversed(msgs):
        content = m.get("content", "")
        total_chars += len(content)
        if total_chars > max_chars:
            break
        out.append({"role": m.get("role", "user"), "content": content})
    return list(reversed(out))

# ✅ FIXED: แก้ไขฟังก์ชันให้รับ 'summarize_func' ได้
def prune_and_maybe_summarize(user_id: str, summarize_func: Callable[[str], str]) -> None:
    """
    If history is too long, it summarizes the older part of the conversation
    and keeps only the most recent messages.
    """
    db = _load()
    b = _get_bucket(db, user_id)
    msgs = b.get("messages", [])

    if len(msgs) <= MAX_HISTORY_ITEMS:
        return

    print(f"[Memory] User {user_id} has {len(msgs)} messages, pruning...")

    # 1. Prepare text for summarization
    part_to_summarize = msgs[:-KEEP_TAIL_AFTER_SUM]
    text_to_summarize = "\n".join(
        f"[{m.get('role', 'user')}] {m.get('content', '')}"
        for m in part_to_summarize
    )

    if not text_to_summarize:
        return

    # 2. Create the new summary
    # ✅ ใช้ summarize_func ที่รับเข้ามาโดยตรง ไม่ต้อง import แล้ว
    previous_summary = b.get("summary", "")
    prompt_for_summary = (
        f"{('[สรุปเดิม] ' + previous_summary) if previous_summary else ''}\n"
        f"[เนื้อหาใหม่ที่จะสรุปต่อ] {text_to_summarize}"
    )
    new_summary = summarize_func(prompt_for_summary)

    b["summary"] = new_summary.strip()

    # 3. Keep only the tail end of the messages
    b["messages"] = msgs[-KEEP_TAIL_AFTER_SUM:]
    _save(db)
    print(f"[Memory] User {user_id} pruned. New summary saved. History now has {len(b['messages'])} messages.")

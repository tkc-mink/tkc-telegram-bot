# handlers/favorite.py
# -*- coding: utf-8 -*-
"""
Handler for user favorites, fully integrated with the persistent database.
Single entry handles:
  - /favorite_add <content>
  - /favorite_list
  - /favorite_remove <index>

Also supports convenient aliases:
  - /fav
  - /fav add <content>
  - /fav del <index>
  - /fav remove <index>
  - /favorite (same as /fav)

Stable + safe:
  - HTML escaping
  - Input normalization (trim/zero-width removal/whitespace compact)
  - Length guard via FAVORITE_MAX_CHARS
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import os
import re

from utils.message_utils import send_message, send_typing_action
from utils.favorite_utils import add_new_favorite, get_user_favorites, remove_user_favorite

# ===== Config (via ENV) =====
_FAVORITE_MAX_CHARS: int = int(os.getenv("FAVORITE_MAX_CHARS", "2000"))   # เก็บสูงสุด
_FAVORITE_LIST_LIMIT: int = int(os.getenv("FAVORITE_LIST_LIMIT", "10"))   # แสดงล่าสุด N รายการ
_PREVIEW_LEN: int = int(os.getenv("FAVORITE_PREVIEW_LEN", "200"))         # ตัวอย่างที่โชว์

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _truncate(s: str, max_len: int = 300) -> str:
    s = s or ""
    return (s[: max_len - 1] + "…") if len(s) > max_len else s

def _normalize_content(s: str) -> str:
    """ทำความสะอาดข้อความก่อนบันทึก: ลบ zero-width, ตัดช่องว่างซ้ำ, จำกัดความยาว"""
    if not s:
        return ""
    s = s.replace("\x00", "")
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)  # zero-width
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in s.split("\n")]
    cleaned: List[str] = []
    for ln in lines:
        if ln == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(ln)
    out = "\n".join(cleaned).strip()
    return out[:_FAVORITE_MAX_CHARS]

def _usage_text() -> str:
    return (
        "<b>คำสั่งสำหรับจัดการรายการโปรด</b>\n"
        f"• <code>/favorite_add &lt;ข้อความ&gt;</code> (เก็บสูงสุด {_FAVORITE_MAX_CHARS} ตัวอักษร)\n"
        f"• <code>/favorite_list</code> (แสดง {_FAVORITE_LIST_LIMIT} รายการล่าสุด)\n"
        "• <code>/favorite_remove &lt;ลำดับ&gt;</code>\n"
        "\n"
        "ทางลัด:\n"
        "• <code>/fav</code>, <code>/fav add ...</code>, <code>/fav del ...</code>, <code>/fav remove ...</code>"
    )

def _format_favorites_list(favs: List[Dict]) -> str:
    if not favs:
        return "📭 คุณยังไม่มีรายการโปรดเลยครับ"
    lines = [f"⭐ <b>รายการโปรด {min(_FAVORITE_LIST_LIMIT, len(favs))} อันดับล่าสุดของคุณ</b>"]
    for i, item in enumerate(favs, start=1):
        raw = str(item.get("content") or item.get("text") or "")
        content = _truncate(_html_escape(raw).strip(), 800)
        lines.append(f"{i}. <b>{content or '-'}</b>")
    lines.append("\nลบรายการ: <code>/favorite_remove &lt;ลำดับ&gt;</code> หรือ <code>/fav del &lt;ลำดับ&gt;</code>")
    return "\n".join(lines)

def _parse_index(idx_text: str) -> Optional[int]:
    try:
        n = int(str(idx_text).strip())
        return n if n >= 1 else None
    except Exception:
        return None

def _send(uid: int, text: str) -> None:
    send_message(uid, text, parse_mode="HTML")

# ===== Command router (string-based) =====
def _parse_cmd_and_args(text: str) -> Tuple[str, List[str]]:
    """
    คืน (command, args)
    รองรับ:
      /favorite_add <content>
      /favorite_list
      /favorite_remove <index>
      /fav [add|del|remove] [...]
      /favorite [add|del|remove] [...]
    """
    t = (text or "").strip()
    if not t.startswith("/"):
        return "", []
    # ตัดกรณี /fav@BotName
    head, *rest = t.split()
    head_only = head.split("@", 1)[0].lower()

    # ตรงตัว
    if head_only in {"/favorite_add", "/favorite_list", "/favorite_remove"}:
        return head_only, rest

    # กลุ่ม alias
    if head_only in {"/fav", "/favorite"}:
        return head_only, rest

    # ไม่รองรับ
    return "", []

# ===== Main handler =====
def handle_favorite(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Entry-point จาก main_handler
    - คาดว่า router จะส่งมาเมื่อเป็นคำสั่ง favorites เท่านั้น
    """
    user_id = int(user_info["profile"]["user_id"])
    text = (user_text or "").strip()

    cmd, args = _parse_cmd_and_args(text)
    if not cmd:
        _send(user_id, _usage_text())
        return

    # --- /favorite_add <content> ---
    if cmd == "/favorite_add":
        content_to_add = text[len("/favorite_add"):].strip()
        if not content_to_add:
            _send(user_id, "วิธีใช้: <code>/favorite_add &lt;ข้อความที่ต้องการบันทึก&gt;</code>")
            return
        send_typing_action(user_id, "typing")
        content_to_store = _normalize_content(content_to_add)
        if not content_to_store:
            _send(user_id, "ข้อความว่างหรือไม่เหมาะสมสำหรับการบันทึกครับ")
            return
        ok = False
        try:
            ok = add_new_favorite(user_id, content_to_store)
        except Exception as e:
            print(f"[favorite] add error: {e}")
            ok = False

        preview = _truncate(_html_escape(content_to_store), _PREVIEW_LEN)
        if ok:
            _send(user_id, f"✅ บันทึกเป็นรายการโปรดแล้ว:\n<blockquote>{preview}</blockquote>")
        else:
            _send(user_id, "❌ บันทึกล้มเหลว ลองใหม่อีกครั้งนะครับ")
        return

    # --- /favorite_list ---
    if cmd == "/favorite_list":
        try:
            favs = get_user_favorites(user_id, limit=_FAVORITE_LIST_LIMIT)
        except Exception as e:
            print(f"[favorite] list error: {e}")
            favs = []
        _send(user_id, _format_favorites_list(favs))
        return

    # --- /favorite_remove <index> ---
    if cmd == "/favorite_remove":
        if not args:
            _send(user_id, "ระบุ <b>ลำดับ</b> ด้วยครับ เช่น <code>/favorite_remove 2</code>")
            return
        idx = _parse_index(args[0])
        if not idx:
            _send(user_id, "ลำดับต้องเป็นตัวเลขตั้งแต่ 1 เป็นต้นไปครับ")
            return
        ok = False
        try:
            ok = remove_user_favorite(user_id, idx)
        except Exception as e:
            print(f"[favorite] remove error: {e}")
            ok = False
        if ok:
            _send(user_id, f"🗑️ ลบรายการโปรดลำดับที่ {idx} แล้วครับ")
        else:
            _send(user_id, "❌ ลบไม่สำเร็จ ตรวจสอบลำดับอีกครั้งนะครับ")
        return

    # --- alias group: /fav, /favorite ---
    if cmd in {"/fav", "/favorite"}:
        # ไม่มี args → แสดงรายการ
        if not args:
            try:
                favs = get_user_favorites(user_id, limit=_FAVORITE_LIST_LIMIT)
            except Exception as e:
                print(f"[favorite] list(alias) error: {e}")
                favs = []
            _send(user_id, _format_favorites_list(favs))
            return

        sub = args[0].lower()
        # /fav add <content>
        if sub == "add":
            if len(args) < 2:
                _send(user_id, "วิธีใช้: <code>/fav add &lt;ข้อความ&gt;</code>")
                return
            content_to_store = _normalize_content(" ".join(args[1:]))
            if not content_to_store:
                _send(user_id, "ข้อความว่างหรือไม่เหมาะสมสำหรับการบันทึกครับ")
                return
            send_typing_action(user_id, "typing")
            ok = False
            try:
                ok = add_new_favorite(user_id, content_to_store)
            except Exception as e:
                print(f"[favorite] add(alias) error: {e}")
                ok = False
            preview = _truncate(_html_escape(content_to_store), _PREVIEW_LEN)
            if ok:
                _send(user_id, f"✅ บันทึกแล้ว:\n<blockquote>{preview}</blockquote>")
            else:
                _send(user_id, "❌ บันทึกล้มเหลว ลองใหม่อีกครั้งนะครับ")
            return

        # /fav del <index>  หรือ  /fav remove <index>
        if sub in {"del", "remove"}:
            if len(args) < 2:
                _send(user_id, "ระบุ <b>ลำดับ</b> ที่ต้องการลบด้วยครับ เช่น <code>/fav del 2</code>")
                return
            idx = _parse_index(args[1])
            if not idx:
                _send(user_id, "ลำดับต้องเป็นตัวเลขตั้งแต่ 1 เป็นต้นไปครับ")
                return
            ok = False
            try:
                ok = remove_user_favorite(user_id, idx)
            except Exception as e:
                print(f"[favorite] remove(alias) error: {e}")
                ok = False
            if ok:
                _send(user_id, f"🗑️ ลบรายการโปรดลำดับที่ {idx} แล้วครับ")
            else:
                _send(user_id, "❌ ลบไม่สำเร็จ ตรวจสอบลำดับอีกครั้งนะครับ")
            return

        # ไม่รู้จัก sub-command
        _send(user_id, _usage_text())
        return

    # default
    _send(user_id, _usage_text())

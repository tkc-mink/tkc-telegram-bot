# utils/admin_utils.py
# -*- coding: utf-8 -*-
"""
Admin utilities (final, robust)
- รองรับหลาย Super Admin จาก ENV: SUPER_ADMIN_IDS="604990227,123456789"
- แจ้งเตือนอนุมัติผู้ใช้ใหม่ถึงทุก Super Admin
- ฟังก์ชันอนุมัติ/ระงับ/ลิสต์ผู้ใช้ ให้เรียกจาก handlers.admin ได้ทันที
"""

from __future__ import annotations
from typing import Dict, Any, Iterable, Optional
import os

from utils.memory_store import (
    get_all_users,
    update_user_status,
    get_user_by_id,
)
from utils.telegram_api import send_message


# ---------- Super Admins ----------

def _load_super_admin_ids() -> set[int]:
    env = (os.getenv("SUPER_ADMIN_IDS") or "").strip()
    if not env:
        # fallback เพื่อรองรับระบบเก่า (ตัวเดียว)
        legacy = os.getenv("SUPER_ADMIN_ID")
        if legacy:
            try:
                return {int(legacy)}
            except ValueError:
                pass
        return set()

    ids: set[int] = set()
    for tok in env.replace(";", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            ids.add(int(tok))
        except ValueError:
            # เผื่อเผลอใส่เป็น @username — ข้ามไป
            pass
    return ids


SUPER_ADMIN_IDS: set[int] = _load_super_admin_ids()


def is_super_admin(user_id: int) -> bool:
    return int(user_id) in SUPER_ADMIN_IDS


# ---------- Helpers ----------

def _broadcast_to_admins(text: str, parse_mode: Optional[str] = "Markdown") -> None:
    if not SUPER_ADMIN_IDS:
        print("[Admin] SUPER_ADMIN_IDS not set. Skip broadcast.")
        return
    for admin_id in SUPER_ADMIN_IDS:
        try:
            send_message(admin_id, text, parse_mode=parse_mode)
        except Exception as e:
            print(f"[Admin] failed to notify {admin_id}: {e}")


def _find_user_id_by_username(username: str) -> Optional[int]:
    """ค้นหา user_id จาก @username (ไม่ต้องใส่ @ ก็ได้)"""
    uname = username.lstrip("@").lower()
    for u in get_all_users():
        if (u.get("username") or "").lower() == uname:
            return int(u["user_id"])
    return None


def _parse_target_identifier(arg: str) -> Optional[int]:
    """
    แปลงพารามิเตอร์เป็น user_id:
    - ตัวเลข -> ตีความเป็น user_id
    - @username หรือ username -> ค้นหาในฐานข้อมูล
    """
    arg = (arg or "").strip()
    if not arg:
        return None
    try:
        return int(arg)
    except ValueError:
        return _find_user_id_by_username(arg)


# ---------- Notifications ----------

def notify_super_admin_for_approval(new_user_data: Dict[str, Any]) -> None:
    """
    ส่งข้อความแจ้งเตือน Super Admin ทุกคนเมื่อมีผู้ใช้ใหม่รออนุมัติ
    เรียกจาก main_handler ตอนเจอ status new_user_pending/pending
    """
    if not SUPER_ADMIN_IDS:
        print("[Admin] SUPER_ADMIN_IDS not set. Cannot send approval notification.")
        return

    user_id = new_user_data.get("id")
    first_name = new_user_data.get("first_name", "")
    username = new_user_data.get("username", "N/A")

    # ใช้ backticks เพื่อกัน Markdown เพี้ยนกรณีมี underscore
    msg = (
        "🔔 **มีผู้ใช้ใหม่รอการอนุมัติ** 🔔\n\n"
        f"**ชื่อ:** {first_name}\n"
        f"**Username:** `@{username}`\n"
        f"**User ID:** `{user_id}`\n\n"
        "ใช้คำสั่ง:\n"
        f"• `/admin approve {user_id}` เพื่ออนุมัติ\n"
        f"• `/admin remove {user_id}` เพื่อระงับ\n"
        "หรือจะระบุเป็น `@username` ก็ได้ครับ"
    )
    _broadcast_to_admins(msg, parse_mode="Markdown")


# ---------- Core admin actions ----------

def approve_user(target_user_id: int) -> str:
    """อนุมัติผู้ใช้ (รับ user_id เป็นตัวเลข)"""
    if update_user_status(target_user_id, "approved"):
        try:
            send_message(
                target_user_id,
                "🎉 ยินดีด้วยครับ! บัญชีของคุณได้รับการอนุมัติให้ใช้งานแล้ว\nพิมพ์ /help เพื่อดูคำสั่งทั้งหมดได้เลยครับ",
            )
        except Exception as e:
            print(f"[Admin] notify approved user failed: {e}")
        return f"✅ อนุมัติผู้ใช้ ID: {target_user_id} เรียบร้อยแล้วครับ"
    return f"❓ ไม่พบผู้ใช้ ID: {target_user_id} หรือเกิดข้อผิดพลาดในการอัปเดตสถานะครับ"


def approve_user_by_identifier(identifier: str) -> str:
    """อนุมัติจาก id หรือ @username เพื่อความสะดวกใน handler"""
    uid = _parse_target_identifier(identifier)
    if uid is None:
        return "กรุณาระบุเป็น user_id หรือ @username ครับ"
    return approve_user(uid)


def remove_user(target_user_id: int) -> str:
    """ระงับผู้ใช้ (รับ user_id เป็นตัวเลข)"""
    if update_user_status(target_user_id, "removed"):
        try:
            send_message(target_user_id, "บัญชีของคุณถูกระงับการใช้งานแล้วครับ")
        except Exception as e:
            print(f"[Admin] notify removed user failed: {e}")
        prof = get_user_by_id(target_user_id) or {}
        name = prof.get("first_name", "") or ""
        return f"🚫 ระงับการใช้งานผู้ใช้ ID: {target_user_id} ({name}) เรียบร้อยแล้วครับ"
    return f"❓ ไม่พบผู้ใช้ ID: {target_user_id} หรือเกิดข้อผิดพลาดครับ"


def remove_user_by_identifier(identifier: str) -> str:
    uid = _parse_target_identifier(identifier)
    if uid is None:
        return "กรุณาระบุเป็น user_id หรือ @username ครับ"
    return remove_user(uid)


def list_all_users() -> str:
    """สรุปรายชื่อผู้ใช้ทั้งหมด"""
    users = get_all_users()
    if not users:
        return "ยังไม่มีผู้ใช้ในระบบเลยครับ"

    icon = {"approved": "✅", "pending": "⏳", "removed": "❌"}
    lines = ["**รายชื่อผู้ใช้ทั้งหมดในระบบ:**"]
    for u in users:
        status = u.get("status") or ""
        lines.append(
            f"{icon.get(status, '❓')} `{u['user_id']}` - {u.get('first_name','')}"
            f" (@{u.get('username','')}) [{u.get('role','')}]"
        )
    return "\n".join(lines)

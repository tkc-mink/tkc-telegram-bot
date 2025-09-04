# handlers/admin.py
# -*- coding: utf-8 -*-
"""
Admin command handler (final, robust)
- รองรับทั้งรูปแบบเก่า:  /admin_approve <id>, /admin_remove <id>, /admin_users
- และรูปแบบใหม่:         /admin approve <id|@username>, /admin remove <id|@username>, /admin users
- ตรวจสิทธิ์ Super Admin ด้วย utils.admin_utils.is_super_admin
- ใช้ approve/remove แบบ "by_identifier" เพื่อรองรับทั้งตัวเลขและ @username
"""

from __future__ import annotations
from typing import Dict, Any, List

from utils.telegram_api import send_message
from utils.admin_utils import (
    is_super_admin,
    list_all_users,
    approve_user_by_identifier,
    remove_user_by_identifier,
)

# ---------- Helpers ----------

def _admin_help() -> str:
    return (
        "**Admin commands**\n"
        "รูปแบบใหม่:\n"
        "• `/admin approve <user_id|@username>` — อนุมัติผู้ใช้\n"
        "• `/admin remove <user_id|@username>` — ระงับผู้ใช้\n"
        "• `/admin users` — ดูรายชื่อผู้ใช้ทั้งหมด\n\n"
        "รูปแบบเก่า (ยังใช้ได้):\n"
        "• `/admin_approve <user_id>`\n"
        "• `/admin_remove <user_id>`\n"
        "• `/admin_users`"
    )

def _send_usage(user_id: int, sub: str) -> None:
    if sub == "approve":
        send_message(user_id, "วิธีใช้: `/admin approve <user_id|@username>`", parse_mode="Markdown")
    elif sub == "remove":
        send_message(user_id, "วิธีใช้: `/admin remove <user_id|@username>`", parse_mode="Markdown")
    else:
        send_message(user_id, _admin_help(), parse_mode="Markdown")

# ---------- Entry Point ----------

def handle_admin_command(user_info: Dict[str, Any], user_text: str) -> None:
    user_id = int(user_info["profile"]["user_id"])
    user_name = user_info["profile"].get("first_name", "")

    # 1) Security check
    if not is_super_admin(user_id):
        print(f"[Admin] Unauthorized access by {user_name} ({user_id}) -> '{user_text}'")
        send_message(user_id, "⛔️ ขออภัยครับ คุณไม่มีสิทธิ์ใช้คำสั่งสำหรับผู้ดูแลระบบครับ")
        return

    # 2) Normalize tokens
    tokens: List[str] = (user_text or "").strip().split()
    if not tokens:
        send_message(user_id, _admin_help(), parse_mode="Markdown")
        return

    base = tokens[0].lower()
    args = tokens[1:]

    # ----- Legacy style: /admin_approve, /admin_remove, /admin_users -----
    if base == "/admin_approve":
        if not args:
            _send_usage(user_id, "approve")
            return
        target = args[0]
        reply = approve_user_by_identifier(target)
        send_message(user_id, reply, parse_mode="Markdown")
        return

    if base == "/admin_remove":
        if not args:
            _send_usage(user_id, "remove")
            return
        target = args[0]
        reply = remove_user_by_identifier(target)
        send_message(user_id, reply, parse_mode="Markdown")
        return

    if base == "/admin_users":
        reply = list_all_users()
        send_message(user_id, reply, parse_mode="Markdown")
        return

    # ----- New style: /admin <subcommand> [args...] -----
    if base == "/admin":
        if not args:
            send_message(user_id, _admin_help(), parse_mode="Markdown")
            return

        sub = args[0].lower()
        sub_args = args[1:]

        if sub == "approve":
            if not sub_args:
                _send_usage(user_id, "approve")
                return
            target = sub_args[0]
            reply = approve_user_by_identifier(target)
            send_message(user_id, reply, parse_mode="Markdown")
            return

        if sub == "remove":
            if not sub_args:
                _send_usage(user_id, "remove")
                return
            target = sub_args[0]
            reply = remove_user_by_identifier(target)
            send_message(user_id, reply, parse_mode="Markdown")
            return

        if sub in ("users", "list", "ls"):
            reply = list_all_users()
            send_message(user_id, reply, parse_mode="Markdown")
            return

        # Unknown subcommand
        send_message(user_id, f"ผมไม่รู้จักคำสั่งผู้ดูแลระบบ '`{sub}`' ครับ\n\n" + _admin_help(), parse_mode="Markdown")
        return

    # Fallback: not recognized
    send_message(user_id, _admin_help(), parse_mode="Markdown")

# handlers/backup.py
# -*- coding: utf-8 -*-
"""
Telegram backup commands (เสถียร/ปลอดภัย):
  /backup_now
  /backup_status
  /list_snapshots
  /restore latest | /restore YYYY-MM-DD

ข้อกำหนด ENV (ต้องตั้งให้เรียบร้อย):
- SUPER_ADMIN_ID=<your_telegram_id>   # หรือ ADMIN_IDS=ไอดีคอมมาเซพาราเรต
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import os
import threading
from datetime import datetime

from utils.message_utils import send_message, send_typing_action
from utils.backup_utils import (
    backup_all,
    restore_all,
    get_backup_status,
    list_snapshots,
)

# ===== Admin guards (ต้องกำหนดอย่างน้อย 1 ราย) =====
_ADMIN_IDS = set()
try:
    sa = (os.getenv("SUPER_ADMIN_ID") or "").strip()
    if sa:
        _ADMIN_IDS.add(int(sa))
    admin_ids = (os.getenv("ADMIN_IDS") or "").strip()
    if admin_ids:
        for x in admin_ids.split(","):
            x = x.strip()
            if x:
                _ADMIN_IDS.add(int(x))
except Exception:
    # ไม่โยนต่อ: ป้องกัน process ตายเพราะ ENV ไม่สะอาด
    pass

def is_admin(user_id: int | str) -> bool:
    try:
        uid = int(str(user_id))
    except Exception:
        return False
    # เสถียร/ปลอดภัย: ถ้าไม่ได้ตั้ง ADMIN เลย → ปฏิเสธ
    return uid in _ADMIN_IDS

# ===== Utilities =====
_inprogress_lock = threading.Lock()
_inprogress: Dict[str, bool] = {"backup": False, "restore": False}

def _html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _short_id(s: Optional[str]) -> str:
    if not s:
        return "-"
    return s[:8] + "…" + s[-4:] if len(s) > 14 else s

def _format_status_for_telegram(status: Dict[str, Any]) -> str:
    ts = _html_escape(status.get("timestamp") or "-")
    ok = status.get("success", False)
    files = status.get("files", [])
    lines = [
        "<b>📦 สถานะสำรองล่าสุด</b>",
        f"• เวลา: <code>{ts}</code>",
        f"• สำเร็จทั้งหมด: {'✅' if ok else '❌'}",
        "",
        "<b>ไฟล์</b>:",
    ]
    if files:
        for it in files:
            name = _html_escape(str(it.get("file", "-")))
            fid = _short_id(it.get("id"))
            okf = "✅" if it.get("ok") else "❌"
            size = it.get("size") or "-"
            err = it.get("err")
            if err:
                err = _html_escape(str(err))
                lines.append(f"• <code>{name}</code> {okf} (id={fid}, size={size}) — <i>{err}</i>")
            else:
                lines.append(f"• <code>{name}</code> {okf} (id={fid}, size={size})")
    else:
        lines.append("• ไม่พบข้อมูลไฟล์ใน log")
    return "\n".join(lines)

def _with_progress(chat_id: int | str, kind: str, target, *args, **kwargs):
    # กันงานชนกันชนิดเดียว (backup/restore)
    with _inprogress_lock:
        if _inprogress.get(kind):
            send_message(chat_id, f"อีกงาน {kind} กำลังทำอยู่ กรุณารอสักครู่ก่อนนะครับ", parse_mode="HTML")
            return
        _inprogress[kind] = True

    def run():
        try:
            send_typing_action(chat_id)
            if args or kwargs:
                target(*args, **kwargs)
            else:
                target()
        except Exception as e:
            send_message(chat_id, f"❌ เกิดข้อผิดพลาดระหว่าง {kind}: <code>{_html_escape(str(e))}</code>", parse_mode="HTML")
        finally:
            with _inprogress_lock:
                _inprogress[kind] = False
            # ส่งสรุปสถานะล่าสุดเสมอ
            try:
                st = get_backup_status()
                send_message(chat_id, _format_status_for_telegram(st), parse_mode="HTML")
            except Exception as e2:
                send_message(chat_id, f"⚠️ อ่านสถานะล่าสุดไม่ได้: <code>{_html_escape(str(e2))}</code>", parse_mode="HTML")

    threading.Thread(target=run, daemon=True).start()

# ===== Entry for main_handler =====
def handle_backup_command(data: Dict[str, Any]) -> bool:
    """
    ตรวจจับและจัดการคำสั่งสำรอง/กู้คืนใน Telegram
    คืน True ถ้าจัดการแล้ว (เพื่อให้ main_handler return ได้เลย)
    """
    try:
        msg = data.get("message") or data.get("edited_message") or {}
        chat = msg.get("chat", {}) or {}
        chat_id = chat.get("id")
        text = (msg.get("text") or msg.get("caption") or "").strip()
        user = msg.get("from", {}) or {}
        user_id = user.get("id")

        if not text:
            return False

        lower = text.lower().strip()

        # /backup_status — ใครก็เห็นได้ (read-only)
        if lower.startswith("/backup_status"):
            st = get_backup_status()
            send_message(chat_id, _format_status_for_telegram(st), parse_mode="HTML")
            return True

        # ด้านล่างนี้ต้องเป็นแอดมินเท่านั้น
        if lower.startswith("/backup_now") or lower.startswith("/restore") or lower.startswith("/list_snapshots"):
            if not is_admin(user_id):
                send_message(chat_id, "คำสั่งนี้สำหรับแอดมินเท่านั้นครับ (โปรดตั้ง SUPER_ADMIN_ID/ADMIN_IDS)", parse_mode="HTML")
                return True

        # /backup_now
        if lower.startswith("/backup_now"):
            send_message(chat_id, "🗂️ กำลังเริ่มสำรองข้อมูลขึ้น Google Drive…", parse_mode="HTML")
            _with_progress(chat_id, "backup", backup_all)
            return True

        # /list_snapshots
        if lower.startswith("/list_snapshots"):
            snaps = list_snapshots()
            if snaps:
                lines = ["<b>🗓️ Snapshots (ใหม่ → เก่า)</b>"] + [f"• <code>{_html_escape(d)}</code>" for d in snaps]
                send_message(chat_id, "\n".join(lines), parse_mode="HTML")
            else:
                send_message(chat_id, "ยังไม่พบ snapshot ใน Google Drive ครับ", parse_mode="HTML")
            return True

        # /restore latest | /restore YYYY-MM-DD
        if lower.startswith("/restore"):
            parts = text.split()
            date_text = parts[1].strip() if len(parts) >= 2 else ""
            if date_text in ("", "latest", "ล่าสุด", "today", "วันนี้"):
                send_message(chat_id, "⏬ เริ่มกู้คืนไฟล์จากชุดล่าสุด…", parse_mode="HTML")
                _with_progress(chat_id, "restore", restore_all, None)  # โฟลเดอร์ราก (latest)
                return True
            # ตรวจรูปแบบวันที่
            try:
                datetime.strptime(date_text, "%Y-%m-%d")
            except Exception:
                send_message(chat_id, "รูปแบบวันที่ไม่ถูกต้องครับ ใช้ <code>/restore YYYY-MM-DD</code>", parse_mode="HTML")
                return True
            send_message(chat_id, f"⏬ เริ่มกู้คืนไฟล์จากชุดวันที่ <code>{_html_escape(date_text)}</code> …", parse_mode="HTML")
            _with_progress(chat_id, "restore", restore_all, date_text)
            return True

        return False
    except Exception as e:
        try:
            chat_id = ((data.get("message") or {}).get("chat") or {}).get("id")
            if chat_id:
                send_message(chat_id, f"❌ เกิดข้อผิดพลาดใน backup handler: <code>{_html_escape(str(e))}</code>", parse_mode="HTML")
        except Exception:
            pass
        return False

# handlers/utils.py
# -*- coding: utf-8 -*-
"""
Compatibility shim for handlers-layer utils.

❗️สิ่งที่เปลี่ยน:
- ไม่ยิง requests ตรง ๆ แล้ว
- ส่งงานต่อให้ utils.message_utils ซึ่งมี retry, แบ่งข้อความอัตโนมัติ (≤4096),
  no-echo blocker, และรองรับ parse_mode ("HTML"/"Markdown"/"MarkdownV2")

ทำไมต้องมีไฟล์นี้:
- เผื่อโค้ดเก่าเคย import จาก handlers.utils (เช่น send_message)
- ลดความสับสน: ทุกอย่างไปทางเดียวกับ utils.message_utils

แนะนำให้ import จาก utils.message_utils โดยตรงในโค้ดใหม่เสมอ
"""

from __future__ import annotations
from typing import Optional, Dict, Any

# รี-เอ็กซ์พอร์ตจากตัวที่เสถียร
from utils.message_utils import (
    send_message as _send_message,
    send_photo as _send_photo,
    send_document as _send_document,
    send_typing_action as _send_typing_action,
)

__all__ = [
    "send_message",
    "send_photo",
    "send_document",
    "send_chat_action",      # alias ให้โค้ดเก่า
    "send_typing_action",    # ชื่อจริงจาก utils.message_utils
]

def send_message(
    chat_id: int | str,
    text: str,
    parse_mode: Optional[str] = None,
    disable_preview: bool = True,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """ส่งข้อความด้วยตัวที่เสถียรจาก utils.message_utils"""
    _send_message(
        chat_id,
        text,
        parse_mode=parse_mode,
        disable_preview=disable_preview,
        reply_markup=reply_markup,
        reply_to_message_id=reply_to_message_id,
    )

def send_photo(
    chat_id: int | str,
    photo_url: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """ส่งรูปภาพ (รองรับ caption และ parse_mode)"""
    _send_photo(
        chat_id,
        photo_url,
        caption=caption,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        reply_to_message_id=reply_to_message_id,
    )

def send_document(
    chat_id: int | str,
    file_url: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """ส่งไฟล์เอกสาร/URL"""
    _send_document(
        chat_id,
        file_url,
        caption=caption,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        reply_to_message_id=reply_to_message_id,
    )

def send_typing_action(chat_id: int | str, action: str = "typing") -> None:
    """
    ส่งสถานะกำลังพิมพ์/อัปโหลด ฯลฯ
    action: typing|upload_photo|record_video|upload_video|record_voice|upload_voice|
            upload_document|choose_sticker|find_location|record_video_note|upload_video_note
    """
    _send_typing_action(chat_id, action)

# alias เพื่อความเข้ากันได้กับโค้ดเก่า
def send_chat_action(chat_id: int | str, action: str = "typing") -> None:
    send_typing_action(chat_id, action)

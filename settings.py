# settings.py
# -*- coding: utf-8 -*-
"""
Global settings สำหรับ TKC Telegram Bot
- อ่านค่าได้จาก Environment เพื่อปรับพฤติกรรมได้โดยไม่ต้องแก้โค้ด
- ค่าเริ่มต้นเหมาะกับ Asia/Bangkok และงานปัจจุบันของบอท
"""

from __future__ import annotations
import os
from typing import List, Dict

# ========== Helpers ==========
def _getenv_bool(name: str, default: bool = False) -> bool:
    val = str(os.getenv(name, "")).strip().lower()
    if val in {"1", "true", "yes", "on"}:
        return True
    if val in {"0", "false", "no", "off"}:
        return False
    return bool(default)

def _getenv_int(name: str, default: int, min_v: int | None = None, max_v: int | None = None) -> int:
    try:
        v = int(str(os.getenv(name, str(default))).strip())
    except Exception:
        v = default
    if min_v is not None:
        v = max(min_v, v)
    if max_v is not None:
        v = min(max_v, v)
    return v

def _norm_hour(v: int) -> int:   # 0..23
    return max(0, min(23, v))

def _norm_minute(v: int) -> int: # 0..59
    return max(0, min(59, v))


# ========== Global Flags ==========
DEBUG_MODE: bool = _getenv_bool("FLASK_DEBUG", False)
TIMEZONE: str = os.getenv("TZ", "Asia/Bangkok")


# ========== Backup Scheduler Config ==========
# กำหนดเวลาแบ็กอัป (Asia/Bangkok) — ดีฟอลต์ 00:09 น.
BACKUP_TIME_HOUR: int = _norm_hour(_getenv_int("BACKUP_TIME_HOUR", 0))
BACKUP_TIME_MINUTE: int = _norm_minute(_getenv_int("BACKUP_TIME_MINUTE", 9))


# ========== Telegram Webhook / Payload Limits ==========
# ใช้ควบคุมลิมิตเพย์โหลดที่ /webhook (main.py จะอ่าน ENV ตรง ๆ)
MAX_PAYLOAD_BYTES: int = _getenv_int("MAX_PAYLOAD_BYTES", 10 * 1024 * 1024)  # 10MB

# ลิมิตไฟล์/เวลาในการดาวน์โหลดไฟล์จาก Telegram (utils/telegram_file_utils ใช้งาน)
TG_MAX_FILE_BYTES: int = _getenv_int("TG_MAX_FILE_BYTES", 25 * 1024 * 1024)  # 25MB
TG_GET_TIMEOUT: float = float(os.getenv("TG_GET_TIMEOUT", "15"))
TG_DL_TIMEOUT: float = float(os.getenv("TG_DL_TIMEOUT", "60"))

# ประเภทอัปเดตที่อนุญาต (ใช้ตอน setWebhook ก็ได้)
TELEGRAM_ALLOWED_UPDATES: List[str] = ["message", "edited_message", "callback_query"]


# ========== Document Upload/Preview Support ==========
# หมายเหตุ: ให้ตรงกับ handler/doc.py ที่รองรับจริง
SUPPORTED_FORMATS: List[str] = [
    ".pdf",   # Portable Document Format
    ".docx",  # Microsoft Word Document
    ".txt",   # Plain Text
    ".xlsx",  # Microsoft Excel
    ".pptx",  # Microsoft PowerPoint
    ".jpg",   # JPEG Image
    ".jpeg",  # JPEG Image (alias)
    ".png",   # PNG Image
]

# mapping เสริม (เผื่อใช้อ้างอิงภายหลัง)
MIME_BY_EXT: Dict[str, str] = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt":  "text/plain; charset=utf-8",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
}

def is_supported_file(filename: str) -> bool:
    """เช็กว่านามสกุลไฟล์อยู่ใน SUPPORTED_FORMATS หรือไม่ (ไม่สนตัวพิมพ์)"""
    _, ext = os.path.splitext(filename or "")
    return (ext or "").lower() in SUPPORTED_FORMATS


# ========== Document Summarization Tunables ==========
# ใช้ร่วมกับ handlers/doc.py (รองรับไฟล์ยาวด้วยการแบ่งตอน)
DOC_SUMMARY_CHUNK_CHARS: int = _getenv_int("DOC_SUMMARY_CHUNK_CHARS", 6000, 1000, 20000)
DOC_SUMMARY_MAX_CHUNKS: int = _getenv_int("DOC_SUMMARY_MAX_CHUNKS", 8, 1, 20)


# ========== OpenAI Model Defaults (อ้างอิง/เอกสาร) ==========
# โค้ดจริงอ่านจาก utils/openai_client.py แต่ตั้งค่าที่นี่ไว้เป็นเอกภาพของโปรเจกต์
OPENAI_MODEL_DEFAULT: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_MODEL_STRONG: str  = os.getenv("OPENAI_MODEL_STRONG", "gpt-5")
OPENAI_MODEL_VISION: str  = os.getenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
OPENAI_MODEL_IMAGE: str   = os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-1")


# ===== Optional extras (safe to add) =====
# เผื่อผู้ใช้ส่งเป็นเอกสารแนวตาราง/รูปแบบ mobile (ยังไม่ได้เปิดใช้ใน handlers/doc.py)
SUPPORTED_FORMATS_EXTRA: List[str] = [
    ".csv",   # Comma-Separated Values
    ".xls",   # Excel format เก่า (ถ้าจะรองรับต้องเพิ่ม extractor)
    ".heic",  # บางคนส่งภาพจาก iPhone เป็นเอกสาร (Telegram มักแปลงเป็น JPEG ในโหมด photo)
]

# Path สำหรับ health check (main.py ตั้งไว้แล้วที่ /healthz)
HEALTHCHECK_PATH: str = os.getenv("HEALTHCHECK_PATH", "/healthz")

def config_summary() -> Dict[str, str]:
    """สรุปค่าคอนฟิกสำคัญ (ไม่โชว์ secrets) ใช้พิมพ์ตอนเริ่มระบบเพื่อดีบักง่าย ๆ"""
    return {
        "DEBUG_MODE": str(DEBUG_MODE),
        "TIMEZONE": TIMEZONE,
        "BACKUP_AT": f"{BACKUP_TIME_HOUR:02d}:{BACKUP_TIME_MINUTE:02d}",
        "MAX_PAYLOAD_BYTES": str(MAX_PAYLOAD_BYTES),
        "TG_MAX_FILE_BYTES": str(TG_MAX_FILE_BYTES),
        "TELEGRAM_ALLOWED_UPDATES": ",".join(TELEGRAM_ALLOWED_UPDATES),
        "OPENAI_MODEL_DEFAULT": OPENAI_MODEL_DEFAULT,
        "OPENAI_MODEL_STRONG": OPENAI_MODEL_STRONG,
        "OPENAI_MODEL_VISION": OPENAI_MODEL_VISION,
        "OPENAI_MODEL_IMAGE": OPENAI_MODEL_IMAGE,
        "HEALTHCHECK_PATH": HEALTHCHECK_PATH,
    }

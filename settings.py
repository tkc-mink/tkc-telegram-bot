# settings.py
# -*- coding: utf-8 -*-
"""
Global settings สำหรับ TKC Telegram Bot
- อ่านค่าได้จาก Environment เพื่อปรับพฤติกรรมได้โดยไม่ต้องแก้โค้ด
- ค่าเริ่มต้นเหมาะกับ Asia/Bangkok และงานปัจจุบันของบอท
- ปลอดภัยและยืดหยุ่นขึ้น: size suffix, TZ sync, ENV overrides
"""

from __future__ import annotations
from typing import List, Dict, Any
import os
import mimetypes
import time

# ========== Helpers ==========
_TRUTHY = {"1", "true", "yes", "on"}
_FALSY  = {"0", "false", "no", "off"}

def _getenv_bool(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if raw in _TRUTHY: return True
    if raw in _FALSY:  return False
    return bool(default)

def _getenv_int(name: str, default: int, min_v: int | None = None, max_v: int | None = None) -> int:
    try:
        v = int(str(os.getenv(name, str(default))).strip())
    except Exception:
        v = default
    if min_v is not None: v = max(min_v, v)
    if max_v is not None: v = min(max_v, v)
    return v

def _getenv_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default

def _norm_hour(v: int) -> int:   # 0..23
    return max(0, min(23, v))

def _norm_minute(v: int) -> int: # 0..59
    return max(0, min(59, v))

def _getenv_csv(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [s.strip() for s in raw.split(",") if s.strip()]

_SIZE_UNITS = {
    "b": 1,
    "kb": 1024,
    "mb": 1024**2,
    "gb": 1024**3,
}
def _getenv_size(name: str, default_bytes: int) -> int:
    """รองรับรูปแบบเช่น 1048576, '1MB', '250kb'"""
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default_bytes
    try:
        # pure int
        return max(0, int(raw))
    except ValueError:
        pass
    # with suffix
    for unit in ("gb", "mb", "kb", "b"):
        if raw.endswith(unit):
            num = raw[: -len(unit)].strip()
            try:
                val = float(num) * _SIZE_UNITS[unit]
                return int(max(0, val))
            except Exception:
                break
    # fallback
    try:
        return max(0, int(float(raw)))
    except Exception:
        return default_bytes


# ========== Global Flags ==========
DEBUG_MODE: bool = _getenv_bool("FLASK_DEBUG", False)

# เวลา: sync TZ ให้ทั้งระบบ (Unix เท่านั้นใช้ tzset ได้) และให้โมดูลที่อ่าน APP_TZ
TIMEZONE: str = os.getenv("TZ", os.getenv("TIMEZONE", "Asia/Bangkok"))
os.environ["TZ"] = TIMEZONE
os.environ.setdefault("APP_TZ", TIMEZONE)  # ให้ utils อื่น ๆ ที่อ่าน APP_TZ เห็นค่าเดียวกัน
try:
    if hasattr(time, "tzset"):
        time.tzset()  # บางแพลตฟอร์ม (Windows) ไม่มี
except Exception:
    pass


# ========== Backup Scheduler Config ==========
# กำหนดเวลาแบ็กอัป (Asia/Bangkok) — ดีฟอลต์ 00:09 น.
BACKUP_TIME_HOUR: int = _norm_hour(_getenv_int("BACKUP_TIME_HOUR", 0))
BACKUP_TIME_MINUTE: int = _norm_minute(_getenv_int("BACKUP_TIME_MINUTE", 9))


# ========== Telegram Webhook / Payload Limits ==========
# ใช้ควบคุมลิมิตเพย์โหลดที่ /webhook (main.py จะอ่าน ENV ตรง ๆ)
# รองรับรูปแบบ ENV เป็น bytes หรือมี suffix เช่น "10MB"
MAX_PAYLOAD_BYTES: int = _getenv_size("MAX_PAYLOAD_BYTES", 10 * 1024 * 1024)  # 10MB

# ลิมิตไฟล์/เวลาในการดาวน์โหลดไฟล์จาก Telegram (utils/telegram_file_utils ใช้งาน)
TG_MAX_FILE_BYTES: int = _getenv_size("TG_MAX_FILE_BYTES", 25 * 1024 * 1024)  # 25MB
TG_GET_TIMEOUT: float = _getenv_float("TG_GET_TIMEOUT", 15.0)
TG_DL_TIMEOUT: float = _getenv_float("TG_DL_TIMEOUT", 60.0)

# ประเภทอัปเดตที่อนุญาต (อ่านจาก ENV เป็น CSV ได้ เช่น "message,callback_query")
_TELEGRAM_ALLOWED_UPDATES_DEFAULT: List[str] = ["message", "edited_message", "callback_query"]
TELEGRAM_ALLOWED_UPDATES: List[str] = _getenv_csv("TELEGRAM_ALLOWED_UPDATES", _TELEGRAM_ALLOWED_UPDATES_DEFAULT)


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

# เผื่อผู้ใช้ส่งเป็นเอกสารแนวตาราง/รูปแบบ mobile (ยังไม่ได้เปิดใช้ใน handlers/doc.py)
SUPPORTED_FORMATS_EXTRA: List[str] = [
    ".csv",   # Comma-Separated Values
    ".xls",   # Excel format เก่า (ถ้าจะรองรับต้องเพิ่ม extractor)
    ".heic",  # บางคนส่งภาพจาก iPhone เป็นเอกสาร
]
ENABLE_EXTRA_FORMATS: bool = _getenv_bool("ENABLE_EXTRA_FORMATS", False)

def _effective_exts() -> List[str]:
    if ENABLE_EXTRA_FORMATS:
        # รวมโดยคงลำดับ และไม่ซ้ำ
        seen = set()
        out: List[str] = []
        for ext in SUPPORTED_FORMATS + SUPPORTED_FORMATS_EXTRA:
            e = (ext or "").lower()
            if e and e not in seen:
                seen.add(e)
                out.append(e)
        return out
    return list(SUPPORTED_FORMATS)

def is_supported_file(filename: str) -> bool:
    """เช็กว่านามสกุลไฟล์อยู่ในรายการรองรับ (ไม่สนตัวพิมพ์)"""
    _, ext = os.path.splitext(filename or "")
    return (ext or "").lower() in set(_effective_exts())

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
    ".csv":  "text/csv; charset=utf-8",
    ".xls":  "application/vnd.ms-excel",
    ".heic": "image/heic",
}

def mime_for(filename: str) -> str:
    """เดา MIME ของไฟล์ จาก map ภายในก่อน แล้วค่อย fallback ไปที่ mimetypes"""
    _, ext = os.path.splitext(filename or "")
    ext_l = (ext or "").lower()
    if ext_l in MIME_BY_EXT:
        return MIME_BY_EXT[ext_l]
    guess, _ = mimetypes.guess_type(filename or "")
    return guess or "application/octet-stream"


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


# ========== Health / Misc ==========
HEALTHCHECK_PATH: str = os.getenv("HEALTHCHECK_PATH", "/healthz")


# ========== Config Summary ==========
def config_summary() -> Dict[str, str]:
    """สรุปค่าคอนฟิกสำคัญ (ไม่โชว์ secrets) ใช้พิมพ์ตอนเริ่มระบบเพื่อดีบักง่าย ๆ"""
    eff_exts = ",".join(_effective_exts())
    return {
        "DEBUG_MODE": str(DEBUG_MODE),
        "TIMEZONE": TIMEZONE,
        "BACKUP_AT": f"{BACKUP_TIME_HOUR:02d}:{BACKUP_TIME_MINUTE:02d}",
        "MAX_PAYLOAD_BYTES": str(MAX_PAYLOAD_BYTES),
        "TG_MAX_FILE_BYTES": str(TG_MAX_FILE_BYTES),
        "TG_GET_TIMEOUT": str(TG_GET_TIMEOUT),
        "TG_DL_TIMEOUT": str(TG_DL_TIMEOUT),
        "TELEGRAM_ALLOWED_UPDATES": ",".join(TELEGRAM_ALLOWED_UPDATES),
        "OPENAI_MODEL_DEFAULT": OPENAI_MODEL_DEFAULT,
        "OPENAI_MODEL_STRONG": OPENAI_MODEL_STRONG,
        "OPENAI_MODEL_VISION": OPENAI_MODEL_VISION,
        "OPENAI_MODEL_IMAGE": OPENAI_MODEL_IMAGE,
        "HEALTHCHECK_PATH": HEALTHCHECK_PATH,
        "SUPPORTED_FORMATS_EFFECTIVE": eff_exts,
        "ENABLE_EXTRA_FORMATS": str(ENABLE_EXTRA_FORMATS),
    }

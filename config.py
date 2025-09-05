# config.py
# -*- coding: utf-8 -*-
"""
Central configuration — safe & robust
- ไม่ล้มตอน import แม้ยังไม่มี ENV ครบ
- ยึดชื่อคีย์มาตรฐาน: GOOGLE_API_KEY (รองรับ alias GEMINI_API_KEY/PALM_API_KEY)
- รวมค่าที่ใช้ทั้งโปรเจกต์ + Orchestrator
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import os

# ---------- helpers ----------
def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)

def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def env_int(name: str, default: int, *, min_v: int | None = None, max_v: int | None = None) -> int:
    try:
        val = int(os.getenv(name, str(default)))
    except Exception:
        val = default
    if min_v is not None:
        val = max(min_v, val)
    if max_v is not None:
        val = min(max_v, val)
    return val

def env_float(name: str, default: float, *, min_v: float | None = None, max_v: float | None = None) -> float:
    try:
        val = float(os.getenv(name, str(default)))
    except Exception:
        val = default
    if min_v is not None:
        val = max(min_v, val)
    if max_v is not None:
        val = min(max_v, val)
    return val

def env_list(name: str, default: Optional[List[str]] = None, sep: str = ",") -> List[str]:
    s = os.getenv(name)
    if not s:
        return default or []
    # รองรับทั้ง comma และ semicolon
    s = s.replace(";", sep)
    out = [x.strip() for x in s.split(sep) if x.strip()]
    # กันซ้ำแบบ preserve order
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); uniq.append(x)
    return uniq

def _first(*vals: Optional[str], default: str = "") -> str:
    for v in vals:
        if v and str(v).strip():
            return str(v).strip()
    return default

def _mask(s: Optional[str]) -> str:
    if not s:
        return ""
    s = str(s)
    return s if len(s) <= 6 else f"{s[:3]}…{s[-3:]}"


# ---------- paths ----------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- tokens / keys (มาตรฐานเดียว) ----------
TELEGRAM_BOT_TOKEN    = _first(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_TOKEN"))
TELEGRAM_SECRET_TOKEN = env("TELEGRAM_SECRET_TOKEN", "").strip()

OPENAI_API_KEY = _first(env("OPENAI_API_KEY"), env("OPENAI_KEY"), env("OPENAI_SECRET_KEY"))
# มาตรฐานคือ GOOGLE_API_KEY; alias รองรับของเดิม
GOOGLE_API_KEY = _first(env("GOOGLE_API_KEY"), env("GEMINI_API_KEY"), env("PALM_API_KEY"))

TELEGRAM_TOKEN_SET = bool(TELEGRAM_BOT_TOKEN)
OPENAI_KEY_SET     = bool(OPENAI_API_KEY)
GOOGLE_KEY_SET     = bool(GOOGLE_API_KEY)

# ---------- models / router ----------
OPENAI_MODEL_DIALOGUE = _first(
    env("OPENAI_MODEL_DIALOGUE"),
    env("OPENAI_MODEL"),
    env("OPENAI_MODEL_STRONG"),
    default="gpt-4o-mini",
)

GEMINI_MODEL_DIALOGUE = _first(
    env("GEMINI_MODEL_DIALOGUE"),
    env("GEMINI_MODEL"),
    env("GOOGLE_MODEL"),
    default="gemini-1.5-pro",
)

ROUTER_MODE           = env("ROUTER_MODE", "hybrid")   # hybrid | gpt | gemini
ROUTER_MIN_CONFIDENCE = env_float("ROUTER_MIN_CONFIDENCE", 0.55, min_v=0.0, max_v=1.0)

# ---------- web / server ----------
MAX_PAYLOAD_BYTES       = env_int("MAX_PAYLOAD_BYTES",       10 * 1024 * 1024, min_v=1024)   # 10MB
MAX_DECOMPRESSED_BYTES  = env_int("MAX_DECOMPRESSED_BYTES",  20 * 1024 * 1024, min_v=2048)   # 20MB
ENABLE_BACKUP_SCHEDULER = env_bool("ENABLE_BACKUP_SCHEDULER", True)
TRUST_PROXY_HEADERS     = env_bool("TRUST_PROXY_HEADERS", True)
LOG_JSON                = env_bool("LOG_JSON", False)

# เส้นทาง webhook (เผื่อใช้งานในส่วนอื่น ๆ)
TELEGRAM_WEBHOOK_PATH   = env("TELEGRAM_WEBHOOK_PATH", "/webhook")

# ---------- db / files ----------
BOT_MEMORY_DB_FILE = env("BOT_MEMORY_DB_FILE", "bot_memory.db")

USAGE_FILE        = env("USAGE_FILE",        os.path.join(DATA_DIR, "usage.json"))
IMAGE_USAGE_FILE  = env("IMAGE_USAGE_FILE",  os.path.join(DATA_DIR, "image_usage.json"))
CONTEXT_FILE      = env("CONTEXT_FILE",      os.path.join(DATA_DIR, "context_history.json"))
CONTEXT_MSG_FILE  = env("CONTEXT_MSG_FILE",  os.path.join(DATA_DIR, "context_messages.json"))
LOCATION_FILE     = env("LOCATION_FILE",     os.path.join(DATA_DIR, "location_logs.json"))

# ---------- limits / access ----------
MAX_QUESTION_PER_DAY = env_int("MAX_QUESTION_PER_DAY", 30, min_v=1)
MAX_IMAGE_PER_DAY    = env_int("MAX_IMAGE_PER_DAY",    15, min_v=1)
EXEMPT_USER_IDS      = env_list("EXEMPT_USER_IDS", ["6849909227"])

# ---------- (optional) supported formats from settings.py ----------
try:
    from settings import SUPPORTED_FORMATS  # type: ignore
except Exception:
    SUPPORTED_FORMATS: List[str] = []

# ---------- build info ----------
GIT_SHA    = env("GIT_SHA", "")
BUILD_TIME = env("BUILD_TIME", "")

# ---------- diagnostics / validation ----------
def missing_required() -> List[str]:
    missing: List[str] = []
    if not TELEGRAM_TOKEN_SET:
        missing.append("TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN")
    return missing

def missing_recommended() -> List[str]:
    out: List[str] = []
    if not OPENAI_KEY_SET:
        out.append("OPENAI_API_KEY")
    if not GOOGLE_KEY_SET:
        out.append("GOOGLE_API_KEY")
    if not TELEGRAM_SECRET_TOKEN:
        out.append("TELEGRAM_SECRET_TOKEN")
    return out

def diag() -> Dict[str, Any]:
    """ข้อมูลสำหรับ /diag (mask คีย์)"""
    return {
        "env": {
            "telegram_token_set": TELEGRAM_TOKEN_SET,
            "openai_key_set": OPENAI_KEY_SET,
            "google_key_set": GOOGLE_KEY_SET,
            "openai_model": OPENAI_MODEL_DIALOGUE,
            "gemini_model": GEMINI_MODEL_DIALOGUE,
            "router_mode": ROUTER_MODE,
            "router_min_confidence": ROUTER_MIN_CONFIDENCE,
            "webhook_path": TELEGRAM_WEBHOOK_PATH,
        },
        "paths": {
            "root_dir": ROOT_DIR,
            "data_dir": DATA_DIR,
            "db_file": BOT_MEMORY_DB_FILE,
            "usage_file": USAGE_FILE,
            "image_usage_file": IMAGE_USAGE_FILE,
            "context_file": CONTEXT_FILE,
            "context_msg_file": CONTEXT_MSG_FILE,
            "location_file": LOCATION_FILE,
        },
        "build": {"git_sha": _mask(GIT_SHA), "build_time": BUILD_TIME},
        "supported_formats": SUPPORTED_FORMATS,
        "secrets_masked": {
            "telegram_secret_token": bool(TELEGRAM_SECRET_TOKEN),
            "openai_api_key": _mask(OPENAI_API_KEY),
            "google_api_key": _mask(GOOGLE_API_KEY),
        },
    }

__all__ = [
    # helpers
    "env", "env_bool", "env_int", "env_float", "env_list", "diag",
    # tokens/keys
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_SECRET_TOKEN",
    "OPENAI_API_KEY", "GOOGLE_API_KEY",
    "TELEGRAM_TOKEN_SET", "OPENAI_KEY_SET", "GOOGLE_KEY_SET",
    # models/router
    "OPENAI_MODEL_DIALOGUE", "GEMINI_MODEL_DIALOGUE",
    "ROUTER_MODE", "ROUTER_MIN_CONFIDENCE",
    # server
    "MAX_PAYLOAD_BYTES", "MAX_DECOMPRESSED_BYTES",
    "ENABLE_BACKUP_SCHEDULER", "TRUST_PROXY_HEADERS", "LOG_JSON",
    "TELEGRAM_WEBHOOK_PATH",
    # files/db
    "ROOT_DIR", "DATA_DIR", "BOT_MEMORY_DB_FILE",
    "USAGE_FILE", "IMAGE_USAGE_FILE", "CONTEXT_FILE", "CONTEXT_MSG_FILE", "LOCATION_FILE",
    # limits
    "MAX_QUESTION_PER_DAY", "MAX_IMAGE_PER_DAY", "EXEMPT_USER_IDS",
    # settings/build
    "SUPPORTED_FORMATS", "GIT_SHA", "BUILD_TIME",
    # validation
    "missing_required", "missing_recommended",
]

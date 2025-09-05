# utils/telegram_file_utils.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import re
import json
import time
import tempfile
from typing import Optional, Dict, Any, Tuple

import requests

from utils.message_utils import get_telegram_token

# ===== Tunables / ENV =====
TG_GET_TIMEOUT        = float(os.getenv("TG_GET_TIMEOUT", "15"))       # วินาที: เรียก getFile
TG_DL_TIMEOUT         = float(os.getenv("TG_DL_TIMEOUT", "60"))        # วินาที: ดาวน์โหลดไฟล์
TG_CHUNK_SIZE         = int(os.getenv("TG_CHUNK_SIZE", str(1024 * 128)))  # 128 KB
TG_MAX_FILE_BYTES     = int(os.getenv("TG_MAX_FILE_BYTES", str(25 * 1024 * 1024)))  # 25MB
TG_RETRIES            = int(os.getenv("TG_RETRIES", "2"))              # จำนวน retry เพิ่มเติม (รวมทั้งหมด ~ 1+TG_RETRIES)
TG_BACKOFF_BASE_SEC   = float(os.getenv("TG_BACKOFF_BASE_SEC", "0.4")) # หน่วงฐานสำหรับ backoff
TG_TEMP_DIR           = os.getenv("TG_TEMP_DIR", "")                   # โฟลเดอร์ temp กำหนดเอง (ไม่ระบุ = ระบบ)
TG_ALLOWED_EXT        = os.getenv("TG_ALLOWED_EXT", "")                # ตัวอย่าง ".pdf,.docx,.xlsx" (ว่าง = อนุญาตทุกชนิด)

# ===== Utilities =====
def _log(tag: str, **kw):
    try:
        print(f"[telegram_file_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[telegram_file_utils] {tag} :: {kw}")

def _sanitize_prefix(name: str) -> str:
    """
    sanitize ชื่อสำหรับ prefix ของไฟล์ชั่วคราว (ตัดอันตราย/อักขระแปลก)
    อนุญาตอักษรไทย อังกฤษ ตัวเลข จุด ขีดล่าง ขีดกลาง ช่องว่าง
    """
    name = os.path.splitext(os.path.basename(name or "tg"))[0]
    name = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9._\-\s]+", "_", name)
    name = name.strip().replace(" ", "_")
    return (name[:40] or "tg")

def _safe_unlink(path: str):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass

def _retry_sleep(attempt: int, retry_after: Optional[float] = None):
    # ถ้า Telegram ส่ง retry_after มาก็ให้เคารพ แต่จำกัดไม่เกิน 3s เพื่อไม่บล็อคระบบ
    if retry_after is not None:
        time.sleep(min(float(retry_after), 3.0))
        return
    # exponential backoff + jitter เล็กน้อย
    delay = TG_BACKOFF_BASE_SEC * (2 ** max(0, attempt - 1))
    delay += 0.05 * attempt
    time.sleep(min(delay, 2.5))

def _allowed_ext_list() -> set[str]:
    if not TG_ALLOWED_EXT.strip():
        return set()
    items = [x.strip().lower() for x in TG_ALLOWED_EXT.split(",") if x.strip()]
    return set(items)

def _ensure_temp_dir() -> str:
    if TG_TEMP_DIR:
        try:
            os.makedirs(TG_TEMP_DIR, exist_ok=True)
            return TG_TEMP_DIR
        except Exception as e:
            _log("TEMP_DIR_ERROR", err=str(e), fallback=tempfile.gettempdir())
    return tempfile.gettempdir()

# ===== Public: getFile metadata =====
def get_file_info(file_id: str) -> Optional[Dict[str, Any]]:
    """
    คืน metadata จาก Telegram getFile:
    { "file_id": ..., "file_unique_id": ..., "file_size": int, "file_path": "photos/..../file.jpg" }
    """
    token = get_telegram_token()
    if not token:
        _log("NO_TOKEN")
        return None

    url = f"https://api.telegram.org/bot{token}/getFile"
    params = {"file_id": file_id}
    last_err = None

    for attempt in range(1, TG_RETRIES + 2):  # 1..(1+retries)
        try:
            r = requests.get(url, params=params, timeout=TG_GET_TIMEOUT)
            if r.status_code == 429:  # Too Many Requests
                retry_after = None
                try:
                    j = r.json()
                    retry_after = j.get("parameters", {}).get("retry_after")
                except Exception:
                    pass
                _log("GETFILE_429", attempt=attempt, retry_after=retry_after)
                _retry_sleep(attempt, retry_after)
                continue

            if not r.ok:
                _log("GETFILE_HTTP_ERROR", status=r.status_code, body=r.text[:200])
                last_err = f"http {r.status_code}"
                _retry_sleep(attempt)
                continue

            try:
                j = r.json()
            except Exception:
                _log("GETFILE_JSON_ERROR", body=r.text[:200])
                last_err = "json"
                _retry_sleep(attempt)
                continue

            if not j.get("ok"):
                _log("GETFILE_NOT_OK", resp=j)
                last_err = "not_ok"
                _retry_sleep(attempt)
                continue

            result = j.get("result") or {}
            if not result.get("file_path"):
                _log("MISSING_FILE_PATH", resp=j)
                last_err = "missing_path"
                _retry_sleep(attempt)
                continue

            return result

        except requests.RequestException as e:
            last_err = str(e)
            _log("GETFILE_REQUEST_ERROR", attempt=attempt, err=str(e))
            _retry_sleep(attempt)
        except Exception as e:
            last_err = str(e)
            _log("GETFILE_UNKNOWN_ERROR", attempt=attempt, err=str(e))
            _retry_sleep(attempt)

    _log("GETFILE_GIVEUP", last_err=last_err)
    return None

# ===== Internal: streaming download =====
def _download_stream(file_url: str, out_fd: int, limit_bytes: int) -> Tuple[bool, int, Optional[str]]:
    """
    สตรีมดาวน์โหลดไปยัง file descriptor (out_fd)
    คืน (ok, written_bytes, err_msg)
    """
    written = 0
    try:
        with requests.get(file_url, stream=True, timeout=TG_DL_TIMEOUT) as resp:
            if not resp.ok:
                return False, 0, f"http {resp.status_code}: {resp.text[:200]}"

            # ตรวจ Content-Length หากมี
            cl = resp.headers.get("content-length")
            if cl:
                try:
                    total = int(cl)
                    if total > limit_bytes:
                        return False, 0, f"too_large(cl={total})"
                except Exception:
                    pass

            with os.fdopen(out_fd, "wb") as f:
                for chunk in resp.iter_content(TG_CHUNK_SIZE):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > limit_bytes:
                        return False, written, f"over_limit({written}>{limit_bytes})"
                    f.write(chunk)
        return (written > 0), written, None
    except requests.RequestException as e:
        return False, written, f"network:{e}"
    except Exception as e:
        return False, written, f"unknown:{e}"

# ===== Public: download (compat) =====
def download_telegram_file(file_id: str, suggested_name: Optional[str] = None) -> str:
    """
    ดาวน์โหลดไฟล์จาก Telegram แล้วคืน path ชั่วคราว (string)
    - คง signature เดิมเพื่อความเข้ากันได้
    - จำกัดขนาดไฟล์ตาม TG_MAX_FILE_BYTES (ดีฟอลต์ 25MB)
    - สร้างไฟล์ชั่วคราวด้วย prefix ปลอดภัย + นามสกุลตามจริง (ถ้ามี)
    - คืน "" หากผิดพลาด
    """
    try:
        meta = download_telegram_file_ex(file_id, suggested_name=suggested_name)
        return meta.get("path", "") if meta else ""
    except Exception as e:
        _log("DOWNLOAD_COMPAT_ERROR", err=str(e))
        return ""

# ===== Public: download (extended metadata) =====
def download_telegram_file_ex(
    file_id: str,
    suggested_name: Optional[str] = None,
    *,
    max_bytes: Optional[int] = None,
    allowed_ext: Optional[set[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    ดาวน์โหลดไฟล์จาก Telegram (เวอร์ชันคืน meta):
    คืน dict:
    {
      "path": "/tmp/tg_....pdf",
      "ext": ".pdf",
      "file_size": 12345,
      "file_id": "...",
      "file_unique_id": "...",
      "mime_type": "<unknown>",     # Telegram getFile ไม่ส่ง mime; ใส่ "-" ไว้เป็นที่หมาย
      "file_path": "documents/file_...pdf"
    }
    กรณีผิดพลาด คืน None
    """
    token = get_telegram_token()
    if not token:
        _log("NO_TOKEN")
        return None

    info = get_file_info(file_id)
    if not info:
        return None

    file_path = info.get("file_path")
    file_unique_id = info.get("file_unique_id")
    file_size = int(info.get("file_size") or 0)

    # เลือกนามสกุลจาก file_path หรือ suggested_name
    ext = os.path.splitext(file_path)[1]
    if not ext and suggested_name:
        ext = os.path.splitext(suggested_name)[1]
    ext = ext or ""

    # sanitize ext (กันอักขระแปลก ๆ)
    if ext and not re.fullmatch(r"\.[0-9A-Za-z]{1,8}", ext):
        # ถ้า ext แปลกเกินไป ตัดทิ้ง
        _log("WEIRD_EXT_STRIPPED", ext=ext)
        ext = ""

    # ตรวจ whitelist ของนามสกุล ถ้ากำหนดไว้
    allow = allowed_ext if allowed_ext is not None else _allowed_ext_list()
    if allow and ext.lower() not in allow:
        _log("EXT_NOT_ALLOWED", ext=ext, allowed=list(allow))
        return None

    # ตรวจขนาดจาก getFile เบื้องต้น
    limit = int(max_bytes if max_bytes is not None else TG_MAX_FILE_BYTES)
    if file_size and file_size > limit:
        _log("SIZE_OVER_LIMIT(getFile)", size=file_size, limit=limit)
        return None

    # สร้างไฟล์ปลายทาง
    temp_dir = _ensure_temp_dir()
    prefix = _sanitize_prefix(suggested_name or os.path.basename(file_path) or "tg") + "_"
    try:
        fd, out_path = tempfile.mkstemp(prefix=prefix, suffix=ext, dir=temp_dir)
    except Exception as e:
        _log("MKSTEMP_ERROR", err=str(e))
        return None

    close_fd = True
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    last_err = None

    # ดาวน์โหลดด้วย retry
    for attempt in range(1, TG_RETRIES + 2):
        ok, written, err = _download_stream(file_url, fd, limit)
        if ok:
            close_fd = False  # ถูกปิดแล้วใน _download_stream
            _log("DOWNLOAD_OK", out_path=out_path, bytes=written)
            return {
                "path": out_path,
                "ext": ext or "",
                "file_size": written if written else file_size,
                "file_id": file_id,
                "file_unique_id": file_unique_id,
                "mime_type": "-",  # Telegram ไม่ส่ง mime ใน getFile
                "file_path": file_path,
            }
        else:
            last_err = err
            _log("DOWNLOAD_ATTEMPT_FAIL", attempt=attempt, err=str(err))
            # ถ้า failure ก่อนเปิดไฟล์สำเร็จ ต้องปิด fd เอง
            if attempt < (TG_RETRIES + 1):
                try:
                    # เปิด fd ใหม่สำหรับรอบถัดไป (รอบก่อน f ปิดไปแล้วใน _download_stream)
                    fd = os.open(out_path, os.O_WRONLY | os.O_TRUNC)
                except Exception as e:
                    _log("REOPEN_FD_ERROR", err=str(e))
                    break
                _retry_sleep(attempt)
            else:
                break

    # ล้มเหลวทั้งหมด
    try:
        if close_fd:
            os.close(fd)
    except Exception:
        pass
    _safe_unlink(out_path)
    _log("DOWNLOAD_GIVEUP", err=last_err)
    return None

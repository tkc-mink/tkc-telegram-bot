# utils/telegram_file_utils.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import re
import requests
import tempfile
from typing import Optional

from utils.message_utils import get_telegram_token

# ===== Tunables / ENV =====
TG_GET_TIMEOUT   = float(os.getenv("TG_GET_TIMEOUT", "15"))     # วินาที: เรียก getFile
TG_DL_TIMEOUT    = float(os.getenv("TG_DL_TIMEOUT", "60"))      # วินาที: ดาวน์โหลดไฟล์
TG_CHUNK_SIZE    = 1024 * 64                                    # 64 KB
TG_MAX_FILE_BYTES = int(os.getenv("TG_MAX_FILE_BYTES", str(25 * 1024 * 1024)))  # 25MB

def _log(tag: str, **kw):
    try:
        import json
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

def download_telegram_file(file_id: str, suggested_name: Optional[str] = None) -> str:
    """
    ดาวน์โหลดไฟล์จาก Telegram แล้วคืน path ชั่วคราว (string)
    - ตรวจสอบ {"ok": true} จาก getFile
    - จำกัดขนาดไฟล์ตาม TG_MAX_FILE_BYTES (ดีฟอลต์ 25MB)
    - สร้างไฟล์ชั่วคราวด้วย prefix ปลอดภัย + นามสกุลตามจริง
    - คืน "" หากผิดพลาด
    """
    token = get_telegram_token()
    if not token:
        _log("NO_TOKEN")
        return ""

    # 1) ขอ file_path ด้วย getFile
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=TG_GET_TIMEOUT,
        )
    except Exception as e:
        _log("GETFILE_REQUEST_ERROR", err=str(e))
        return ""

    if not r.ok:
        _log("GETFILE_HTTP_ERROR", status=r.status_code, body=r.text[:200])
        return ""

    try:
        j = r.json()
    except Exception:
        _log("GETFILE_JSON_ERROR", body=r.text[:200])
        return ""

    if not j.get("ok"):
        _log("GETFILE_NOT_OK", resp=j)
        return ""

    result = j.get("result") or {}
    file_path = result.get("file_path")
    if not file_path:
        _log("MISSING_FILE_PATH", resp=j)
        return ""

    # เดา/เลือกนามสกุล
    ext = os.path.splitext(file_path)[1]
    if not ext and suggested_name:
        ext = os.path.splitext(suggested_name)[1]
    ext = ext or ""

    # 2) เตรียมไฟล์ temp
    prefix = _sanitize_prefix(suggested_name or "tg") + "_"
    fd, out_path = tempfile.mkstemp(prefix=prefix, suffix=ext)
    close_fd = True

    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    try:
        with requests.get(file_url, stream=True, timeout=TG_DL_TIMEOUT) as resp:
            if not resp.ok:
                _log("DOWNLOAD_HTTP_ERROR", status=resp.status_code, body=resp.text[:200])
                os.close(fd)
                _safe_unlink(out_path)
                return ""

            # เช็ก Content-Length ถ้ามี
            cl = resp.headers.get("content-length")
            if cl:
                try:
                    total = int(cl)
                    if total > TG_MAX_FILE_BYTES:
                        _log("DOWNLOAD_TOO_LARGE", content_length=total, limit=TG_MAX_FILE_BYTES)
                        os.close(fd)
                        _safe_unlink(out_path)
                        return ""
                except Exception:
                    pass

            # เขียนไฟล์เป็นชิ้น ๆ และตรวจขนาดสะสม
            written = 0
            with os.fdopen(fd, "wb") as f:
                close_fd = False
                for chunk in resp.iter_content(TG_CHUNK_SIZE):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > TG_MAX_FILE_BYTES:
                        _log("DOWNLOAD_OVER_LIMIT", written=written, limit=TG_MAX_FILE_BYTES)
                        _safe_unlink(out_path)
                        return ""
                    f.write(chunk)

        # สำเร็จ
        _log("DOWNLOAD_OK", out_path=out_path, bytes=written if 'written' in locals() else None)
        return out_path

    except Exception as e:
        _log("DOWNLOAD_STREAM_ERROR", err=str(e))
        try:
            if close_fd:
                os.close(fd)
        except Exception:
            pass
        _safe_unlink(out_path)
        return ""

# utils/telegram_file_utils.py
# -*- coding: utf-8 -*-
import os
import requests
import tempfile
from typing import Optional

from utils.message_utils import get_telegram_token

def download_telegram_file(file_id: str, suggested_name: Optional[str] = None) -> str:
    """
    ดาวน์โหลดไฟล์จาก Telegram แล้วคืน path ชั่วคราวของไฟล์ (string)
    - ตรวจสอบผลลัพธ์ getFile ว่า {"ok": true} จริง (ไม่ใช่แค่ HTTP 200)
    - ตั้งชื่อไฟล์ชั่วคราวตามนามสกุลจริง
    - คืน "" หากมีข้อผิดพลาด
    """
    token = get_telegram_token()
    if not token:
        print("[download_telegram_file] No Telegram token set in TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return ""

    # 1) ขอ file_path จาก getFile
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=15
        )
    except Exception as e:
        print(f"[download_telegram_file] getFile request error: {e}")
        return ""

    try:
        j = r.json()
    except Exception:
        print(f"[download_telegram_file] getFile non-JSON response: {r.text[:200]}")
        return ""

    if not j.get("ok"):
        print(f"[download_telegram_file] getFile not ok: {j}")
        return ""

    result = j.get("result") or {}
    file_path = result.get("file_path")
    if not file_path:
        print(f"[download_telegram_file] Missing file_path in result: {j}")
        return ""

    # 2) ดาวน์โหลดไฟล์จริง
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    ext = os.path.splitext(file_path)[1] or (os.path.splitext(suggested_name or "")[1]) or ""

    # ตั้งชื่อไฟล์ temp ให้ปลอดภัย/อ่านง่าย
    prefix_base = os.path.splitext(os.path.basename(suggested_name or "tg"))[0][:30]
    prefix = f"{prefix_base}_" if prefix_base else "tg_"

    fd, out_path = tempfile.mkstemp(prefix=prefix, suffix=ext)
    try:
        with requests.get(file_url, stream=True, timeout=60) as resp:
            if not resp.ok:
                print(f"[download_telegram_file] download error: {resp.status_code} - {resp.text[:120]}")
                os.close(fd)
                os.unlink(out_path)
                return ""
            with os.fdopen(fd, "wb") as f:
                for chunk in resp.iter_content(1024 * 64):
                    if chunk:
                        f.write(chunk)
        return out_path
    except Exception as e:
        print(f"[download_telegram_file] stream error: {e}")
        try:
            os.close(fd)
        except Exception:
            pass
        try:
            os.unlink(out_path)
        except Exception:
            pass
        return ""

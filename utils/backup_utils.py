# utils/backup_utils.py
# -*- coding: utf-8 -*-
"""
Google Drive Backup/Restore (Service Account, Render-friendly)

ปรับปรุงสำคัญ:
- ครอบ .execute() ด้วย retry/backoff ที่ถูกต้อง (เดิม retry ครอบเฉพาะตัวสร้าง request)
- รองรับทั้งไฟล์ key (.json path ผ่าน GOOGLE_APPLICATION_CREDENTIALS) และ JSON ใน ENV (GOOGLE_SERVICE_ACCOUNT_JSON)
- ใช้ scope 'drive' (อ่าน/เขียน/ลบ) เพื่อให้ลบไฟล์เดิมได้จริงในโฟลเดอร์ที่แชร์ให้ Service Account
- ค้นหา/ลบแบบปลอดภัยด้วยเงื่อนไข 'trashed=false' และ 'in parents' (ไม่ลบทั้งไดรฟ์)
- รองรับ Snapshot รายวัน: อัปโหลดเข้าโฟลเดอร์ย่อย YYYY-MM-DD (เปิด/ปิดได้ด้วย ENV)
- เก็บ backup_log.json พร้อมรายการไฟล์/ขนาด/เวลา/ผลลัพธ์ (เขียนแบบ atomic)
- เพิ่ม restore_by_date('YYYY-MM-DD') และ list_snapshots()
"""

from __future__ import annotations

import os
import io
import json
import mimetypes
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

# ---- optional safe writer ----
try:
    from utils.json_utils import save_json_safe as _save_json_safe
except Exception:
    _save_json_safe = None  # fallback ด้านล่าง

# --- Config ---
CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

# ใช้ scope 'drive' เพื่อให้ลบ/ย้าย/อ่านเมตาดาตาได้ครบ (ภายใต้สิทธิ์ที่ถูกแชร์)
SCOPES = ["https://www.googleapis.com/auth/drive"]

# รายการไฟล์ดีฟอลต์ (แก้ได้ด้วย BACKUP_FILES_JSON)
BACKUP_FILES = [
    "usage.json",
    "image_usage.json",
    "context_history.json",
    "location_logs.json",
]
try:
    if os.getenv("BACKUP_FILES_JSON"):
        BACKUP_FILES = json.loads(os.getenv("BACKUP_FILES_JSON") or "[]") or BACKUP_FILES
except Exception:
    pass

BACKUP_LOG_FILE = "data/backup_log.json"
GDRIVE_BACKUP_FOLDER_ID = os.getenv("GDRIVE_BACKUP_FOLDER_ID", "").strip() or None
SNAPSHOT_BY_DATE = (os.getenv("GDRIVE_SNAPSHOT_BY_DATE", "1").strip() == "1")


# ===== Helpers: time & log =====
def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _print(tag: str, **kw):
    try:
        print(f"[GDRIVE {tag}] " + json.dumps(kw, ensure_ascii=False, default=str))
    except Exception:
        print(f"[GDRIVE {tag}] (unprintable log)")


# ===== Credentials / Service =====
def _get_credentials():
    """
    คืน Credentials จาก:
    1) GOOGLE_SERVICE_ACCOUNT_JSON (เนื้อหา JSON ตรง ๆ) หรือ
    2) GOOGLE_APPLICATION_CREDENTIALS (path)
    """
    if SERVICE_ACCOUNT_JSON:
        info = json.loads(SERVICE_ACCOUNT_JSON)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    if CREDENTIALS_FILE and os.path.exists(CREDENTIALS_FILE):
        return service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    raise RuntimeError(
        "ไม่พบ Service Account credentials (ตั้ง GOOGLE_SERVICE_ACCOUNT_JSON หรือ GOOGLE_APPLICATION_CREDENTIALS)"
    )


def get_drive_service():
    try:
        creds = _get_credentials()
        # cache_discovery=False เพื่อเลี่ยง warning/caching ปัญหาในคอนเทนเนอร์ชั่วคราว
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        _print("ERROR_CREDENTIALS", err=str(e))
        raise


# ===== Retry / Exec helpers =====
def _retry(func, *args, **kwargs):
    """
    Retry แบบ backoff สำหรับ 429/5xx และ error เครือข่ายทั่วไป (สูงสุด ~4 ครั้ง)
    ใช้โดยส่งเป็น lambda: _retry(lambda: service.files().list(...).execute())
    """
    attempts = kwargs.pop("_attempts", 4)
    delay = kwargs.pop("_delay", 0.7)
    for i in range(attempts):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            status = getattr(e, "status_code", None) or (e.resp.status if hasattr(e, "resp") else None)
            if status in (429, 500, 502, 503, 504):
                sleep = delay * (2**i)
                _print("RETRY_HTTP", status=status, attempt=i + 1, sleep=round(sleep, 2))
                time.sleep(sleep)
                continue
            raise
        except Exception as e:
            # เครือข่าย/timeout อื่น ๆ
            sleep = delay * (2**i)
            _print("RETRY_MISC", attempt=i + 1, sleep=round(sleep, 2), err=str(e))
            time.sleep(sleep)
    # last try
    return func(*args, **kwargs)


def _q_and(*parts: str) -> str:
    parts2 = [p for p in parts if p and p.strip()]
    return " and ".join(parts2) if parts2 else ""


def _q_escape(name: str) -> str:
    """escape ชื่อสำหรับ query (single quote)"""
    return (name or "").replace("\\", "\\\\").replace("'", "\\'")


# ===== Drive helpers =====
def ensure_folder(name: str, parent_id: Optional[str]) -> str:
    """
    สร้างโฟลเดอร์หากยังไม่มี (คืน folder_id)
    หมายเหตุ: ใช้ชื่อเท่ากันหลายอันในโฟลเดอร์เดียวกันได้ใน Google Drive
    โค้ดนี้จะใช้ "ตัวแรกที่พบ" หากมีอยู่แล้ว
    """
    service = get_drive_service()
    q = _q_and(
        f"name = '{_q_escape(name)}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false",
        (f"'{parent_id}' in parents" if parent_id else None),
    )
    results = _retry(lambda: service.files().list(q=q, fields="files(id,name,parents)", pageSize=1).execute())
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        file_metadata["parents"] = [parent_id]
    folder = _retry(lambda: service.files().create(body=file_metadata, fields="id").execute())
    return folder["id"]


def _search_files(name: Optional[str] = None, parent_id: Optional[str] = None, page_size: int = 100) -> List[Dict]:
    service = get_drive_service()
    conds = ["trashed = false"]
    if name:
        conds.append(f"name = '{_q_escape(name)}'")
    if parent_id:
        conds.append(f"'{parent_id}' in parents")
    q = _q_and(*conds)
    fields = "files(id,name,mimeType,parents,modifiedTime,size,md5Checksum),nextPageToken"

    files: List[Dict] = []
    page_token = None
    while True:
        resp = _retry(lambda: service.files().list(q=q, fields=fields, pageSize=page_size, pageToken=page_token).execute())
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def delete_all_by_name(file_name: str, parent_id: Optional[str] = None):
    """Delete all files with same name within *given folder* (avoid cross-drive deletes)"""
    service = get_drive_service()
    try:
        targets = _search_files(name=file_name, parent_id=parent_id, page_size=100)
        for f in targets:
            try:
                _retry(lambda: service.files().delete(fileId=f["id"]).execute())
            except Exception as e:
                _print("ERROR_DELETE", id=f.get("id"), err=str(e))
    except Exception as e:
        _print("ERROR_DELETE_QUERY", err=str(e))


def upload_to_gdrive(file_path: str, gdrive_folder_id: Optional[str] = None, overwrite: bool = True) -> Optional[str]:
    """
    Upload local file to Google Drive
    - หาก overwrite=True จะลบไฟล์ชื่อเดียวกันในโฟลเดอร์นั้นก่อน
    """
    if not os.path.exists(file_path):
        _print("WARN_UPLOAD_MISSING", path=file_path)
        return None

    service = get_drive_service()
    file_name = os.path.basename(file_path)
    if overwrite:
        delete_all_by_name(file_name, parent_id=gdrive_folder_id)

    file_metadata = {"name": file_name}
    if gdrive_folder_id:
        file_metadata["parents"] = [gdrive_folder_id]

    mime_type, _ = mimetypes.guess_type(file_path)
    media = MediaFileUpload(file_path, mimetype=mime_type or "application/octet-stream", resumable=True)
    created = _retry(lambda: service.files().create(body=file_metadata, media_body=media, fields="id,name,parents").execute())
    return created.get("id")


def search_file_by_name(file_name: str, parent_id: Optional[str] = None) -> Optional[str]:
    try:
        files = _search_files(name=file_name, parent_id=parent_id, page_size=1)
        return files[0]["id"] if files else None
    except Exception as e:
        _print("ERROR_SEARCH", err=str(e))
        return None


def download_from_gdrive(file_name: str, destination: str, parent_id: Optional[str] = None) -> bool:
    """
    Download file by name from Google Drive -> local path
    ค้นหาเฉพาะในโฟลเดอร์ parent_id (ถ้าให้มา)
    """
    service = get_drive_service()
    file_id = search_file_by_name(file_name, parent_id=parent_id)
    if not file_id:
        _print("RESTORE_NOT_FOUND", name=file_name)
        return False

    request = service.files().get_media(fileId=file_id)
    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
    fh = io.FileIO(destination, "wb")

    try:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = _retry(downloader.next_chunk)  # ใช้ถูกแล้ว
            # ไม่ spam log ความคืบหน้า
        fh.close()
        ok = os.path.exists(destination) and os.path.getsize(destination) > 0
        if not ok:
            _print("RESTORE_EMPTY", dest=destination)
        return ok
    except Exception as e:
        fh.close()
        _print("RESTORE_ERROR", name=file_name, err=str(e))
        return False


# ===== Snapshot helpers =====
def _ensure_root_folder() -> str:
    if not GDRIVE_BACKUP_FOLDER_ID:
        raise RuntimeError("กรุณาตั้งค่า GDRIVE_BACKUP_FOLDER_ID ให้เป็นโฟลเดอร์ปลายทางบน Google Drive")
    return GDRIVE_BACKUP_FOLDER_ID


def _get_today_folder(parent_id: str, date_text: Optional[str] = None) -> str:
    date_text = date_text or datetime.now().strftime("%Y-%m-%d")
    return ensure_folder(date_text, parent_id)


def list_snapshots(limit: int = 30) -> List[str]:
    """
    คืนรายการ snapshot (โฟลเดอร์รูปแบบ YYYY-MM-DD) ใต้โฟลเดอร์ราก เรียงใหม่→เก่า
    """
    parent = _ensure_root_folder()
    service = get_drive_service()
    q = _q_and(
        "trashed = false",
        "mimeType = 'application/vnd.google-apps.folder'",
        f"'{parent}' in parents",
    )
    fields = "files(id,name,modifiedTime),nextPageToken"

    out: List[str] = []
    token = None
    while True:
        res = _retry(lambda: service.files().list(q=q, fields=fields, pageSize=200, pageToken=token).execute())
        rows = res.get("files", [])
        for r in rows:
            name = r.get("name", "")
            try:
                datetime.strptime(name, "%Y-%m-%d")
                out.append(name)
            except Exception:
                continue
        token = res.get("nextPageToken")
        if not token:
            break
    return sorted(out, reverse=True)[:limit]


# ===== Main Backup/Restore =====
def backup_all(date_text: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Backup all files in BACKUP_FILES
    - อัปโหลดเข้าโฟลเดอร์ราก (latest) แบบ overwrite
    - ถ้า SNAPSHOT_BY_DATE=True จะอัปโหลดสำเนาเข้าโฟลเดอร์ย่อย YYYY-MM-DD ด้วย (ไม่ overwrite)
    """
    root_id = _ensure_root_folder()
    results: Dict[str, Optional[str]] = {}
    status = {
        "timestamp": _now_iso(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "files": [],
        "success": True,
        "snapshot": SNAPSHOT_BY_DATE,
    }

    # โฟลเดอร์ snapshot (optional)
    snapshot_id = None
    if SNAPSHOT_BY_DATE:
        try:
            snapshot_id = _get_today_folder(root_id, date_text=date_text)
        except Exception as e:
            _print("SNAPSHOT_FOLDER_ERROR", err=str(e))
            status["snapshot"] = False

    for file_path in BACKUP_FILES:
        entry = {"file": file_path, "id": None, "ok": False, "size": 0}
        try:
            if os.path.exists(file_path):
                # latest (overwrite)
                latest_id = upload_to_gdrive(file_path, gdrive_folder_id=root_id, overwrite=True)
                entry["id"] = latest_id
                entry["ok"] = bool(latest_id)
                entry["size"] = os.path.getsize(file_path)

                # snapshot (keep history)
                if snapshot_id and latest_id:
                    _ = upload_to_gdrive(file_path, gdrive_folder_id=snapshot_id, overwrite=False)
            else:
                entry["err"] = "File not found"
                status["success"] = False
        except Exception as e:
            entry["err"] = str(e)
            status["success"] = False
        finally:
            status["files"].append(entry)
            results[file_path] = entry.get("id")

    # Save log (atomic ถ้ามี util)
    try:
        os.makedirs(os.path.dirname(BACKUP_LOG_FILE) or ".", exist_ok=True)
        if _save_json_safe:
            _save_json_safe(status, BACKUP_LOG_FILE, ensure_ascii=False, indent=2, sort_keys=False)
        else:
            tmp = f"{BACKUP_LOG_FILE}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            os.replace(tmp, BACKUP_LOG_FILE)
    except Exception as log_err:
        _print("BACKUP_LOG_ERROR", err=str(log_err))

    _print("BACKUP_RESULT", success=status["success"])
    return results


def restore_all(date_text: Optional[str] = None):
    """
    Restore all files in BACKUP_FILES
    - ถ้า date_text ให้ค้นในโฟลเดอร์ YYYY-MM-DD
    - ถ้าไม่ระบุ จะดึงจากโฟลเดอร์ราก (latest)
    """
    root_id = _ensure_root_folder()
    parent_id = None

    if date_text:
        try:
            # ใช้โฟลเดอร์ snapshot ตามวันที่ที่ให้มา
            datetime.strptime(date_text, "%Y-%m-%d")
            parent_id = ensure_folder(date_text, root_id)  # ถ้ามีอยู่แล้วจะคืน id เดิม
        except Exception:
            _print("RESTORE_DATE_INVALID", date=date_text)
            parent_id = None

    for file_path in BACKUP_FILES:
        try:
            ok = download_from_gdrive(os.path.basename(file_path), file_path, parent_id=parent_id or root_id)
            _print("RESTORE_FILE", file=file_path, ok=ok)
        except Exception as e:
            _print("RESTORE_ERROR", file=file_path, err=str(e))


def restore_by_date(date_text: str):
    """Helper ตรง ๆ — เท่ากับ restore_all(date_text='YYYY-MM-DD')"""
    restore_all(date_text=date_text)


def get_backup_status() -> Dict:
    """
    อ่านสถานะจาก BACKUP_LOG_FILE
    """
    try:
        with open(BACKUP_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {
            "timestamp": None,
            "success": False,
            "files": [],
            "err": f"ไม่พบ log การสำรองล่าสุด ({e})",
        }


def setup_backup_scheduler():
    """
    ตั้ง APScheduler ให้รัน backup_all() ทุกวัน 00:09 ตาม Asia/Bangkok
    (เหมาะกับ web process ที่รันยาว ๆ)
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    import pytz

    def backup_job():
        _print("SCHEDULED_BACKUP_START")
        backup_all()

    scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Bangkok"))
    scheduler.add_job(backup_job, "cron", hour=0, minute=9)
    scheduler.start()
    _print("SCHEDULED_BACKUP_STARTED")


# --- CLI/Test mode ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Drive Backup Utils")
    parser.add_argument("--backup", action="store_true", help="Run backup_all()")
    parser.add_argument("--restore", action="store_true", help="Run restore_all() (latest)")
    parser.add_argument("--restore-date", type=str, help="Run restore_all() for a given date YYYY-MM-DD")
    parser.add_argument("--list", action="store_true", help="List available snapshot dates")
    args = parser.parse_args()

    if args.list:
        print("\nSnapshots (newest → oldest):")
        for d in list_snapshots():
            print(" -", d)

    if args.backup:
        backup_all()

    if args.restore:
        restore_all()

    if args.restore_date:
        restore_all(args.restore_date)

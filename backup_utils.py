import os
import io
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# --- Config ---
CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'avian-silo-466800-g2-9f6c4fb7500c.json')
SCOPES = ['https://www.googleapis.com/auth/drive.file']
BACKUP_FILES = [
    "usage.json",
    "image_usage.json",
    "context_history.json",
    "location_logs.json"
]
BACKUP_LOG_FILE = "data/backup_log.json"
GDRIVE_BACKUP_FOLDER_ID = os.getenv('GDRIVE_BACKUP_FOLDER_ID', None)

# --- Google Drive ---
def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[GOOGLE DRIVE ERROR] Credentials: {e}")
        raise

def delete_all_by_name(file_name):
    """Delete all files in Google Drive with the same name (avoid duplicates)"""
    service = get_drive_service()
    query = f"name='{file_name}'"
    try:
        results = service.files().list(q=query, fields="files(id, name)", pageSize=100).execute()
        files = results.get('files', [])
        for f in files:
            try:
                service.files().delete(fileId=f['id']).execute()
            except Exception as e:
                print(f"[GOOGLE DRIVE ERROR] Delete {f['id']}: {e}")
    except Exception as e:
        print(f"[GOOGLE DRIVE ERROR] Delete query: {e}")

def upload_to_gdrive(file_path, gdrive_folder_id=None):
    """Upload local file to Google Drive, overwrite previous file"""
    delete_all_by_name(os.path.basename(file_path))
    service = get_drive_service()
    file_metadata = {'name': os.path.basename(file_path)}
    if gdrive_folder_id:
        file_metadata['parents'] = [gdrive_folder_id]
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def search_file_by_name(file_name):
    service = get_drive_service()
    query = f"name='{file_name}'"
    try:
        results = service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        print(f"[GOOGLE DRIVE ERROR] Search: {e}")
        return None

def download_from_gdrive(file_name, destination):
    """Download file by name from Google Drive to local path"""
    file_id = search_file_by_name(file_name)
    if not file_id:
        print(f"[RESTORE] Not found {file_name} on Google Drive")
        return False
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    try:
        while not done:
            status, done = downloader.next_chunk()
        fh.close()
        if os.path.exists(destination) and os.path.getsize(destination) > 0:
            return True
        else:
            print(f"[RESTORE] Downloaded but file is empty: {destination}")
            return False
    except Exception as e:
        print(f"[RESTORE ERROR] {file_name}: {e}")
        fh.close()
        return False

# --- Main Backup/Restore ---
def backup_all():
    """
    Backup all files in BACKUP_FILES to Google Drive.
    Save backup log to BACKUP_LOG_FILE.
    """
    results = {}
    status = {
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "success": True
    }
    for file_path in BACKUP_FILES:
        try:
            if os.path.exists(file_path):
                file_id = upload_to_gdrive(file_path, GDRIVE_BACKUP_FOLDER_ID)
                results[file_path] = file_id
                status["files"].append({"file": file_path, "id": file_id, "ok": True})
            else:
                results[file_path] = None
                status["files"].append({"file": file_path, "id": None, "ok": False, "err": "File not found"})
                status["success"] = False
        except Exception as e:
            results[file_path] = f"error: {e}"
            status["files"].append({"file": file_path, "id": None, "ok": False, "err": str(e)})
            status["success"] = False
    # Save log
    try:
        os.makedirs(os.path.dirname(BACKUP_LOG_FILE), exist_ok=True)
        with open(BACKUP_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except Exception as log_err:
        print(f"[BACKUP LOG ERROR] {log_err}")
    print("[BACKUP RESULT]", results)
    return results

def restore_all():
    """
    Restore all files in BACKUP_FILES from Google Drive.
    """
    for file_path in BACKUP_FILES:
        try:
            ok = download_from_gdrive(os.path.basename(file_path), file_path)
            print(f"[RESTORE] {file_path}: {'OK' if ok else 'Not found'}")
        except Exception as e:
            print(f"[RESTORE ERROR] {file_path}: {e}")

def get_backup_status():
    """
    Get last backup status for bot/admin.
    Returns: dict (timestamp, success, files[], err)
    """
    try:
        with open(BACKUP_LOG_FILE, "r", encoding="utf-8") as f:
            status = json.load(f)
        return status
    except Exception as e:
        return {
            "timestamp": None,
            "success": False,
            "files": [],
            "err": f"ไม่พบ log การสำรองล่าสุด ({e})"
        }

def setup_backup_scheduler():
    """
    Setup APScheduler to run backup_all() every day at 00:09 Asia/Bangkok.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    import pytz

    def backup_job():
        print("[SCHEDULED BACKUP] Starting backup job...")
        backup_all()

    scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Bangkok'))
    scheduler.add_job(backup_job, 'cron', hour=0, minute=9)
    scheduler.start()
    print("[SCHEDULED BACKUP] Backup scheduler started")

# --- CLI/Test mode ---
if __name__ == "__main__":
    print("== [INFO] Restore all files from Google Drive ==")
    restore_all()
    print("== [INFO] Start Backup Scheduler ==")
    setup_backup_scheduler()
    # (อย่าลืม run main.py หรือ gunicorn ตามปกติ ถ้ารันแอป)

import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'avian-silo-466800-g2-9f6c4fb7500c.json')
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# รายชื่อไฟล์ที่ต้องสำรอง/คืนค่า (ข้อมูลเท่านั้น)
BACKUP_FILES = [
    "usage.json",
    "image_usage.json",
    "context_history.json",
    "location_logs.json"
    # เพิ่มได้ตามต้องการ
]

GDRIVE_BACKUP_FOLDER_ID = None  # ใส่ folder id หากต้องการ backup ไว้ในโฟลเดอร์บน Google Drive

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def delete_all_by_name(file_name):
    service = get_drive_service()
    query = f"name='{file_name}'"
    results = service.files().list(q=query, fields="files(id, name)", pageSize=100).execute()
    files = results.get('files', [])
    for f in files:
        try:
            service.files().delete(fileId=f['id']).execute()
        except Exception as e:
            print(f"Cannot delete file: {f['id']} - {e}")

def upload_to_gdrive(file_path, gdrive_folder_id=None):
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
    results = service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None

def download_from_gdrive(file_name, destination):
    file_id = search_file_by_name(file_name)
    if not file_id:
        print(f"[restore] Not found {file_name} on Google Drive")
        return False
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()
    if os.path.exists(destination) and os.path.getsize(destination) > 0:
        return True
    else:
        print(f"[restore] Downloaded but file is empty: {destination}")
        return False

def backup_all():
    results = {}
    for file_path in BACKUP_FILES:
        try:
            if os.path.exists(file_path):
                file_id = upload_to_gdrive(file_path, GDRIVE_BACKUP_FOLDER_ID)
                results[file_path] = file_id
            else:
                results[file_path] = None
        except Exception as e:
            results[file_path] = f"error: {e}"
    print("[BACKUP RESULT]", results)
    return results

def restore_all():
    for file_path in BACKUP_FILES:
        try:
            ok = download_from_gdrive(os.path.basename(file_path), file_path)
            print(f"[RESTORE] {file_path}: {'OK' if ok else 'Not found'}")
        except Exception as e:
            print(f"[RESTORE ERROR] {file_path}: {e}")

# --- (Optional) ใช้ APScheduler สำหรับ backup อัตโนมัติทุกวัน ---
def setup_backup_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    import pytz

    def backup_job():
        print("[SCHEDULED BACKUP] Starting backup job...")
        backup_all()

    scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Bangkok'))
    # ตั้งเวลา 00:09 ทุกวัน
    scheduler.add_job(backup_job, 'cron', hour=0, minute=9)
    scheduler.start()
    print("[SCHEDULED BACKUP] Backup scheduler started")

# ใช้ใน main.py (หรือ bot startup)
if __name__ == "__main__":
    restore_all()              # Restore ทุกครั้งที่เริ่มระบบ
    setup_backup_scheduler()   # เริ่ม backup อัตโนมัติ
    # ...start bot/app ตามปกติ...

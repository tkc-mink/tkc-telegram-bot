import os
import io
import time
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'avian-silo-466800-g2-9f6c4fb7500c.json')
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ปรับชื่อไฟล์สำรอง/คืนค่าตามชื่อจริง
BACKUP_FILES = [
    "usage.json",
    "image_usage.json",
    "context_history.json",
    "location_logs.json"
    # เพิ่มไฟล์อื่นๆที่ต้องการ backup/restore ได้
]

GDRIVE_BACKUP_FOLDER_ID = None  # ถ้ามี folder บนไดรฟ์ให้ใส่ id (ไม่มีก็ไม่ต้อง)

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def upload_to_gdrive(file_path, gdrive_folder_id=None):
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
    return True

def backup_all():
    """Backup ไฟล์ทั้งหมดขึ้น Google Drive"""
    results = {}
    for file_path in BACKUP_FILES:
        if os.path.exists(file_path):
            file_id = upload_to_gdrive(file_path, GDRIVE_BACKUP_FOLDER_ID)
            results[file_path] = file_id
        else:
            results[file_path] = None
    print("[BACKUP RESULT]", results)
    return results

def restore_all():
    """Restore ไฟล์ทั้งหมดจาก Google Drive"""
    for file_path in BACKUP_FILES:
        ok = download_from_gdrive(os.path.basename(file_path), file_path)
        print(f"[RESTORE] {file_path}: {'OK' if ok else 'Not found'}")

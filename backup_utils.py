import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'avian-silo-466800-g2-9f6c4fb7500c.json')
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def upload_to_gdrive(file_path, gdrive_folder_id=None):
    """อัปโหลดไฟล์ขึ้น Google Drive (คืนค่า file_id)"""
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    file_metadata = {'name': os.path.basename(file_path)}
    if gdrive_folder_id:
        file_metadata['parents'] = [gdrive_folder_id]
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def backup_jsons_to_gdrive(files, gdrive_folder_id=None):
    """สำรองไฟล์ JSON หลายไฟล์ขึ้น Google Drive"""
    results = {}
    for file_path in files:
        if os.path.exists(file_path):
            file_id = upload_to_gdrive(file_path, gdrive_folder_id)
            results[file_path] = file_id
        else:
            results[file_path] = None
    return results

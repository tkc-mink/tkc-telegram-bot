import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SERVICE_ACCOUNT_FILE = 'avian-silo-466800-g2-9f6c4fb7500c.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def backup_to_gdrive(filepath, filename_on_drive=None, folder_id=None):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    file_metadata = {'name': filename_on_drive or os.path.basename(filepath)}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    media = MediaFileUpload(filepath, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"Upload success: https://drive.google.com/file/d/{file.get('id')}")
    return file.get('id')

def daily_backup():
    for f in ["history.json", "usage.json", "context_history.json", "location_logs.json"]:
        if os.path.exists(f):
            backup_to_gdrive(f)

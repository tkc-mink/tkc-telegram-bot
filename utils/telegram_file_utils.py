import os
import requests
import tempfile

from utils.message_utils import get_telegram_token

def download_telegram_file(file_id: str, suggested_name: str) -> str:
    """
    ดาวน์โหลดไฟล์จาก Telegram แล้วคืน path ชั่วคราว
    """
    r = requests.get(
        f"https://api.telegram.org/bot{get_telegram_token()}/getFile",
        params={"file_id": file_id},
        timeout=10
    )
    if not r.ok:
        return ""

    file_path = r.json()["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{get_telegram_token()}/{file_path}"
    ext = os.path.splitext(file_path)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    with requests.get(url, stream=True, timeout=20) as resp:
        for chunk in resp.iter_content(8192):
            tmp.write(chunk)
    tmp.close()
    return tmp.name

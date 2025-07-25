from utils.backup_utils import get_backup_status

def handle_backup_status(chat_id, user_text):
    info = get_backup_status()
    from utils.message_utils import send_message   # local import ป้องกัน import วน

    if info and info.get("timestamp"):
        # เตรียมสรุปสถานะ
        time_str = info.get("timestamp", "-")
        status_str = "✅ สำเร็จ" if info.get("success") else "❌ ผิดพลาด"
        file_list = info.get("files", [])
        if file_list:
            file_lines = []
            for f in file_list:
                fname = f.get("file", "-")
                ok = f.get("ok", False)
                file_id = f.get("id", "")
                err = f.get("err", "")
                mark = "🟢" if ok else "🔴"
                detail = f"{mark} {fname}"
                if file_id:
                    detail += f" (ID: {file_id})"
                if err:
                    detail += f"\n    [Error: {err}]"
                file_lines.append(detail)
            file_str = "\n".join(file_lines)
        else:
            file_str = "ไม่พบข้อมูลไฟล์ใน log"

        message = (
            f"🟢 <b>Backup ล่าสุด</b>\n"
            f"- วันที่/เวลา: <code>{time_str}</code>\n"
            f"- สถานะ: {status_str}\n"
            f"- ไฟล์ที่สำรอง:\n{file_str}"
        )
    else:
        message = "⚠️ ยังไม่พบ log หรือยังไม่เคย backup สำเร็จ"

    send_message(chat_id, message, parse_mode="HTML")

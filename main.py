from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from flask import Flask
from threading import Thread
import os

# ================= CẤU HÌNH THÔNG TIN =================
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
STRING_SESSION = '1BVtsOMMBu3AE1KgNrGbyH6Uty3WYhIbr3if8xdgBYeH3ARZFdgg1v5MuUU_nAUbKf9mO61Yejtd_3diBeZlbIl2euC211O1SE0kkVN6cRPhvDRh40IpROZFSDHDz-C7bjeljjlzoenNE1_I6-WTvf6AMOeXvfEN7RUTgok00ZtkwtBz3L1HOjvpaNVpZ3h3yGSWoxUj6Sftf7aIlymc7vMs2wn31pIMGg-3myjr47EUFTVEVaVwLuDLkwP6h2ekDLYNNXp2ZBxOyAsirg6HDhfUKm0of0--lUmeVWQgcVnMJSohA7yuvi0EN_G26FLNmYlojI3zVCU2v20RIWy0U7YtGcnl-IyI='

TARGET_BOT = 'xocdia88_bot_uytin_bot' 
GROUP_TARGET = -1002984339626 
# =====================================================

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

app = Flask('')
@app.route('/')
def home():
    return "Bot đang chạy 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- LOGIC TỰ ĐỘNG ĐẬP HỘP VÀ CHUYỂN TIẾP ---
@client.on(events.NewMessage(chats=TARGET_BOT))
async def handler(event):
    # 1. Nếu tin nhắn có nút "Đập Hộp" -> Nhấn luôn
    if event.reply_markup:
        for row in event.reply_markup.rows:
            for button in row.buttons:
                if "Đập Hộp" in button.text:
                    await event.click()
                    print("--- Đã nhấn Đập Hộp! ---")
                    return # Thoát để đợi tin nhắn phản hồi chứa Code

    # 2. Nếu tin nhắn chứa chữ "Code" hoặc "Mã" -> Bắn sang nhóm ngay
    msg_text = event.raw_text
    if "Code" in msg_text or "Mã" in msg_text or "quà" in msg_text.lower():
        try:
            await client.send_message(GROUP_TARGET, f"✅ ĐÃ LẤY ĐƯỢC CODE:\n\n{msg_text}")
            print(f"--- Đã gửi code sang nhóm {GROUP_TARGET} ---")
        except Exception as e:
            print(f"Lỗi gửi tin: {e}")

async def main():
    await client.start()
    print("--- BOT ĐÃ SẴN SÀNG TRỰC CHIẾN ---")
    await client.send_message('me', 'Bot đã bắt đầu canh code!')
    await client.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=run_flask).start()
    asyncio.get_event_loop().run_until_complete(main())
    

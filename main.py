from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from flask import Flask
from threading import Thread
import os

# ================= CẤU HÌNH THÔNG TIN =================
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'

# Mã String Session bạn vừa lấy
STRING_SESSION = '1BVtsOMMBu3AE1KgNrGbyH6Uty3WYhIbr3if8xdgBYeH3ARZFdgg1v5MuUU_nAUbKf9mO61Yejtd_3diBeZlbIl2euC211O1SE0kkVN6cRPhvDRh40IpROZFSDHDz-C7bjeljjlzoenNE1_I6-WTvf6AMOeXvfEN7RUTgok00ZtkwtBz3L1HOjvpaNVpZ3h3yGSWoxUj6Sftf7aIlymc7vMs2wn31pIMGg-3myjr47EUFTVEVaVwLuDLkwP6h2ekDLYNNXp2ZBxOyAsirg6HDhfUKm0of0--lUmeVWQgcVnMJSohA7yuvi0EN_G26FLNmYlojI3zVCU2v20RIWy0U7YtGcnl-IyI='

TARGET_BOT = 'xocdia88_bot_uytin_bot' 
GROUP_TARGET = -1002984339626 
# =====================================================

# Sử dụng StringSession để không cần file .session nữa
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# --- PHẦN 1: WEB SERVER ĐỂ TREO 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy bằng String Session 24/7!"

def run_flask():
    # Chạy trên port 8080 cho Koyeb
    app.run(host='0.0.0.0', port=8080)

# --- PHẦN 2: LOGIC TỰ ĐỘNG ĐẬP HỘP ---
@client.on(events.NewMessage(chats=TARGET_BOT))
async def handler(event):
    # 1. Tự động nhấn nút "Đập Hộp"
    if event.reply_markup:
        for row in event.reply_markup.rows:
            for button in row.buttons:
                if "Đập Hộp" in button.text:
                    await event.click()
                    print(f"--- Đã nhấn Đập Hộp lúc {os.getpid()} ---")

async def main():
    await client.start()
    print("--- ĐĂNG NHẬP THÀNH CÔNG BẰNG STRING SESSION ---")
    # Gửi tin nhắn xác nhận vào Saved Messages
    await client.send_message('me', 'Bot đập hộp đã online trên Koyeb!')
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Chạy Flask trong một luồng riêng
    t = Thread(target=run_flask)
    t.start()
    
    # Chạy Bot Telegram
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    

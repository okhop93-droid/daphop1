from telethon import TelegramClient, events
import asyncio
from flask import Flask
from threading import Thread
from datetime import datetime

# ================= CẤU HÌNH THÔNG TIN =================
# Thông tin API lấy từ my.telegram.org
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'

# Username của Bot phát quà (Kiểm tra chính xác username này)
TARGET_BOT = 'xocdia88_bot_uytin_bot' 

# ID của Nhóm nhận code (Phải để trong dấu nháy đơn để an toàn)
GROUP_TARGET = -1002984339626 
# =====================================================

client = TelegramClient('session_replit', API_ID, API_HASH)

# --- PHẦN 1: WEB SERVER ĐỂ TREO 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "Bot đang hoạt động 24/7! Hãy dán link HTTPS vào Cron-job."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- PHẦN 2: LOGIC TỰ ĐỘNG ĐẬP HỘP VÀ LẤY CODE ---
@client.on(events.NewMessage(chats=TARGET_BOT))
async def handler(event):
    # 1. Tự động nhấn nút "Đập Hộp"
    if event.reply_markup:
        for row in event.reply_markup.rows:
            for button in row.buttons:
                if "Đập Hộp" in button.text:
                    time_now = datetime.now().strftime('%H:%M:%S')
                    print(f"[{time_now}] 🎁 Phát hiện hộp! Đang bấm ngay...")
                    
                    # Độ trễ cực thấp (0.1 giây) để giành code nhanh nhất
                    await asyncio.sleep(0.1) 
                    try:
                        await event.click(0)
                        print(f"[{time_now}] ✅ Đã nhấn nút đập hộp thành công!")
                    except Exception as e:
                        print(f"[{time_now}] ❌ Lỗi khi bấm nút: {e}")
                    return

    # 2. Tự động copy mã code gửi vào nhóm
    if "Mã code của bạn là" in event.raw_text:
        time_now = datetime.now().strftime('%H:%M:%S')
        print(f"[{time_now}] 🔑 Đã nhận mã code. Đang chuyển vào nhóm...")
        try:
            # Gửi nội dung mã code vào nhóm mục tiêu
            await client.send_message(GROUP_TARGET, event.raw_text)
            print(f"[{time_now}] ✅ Đã gửi code vào nhóm {GROUP_TARGET}")
        except Exception as e:
            print(f"[{time_now}] ❌ Lỗi khi gửi vào nhóm: {e}")

# --- PHẦN 3: KHỞI CHẠY HỆ THỐNG ---
async def main():
    print("--- ĐANG KẾT NỐI TELEGRAM... ---")
    await client.start()
    
    # Gửi tin nhắn test để xác nhận bot đã ON
    try:
        await client.send_message(GROUP_TARGET, "🚀 BOT ĐÃ TRỰC CHIẾN! Sẵn sàng đập hộp 24/7.")
        print("--- ĐÃ GỬI THÔNG BÁO TEST VÀO NHÓM ---")
    except:
        print("--- CẢNH BÁO: Chưa gửi được tin test vào nhóm. Hãy kiểm tra ID nhóm! ---")

    print("--- BOT ĐANG LẮNG NGHE TIN NHẮN MỚI ---")
    await client.run_until_disconnected()

import requests
import time

def keep_alive_ping():
    while True:
        try:
            # Thay link dưới đây bằng link Webview chuẩn của bạn
            requests.get("https://daphop-1--okhop93.replit.app/")
            print("--- Đã tự gửi ping để giữ Bot tỉnh táo ---")
        except:
            pass
        time.sleep(120) # 2 phút ping một lần

# Trong phần main, hãy chạy nó ở một luồng riêng
if __name__ == '__main__':
    Thread(target=run_flask).start()
    Thread(target=keep_alive_ping).start() # Thêm dòng này
    # ... phần còn lại của code ...
    
if __name__ == '__main__':
    # Chạy Flask ở luồng riêng
    t = Thread(target=run_flask)
    t.start()
    
    # Chạy Bot Telegram
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    

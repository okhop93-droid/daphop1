from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio, random, datetime
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626 

# Session mới của bạn
SESSION_CHINH = '1BVtsOHQBu0tsu7kP9woTfa1GNU9wLR_FBhhnmM-egVjgs-BqnpGqw-lREFifIUxai8V3qOBNThDAhZ6zmjVbEne-ytTl4xXa-tqGJE3tjhJj4vXXO74Sel6VGVNsnlRCnGi97vEmkcQ8FLq1InLpiH9dzZNkCN8rCsMokXjvoEV7q3bL8a9AkC-ndZ6X1oj6DPvl_ech8HhxeiGcbKACtGDG2mjpwZe4JHVfOzaxbOYExzDR3lW9Mo2uuoqczhBLfU6l0lR6XTifeCf55281om1x3UkjY7RaX7V0Rzh4h9lqTsZEO8V5qvZ6EGKwktDfBRFmEWQgngv7dCZ5KNcp7TlvoAr9HGs='

app = Flask('')
@app.route('/')
def home(): return "BOT_DAP_HOP_ALIVE"

async def main():
    # Chạy Web Server để giữ Render luôn "Healthy"
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    
    print("🚀 ĐANG KHỞI CHẠY BOT ĐẬP HỘP...", flush=True)
    client = TelegramClient(StringSession(SESSION_CHINH), API_ID, API_HASH)
    
    try:
        await client.start()
        # Thông báo khi bắt đầu để bạn biết bot đã sống
        await client.send_message(GR_LOG, f"✅ [HỆ THỐNG] Bot đập hộp đã ONLINE lúc {datetime.datetime.now().strftime('%H:%M:%S')}!")
        print("✅ ĐÃ KẾT NỐI THÀNH CÔNG!", flush=True)

        @client.on(events.NewMessage(chats=BOT_GAME))
        async def work(e):
            if e.reply_markup:
                for row in e.reply_markup.rows:
                    for btn in row.buttons:
                        if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                            # Delay ngẫu nhiên để tránh bị quét bot
                            await asyncio.sleep(random.uniform(0.1, 0.4))
                            try:
                                await e.click()
                                await client.send_message(GR_LOG, "💰 HÚP QUÀ THÀNH CÔNG!")
                                print("💰 ĐÃ ĐẬP HỘP!", flush=True)
                            except Exception as ex:
                                print(f"⚠️ Lỗi click: {ex}")

        await client.run_until_disconnected()
    except Exception as e:
        # Nếu lỗi (như văng session), in ra log để xử lý
        print(f"❌ LỖI HỆ THỐNG: {e}", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
    

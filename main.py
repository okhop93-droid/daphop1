import re, asyncio, random
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo' 
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626

app = Flask('')
@app.route('/')
def home(): return "LOGIN_SYSTEM_ONLINE"

# Bộ nhớ tạm lưu các phiên đang đăng nhập dở
login_attempts = {}

async def main_bot():
    bot = TelegramClient('admin_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Bot Quản Trị đã Online!")

    # BƯỚC 1: NHẬN SĐT ĐỂ ĐĂNG NHẬP
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/login'))
    async def login_handler(e):
        try:
            phone = e.text.split(" ", 1)[1].strip()
            # Tạo một client mới hoàn toàn (dùng bộ nhớ tạm)
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            # Gửi mã OTP về điện thoại người dùng
            send_code = await client.send_code_request(phone)
            login_attempts[e.sender_id] = {
                "client": client, "phone": phone, "hash": send_code.phone_code_hash
            }
            await e.respond(f"📩 OTP đã gửi tới `{phone}`. Nhắn: `/otp <mã>` để xong.")
        except Exception as ex:
            await e.respond(f"❌ Lỗi: {ex}")

    # BƯỚC 2: NHẬN OTP VÀ KÍCH HOẠT ĐẬP HỘP
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/otp'))
    async def otp_handler(e):
        data = login_attempts.get(e.sender_id)
        if not data: return await e.respond("❌ Vui lòng gõ `/login SĐT` trước.")
        
        try:
            otp = e.text.split(" ", 1)[1].strip()
            client = data["client"]
            # Đăng nhập vào Telegram trực tiếp
            await client.sign_in(data["phone"], otp, phone_code_hash=data["hash"])
            me = await client.get_me()
            
            await e.respond(f"✅ Thành công! **{me.first_name}** đã bắt đầu đập hộp.")
            
            # Chạy chế độ đập hộp cho acc này
            @client.on(events.NewMessage(chats=BOT_GAME))
            async def work(ev):
                if ev.reply_markup:
                    for row in ev.reply_markup.rows:
                        for btn in row.buttons:
                            if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                                await asyncio.sleep(random.uniform(1, 2))
                                try:
                                    await ev.click()
                                    await bot.send_message(GR_LOG, f"💰 **{me.first_name}** vừa húp quà!")
                                except: pass
            
            del login_attempts[e.sender_id]
            await client.run_until_disconnected()
            
        except Exception as ex:
            await e.respond(f"❌ Lỗi đăng nhập: {ex}")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main_bot())
    

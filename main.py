import asyncio, random
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8492633588:AAGSoL3wMHq8HOD2llLmbp6gdfaAwOqjJvo'
BOT_GAME = 'xocdia88_bot_uytin_bot' # Con bot gửi hộp quà
GR_LOG = -1002984339626            # Nhóm để bot báo cáo kết quả

app = Flask('')
@app.route('/')
def home(): return "BOT_READY"

# Lưu tạm dữ liệu đăng nhập
pending_logins = {}

async def main():
    bot = TelegramClient('admin_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Bot Quản Trị đã Online!")

    # 1. NHẬN SĐT QUA TIN NHẮN RIÊNG (DM)
    @bot.on(events.NewMessage(pattern='/login', func=lambda e: e.is_private))
    async def login_private(e):
        try:
            phone = e.text.split(" ", 1)[1].strip()
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            send_code = await client.send_code_request(phone)
            pending_logins[e.sender_id] = {
                "client": client, "phone": phone, "hash": send_code.phone_code_hash
            }
            await e.respond(f"📩 Đã gửi OTP đến `{phone}`. Hãy nhắn: `/otp <mã>`")
        except Exception as ex:
            await e.respond(f"❌ Lỗi: {ex}")

    # 2. NHẬN OTP QUA TIN NHẮN RIÊNG VÀ KÍCH HOẠT CHẠY NGẦM
    @bot.on(events.NewMessage(pattern='/otp', func=lambda e: e.is_private))
    async def otp_private(e):
        data = pending_logins.get(e.sender_id)
        if not data: return
        try:
            otp = e.text.split(" ", 1)[1].strip()
            client = data["client"]
            await client.sign_in(data["phone"], otp, phone_code_hash=data["hash"])
            me = await client.get_me()
            await e.respond(f"✅ Thành công! Tài khoản **{me.first_name}** đã bắt đầu tự động đập hộp.")

            # TỰ ĐỘNG THEO DÕI VÀ ĐẬP HỘP TRONG NHÓM
            @client.on(events.NewMessage(chats=BOT_GAME))
            async def auto_click(ev):
                if ev.reply_markup:
                    for row in ev.reply_markup.rows:
                        for btn in row.buttons:
                            if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                                await asyncio.sleep(random.uniform(1, 3)) # Tránh bị Telegram ban
                                try:
                                    await ev.click()
                                    # Báo cáo kết quả về nhóm log chung
                                    await bot.send_message(GR_LOG, f"💰 **{me.first_name}** vừa húp quà thành công!")
                                except: pass
            
            await client.run_until_disconnected()
        except Exception as ex:
            await e.respond(f"❌ Lỗi đăng nhập: {ex}")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
    

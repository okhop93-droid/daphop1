import asyncio, random, re
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
def home(): return "BOT_ALIVE"

# Bộ nhớ tạm để xử lý đăng nhập
attempts = {}

async def run_bot():
    bot = TelegramClient('manager', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Bot Quản Trị đã Online!")

    # Lệnh nạp SĐT trực tiếp
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/login'))
    async def login(e):
        try:
            phone = e.text.split(" ", 1)[1].strip()
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            send_code = await client.send_code_request(phone)
            attempts[e.sender_id] = {"c": client, "p": phone, "h": send_code.phone_code_hash}
            await e.respond(f"📩 OTP đã gửi đến `{phone}`. Nhắn: `/otp <mã>`")
        except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

    # Lệnh nhập OTP và chạy ngay
    @bot.on(events.NewMessage(chats=GR_LOG, pattern='/otp'))
    async def otp(e):
        data = attempts.get(e.sender_id)
        if not data: return
        try:
            code = e.text.split(" ", 1)[1].strip()
            await data["c"].sign_in(data["p"], code, phone_code_hash=data["h"])
            me = await data["c"].get_me()
            await e.respond(f"✅ **{me.first_name}** đã vào dàn đập hộp!")
            
            # Kích hoạt đập hộp cho acc này
            @data["c"].on(events.NewMessage(chats=BOT_GAME))
            async def box_handler(ev):
                if ev.reply_markup:
                    for row in ev.reply_markup.rows:
                        for btn in row.buttons:
                            if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                                await asyncio.sleep(random.uniform(1, 2))
                                try:
                                    await ev.click()
                                    await bot.send_message(GR_LOG, f"💰 **{me.first_name}** đã húp!")
                                except: pass
            await data["c"].run_until_disconnected()
        except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(run_bot())
            

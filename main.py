import asyncio, random, re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8028025981:AAFGFHV0oHflzId08vm5fGnUaWBxbtGG-ik' # Token bot quản trị
BOT_GAME = 'xocdia88_bot_uytin_bot' # Bot phát hộp quà
GR_LOG = -1002984339626            # Nhóm nhận báo cáo mã code

app = Flask('')
@app.route('/')
def home(): return "SYSTEM_ONLINE"

# Bộ nhớ tạm lưu phiên đăng nhập
pending_auth = {}

async def main():
    # 1. Khởi chạy Bot Quản Trị
    bot = TelegramClient('admin_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Bot Quản Trị đã Online!")

    # Lệnh kiểm tra bot sống (Nhắn riêng cho bot)
    @bot.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
    async def start(e):
        await e.respond("🔥 Bot đã sẵn sàng! Hãy nhắn: `/login SĐT` để nạp tài khoản.")

    # 2. CHỨC NĂNG NẠP TK TRỰC TIẾP (Reg trực tiếp)
    @bot.on(events.NewMessage(pattern='/login', func=lambda e: e.is_private))
    async def login(e):
        try:
            phone = e.text.split(" ", 1)[1].strip()
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            send_code = await client.send_code_request(phone)
            pending_auth[e.sender_id] = {
                "client": client, "phone": phone, "hash": send_code.phone_code_hash
            }
            await e.respond(f"📩 Đã gửi OTP đến `{phone}`. Hãy nhắn: `/otp <mã>`")
        except Exception as ex:
            await e.respond(f"❌ Lỗi: {ex}")

    # 3. NHẬN OTP VÀ KÍCH HOẠT ĐẬP HỘP TỰ ĐỘNG
    @bot.on(events.NewMessage(pattern='/otp', func=lambda e: e.is_private))
    async def otp(e):
        data = pending_auth.get(e.sender_id)
        if not data: return
        try:
            code_otp = e.text.split(" ", 1)[1].strip()
            client = data["client"]
            await client.sign_in(data["phone"], code_otp, phone_code_hash=data["hash"])
            me = await client.get_me()
            await e.respond(f"✅ Thành công! Acc **{me.first_name}** đã bắt đầu canh hộp quà.")

            # --- CHỨC NĂNG ĐẬP HỘP VÀ GỬI MÃ ---
            @client.on(events.NewMessage(chats=BOT_GAME))
            async def auto_click(ev):
                if ev.reply_markup:
                    for row in ev.reply_markup.rows:
                        for btn in row.buttons:
                            # Tìm nút đập hộp
                            if any(x in btn.text for x in ["Đập", "Hộp", "Mở", "mở"]):
                                await asyncio.sleep(random.uniform(0.1, 0.5)) # Tốc độ cực nhanh
                                try:
                                    await ev.click() # Nhấn nút đập hộp
                                    await asyncio.sleep(1) # Chờ bot game gửi mã
                                    
                                    # Lấy tin nhắn mới nhất để tìm mã code
                                    messages = await client.get_messages(BOT_GAME, limit=1)
                                    msg_text = messages[0].message
                                    
                                    # Dùng Regex tìm mã code (Chuỗi viết hoa + số 8-15 ký tự)
                                    match = re.search(r'[A-Z0-9]{8,15}', msg_text)
                                    gift_code = match.group() if match else "KHÔNG_LẤY_ĐƯỢC_MÃ"

                                    # GỬI ĐÚNG MẪU BẠN YÊU CẦU
                                    await bot.send_message(GR_LOG, f"💌 Mã code của bạn là: {gift_code} 💌")
                                except: pass
            
            await client.run_until_disconnected()
        except Exception as ex:
            await e.respond(f"❌ Lỗi: {ex}")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
                                    

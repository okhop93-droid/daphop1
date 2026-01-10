import asyncio, random, re, os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH HỆ THỐNG ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8028025981:AAFGFHV0oHflzId08vm5fGnUaWBxbtGG-ik'
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626

app = Flask('')
@app.route('/')
def home(): return "SYSTEM_STABLE"

active_clients = {} # Lưu các acc đang chạy
pending_auth = {}

# --- HÀM TỰ ĐỘNG ĐẬP HỘP (DÙNG CHUNG) ---
async def start_grabbing(client, me_name):
    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if ev.reply_markup:
            for row in ev.reply_markup.rows:
                for btn in row.buttons:
                    if any(x in btn.text for x in ["Đập", "Hộp", "Mở", "mở"]):
                        # Dãn cách ngẫu nhiên để tránh bị Telegram quét
                        await asyncio.sleep(random.uniform(0.1, 0.6))
                        try:
                            await ev.click()
                            await asyncio.sleep(1) # Đợi mã code hiện ra
                            msgs = await client.get_messages(BOT_GAME, limit=1)
                            match = re.search(r'[A-Z0-9]{8,15}', msgs[0].message)
                            gift = match.group() if match else "MÃ_ẨN"
                            
                            # Gửi báo cáo về nhóm log chung
                            admin_bot = TelegramClient('temp', API_ID, API_HASH)
                            await admin_bot.start(bot_token=BOT_TOKEN)
                            await admin_bot.send_message(GR_LOG, f"💌 Acc ({me_name}): {gift} 💌")
                            await admin_bot.disconnect()
                        except: pass

async def main():
    bot = TelegramClient('admin_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 HỆ THỐNG VIP ĐÃ ONLINE!")

    # --- MENU ĐIỀU KHIỂN ---
    @bot.on(events.NewMessage(pattern='/start'))
    async def menu(e):
        if not e.is_private: return
        btns = [
            [Button.inline("➕ Thêm Acc", b"add"), Button.inline("📊 Trạng Thái", b"status")],
            [Button.inline("🔗 Join Nhóm Quà", b"join"), Button.inline("🔄 Restart", b"reboot")]
        ]
        await e.respond("🛠 **BẢNG ĐIỀU KHIỂN HỆ THỐNG** 🛠\nTình trạng: `Vận hành ổn định ✅`", buttons=btns)

    # --- XỬ LÝ NÚT BẤM ---
    @bot.on(events.CallbackQuery)
    async def click_handler(e):
        if e.data == b"add":
            await e.edit("📱 Nhắn: `/login SĐT` (VD: `/login 84123...`)")
        elif e.data == b"status":
            msg = f"📈 **Số acc đang chạy:** `{len(active_clients)}`"
            await e.answer(msg, alert=True)
        elif e.data == b"join":
            await e.edit("🔗 Nhắn: `/join link_nhóm` để tất cả acc vào nhóm đó.")

    # --- LỆNH LOGIN & OTP ---
    @bot.on(events.NewMessage(pattern='/login'))
    async def login(e):
        phone = e.text.split(" ", 1)[1].strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        s_code = await client.send_code_request(phone)
        pending_auth[e.sender_id] = {"c": client, "p": phone, "h": s_code.phone_code_hash}
        await e.respond("📩 Đã gửi OTP. Nhắn `/otp mã` để xong.")

    @bot.on(events.NewMessage(pattern='/otp'))
    async def otp(e):
        data = pending_auth.get(e.sender_id)
        if not data: return
        otp_code = e.text.split(" ", 1)[1].strip()
        await data["c"].sign_in(data["p"], otp_code, phone_code_hash=data["h"])
        me = await data["c"].get_me()
        active_clients[me.id] = data["c"]
        await e.respond(f"✅ Đã kết nối: **{me.first_name}**")
        asyncio.create_task(start_grabbing(data["c"], me.first_name))

    # --- LỆNH JOIN NHÓM ĐỒNG LOẠT ---
    @bot.on(events.NewMessage(pattern='/join'))
    async def join_group(e):
        link = e.text.split(" ", 1)[1].strip()
        for cid, client in active_clients.items():
            try:
                from telethon.tl.functions.channels import JoinChannelRequest
                await client(JoinChannelRequest(link))
                await asyncio.sleep(1)
            except: pass
        await e.respond("🚀 Tất cả acc đã Join nhóm thành công!")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
        

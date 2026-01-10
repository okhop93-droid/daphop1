import asyncio, random, re, os, time
from telethon import TelegramClient, events, Button, errors, functions
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH HỆ THỐNG ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8028025981:AAHkk0rLr35pDP6ooYg09hSV9ys1SJu9pfY'
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626
SESSION_FILE = "database_sessions.txt"

app = Flask('')
@app.route('/')
def home(): return "SYSTEM_STABLE_READY"

active_clients = {} 
pending_auth = {}
recent_codes = set()
stat_counter = 0

# --- CHỨC NĂNG HỒI SINH & LƯU TRỮ ---
def save_session(session_str):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        content = f.read()
        if session_str not in content:
            f.write(session_str + "\n")

async def auto_revive(bot_admin):
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            sessions = f.read().splitlines()
        count = 0
        for s_str in sessions:
            if not s_str.strip(): continue
            try:
                c = TelegramClient(StringSession(s_str), API_ID, API_HASH)
                await c.connect()
                if await c.is_user_authorized():
                    me = await c.get_me()
                    active_clients[me.id] = c
                    asyncio.create_task(start_grabbing(c, me.first_name, bot_admin))
                    count += 1
            except: continue
        if count > 0:
            await bot_admin.send_message(GR_LOG, f"🔄 **HỒI SINH:** Đã kết nối lại `{count}` tài khoản!")

# --- LOGIC ĐẬP HỘP THÔNG MINH ---
async def start_grabbing(client, me_name, bot_admin):
    global stat_counter
    @client.on(events.NewMessage(chats=BOT_GAME))
    async def grab_handler(ev):
        if not ev.reply_markup: return
        target = next((b for r in ev.reply_markup.rows for b in r.buttons if any(x in b.text.lower() for x in ["đập", "hộp", "mở"])), None)
        
        if target:
            await asyncio.sleep(random.uniform(0.1, 0.7))
            try:
                await ev.click()
                await asyncio.sleep(1.2)
                msgs = await client.get_messages(BOT_GAME, limit=1)
                match = re.search(r'[A-Z0-9]{8,15}', msgs[0].message)
                if match:
                    gift = match.group()
                    if gift not in recent_codes:
                        recent_codes.add(gift)
                        stat_counter += 1
                        await bot_admin.send_message(GR_LOG, f"🎁 **HÚP QUÀ THÀNH CÔNG** 🎁\n━━━━━━━━━━━━━\n👤 **Acc:** `{me_name}`\n📩 **Mã:** `{gift}`")
                        await asyncio.sleep(60)
                        recent_codes.discard(gift)
            except: pass

async def main():
    # Khởi tạo Admin Bot (Xử lý drop_pending để fix phân thân)
    bot = TelegramClient('admin_core', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # Kích hoạt hồi sinh tự động
    await auto_revive(bot)

    # --- MENU GIAO DIỆN LUXURY ---
    def main_btns():
        return [
            [Button.inline("➕ Nạp Acc", b"add"), Button.inline("📑 Danh Sách", b"list")],
            [Button.inline("🛡️ Check Spam", b"check"), Button.inline("📊 Thống Kê", b"stats")],
            [Button.inline("🔗 Join Nhóm", b"join_ui"), Button.inline("🔄 Restart", b"reboot")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def dashboard(e):
        if not e.is_private: return
        text = (
            "💎 **HỆ THỐNG QUẢN TRỊ TRUNG TÂM** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Admin:** `{e.sender.first_name}`\n"
            f"📦 **Đang trực:** `{len(active_clients)}` Acc | 🟢 Online\n"
            f"📅 **Ngày:** {time.strftime('%d/%m/%Y')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await e.respond(text, buttons=main_btns())

    @bot.on(events.CallbackQuery)
    async def cb_handler(e):
        if e.data == b"list":
            text = "📑 **DANH SÁCH TÀI KHOẢN:**\n━━━━━━━━━━━━━━━━━━━━\n"
            for i, (uid, c) in enumerate(active_clients.items(), 1):
                me = await c.get_me()
                text += f"{i}. 👤 `{me.first_name}` | `+{me.phone}`\n"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])
        
        elif e.data == b"stats":
            text = (
                "📊 **BÁO CÁO CHIẾN DỊCH** 📊\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 **Tổng quà đã húp:** `{stat_counter}`\n"
                f"👤 **Số acc:** `{len(active_clients)}` acc\n"
                f"📈 **Biểu đồ:** {'🟩' * len(active_clients)}{'⬜' * (10-len(active_clients))}"
            )
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif e.data == b"check":
            await e.answer("⏳ Đang quét trạng thái SpamBot...", alert=False)
            res = "🛡️ **KẾT QUẢ CHECK SPAM:**\n\n"
            for uid, c in active_clients.items():
                me = await c.get_me()
                async with c.conversation("@SpamBot") as conv:
                    await conv.send_message("/start")
                    reply = await conv.get_response()
                    status = "✅ Sạch" if "no limits" in reply.text.lower() else "🔴 Chặn"
                    res += f"• `{me.first_name}`: {status}\n"
            await e.edit(res, buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif e.data == b"add":
            await e.edit("📱 Nhắn: `/login SĐT` (VD: `/login 84xxx`)", buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif e.data == b"join_ui":
            await e.edit("🔗 Nhắn: `/join link_hoặc_username` để dàn acc vào nhóm.", buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif e.data == b"back":
            await e.edit("💎 **HỆ THỐNG QUẢN TRỊ TRUNG TÂM**", buttons=main_btns())

    # --- LOGIC NẠP ACC & OTP ---
    @bot.on(events.NewMessage(pattern='/login'))
    async def login(e):
        try:
            phone = e.text.split(" ", 1)[1].strip().replace("+", "").replace(" ", "")
            c = TelegramClient(StringSession(), API_ID, API_HASH)
            await c.connect()
            s = await c.send_code_request(phone)
            pending_auth[e.sender_id] = {"c": c, "p": phone, "h": s.phone_code_hash}
            await e.respond(f"📩 **OTP** đã gửi tới `+{phone}`. Nhắn `/otp mã` ngay.")
        except: await e.respond("❌ Lỗi: Sai định dạng SĐT!")

    @bot.on(events.NewMessage(pattern='/otp'))
    async def otp(e):
        data = pending_auth.get(e.sender_id)
        if not data: return
        try:
            code = e.text.split(" ", 1)[1].strip()
            await data["c"].sign_in(data["p"], code, phone_code_hash=data["h"])
            save_session(data["c"].session.save())
            me = await data["c"].get_me()
            active_clients[me.id] = data["c"]
            await e.respond(f"🌟 **NẠP THÀNH CÔNG:** `{me.first_name}`")
            asyncio.create_task(start_grabbing(data["c"], me.first_name, bot))
        except Exception as ex: await e.respond(f"❌ **Lỗi OTP:** `{ex}`")

    # --- AUTO JOIN NHÓM ---
    @bot.on(events.NewMessage(pattern='/join'))
    async def join_cmd(e):
        link = e.text.split(" ", 1)[1].strip()
        await e.respond(f"🚀 Đang cho {len(active_clients)} acc join...")
        for c in active_clients.values():
            try: await c(functions.channels.JoinChannelRequest(channel=link)); await asyncio.sleep(5)
            except: pass
        await e.respond("✅ Hoàn tất lệnh Join!")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
        
        elif e.data == b"check":
            await e.answer("⏳ Đang quét trạng thái SpamBot...", alert=False)
            res = "🛡️ **KẾT QUẢ KIỂM TRA SPAM:**\n\n"
            for uid, c in active_clients.items():
                me = await c.get_me()
                async with c.conversation("@SpamBot") as conv:
                    await conv.send_message("/start")
                    reply = await conv.get_response()
                    status = "✅ Sạch" if "no limits" in reply.text.lower() else "🔴 Bị chặn"
                    res += f"• `{me.first_name}`: {status}\n"
            await e.edit(res, buttons=[Button.inline("⬅️ Quay lại", b"back")])

        elif e.data == b"back":
            await e.edit("💎 **BẢNG QUẢN TRỊ HỆ THỐNG VIP**", buttons=get_main_btns())

    # --- ĐĂNG NHẬP LUXURY ---
    @bot.on(events.NewMessage(pattern='/login'))
    async def login_proc(e):
        try:
            phone = e.text.split(" ", 1)[1].strip()
            c = TelegramClient(StringSession(), API_ID, API_HASH)
            await c.connect()
            s = await c.send_code_request(phone)
            pending_auth[e.sender_id] = {"c": c, "p": phone, "h": s.phone_code_hash}
            await e.respond(f"📩 **Mã OTP** đã gửi về `+{phone}`. Nhập `/otp <mã>` ngay.")
        except: await e.respond("❌ Lỗi: Sai SĐT hoặc API!")

    @bot.on(events.NewMessage(pattern='/otp'))
    async def otp_proc(e):
        data = pending_auth.get(e.sender_id)
        if not data: return
        code = e.text.split(" ", 1)[1].strip()
        try:
            await data["c"].sign_in(data["p"], code, phone_code_hash=data["h"])
            save_session(data["c"].session.save()) # Lưu lại để không mất acc
            me = await data["c"].get_me()
            active_clients[me.id] = data["c"]
            await e.respond(f"🌟 **NẠP THÀNH CÔNG:** `{me.first_name}`")
            asyncio.create_task(start_grabbing(data["c"], me.first_name, bot))
        except Exception as ex: await e.respond(f"❌ **Lỗi OTP:** `{ex}`")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
    

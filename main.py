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
def home(): return "👑 SYSTEM ONLINE"

active_clients = {} 
pending_auth = {}
recent_codes = set()
stat_counter = 0

# --- LOGIC LƯU TRỮ BỀN BỈ ---
def save_session(session_str):
    try:
        with open(SESSION_FILE, "a+") as f:
            f.seek(0)
            if session_str not in f.read():
                f.write(session_str + "\n")
    except: pass

# --- LOGIC ĐẬP HỘP THÔNG MINH (CHỐNG TRÙNG & DELAY) ---
async def start_grabbing(client, me_name, bot_admin):
    global stat_counter
    @client.on(events.NewMessage(chats=BOT_GAME))
    async def grabber(ev):
        if not ev.reply_markup: return
        target = next((b for r in ev.reply_markup.rows for b in r.buttons if any(x in b.text.lower() for x in ["đập", "hộp", "mở"])), None)
        
        if target:
            # Delay thông minh chống bị quét Bot
            await asyncio.sleep(random.uniform(0.1, 0.6))
            try:
                await ev.click()
                await asyncio.sleep(1.2)
                msgs = await client.get_messages(BOT_GAME, limit=1)
                match = re.search(r'[A-Z0-9]{8,15}', msgs[0].message)
                if match:
                    code = match.group()
                    # Chống báo trùng tin nhắn log
                    if code not in recent_codes:
                        recent_codes.add(code)
                        stat_counter += 1
                        await bot_admin.send_message(GR_LOG, f"🎁 **HÚP QUÀ THÀNH CÔNG** 🎁\n━━━━━━━━━━━━━\n👤 **Acc:** `{me_name}`\n📩 **Mã:** `{code}`")
                        await asyncio.sleep(60)
                        recent_codes.discard(code)
            except: pass

async def main():
    # Khởi tạo bot - Fix lỗi phân thân triệt để
    bot = TelegramClient('admin_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # TỰ ĐỘNG HỒI SINH DÀN ACC
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            sessions = f.read().splitlines()
        for s in sessions:
            if not s.strip(): continue
            try:
                c = TelegramClient(StringSession(s), API_ID, API_HASH)
                await c.connect()
                if await c.is_user_authorized():
                    me = await c.get_me()
                    active_clients[me.id] = c
                    asyncio.create_task(start_grabbing(c, me.first_name, bot))
            except: continue

    # --- GIAO DIỆN DASHBOARD ---
    def menu_ui():
        return [
            [Button.inline("➕ Nạp Acc VIP", b"add_acc"), Button.inline("📑 Danh Sách Acc", b"list_acc")],
            [Button.inline("📊 Thống Kê", b"view_stats"), Button.inline("🛡️ Check Spam", b"check_spam")],
            [Button.inline("🔄 Restart", b"reboot_system")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(e):
        if not e.is_private: return
        text = (
            "💎 **HỆ THỐNG QUẢN TRỊ TRUNG TÂM** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Admin:** `{e.sender.first_name}`\n"
            f"📦 **Đang chạy:** `{len(active_clients)}` Acc | 🟢 Online\n"
            f"📈 **Tổng húp:** `{stat_counter}` mã quà\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await e.respond(text, buttons=menu_ui())

    # --- XỬ LÝ NÚT BẤM (DÙNG EDIT ĐỂ CHỐNG PHÂN THÂN) ---
    @bot.on(events.CallbackQuery)
    async def callback_mgr(e):
        if e.data == b"list_acc":
            text = "📑 **DANH SÁCH ACC ĐANG TRỰC:**\n━━━━━━━━━━━━━━━━━━━━\n"
            if not active_clients: text += "*(Trống)*"
            for i, (uid, c) in enumerate(active_clients.items(), 1):
                me = await c.get_me()
                text += f"{i}. 👤 `{me.first_name}` | `+{me.phone}` 🟢\n"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back_home")])
            
        elif e.data == b"add_acc":
            await e.edit("📱 **TRÌNH NẠP ACC VIP**\n\nNhập lệnh theo cú pháp bên dưới:\n`/login SĐT` (Ví dụ: `/login 84123...`)", 
                         buttons=[Button.inline("⬅️ Quay lại", b"back_home")])

        elif e.data == b"view_stats":
            await e.edit(f"📊 **BÁO CÁO CHIẾN DỊCH**\n━━━━━━━━━━━━━━━━━━━━\n🎁 Tổng mã húp: `{stat_counter}`\n📦 Acc Online: `{len(active_clients)}`", 
                         buttons=[Button.inline("⬅️ Quay lại", b"back_home")])

        elif e.data == b"back_home":
            await e.edit("💎 **HỆ THỐNG QUẢN TRỊ TRUNG TÂM**", buttons=menu_ui())

    # --- LOGIC LOGIN & OTP (FIX MỌI LỖI NHẬP LIỆU) ---
    @bot.on(events.NewMessage(pattern='/login'))
    async def login_cmd(e):
        try:
            raw_phone = e.text.split(" ", 1)[1]
            phone = "".join(filter(str.isdigit, raw_phone)) # Chỉ lấy số, xoá mọi kí tự lạ
            
            c = TelegramClient(StringSession(), API_ID, API_HASH)
            await c.connect()
            s = await c.send_code_request(phone)
            pending_auth[e.sender_id] = {"c": c, "p": phone, "h": s.phone_code_hash}
            
            await e.respond(f"📩 **OTP** đã gửi đến `+{phone}`\nNhập: `/otp mã` (VD: `/otp 12345`)")
        except:
            await e.respond("❌ **Lỗi:** Sai định dạng SĐT. Hãy nhập `/login 84...`")

    @bot.on(events.NewMessage(pattern='/otp'))
    async def otp_cmd(e):
        data = pending_auth.get(e.sender_id)
        if not data: return
        try:
            otp_val = "".join(filter(str.isdigit, e.text))
            await data["c"].sign_in(data["p"], otp_val, phone_code_hash=data["h"])
            save_session(data["c"].session.save())
            me = await data["c"].get_me()
            active_clients[me.id] = data["c"]
            await e.respond(f"🌟 **KÍCH HOẠT THÀNH CÔNG:** `{me.first_name}`")
            asyncio.create_task(start_grabbing(data["c"], me.first_name, bot))
        except Exception as ex:
            await e.respond(f"❌ **Lỗi:** `{str(ex)}`")

    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
    

import asyncio, random, re, os
from telethon import TelegramClient, events, Button, errors
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
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
recent_codes = set() # Bộ nhớ đệm chống trùng tin

# --- HÀM LƯU SESSION (BẢO VỆ DÀN ACC) ---
def save_session(session_str):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if session_str not in f.read():
            f.write(session_str + "\n")

# --- LOGIC ĐẬP HỘP & CHỐNG TRÙNG TIN ---
async def start_grabbing(client, me_name, bot_admin):
    @client.on(events.NewMessage(chats=BOT_GAME))
    async def grab_handler(ev):
        if not ev.reply_markup: return
        
        target = None
        for row in ev.reply_markup.rows:
            for btn in row.buttons:
                if any(x in btn.text.lower() for x in ["đập", "hộp", "mở", "click"]):
                    target = btn
                    break
        
        if target:
            # Dãn cách ngẫu nhiên 0.1s - 0.8s (Chống ban)
            await asyncio.sleep(random.uniform(0.1, 0.8))
            try:
                await ev.click()
                await asyncio.sleep(1.2)
                msgs = await client.get_messages(BOT_GAME, limit=1)
                match = re.search(r'[A-Z0-9]{8,15}', msgs[0].message)
                if match:
                    gift = match.group()
                    # CHỐNG TRÙNG TIN: Chỉ báo nếu mã này mới húp lần đầu
                    if gift not in recent_codes:
                        recent_codes.add(gift)
                        await bot_admin.send_message(GR_LOG, f"🎁 **HÚP QUÀ THÀNH CÔNG** 🎁\n━━━━━━━━━━━━━\n👤 **Acc:** `{me_name}`\n📩 **Mã:** `{gift}`")
                        await asyncio.sleep(60) # Lưu vết 60s
                        recent_codes.discard(gift)
            except: pass

async def main():
    # Fix phân thân bằng drop_pending
    bot = TelegramClient('admin_core', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # Hồi sinh dàn acc sau khi reset server
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            for s in f.read().splitlines():
                if not s.strip(): continue
                try:
                    c = TelegramClient(StringSession(s), API_ID, API_HASH)
                    await c.connect()
                    if await c.is_user_authorized():
                        me = await c.get_me()
                        active_clients[me.id] = c
                        asyncio.create_task(start_grabbing(c, me.first_name, bot))
                except: continue

    # --- MENU DASHBOARD LOGIC (FIX PHÂN THÂN) ---
    def get_main_btns():
        return [
            [Button.inline("➕ Nạp Acc", b"add"), Button.inline("📑 Danh Sách Acc", b"list")],
            [Button.inline("🛡️ Check SpamBot", b"check"), Button.inline("📊 Thống Kê", b"stats")],
            [Button.inline("🔄 Restart", b"reboot")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def dashboard(e):
        if not e.is_private: return
        text = (
            "💎 **BẢNG QUẢN TRỊ HỆ THỐNG VIP** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Admin:** `{e.sender.first_name}`\n"
            f"📦 **Đang trực:** `{len(active_clients)}` Tài khoản\n"
            "🟢 **Trạng thái:** `Vận hành ổn định`"
        )
        await e.respond(text, buttons=get_main_btns())

    @bot.on(events.CallbackQuery)
    async def cb_logic(e):
        # Dùng edit() để không đẻ thêm tin nhắn mới
        if e.data == b"list":
            text = "📑 **TRẠNG THÁI DÀN ACC SỊN:**\n\n"
            for uid, c in active_clients.items():
                me = await c.get_me()
                text += f"• `{me.first_name}` | `+{me.phone}` 🟢\n"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])
        
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
    

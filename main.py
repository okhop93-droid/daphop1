import asyncio, random, re, os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH HỆ THỐNG ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8028025981:AAE0TJ_wB0AIYvjjbp_qcupIkEQXdtNEKdU'
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626
SESSION_FILE = "sessions.txt" # Nơi lưu trữ dàn acc để không mất khi reset

app = Flask('')
@app.route('/')
def home(): return "SYSTEM_STABLE_2026"

active_clients = {} 
pending_auth = {}

# --- HÀM LƯU VÀ TẢI SESSION (CHỐNG MẤT ACC) ---
def save_session(session_str):
    with open(SESSION_FILE, "a") as f:
        f.write(session_str + "\n")

async def load_sessions(bot_admin):
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            sessions = f.read().splitlines()
            for s in sessions:
                if s.strip():
                    try:
                        client = TelegramClient(StringSession(s), API_ID, API_HASH)
                        await client.connect()
                        if await client.is_user_authorized():
                            me = await client.get_me()
                            active_clients[me.id] = client
                            asyncio.create_task(start_grabbing(client, me.first_name, bot_admin))
                    except: pass
        print(f"✅ Đã hồi sinh {len(active_clients)} tài khoản từ bộ nhớ!")

# --- LOGIC ĐẬP HỘP THÔNG MINH (ANTI-BAN) ---
async def start_grabbing(client, me_name, bot_admin):
    @client.on(events.NewMessage(chats=BOT_GAME))
    async def grab_box(ev):
        if ev.reply_markup:
            for row in ev.reply_markup.rows:
                for btn in row.buttons:
                    if any(x in btn.text.lower() for x in ["đập", "hộp", "mở"]):
                        # Delay dãn cách giữa các acc để tránh bị quét
                        await asyncio.sleep(random.uniform(0.1, 0.8))
                        try:
                            await ev.click()
                            await asyncio.sleep(1)
                            msgs = await client.get_messages(BOT_GAME, limit=1)
                            match = re.search(r'[A-Z0-9]{8,15}', msgs[0].message)
                            if match:
                                code = match.group()
                                await bot_admin.send_message(GR_LOG, f"💌 **Acc ({me_name}) húp được:** `{code}` 💌")
                        except: pass

async def main():
    # Khởi tạo bot với drop_pending=True để DIỆT LỖI PHÂN THÂN
    bot = TelegramClient('admin_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # Tự động tải lại dàn acc cũ khi server restart
    await load_sessions(bot)

    # --- GIAO DIỆN DASHBOARD SỊN ---
    def get_main_buttons():
        return [
            [Button.inline("➕ Nạp Acc Mới", b"add"), Button.inline("📑 Danh Sách Acc", b"list")],
            [Button.inline("🔗 Join Nhóm", b"join"), Button.inline("📊 Thống Kê", b"stats")],
            [Button.inline("🔄 Restart Hệ Thống", b"reboot")]
        ]

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(e):
        if not e.is_private: return
        text = (
            "💎 **HỆ THỐNG QUẢN TRỊ TRUNG TÂM** 💎\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Admin:** `{e.sender.first_name}`\n"
            f"📦 **Đang trực chiến:** `{len(active_clients)}` Acc\n"
            "🟢 **Trạng thái:** `Vận hành ổn định`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 *Vui lòng chọn chức năng:*"
        )
        await e.respond(text, buttons=get_main_buttons())

    # --- XỬ LÝ LOGIC NÚT BẤM ---
    @bot.on(events.CallbackQuery)
    async def cb_handler(e):
        if e.data == b"add":
            await e.edit("📱 Nhắn: `/login SĐT` (Ví dụ: `/login 84123...`)", 
                         buttons=[Button.inline("⬅️ Quay lại", b"back")])
        
        elif e.data == b"list":
            text = "📑 **DANH SÁCH TÀI KHOẢN SỊN**\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, (uid, client) in enumerate(active_clients.items(), 1):
                me = await client.get_me()
                p = me.phone
                text += f"{i}. 👤 **{me.first_name}** | 📱 `+{p[:2]} {p[2:5]}...` | 🟢\n"
            await e.edit(text, buttons=[Button.inline("⬅️ Quay lại", b"back")])
            
        elif e.data == b"back":
            await e.edit("💎 **BẢNG ĐIỀU KHIỂN TRUNG TÂM**", buttons=get_main_buttons())

    # --- ĐĂNG NHẬP & GIÁM SÁT ACC CHẾT ---
    @bot.on(events.NewMessage(pattern='/login'))
    async def login(e):
        phone = e.text.split(" ", 1)[1].strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        s_code = await client.send_code_request(phone)
        pending_auth[e.sender_id] = {"c": client, "p": phone, "h": s_code.phone_code_hash}
        await e.respond(f"📩 OTP đã gửi tới `{phone}`. Nhắn `/otp mã` ngay.")

    @bot.on(events.NewMessage(pattern='/otp'))
    async def otp(e):
        data = pending_auth.get(e.sender_id)
        if not data: return
        otp_val = e.text.split(" ", 1)[1].strip()
        await data["c"].sign_in(data["p"], otp_val, phone_code_hash=data["h"])
        me = await data["c"].get_me()
        active_clients[me.id] = data["c"]
        
        # Lưu Session String để không mất khi server reset
        save_session(data["c"].session.save())
        
        await e.respond(f"✅ **Đã nạp thành công:** {me.first_name}")
        asyncio.create_task(start_grabbing(data["c"], me.first_name, bot))

    # --- TRÌNH GIÁM SÁT ACC CHẾT ---
    async def health_check():
        while True:
            await asyncio.sleep(300)
            for uid, client in list(active_clients.items()):
                try:
                    if not await client.is_user_authorized(): raise Exception()
                except:
                    me = await client.get_me()
                    phone = me.phone if me else "???"
                    del active_clients[uid]
                    await bot.send_message(GR_LOG, f"🚨 **SỐ ĐIỆN THOẠI CHẾT:** `+{phone}` đã văng hệ thống!")
    
    asyncio.create_task(health_check())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.run(main())
            

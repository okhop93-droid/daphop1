import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from supabase import create_client, Client
from quart import Quart, request, jsonify

# ===== CẤU HÌNH HỆ THỐNG =====
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"
STK_MSB = "96886693002613"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"
PRICE_PER_DAY = 10000
ADMIN_ID = 7816353760  # <<< THAY ID TELEGRAM CỦA BẠN VÀO ĐÂY

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)

# --- HELPER FUNCTIONS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- LOGIC GRAB LOOP ---
async def worker_grab_loop(client, phone, owner_id):
    try:
        if not client.is_connected(): await client.connect()
        if not await client.is_user_authorized(): return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            # Kiểm tra hết hạn mỗi khi có tin nhắn mới
            res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
            if not res.data: return
            
            expiry = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
            if expiry < datetime.now(timezone.utc):
                await client.disconnect()
                return

            if ev.reply_markup:
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.1, 0.4))
                    try:
                        await ev.click()
                        await asyncio.sleep(1.5)
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        if msgs and "là:" in msgs[0].message:
                            code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                            await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                    except: pass
        await client.run_until_disconnected()
    except Exception: pass

# --- UI COMPONENTS ---
def main_menu_text(user):
    return (
        f"👑 **HỆ THỐNG CLONE VIP** 👑\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Người dùng: `{user['user_id']}`\n"
        f"💰 Số dư: **{user['balance']:,} VNĐ**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *Trạng thái: Hoạt động ổn định*"
    )

def main_btns(uid):
    btns = [
        [TButton.inline("➕ THÊM ACC MỚI", b"add_clone")],
        [TButton.inline("📱 DANH SÁCH CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("👤 VÍ CỦA TÔI", b"me")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]
    if uid == ADMIN_ID:
        btns.append([TButton.inline("🛠 QUẢN TRỊ VIÊN", b"admin_panel")])
    return btns

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(main_menu_text(user), buttons=main_btns(e.sender_id))

# --- CALLBACK HANDLER ---
@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    await e.answer() # Fix lỗi treo nút (quay quay)

    if data == "back":
        user = db_get_user(uid)
        await e.edit(main_menu_text(user), buttons=main_btns(uid))
    
    elif data == "dep_menu":
        btns = [
            [TButton.inline("💸 10k", b"p_10000"), TButton.inline("💸 20k", b"p_20000")],
            [TButton.inline("💸 50k", b"p_50000"), TButton.inline("💸 100k", b"p_100000")],
            [TButton.inline("🔙 QUAY LẠI", b"back")]
        ]
        await e.edit("🏦 **CHỌN MỆNH GIÁ NẠP**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"📥 **THÔNG TIN CHUYỂN KHOẢN**\n\nSTK: `{STK_MSB}`\nSố tiền: **{int(amt):,}đ**\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 MỞ APP BANK", qr)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.respond("❌ Bạn chưa có clone nào!", buttons=[TButton.inline("🔙", b"back")])
        txt = "📱 **CLONE CỦA BẠN**\n\n"
        btns = []
        for c in res.data:
            txt += f"🔹 `{c['phone']}`\n"
            btns.append([TButton.inline(f"🗑 Xóa {c['phone']}", f"del_{c['id']}")])
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(txt, buttons=btns)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.respond("✅ Đã xóa thành công!")

    # --- ADMIN CALLBACKS ---
    elif data == "admin_panel" and uid == ADMIN_ID:
        u_count = supabase.table("users").select("user_id", count="exact").execute().count
        c_count = supabase.table("my_clones").select("id", count="exact").execute().count
        await e.edit(f"🛠 **ADMIN**\n\nUsers: `{u_count}`\nClones: `{c_count}`", 
                     buttons=[[TButton.inline("📊 XEM TẤT CẢ CLONE", b"adm_clones")], [TButton.inline("🔙", b"back")]])

    elif data == "adm_clones" and uid == ADMIN_ID:
        res = supabase.table("my_clones").select("*").execute()
        txt = "📋 **TẤT CẢ CLONE HỆ THỐNG**\n\n"
        for c in res.data: txt += f"👤 `{c['owner_id']}` | 📱 `{c['phone']}`\n"
        await e.edit(txt[:4000], buttons=[[TButton.inline("🔙", b"admin_panel")]])

# --- ADD CLONE CONVERSATION ---
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_process(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY:
        return await e.answer(f"❌ Cần {PRICE_PER_DAY:,} VNĐ", alert=True)

    async with bot.conversation(e.sender_id) as conv:
        try:
            await conv.send_message("📞 Nhập số điện thoại (+84...):")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)
            
            await conv.send_message("📩 Nhập mã OTP:")
            otp = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 Nhập mật khẩu 2FA:")
                await client.sign_in(password=(await conv.get_response()).text.strip())

            session_str = client.session.save()
            expiry_date = datetime.now(timezone.utc) + timedelta(days=1)
            
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            supabase.table("my_clones").insert({
                "owner_id": e.sender_id, "phone": phone, 
                "session": session_str, "expiry": expiry_date.isoformat()
            }).execute()

            await conv.send_message(f"✅ Đã kích hoạt clone `{phone}`!")
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id))
        except Exception as ex:
            await conv.send_message(f"❌ Lỗi: {str(ex)}")

# --- WEBHOOK SEPAY ---
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    content = d.get("content", "").upper()
    m = re.search(r'NAP\s+(\d+)', content)
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if res.data:
            new_bal = res.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            # Gửi thông báo an toàn qua loop
            bot.loop.create_task(bot.send_message(uid, f"✅ **NẠP THÀNH CÔNG!**\n💰 +{amt:,} VNĐ"))
            bot.loop.create_task(bot.send_message(ADMIN_ID, f"📢 User `{uid}` vừa nạp `{amt:,}` VNĐ"))
    return jsonify({"status": "ok"}), 200

@app.route('/')
async def index():
    return "Bot is running!", 200

# --- KHỞI CHẠY ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    # Tự động chạy lại các clone cũ khi restart
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
            asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
    except: pass
    
    # Chạy Web Server và Bot song song
    config = asyncio.gather(
        bot.run_until_disconnected(),
        app.run_task(host='0.0.0.0', port=10000)
    )
    await config

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    

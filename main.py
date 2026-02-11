import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from supabase import create_client, Client
from quart import Quart, request, jsonify

# ===== CẤU HÌNH =====
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"
STK_MSB = "96886693002613"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"
PRICE_PER_DAY = 10000
ADMIN_ID = 7816353760 

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)
active_clients = {} # Lưu session đang chạy để quản lý trạng thái

# --- DB HELPERS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- CORE LOGIC ---
async def worker_grab_loop(client, phone, owner_id):
    try:
        if not client.is_connected(): await client.connect()
        if not await client.is_user_authorized(): return
        
        active_clients[phone] = True
        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
            if not res.data: return
            exp = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
            if exp < datetime.now(timezone.utc):
                active_clients[phone] = False
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
                            # Lưu vào lịch sử trúng
                            supabase.table("history").insert({"user_id": owner_id, "phone": phone, "code": code}).execute()
                            await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                    except: pass
        await client.run_until_disconnected()
    except: active_clients[phone] = False

# --- UI ---
def main_btns(uid):
    btns = [
        [TButton.inline("➕ THÊM ACC MỚI (10k/ngày)", b"add_clone")],
        [TButton.inline("📱 QUẢN LÝ CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("👤 VÍ / LỊCH SỬ", b"me")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]
    if uid == ADMIN_ID: btns.append([TButton.inline("🛠 QUẢN TRỊ VIÊN", b"adm_main")])
    return btns

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(f"👑 **HỆ THỐNG CLONE VIP**\n💰 Số dư: **{user['balance']:,}đ**", buttons=main_btns(e.sender_id))

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    await e.answer()

    if data == "back":
        user = db_get_user(uid)
        await e.edit(f"👑 **HỆ THỐNG CLONE VIP**\n💰 Số dư: **{user['balance']:,}đ**", buttons=main_btns(uid))

    elif data == "me":
        res = supabase.table("history").select("*").eq("user_id", uid).limit(10).execute()
        txt = f"👤 **HỒ SƠ**\n💰 Số dư: {db_get_user(uid)['balance']:,}đ\n\n🔑 **CODE TRÚNG GẦN ĐÂY:**\n"
        for h in res.data: txt += f"- `{h['code']}` ({h['phone']})\n"
        await e.edit(txt, buttons=[[TButton.inline("🔙", b"back")]])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.edit("❌ Bạn chưa có clone!", buttons=[[TButton.inline("🔙", b"back")]])
        txt = "📱 **DANH SÁCH CLONE**\n\n"
        btns = []
        for c in res.data:
            exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            is_live = "🟢" if active_clients.get(c['phone']) else "🔴"
            txt += f"{is_live} `{c['phone']}`\n⌛ Hết hạn: {exp.strftime('%H:%M %d/%m')}\n\n"
            btns.append([TButton.inline(f"⚙️ Quản lý {c['phone']}", f"mng_{c['id']}")])
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(txt, buttons=btns)

    elif data.startswith("mng_"):
        cid = data.split("_")[1]
        c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
        txt = f"📱 **QUẢN LÝ:** `{c['phone']}`\n⌛ Hết hạn: `{c['expiry']}`"
        btns = [
            [TButton.inline("⏳ GIA HẠN (10k/ngày)", f"ren_{c['id']}")],
            [TButton.inline("🗑 XÓA CLONE", f"del_{c['id']}")],
            [TButton.inline("🔙 QUAY LẠI", b"list_clones")]
        ]
        await e.edit(txt, buttons=btns)

    elif data.startswith("ren_"):
        cid = data.split("_")[1]
        user = db_get_user(uid)
        if user['balance'] < PRICE_PER_DAY: return await e.respond("❌ Không đủ tiền!")
        c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
        cur_exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
        new_exp = max(cur_exp, datetime.now(timezone.utc)) + timedelta(days=1)
        supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("id", cid).execute()
        supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", uid).execute()
        await e.respond(f"✅ Đã gia hạn `{c['phone']}` thêm 24h!")

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.edit("✅ Đã xóa!", buttons=[[TButton.inline("🔙", b"list_clones")]])

    elif data == "dep_menu":
        btns = [[TButton.inline(f"💸 {amt:,}đ", f"p_{amt}")] for amt in [10000, 20000, 50000, 100000]]
        btns.append([TButton.inline("🔙", b"back")])
        await e.edit("🏦 **CHỌN SỐ TIỀN NẠP:**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"📥 **Nạp {int(amt):,}đ**\nSTK: `{STK_MSB}`\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 MỞ APP", qr)], [TButton.inline("🔙", b"dep_menu")]])

    # --- ADMIN ---
    elif data == "adm_main" and uid == ADMIN_ID:
        u_count = supabase.table("users").select("user_id", count="exact").execute().count
        c_count = supabase.table("my_clones").select("id", count="exact").execute().count
        await e.edit(f"🛠 **ADMIN PANEL**\n\nNgười dùng: `{u_count}`\nClone hệ thống: `{c_count}`",
                     buttons=[[TButton.inline("📋 DANH SÁCH CLONE", b"adm_clones")], [TButton.inline("🔙", b"back")]])

    elif data == "adm_clones" and uid == ADMIN_ID:
        res = supabase.table("my_clones").select("*").execute()
        txt = "📋 **TẤT CẢ CLONE:**\n"
        for c in res.data: txt += f"👤 `{c['owner_id']}` | 📱 `{c['phone']}`\n"
        await e.edit(txt[:4000], buttons=[[TButton.inline("🔙", b"adm_main")]])

# --- LOGIN ---
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_process(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY: return await e.answer("❌ Cần 10.000đ", alert=True)
    async with bot.conversation(e.sender_id) as conv:
        try:
            await conv.send_message("📞 Nhập số điện thoại:")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)
            await conv.send_message("📩 Nhập OTP:")
            otp = (await conv.get_response()).text.strip()
            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 Nhập 2FA:")
                await client.sign_in(password=(await conv.get_response()).text.strip())
            
            exp = datetime.now(timezone.utc) + timedelta(days=1)
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            supabase.table("my_clones").insert({"owner_id":e.sender_id,"phone":phone,"session":client.session.save(),"expiry":exp.isoformat()}).execute()
            await conv.send_message(f"✅ Kích hoạt thành công `{phone}`!")
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id))
        except Exception as ex: await conv.send_message(f"❌ Lỗi: {ex}")

# --- WEBHOOK ---
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if res.data:
            new_bal = res.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            bot.loop.create_task(bot.send_message(uid, f"✅ **NẠP THÀNH CÔNG!**\n💰 +{amt:,}đ"))
            bot.loop.create_task(bot.send_message(ADMIN_ID, f"📢 User `{uid}` nạp `{amt:,}`đ"))
    return jsonify({"status": "ok"}), 200

@app.route('/')
async def index(): return "Running!", 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
            asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
    except: pass
    await asyncio.gather(bot.run_until_disconnected(), app.run_task(host='0.0.0.0', port=10000))

if __name__ == '__main__':
    asyncio.run(main())
                

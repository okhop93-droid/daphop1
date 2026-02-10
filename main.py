import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from supabase import create_client, Client

# ===== CẤU HÌNH HỆ THỐNG =====
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"
STK_MSB = "96886693002613"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
PENDING_LOGINS = {}

# --- DB HELPERS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- 🎯 LOGIC ĐẬP HỘP & GỬI CODE RIÊNG BIỆT ---
async def worker_grab_loop(client, phone, owner_id):
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        # Chỉ những người có hạn dùng mới được đập
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
                    await asyncio.sleep(2.0)
                    # Lấy tin nhắn code và chỉ gửi cho chủ clone đó
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        # GỬI RIÊNG TƯ: Không ai nhìn thấy code của ai
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                except: pass

# --- GIAO DIỆN CHÍNH ---
def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"dep_menu")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(f"🦅 **HỆ THỐNG TREO CLONE ĐẬP HỘP**\n💰 Số dư: **{user['balance']:,}đ**\n\n*Giá thuê: 10,000đ / 1 ngày*", buttons=main_btns())
    raise events.StopPropagation

# --- XỬ LÝ CALLBACK (NẠP TIỀN & MENU) ---
@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE**\n💰 Số dư: **{user['balance']:,}đ**", buttons=main_btns())
    
    elif data == "dep_menu":
        btns = [
            [TButton.inline("💰 10k (1 ngày)", b"p_10000"), TButton.inline("💰 20k (2 ngày)", b"p_20000")],
            [TButton.inline("💰 50k (5 ngày)", b"p_50000"), TButton.inline("💰 100k (10 ngày)", b"p_100000")],
            [TButton.inline("🔙 Quay lại", b"back")]
        ]
        await e.edit("🏦 **CHỌN MỨC NẠP TIỀN TỰ ĐỘNG**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **QUÉT MÃ ĐỂ NẠP {int(amt):,}đ**\n\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 MỞ APP NGÂN HÀNG", qr)], [TButton.inline("🔙 Quay lại", b"dep_menu")]])

    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **THÔNG TIN VÍ**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**", buttons=[TButton.inline("🔙 Quay lại", b"back")])

    await e.answer()

# --- WEBHOOK SEPAY (TỰ ĐỘNG CỘNG TIỀN) ---
app = Flask(__name__)
@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    d = request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        new_bal = (res.data[0]['balance'] if res.data else 0) + amt
        supabase.table("users").upsert({"user_id": uid, "balance": new_bal}).execute()
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"✅ **NẠP THÀNH CÔNG!**\n💰 +{amt:,}đ đã vào ví."), asyncio.get_event_loop())
    return jsonify({"status": "ok"}), 200

# --- KHỞI CHẠY ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    # Tự động kết nối lại các clone trong DB
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            try:
                cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
                await cl.connect()
                asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
            except: pass
    except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
        

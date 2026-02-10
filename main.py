import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from supabase import create_client, Client

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

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# --- TRUY VẤN DB ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- LOGIC ĐẬP HỘP ---
async def worker_grab_loop(client, phone, owner_id):
    await client.connect()
    if not await client.is_user_authorized():
        return # Session hết hạn

    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        # Kiểm tra hạn dùng từ DB mỗi lần có tin mới
        res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
        if not res.data: return
        
        expiry = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            await client.disconnect()
            return

        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.5)) # Tránh bị coi là bot quá nhanh
                try:
                    await ev.click()
                    await asyncio.sleep(1.5)
                    # Kiểm tra kết quả
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                except: pass

# --- GIAO DIỆN ---
def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC (10k/ngày)", b"add_clone")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"dep_menu")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(f"🦅 **HỆ THỐNG TREO CLONE ĐẬP HỘP**\n💰 Số dư: **{user['balance']:,}đ**", buttons=main_btns())

# --- XỬ LÝ NẠP TIỀN & MENU ---
@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE**\n💰 Số dư: **{user['balance']:,}đ**", buttons=main_btns())
    
    elif data == "dep_menu":
        btns = [[TButton.inline(f"💰 {amt//1000}k", f"p_{amt}")] for amt in [10000, 20000, 50000, 100000]]
        btns.append([TButton.inline("🔙 Quay lại", b"back")])
        await e.edit("🏦 **CHỌN MỨC NẠP TIỀN TỰ ĐỘNG**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **QUÉT MÃ ĐỂ NẠP {int(amt):,}đ**\n\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 MỞ APP NGÂN HÀNG", qr)], [TButton.inline("🔙 Quay lại", b"dep_menu")]])

    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **THÔNG TIN VÍ**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**", buttons=[TButton.inline("🔙 Quay lại", b"back")])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data:
            return await e.answer("❌ Bạn chưa có clone nào!", alert=True)
        
        msg = "📱 **CLONE ĐANG TREO:**\n"
        for c in res.data:
            msg += f"• `{c['phone']}` - Hết hạn: {c['expiry'][:10]}\n"
        await e.edit(msg, buttons=[TButton.inline("🔙 Quay lại", b"back")])

# --- LUỒNG THÊM ACC (LOGIN) ---
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_process(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY:
        return await e.answer(f"❌ Cần ít nhất {PRICE_PER_DAY:,}đ để thuê!", alert=True)

    async with bot.conversation(e.sender_id) as conv:
        try:
            await conv.send_message("📞 Nhập số điện thoại (VD: +84xxx):")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            send_code = await client.send_code_request(phone)
            await conv.send_message("📩 Nhập mã OTP đã gửi về Telegram:")
            otp = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 Nhập mật khẩu 2 lớp (2FA):")
                pwd = (await conv.get_response()).text.strip()
                await client.sign_in(password=pwd)

            # Thành công -> Trừ tiền & Lưu DB
            session_str = client.session.save()
            expiry_date = datetime.now(timezone.utc) + timedelta(days=1)
            
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            supabase.table("my_clones").insert({
                "owner_id": e.sender_id, "phone": phone, 
                "session": session_str, "expiry": expiry_date.isoformat()
            }).execute()

            await conv.send_message(f"✅ Thuê thành công! `{phone}` bắt đầu đập hộp.")
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id))
            
        except Exception as ex:
            await conv.send_message(f"❌ Lỗi: {str(ex)}")

# --- WEBHOOK SEPAY ---
app = Flask(__name__)
@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    d = request.json
    content = d.get("content", "").upper()
    m = re.search(r'NAP\s+(\d+)', content)
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if res.data:
            new_bal = res.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"✅ **NẠP THÀNH CÔNG!**\n💰 +{amt:,}đ"), asyncio.get_event_loop())
    return jsonify({"status": "ok"}), 200

# --- CHẠY HỆ THỐNG ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    # Load lại các clone cũ khi khởi động lại bot
    clones = supabase.table("my_clones").select("*").execute()
    for c in clones.data:
        cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
        asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
    
    print("--- BOT IS RUNNING ---")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
                                                  

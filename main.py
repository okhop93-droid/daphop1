import asyncio
import re
import os
import random
import logging
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

RENT_PACKAGES = {
    "1day": {"price": 10000, "days": 1, "text": "💎 10k / 1 Ngày"},
    "5day": {"price": 50000, "days": 5, "text": "💎 50k / 5 Ngày"},
    "10day": {"price": 100000, "days": 10, "text": "💎 100k / 10 Ngày"}
}

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
PENDING_LOGINS = {}

# --- DATABASE HELPERS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

def db_update_bal(uid, amount):
    user = db_get_user(uid)
    new_bal = user['balance'] + amount
    supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
    return new_bal

# --- LOGIC ĐẬP HỘP TỰ ĐỘNG & GỬI CODE ---
async def worker_grab_loop(client, phone, owner_id):
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
        if not res.data: return
        expiry = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            await client.disconnect()
            return

        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.5))
                try:
                    await ev.click()
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` ĐÃ TRÚNG!**\n🔑 Code: `{code}`")
                except: pass

# --- GIAO DIỆN MENU ---
def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(f"🦅 **TREO CLONE ONLINE**\n💰 Ví: **{user['balance']:,}đ**", buttons=main_btns())
    raise events.StopPropagation

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(f"🦅 **TREO CLONE ONLINE**\n💰 Ví: **{user['balance']:,}đ**", buttons=main_btns())
    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **VÍ TIỀN**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**", buttons=[TButton.inline("🔙 Quay lại", b"back")])
    elif data == "deposit":
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=10000&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **NẠP TIỀN MSB**\nSTK: `{STK_MSB}`\nND: `NAP {uid}`", buttons=[[TButton.url("QUÉT MÃ QR", qr)], [TButton.inline("🔙 Quay lại", b"back")]])
    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_{k}")] for k, v in RENT_PACKAGES.items()]
        btns.append([TButton.inline("🔙 Quay lại", b"back")])
        await e.edit("💎 **CHỌN GÓI GIA HẠN:**", buttons=btns)
    elif data == "add_clone":
        await e.edit("📱 Gửi số điện thoại: `/addacc 84xxxxxxxxx`", buttons=[TButton.inline("🔙 Quay lại", b"back")])
    elif data == "list_clones":
        clones = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        msg = "📱 **CLONE CỦA BẠN:**\n\n"
        if clones.data:
            for c in clones.data: msg += f"▪️ `{c['phone']}` - Hết hạn: `{c['expiry'][:16]}`\n"
        else: msg += "Bạn chưa có clone nào."
        await e.edit(msg, buttons=[TButton.inline("🔙 Quay lại", b"back")])
    
    # LOGIC MUA GÓI GIA HẠN
    elif data.startswith("buy_"):
        pkg = RENT_PACKAGES[data.replace("buy_", "")]
        user = db_get_user(uid)
        if user['balance'] < pkg['price']:
            return await e.answer(f"❌ Thiếu {(pkg['price'] - user['balance']):,}đ!", alert=True)
        
        clones = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not clones.data: return await e.answer("⚠️ Bạn chưa có acc nào!", alert=True)

        new_bal = user['balance'] - pkg['price']
        supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
        for c in clones.data:
            expiry_str = c['expiry'].replace('Z', '+00:00')
            curr = datetime.fromisoformat(expiry_str)
            now = datetime.now(timezone.utc)
            new_exp = (curr if curr > now else now) + timedelta(days=pkg['days'])
            supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("phone", c['phone']).execute()
        
        await e.answer(f"✅ Đã gia hạn thành công!", alert=True)
        await e.edit(f"🦅 **TREO CLONE ONLINE**\n💰 Ví: **{new_bal:,}đ**", buttons=main_btns())
    
    await e.answer()

# --- LOGIN & THÊM ACC ---
@bot.on(events.NewMessage(pattern=r"/addacc (.+)"))
async def add_acc(e):
    phone = e.pattern_match.group(1).strip()
    c = TelegramClient(StringSession(), API_ID, API_HASH)
    await c.connect()
    try:
        sent = await c.send_code_request(phone)
        PENDING_LOGINS[e.sender_id] = {"p": phone, "h": sent.phone_code_hash, "c": c}
        await e.reply("📩 Nhập OTP: `/otp <mã>`")
    except Exception as ex: await e.reply(f"❌ Lỗi: {ex}")

@bot.on(events.NewMessage(pattern=r"/otp (\d+)"))
async def otp_cmd(e):
    uid = e.sender_id
    if uid not in PENDING_LOGINS: return
    data = PENDING_LOGINS[uid]
    try:
        await data['c'].sign_in(data['p'], e.pattern_match.group(1), phone_code_hash=data['h'])
        ss = data['c'].session.save()
        exp = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        supabase.table("my_clones").upsert({"phone": data['p'], "owner_id": uid, "session": ss, "expiry": exp}).execute()
        asyncio.create_task(worker_grab_loop(data['c'], data['p'], uid))
        await e.reply(f"✅ Acc `{data['p']}` đã bắt đầu treo!")
        del PENDING_LOGINS[uid]
    except Exception as ex: await e.reply(f"❌ OTP lỗi: {ex}")

# --- WEB SERVER (FIX RENDER PORT & WEBHOOK) ---
app = Flask(__name__)
loop = asyncio.get_event_loop()

@app.route('/')
def home(): return "OK"

@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    data = request.json
    content = data.get("content", "").upper()
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content)
    if match:
        uid = int(match.group(1))
        db_update_bal(uid, amount)
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 Đã nạp thành công +{amount:,}đ!"), loop)
    return jsonify({"status": "ok"}), 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot is LIVE...")
    # Tự động bật lại toàn bộ clone khi restart
    clones = supabase.table("my_clones").select("*").execute()
    for c in clones.data:
        try:
            if datetime.fromisoformat(c['expiry'].replace('Z', '+00:00')) > datetime.now(timezone.utc):
                client = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
                await client.connect()
                asyncio.create_task(worker_grab_loop(client, c['phone'], c['owner_id']))
        except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    loop.run_until_complete(main())
        

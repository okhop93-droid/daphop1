import asyncio
import re
import os
import random
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from supabase import create_client, Client

# ===== CẤU HÌNH HỆ THỐNG =====
# Thay URL và KEY từ Supabase của bạn vào đây
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co"
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"

STK_MSB = "96886693002613"
TEN_CHU_TK = "NGUYEN THANH HOP"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

RENT_PACKAGES = {
    "1day": {"price": 10000, "days": 1, "text": "💎 10k / 1 Ngày"},
    "5day": {"price": 50000, "days": 5, "text": "💎 50k / 5 Ngày"},
    "10day": {"price": 100000, "days": 10, "text": "💎 100k / 10 Ngày"}
}

logging.basicConfig(level=logging.INFO)

# ===== HÀM XỬ LÝ DATABASE ONLINE (THAY THẾ SQLITE) =====
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

def db_update_bal(uid, amount, mode="add"):
    user = db_get_user(uid)
    new_bal = (user['balance'] + amount) if mode == "add" else (user['balance'] - amount)
    supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
    return new_bal

def db_get_clones(uid=None, active_only=False):
    query = supabase.table("my_clones").select("*")
    if uid: query = query.eq("owner_id", uid)
    if active_only: query = query.gt("expiry", datetime.now().isoformat())
    return query.execute().data

# ===== LOGIC ĐẬP HỘP (TREO CLONE) =====
async def worker_grab_loop(client, phone, owner_id):
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        # Kiểm tra hạn dùng từ Database Online
        res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
        if not res.data or datetime.fromisoformat(res.data[0]['expiry']) < datetime.now():
            await client.disconnect()
            return

        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.4))
                try:
                    await ev.click()
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` ĐÃ TRÚNG!**\n🔑 Code: `{code}`")
                except: pass

# ===== BOT INTERFACE =====
bot = TelegramClient(StringSession(), API_ID, API_HASH)
PENDING_LOGINS = {}

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    buttons = [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]
    await e.respond(f"🦅 **HỆ THỐNG TREO CLONE (DỮ LIỆU ONLINE)**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=buttons)

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid = e.sender_id
    data = e.data.decode()

    if data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **VÍ TIỀN**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**\n*(Dữ liệu không bao giờ mất)*")

    elif data == "list_clones":
        clones = db_get_clones(uid)
        if not clones: return await e.answer("Bạn chưa có clone!", alert=True)
        msg = "📱 **CLONE CỦA BẠN:**\n"
        for c in clones: msg += f"▪️ `{c['phone']}` - Hết hạn: `{c['expiry']}`\n"
        await e.edit(msg)

    elif data == "deposit":
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=10000&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **NẠP TIỀN MSB**\nSTK: `{STK_MSB}`\nND: `NAP {uid}`", buttons=[[TButton.url("QUÉT MÃ QR", qr)]])

    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_{k}")] for k, v in RENT_PACKAGES.items()]
        await e.edit("💎 **CHỌN GÓI THUÊ:**", buttons=btns)

    elif data.startswith("buy_"):
        pkg_id = data.replace("buy_", "")
        pkg = RENT_PACKAGES[pkg_id]
        user = db_get_user(uid)
        if user['balance'] < pkg['price']: return await e.answer("Số dư không đủ!", alert=True)
        
        db_update_bal(uid, pkg['price'], mode="sub")
        clones = db_get_clones(uid)
        for c in clones:
            curr = datetime.fromisoformat(c['expiry'])
            new_exp = (curr if curr > datetime.now() else datetime.now()) + timedelta(days=pkg['days'])
            supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("phone", c['phone']).execute()
        await e.respond(f"✅ Đã mua {pkg['text']} thành công!")

# --- LOGIC THÊM ACC ---
@bot.on(events.NewMessage(pattern=r"/addacc (.+)"))
async def add_acc_cmd(e):
    phone = e.pattern_match.group(1).strip()
    c = TelegramClient(StringSession(), API_ID, API_HASH)
    await c.connect()
    sent = await c.send_code_request(phone)
    PENDING_LOGINS[e.sender_id] = {"p": phone, "h": sent.phone_code_hash, "c": c}
    await e.reply("📩 Nhập OTP: `/otp <mã>`")

@bot.on(events.NewMessage(pattern=r"/otp (\d+)"))
async def otp_cmd(e):
    uid = e.sender_id
    if uid not in PENDING_LOGINS: return
    data = PENDING_LOGINS[uid]
    await data['c'].sign_in(data['p'], e.pattern_match.group(1), phone_code_hash=data['h'])
    ss = data['c'].session.save()
    exp = (datetime.now() + timedelta(hours=1)).isoformat()
    supabase.table("my_clones").upsert({"phone": data['p'], "owner_id": uid, "session": ss, "expiry": exp}).execute()
    asyncio.create_task(worker_grab_loop(data['c'], data['p'], uid))
    await e.reply("✅ Đã thêm acc thành công!")

# ===== WEBHOOK & RUNNER =====
app = Flask(__name__)
main_loop = None

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    content = data.get("content", "").upper()
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content)
    if match and amount > 0:
        uid = int(match.group(1))
        db_update_bal(uid, amount, mode="add")
        if main_loop: asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 Nạp thành công +{amount:,}đ"), main_loop)
    return jsonify({"status": "ok"}), 200

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    await bot.start(bot_token=BOT_TOKEN)
    # Tải lại các clone còn hạn từ Supabase
    active = db_get_clones(active_only=True)
    for c in active:
        try:
            client = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
            await client.connect()
            asyncio.create_task(worker_grab_loop(client, c['phone'], c['owner_id']))
        except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    asyncio.run(runner())
    

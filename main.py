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
bot = TelegramClient(StringSession(), API_ID, API_HASH)
PENDING_LOGINS = {}

# --- DB FUNCTIONS ---
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

# --- WORKER ---
async def worker_grab_loop(client, phone, owner_id):
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
        if not res.data or datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00')) < datetime.now(datetime.timezone.utc):
            await client.disconnect()
            return
        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.4))
                try:
                    await ev.click()
                except: pass

# --- BOT EVENTS ---
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    buttons = [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]
    await e.respond(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=buttons)

@bot.on(events.CallbackQuery)
async def callback_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    
    if data == "add_clone":
        await e.edit("📱 Gửi số điện thoại theo định dạng: `/addacc 84xxxxxxxxx`", buttons=[TButton.inline("🔙 Quay lại", b"back")])
    
    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **VÍ TIỀN**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**", buttons=[TButton.inline("🔙 Quay lại", b"back")])
        
    elif data == "deposit":
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=10000&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **NẠP TIỀN MSB**\nSTK: `{STK_MSB}`\nND: `NAP {uid}`", buttons=[[TButton.url("QUÉT MÃ QR", qr)], [TButton.inline("🔙 Quay lại", b"back")]])

    elif data == "back":
        user = db_get_user(uid)
        buttons = [[TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")], [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")]]
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=buttons)

# --- LOGIN CLONE ---
@bot.on(events.NewMessage(pattern=r"/addacc (.+)"))
async def add_acc(e):
    phone = e.pattern_match.group(1).strip()
    c = TelegramClient(StringSession(), API_ID, API_HASH)
    await c.connect()
    try:
        sent = await c.send_code_request(phone)
        PENDING_LOGINS[e.sender_id] = {"p": phone, "h": sent.phone_code_hash, "c": c}
        await e.reply("📩 Nhập mã OTP theo cú pháp: `/otp <mã>`")
    except Exception as ex:
        await e.reply(f"❌ Lỗi: {str(ex)}")

@bot.on(events.NewMessage(pattern=r"/otp (\d+)"))
async def otp_verify(e):
    uid = e.sender_id
    if uid not in PENDING_LOGINS: return
    otp = e.pattern_match.group(1)
    data = PENDING_LOGINS[uid]
    try:
        await data['c'].sign_in(data['p'], otp, phone_code_hash=data['h'])
        ss = data['c'].session.save()
        exp = (datetime.now() + timedelta(hours=1)).isoformat()
        supabase.table("my_clones").upsert({"phone": data['p'], "owner_id": uid, "session": ss, "expiry": exp}).execute()
        asyncio.create_task(worker_grab_loop(data['c'], data['p'], uid))
        await e.reply(f"✅ Thành công! Acc `{data['p']}` đã bắt đầu treo.")
        del PENDING_LOGINS[uid]
    except Exception as ex:
        await e.reply(f"❌ OTP sai hoặc hết hạn: {str(ex)}")

# --- WEB SERVER ---
app = Flask(__name__)
loop = asyncio.get_event_loop()

@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    data = request.json
    content = data.get("content", "").upper()
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content)
    if match and amount > 0:
        uid = int(match.group(1))
        db_update_bal(uid, amount, mode="add")
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 Đã nhận +{amount:,}đ!"), loop)
    return jsonify({"status": "ok"}), 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    loop.run_until_complete(main())

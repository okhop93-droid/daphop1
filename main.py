import asyncio
import re
import os
import logging
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from supabase import create_client, Client

# ===== CẤU HÌNH ĐÃ FIX URL CHUẨN =====
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"

STK_MSB = "96886693002613"
RENT_PACKAGES = {
    "1day": {"price": 10000, "days": 1, "text": "💎 10k / 1 Ngày"},
    "5day": {"price": 50000, "days": 5, "text": "💎 50k / 5 Ngày"},
    "10day": {"price": 100000, "days": 10, "text": "💎 100k / 10 Ngày"}
}

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# --- DB HELPERS ---
def db_get_user(uid):
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
            return {"user_id": uid, "balance": 0}
        return res.data[0]
    except:
        return {"user_id": uid, "balance": 0}

def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]

# --- BOT EVENTS ---
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
        await e.edit(f"👤 **THÔNG TIN VÍ**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**", buttons=[TButton.inline("🔙 Quay lại", b"back")])

    elif data == "deposit":
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=10000&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **NẠP TIỀN QUA MSB**\nSTK: `{STK_MSB}`\nND: `NAP {uid}`", buttons=[[TButton.url("QUÉT MÃ QR", qr)], [TButton.inline("🔙 Quay lại", b"back")]])

    elif data == "add_clone":
        await e.edit("📱 Để thêm acc, hãy gửi số điện thoại theo cú pháp:\n`/addacc 84xxxxxxxxx`", buttons=[TButton.inline("🔙 Quay lại", b"back")])

    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_{k}")] for k, v in RENT_PACKAGES.items()]
        btns.append([TButton.inline("🔙 Quay lại", b"back")])
        await e.edit("💎 **CHỌN GÓI GIA HẠN:**", buttons=btns)

    elif data.startswith("buy_"):
        pkg = RENT_PACKAGES[data.replace("buy_", "")]
        user = db_get_user(uid)
        if user['balance'] < pkg['price']:
            return await e.answer(f"❌ Thiếu {(pkg['price'] - user['balance']):,}đ!", alert=True)
        # Logic update database tại đây
        await e.answer("✅ Đã ghi nhận yêu cầu!", alert=True)
    
    await e.answer() # Kết thúc hiệu ứng xoay tròn trên nút

# --- WEB SERVER (FIX LỖI RENDER) ---
app = Flask(__name__)
@app.route('/')
def index(): return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
    

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

# ===== CẤU HÌNH =====
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

# --- DB ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- MENU CHÍNH ---
def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=main_btns())
    raise events.StopPropagation # Chặn gửi menu thứ 2

@bot.on(events.CallbackQuery)
async def callback_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=main_btns())

    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **VÍ TIỀN**\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,}đ**", buttons=[TButton.inline("🔙 Quay lại", b"back")])
        
    elif data == "deposit":
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=10000&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **NẠP TIỀN MSB**\nSTK: `{STK_MSB}`\nND: `NAP {uid}`", buttons=[[TButton.url("QUÉT MÃ QR", qr)], [TButton.inline("🔙 Quay lại", b"back")]])

    elif data == "add_clone":
        await e.edit("📱 Gửi số điện thoại theo định dạng: `/addacc 84xxxxxxxxx`", buttons=[TButton.inline("🔙 Quay lại", b"back")])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data:
            return await e.answer("⚠️ Bạn chưa có clone nào!", alert=True)
        msg = "📱 **DANH SÁCH CLONE:**\n\n"
        for c in res.data:
            msg += f"▪️ `{c['phone']}` - Hết hạn: `{c['expiry'][:16]}`\n"
        await e.edit(msg, buttons=[TButton.inline("🔙 Quay lại", b"back")])

    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_{k}")] for k, v in RENT_PACKAGES.items()]
        btns.append([TButton.inline("🔙 Quay lại", b"back")])
        await e.edit("💎 **CHỌN GÓI GIA HẠN:**", buttons=btns)

    elif data.startswith("buy_"):
        pkg_id = data.replace("buy_", "")
        pkg = RENT_PACKAGES[pkg_id]
        user = db_get_user(uid)
        
        if user['balance'] < pkg['price']:
            return await e.answer(f"❌ Thiếu {(pkg['price'] - user['balance']):,}đ để mua!", alert=True)
        
        clones = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not clones.data:
            return await e.answer("❌ Bạn phải thêm acc trước khi gia hạn!", alert=True)

        # Trừ tiền & Cộng ngày
        new_bal = user['balance'] - pkg['price']
        supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
        
        for c in clones.data:
            curr = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            new_date = (curr if curr > datetime.now(datetime.timezone.utc) else datetime.now(datetime.timezone.utc)) + timedelta(days=pkg['days'])
            supabase.table("my_clones").update({"expiry": new_date.isoformat()}).eq("phone", c['phone']).execute()
            
        await e.answer("✅ Gia hạn thành công cho tất cả clone!", alert=True)
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{new_bal:,}đ**", buttons=main_btns())

# --- CÁC PHẦN CÒN LẠI GIỮ NGUYÊN (LOGIN, WORKER, FLASK) ---
# (Phần này giống hệt bản trước của bạn)

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

# ===== CẤU HÌNH (Dựa trên ảnh của bạn) =====
# Project ID: qaptttdmntjwsizoovre
SUPABASE_URL = "https://qaptttdmntjwsizoovre.supabase.co" 
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

# --- DB HELPERS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("⏳ GIA HẠN", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_clones")]
    ]

# --- EVENTS ---
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=main_btns())
    raise events.StopPropagation # FIX: Chặn gửi 2 Menu cùng lúc

@bot.on(events.CallbackQuery)
async def callback_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{user['balance']:,}đ**", buttons=main_btns())

    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_{k}")] for k, v in RENT_PACKAGES.items()]
        btns.append([TButton.inline("🔙 Quay lại", b"back")])
        await e.edit("💎 **CHỌN GÓI GIA HẠN:**", buttons=btns)

    elif data.startswith("buy_"):
        pkg_id = data.replace("buy_", "")
        pkg = RENT_PACKAGES[pkg_id]
        user = db_get_user(uid)
        
        if user['balance'] < pkg['price']:
            return await e.answer(f"❌ Thiếu {(pkg['price'] - user['balance']):,}đ!", alert=True)
        
        clones = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not clones.data:
            return await e.answer("⚠️ Phải thêm acc trước khi thuê!", alert=True)

        # Trừ tiền
        new_bal = user['balance'] - pkg['price']
        supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
        
        # Cộng ngày
        for c in clones.data:
            # Xử lý format thời gian chuẩn từ DB
            expiry_str = c['expiry'].replace('Z', '+00:00')
            curr = datetime.fromisoformat(expiry_str)
            now = datetime.now(timezone.utc)
            new_date = (curr if curr > now else now) + timedelta(days=pkg['days'])
            supabase.table("my_clones").update({"expiry": new_date.isoformat()}).eq("phone", c['phone']).execute()
            
        await e.answer("✅ Gia hạn thành công!", alert=True)
        await e.edit(f"🦅 **HỆ THỐNG TREO CLONE ONLINE**\n\n💰 Ví: **{new_bal:,}đ**", buttons=main_btns())

    # --- Các data khác (me, deposit, add_clone, list_clones) giữ nguyên như cũ ---

# --- GIỮ NGUYÊN PHẦN LOGIN VÀ WEB SERVER Ở CUỐI ---

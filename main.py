import asyncio
import sqlite3
import re
import os
import logging
import requests
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button

# ===== CẤU HÌNH HỆ THỐNG =====
API_ID = 36437338 
API_HASH = "18d34c7efc396d277f3db62baa078efc" 
BOT_TOKEN = "8404770438:AAHeGHh5CVtLAuNvX4Fo6F_I-OKG0Px1_g0"
ADMIN_ID = 7816353760
API_URL = "https://sunwinsaygex-production.up.railway.app/api/sun"

STK_MSB = "96886693002613"  
TEN_CHU_TK = "NGUYEN THANH HOP" 

DB_FILE = "sunwin_bot.db"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TelegramClient('bot_session', API_ID, API_HASH)

# ===== DATABASE CORE =====
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            balance INTEGER DEFAULT 0, 
            status INTEGER DEFAULT 0, 
            total_bet INTEGER DEFAULT 0)''')
        conn.commit()

def db_exec(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute(query, params); conn.commit()

def db_fetch(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.cursor().execute(query, params).fetchall()

# ===== MENU NÚT BẤM =====
def main_menu(uid):
    buttons = [
        [Button.inline("🚀 CHẠY DỰ ĐOÁN", b"start_predict"), Button.inline("🛑 DỪNG DỰ ĐOÁN", b"stop_predict")],
        [Button.inline("👤 THÔNG TIN TK", b"user_info"), Button.inline("💰 NẠP TIỀN", b"deposit")],
    ]
    if uid == ADMIN_ID:
        buttons.append([Button.inline("📊 THỐNG KÊ ADMIN", b"admin_stats")])
    return buttons

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if not db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,)):
        db_exec("INSERT INTO users (user_id) VALUES (?)", (uid,))
    await event.respond("🦅 **BOT DỰ ĐOÁN SUNWIN AI**\n━━━━━━━━━━━━━━━━━━━━", buttons=main_menu(uid))

# ===== LOGIC DỰ ĐOÁN =====
async def prediction_task(uid, chat_id):
    last_phien = ""
    while True:
        user = db_fetch("SELECT status FROM users WHERE user_id=?", (uid,))
        if not user or user[0][0] == 0: break
        try:
            response = requests.get(API_URL, timeout=10).json()
            phien_hien_tai = response.get("phien_hien_tai")
            if phien_hien_tai != last_phien:
                last_phien = phien_hien_tai
                du_doan = response.get("du_doan", "N/A")
                tin_cay = response.get("do_tin_cay", "0")
                msg = f"🎰 **PHIÊN: `{phien_hien_tai}`**\n🔮 Dự đoán: **{du_doan.upper()}**\n📊 Độ tin cậy: `{tin_cay}%`"
                await bot.send_message(chat_id, msg)
        except: pass
        await asyncio.sleep(8) 

# ===== XỬ LÝ SỰ KIỆN NÚT BẤM (FIXED) =====
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data
    
    if data == b"start_predict":
        user = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))
        if not user or user[0][0] <= 0:
            return await event.answer("❌ Tài khoản không đủ số dư!", alert=True)
        db_exec("UPDATE users SET status = 1 WHERE user_id=?", (uid,))
        await event.respond("🚀 **Đã bật AI!**")
        asyncio.create_task(prediction_task(uid, event.chat_id))

    elif data == b"stop_predict":
        db_exec("UPDATE users SET status = 0 WHERE user_id=?", (uid,))
        await event.respond("🛑 **Đã dừng dự đoán.**")

    elif data == b"user_info":
        user = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))
        msg = f"👤 **TÀI KHOẢN**\n🆔 ID: `{uid}`\n💰 Số dư: `{user[0][0]:,} VNĐ`"
        await event.respond(msg, buttons=main_menu(uid))

    elif data == b"deposit":
        qr_url = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=50000&addInfo=NAP%20{uid}&accountName={TEN_CHU_TK}"
        msg = f"🏦 **NẠP TIỀN**\nSTK: `{STK_MSB}`\nNội dung: `NAP {uid}`"
        await event.respond(msg, buttons=[[Button.url("🖼 QUÉT MÃ QR", qr_url)]])

    elif data == b"admin_stats":
        if uid != ADMIN_ID: return
        total_users = db_fetch("SELECT COUNT(*) FROM users")[0][0]
        total_bal = db_fetch("SELECT SUM(balance) FROM users")[0][0] or 0
        await event.respond(f"📊 **THỐNG KÊ ADMIN**\n👥 Tổng khách: `{total_users}`\n💰 Tổng số dư: `{total_bal:,}đ`")

# ===== SEPAY WEBHOOK (NẠP TỰ ĐỘNG) =====
app = Flask(__name__)
main_loop = None

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    if not data: return jsonify({"status": "no_data"}), 400
    content = data.get("content", "")
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content.upper())
    if match and amount > 0:
        uid = int(match.group(1))
        if db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,)):
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
            if main_loop:
                asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 **NẠP THÀNH CÔNG!**\n+ `{amount:,} VNĐ`"), main_loop)
            return jsonify({"status": "success"}), 200
    return jsonify({"status": "ignored"}), 200

@app.route('/')
def home(): return "RUNNING"

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    init_db()
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("🚀 Bot Predict Online!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # Fix Render: Tắt use_reloader để không bị kẹt nút bấm
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), use_reloader=False), daemon=True).start()
    try:
        asyncio.run(runner())
    except KeyboardInterrupt: pass

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
from telethon.sessions import StringSession

# ===== CẤU HÌNH HỆ THỐNG =====
API_ID = 36437338 
API_HASH = "18d34c7efc396d277f3db62baa078efc" 
BOT_TOKEN = "8404770438:AAHeGHh5CVtLAuNvX4Fo6F_I-OKG0Px1_g0"
ADMIN_ID = 7816353760
API_URL = "https://sunwinsaygex-production.up.railway.app/api/sun"

# THÔNG TIN NGÂN HÀNG CỦA BẠN
STK_MSB = "96886693002613"  # Số tài khoản MSB của bạn
TEN_CHU_TK = "NGUYEN THANH HOP" # Tên chủ tài khoản của bạn (Viết hoa không dấu)

DB_FILE = "sunwin_bot.db"
PRICE_PER_SESSION = 1000  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# ===== BOT LOGIC =====
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

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
    
    await event.respond(
        "🦅 **BOT DỰ ĐOÁN TÀI XỈU SUNWIN AI**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Sử dụng công nghệ Markov & Pattern nhận diện cầu.\n"
        "Vui lòng nạp tiền để bắt đầu chạy dự đoán.",
        buttons=main_menu(uid)
    )

async def prediction_task(uid, chat_id):
    last_phien = ""
    while True:
        user = db_fetch("SELECT status FROM users WHERE user_id=?", (uid,))
        if not user or user[0][0] == 0:
            break
            
        try:
            response = requests.get(API_URL).json()
            phien_hien_tai = response.get("phien_hien_tai")
            
            if phien_hien_tai != last_phien:
                last_phien = phien_hien_tai
                du_doan = response.get("du_doan")
                do_tin_cay = response.get("do_tin_cay")
                chi_tiet = response.get("chi_tiet")
                
                msg = (
                    f"🎰 **PHIÊN DỰ ĐOÁN: `{phien_hien_tai}`**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔮 Dự đoán: **{du_doan.upper()}**\n"
                    f"📊 Độ tin cậy: `{do_tin_cay}%`\n"
                    f"📝 Phân tích: `{chi_tiet}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                await bot.send_message(chat_id, msg)
        except Exception as e:
            logger.error(f"Lỗi API: {e}")
            
        await asyncio.sleep(5) 

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data
    
    if data == b"start_predict":
        user = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))
        if user[0][0] <= 0:
            return await event.answer("❌ Tài khoản không đủ số dư! Vui lòng nạp thêm.", alert=True)
        
        db_exec("UPDATE users SET status = 1 WHERE user_id=?", (uid,))
        await event.respond("🚀 **Đã khởi động AI dự đoán!** Hệ thống sẽ báo khi có phiên mới.")
        asyncio.create_task(prediction_task(uid, event.chat_id))

    elif data == b"stop_predict":
        db_exec("UPDATE users SET status = 0 WHERE user_id=?", (uid,))
        await event.respond("🛑 **Đã dừng dự đoán.**")

    elif data == b"user_info":
        user = db_fetch("SELECT balance, total_bet FROM users WHERE user_id=?", (uid,))
        msg = (
            f"👤 **THÔNG TIN TÀI KHOẢN**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{uid}`\n"
            f"💰 Số dư: `{user[0][0]:,} VNĐ`\n"
            f"📊 Đã chạy: `{user[0][1]} phiên`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await event.respond(msg, buttons=main_menu(uid))

    elif data == b"deposit":
        msg = (
            f"🏦 **HƯỚNG DẪN NẠP TIỀN TỰ ĐỘNG**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Ngân hàng: **MSB (Maritime Bank)**\n"
            f"🔢 STK: `{STK_MSB}`\n"
            f"👤 Chủ TK: **{TEN_CHU_TK}**\n"
            f"📝 Nội dung CK: `NAP {uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **Lưu ý:** Chuyển đúng nội dung để được cộng tiền tự động sau 1-3 phút."
        )
        await event.respond(msg)

    elif data == b"admin_stats" and uid == ADMIN_ID:
        total_users = db_fetch("SELECT COUNT(*) FROM users")[0][0]
        total_balance = db_fetch("SELECT SUM(balance) FROM users")[0][0]
        await event.respond(f"📊 **THỐNG KÊ HỆ THỐNG**\n- Tổng User: {total_users}\n- Tổng Số Dư: {total_balance:,}đ")

# ===== SEPAY WEBHOOK & FLASK =====
app = Flask(__name__)
main_loop = None

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    if not data: return jsonify({"status": "error"}), 400
    
    content = data.get("content", "")
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content.upper())
    
    if match and amount > 0:
        uid = int(match.group(1))
        user = db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,))
        if user:
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
            msg = f"💰 **NẠP TIỀN THÀNH CÔNG!**\n✅ Số tiền: `+{amount:,}đ` đã được cộng vào tài khoản."
            asyncio.run_coroutine_threadsafe(bot.send_message(uid, msg), main_loop)
            return jsonify({"status": "success"}), 200
    return jsonify({"status": "ignored"}), 200

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    init_db()
    logger.info("🚀 Bot Predict & Webhook Online!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080, use_reloader=False), daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(runner())
            

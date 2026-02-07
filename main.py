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

# THÔNG TIN NGÂN HÀNG CỦA BẠN
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

# ===== BOT LOGIC =====
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
        "Sử dụng công nghệ AI nhận diện cầu Sunwin.\n"
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
            response = requests.get(API_URL, timeout=10).json()
            phien_hien_tai = response.get("phien_hien_tai")
            
            if phien_hien_tai != last_phien:
                last_phien = phien_hien_tai
                du_doan = response.get("du_doan", "N/A")
                tin_cay = response.get("do_tin_cay", "0")
                chi_tiet = response.get("chi_tiet", "")
                
                msg = (
                    f"🎰 **PHIÊN DỰ ĐOÁN: `{phien_hien_tai}`**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔮 Dự đoán: **{du_doan.upper()}**\n"
                    f"📊 Độ tin cậy: `{tin_cay}%`\n"
                    f"📝 Phân tích: `{chi_tiet}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                await bot.send_message(chat_id, msg)
        except Exception as e:
            logger.error(f"Lỗi API Sunwin: {e}")
            
        await asyncio.sleep(8) 

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data
    
    if data == b"start_predict":
        user = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))
        if not user or user[0][0] <= 0:
            return await event.answer("❌ Tài khoản không đủ số dư!", alert=True)
        
        db_exec("UPDATE users SET status = 1 WHERE user_id=?", (uid,))
        await event.respond("🚀 **Đã bật AI!** Kèo sẽ tự gửi khi có phiên mới.")
        asyncio.create_task(prediction_task(uid, event.chat_id))

    elif data == b"stop_predict":
        db_exec("UPDATE users SET status = 0 WHERE user_id=?", (uid,))
        await event.respond("🛑 **Đã dừng nhận dự đoán.**")

    elif data == b"user_info":
        user = db_fetch("SELECT balance, total_bet FROM users WHERE user_id=?", (uid,))
        msg = f"👤 **TÀI KHOẢN**\n🆔 ID: `{uid}`\n💰 Số dư: `{user[0][0]:,} VNĐ`"
        await event.respond(msg, buttons=main_menu(uid))

    elif data == b"deposit":
        # Thêm mã QR VietQR để khách quét nạp nhanh hơn
        qr_url = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=50000&addInfo=NAP%20{uid}&accountName={TEN_CHU_TK}"
        msg = (
            f"🏦 **NẠP TIỀN TỰ ĐỘNG**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 STK: `{STK_MSB}` (MSB)\n"
            f"👤 Chủ TK: **{TEN_CHU_TK}**\n"
            f"📝 Nội dung: `NAP {uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Vui lòng ghi đúng nội dung để được cộng tiền tự động!*"
        )
        await event.respond(msg, buttons=[[Button.url("🖼 QUÉT MÃ QR", qr_url)]])

# ===== SEPAY WEBHOOK (XỬ LÝ NẠP TỰ ĐỘNG) =====
app = Flask(__name__)
main_loop = None

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    if not data: return jsonify({"status": "error"}), 400
    
    content = data.get("content", "") # Nội dung chuyển khoản
    amount = int(data.get("transferAmount", 0)) # Số tiền nhận
    
    # Tìm mã NAP ID trong nội dung chuyển khoản
    match = re.search(r'NAP\s+(\d+)', content.upper())
    
    if match and amount > 0:
        uid = int(match.group(1))
        user_exists = db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,))
        
        if user_exists:
            # Cộng tiền vào database
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
            
            # Gửi thông báo cho khách hàng
            msg = (
                f"💰 **THÔNG BÁO NẠP TIỀN**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Số dư đã cộng: `+{amount:,}đ`\n"
                f"👤 Tài khoản: `{uid}`\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            # Dùng run_coroutine_threadsafe để gửi tin nhắn từ luồng Flask sang luồng Telegram
            if main_loop:
                asyncio.run_coroutine_threadsafe(bot.send_message(uid, msg), main_loop)
                asyncio.run_coroutine_threadsafe(bot.send_message(ADMIN_ID, f"🔔 **ADMIN:** Khách `{uid}` vừa nạp `{amount:,}đ`"), main_loop)
            
            return jsonify({"status": "success"}), 200
    return jsonify({"status": "ignored"}), 200

@app.route('/')
def home(): return "SYSTEM OPERATIONAL"

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    init_db()
    await bot.start(bot_token=BOT_TOKEN)
    logger.info("🚀 Bot Predict Online!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # Chạy Flask Server (Tắt use_reloader để không bị chạy 2 bot gây lỗi gửi 2 tin nhắn)
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port, use_reloader=False), daemon=True).start()
    
    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        pass
    

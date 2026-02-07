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

# ===== CẤU HÌNH =====
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

# ===== DATABASE =====
def db_exec(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute(query, params); conn.commit()

def db_fetch(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.cursor().execute(query, params).fetchall()

def init_db():
    db_exec('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, status INTEGER DEFAULT 0)''')

# ===== MENU =====
def get_menu(uid):
    btns = [
        [Button.inline("🚀 CHẠY DỰ ĐOÁN", b"start"), Button.inline("🛑 DỪNG", b"stop")],
        [Button.inline("👤 TÀI KHOẢN", b"info"), Button.inline("💰 NẠP TIỀN", b"nap")],
    ]
    if uid == ADMIN_ID:
        btns.append([Button.inline("📊 THỐNG KÊ", b"admin")])
    return btns

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(e):
    if not db_fetch("SELECT user_id FROM users WHERE user_id=?", (e.sender_id,)):
        db_exec("INSERT INTO users (user_id) VALUES (?)", (e.sender_id,))
    await e.respond("🦅 **BOT AI SUNWIN**", buttons=get_menu(e.sender_id))

# ===== DỰ ĐOÁN =====
async def predict_loop(uid, chat_id):
    last_p = ""
    while True:
        u = db_fetch("SELECT status FROM users WHERE user_id=?", (uid,))
        if not u or u[0][0] == 0: break
        try:
            r = requests.get(API_URL, timeout=5).json()
            curr_p = r.get("phien_hien_tai")
            if curr_p != last_p:
                last_p = curr_p
                msg = f"🎰 **PHIÊN: {curr_p}**\n🔮 Dự đoán: **{r.get('du_doan','').upper()}**\n📊 Tin cậy: {r.get('do_tin_cay')}%"
                await bot.send_message(chat_id, msg)
        except: pass
        await asyncio.sleep(10)

# ===== XỬ LÝ NÚT (FIXED) =====
@bot.on(events.CallbackQuery)
async def handle_callback(e):
    uid = e.sender_id
    data = e.data
    
    if data == b"start":
        bal = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))[0][0]
        if bal <= 0: return await e.answer("❌ Hết tiền!", alert=True)
        db_exec("UPDATE users SET status=1 WHERE user_id=?", (uid,))
        await e.answer("🚀 Đã bật AI", alert=False)
        asyncio.create_task(predict_loop(uid, e.chat_id))
        
    elif data == b"stop":
        db_exec("UPDATE users SET status=0 WHERE user_id=?", (uid,))
        await e.answer("🛑 Đã dừng", alert=True)

    elif data == b"info":
        bal = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))[0][0]
        await e.respond(f"👤 ID: `{uid}`\n💰 Số dư: `{bal:,}đ`", buttons=get_menu(uid))

    elif data == b"nap":
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=50000&addInfo=NAP%20{uid}"
        await e.respond(f"🏦 **NẠP TIỀN MSB**\nSTK: `{STK_MSB}`\nND: `NAP {uid}`", buttons=[Button.url("🖼 QUÉT QR", qr)])

    elif data == b"admin":
        if uid != ADMIN_ID: return
        count = db_fetch("SELECT COUNT(*) FROM users")[0][0]
        await e.respond(f"📊 Tổng khách: {count}")

# ===== WEBHOOK NẠP TIỀN =====
app = Flask(__name__)
loop_chinh = None

@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    data = request.json
    content = data.get("content", "").upper()
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content)
    
    if match and amount > 0:
        uid = int(match.group(1))
        if db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,)):
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
            if loop_chinh:
                asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"✅ Đã nạp thành công +{amount:,}đ"), loop_chinh)
            return jsonify({"status": "ok"}), 200
    return jsonify({"status": "skip"}), 200

@app.route('/')
def home(): return "OK"

async def main():
    global loop_chinh
    loop_chinh = asyncio.get_event_loop()
    init_db()
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), use_reloader=False), daemon=True).start()
    asyncio.run(main())
    

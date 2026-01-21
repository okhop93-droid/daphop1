import logging
import sqlite3
import requests
import json
from flask import Flask, request
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- CẤU HÌNH (THAY THÔNG TIN CỦA BẠN VÀO ĐÂY) ---
TOKEN = "8361903272:AAGTo7mAZgDUn7tgza_rNKVvstMd55Irg-Y"
ADMIN_ID = 7816353760  # ID Telegram của bạn (Lấy tại @userinfobot)
API_TSR_KEY = "KEY_CỦA_BẠN" # Nếu cần dùng gửi thẻ

app = Flask(__name__)

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, code_val TEXT, status INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    res = None
    if fetchone: res = c.fetchone()
    if fetchall: res = c.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- WEBHOOK HỨNG TIỀN (SEPAY & TSR) ---
@app.route('/webhook/sepay', methods=['POST'])
def sepay_webhook():
    data = request.json
    content = data.get('content', '') # Nội dung chuyển khoản: NAP 123456
    amount = int(data.get('transferAmount', 0))
    if "NAP" in content.upper():
        try:
            u_id = content.upper().replace("NAP", "").strip()
            db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, u_id), commit=True)
            requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={u_id}&text=✅ Bank: +{amount}đ. Chúc bạn chơi vui vẻ!")
        except: pass
    return "OK", 200

@app.route('/webhook/tsr', methods=['GET'])
def tsr_webhook():
    status = request.args.get('status')
    val = request.args.get('value')
    rid = request.args.get('request_id') # Bạn cần lưu request_id vào DB để khớp user_id
    if status == '1':
        # Logic cộng tiền dựa trên request_id
        pass
    return "OK", 200

# --- CÁC HÀM XỬ LÝ BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id, balance) VALUES (?, 0)", (user_id,), commit=True)
    
    # Menu cho User
    keyboard = [
        [InlineKeyboardButton("🎁 Mua Code Tân Thủ (0đ)", callback_query_data='buy_TANTU')],
        [InlineKeyboardButton("💎 Mua Code VIP (20k)", callback_query_data='buy_VIP20')],
        [InlineKeyboardButton("💳 Nạp Tiền", callback_query_data='menu_nap')],
        [InlineKeyboardButton("👤 Tài Khoản", callback_query_data='profile')]
    ]
    # Nếu là Admin thì hiện thêm nút Admin
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🛠 MENU ADMIN", callback_query_data='admin_panel')])
        
    await update.message.reply_text("🔥 WELCOME TO XOCDIA88 BOT 🔥\nHệ thống bán code tự động 24/7", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == 'profile':
        user = db_query("SELECT balance FROM users WHERE id = ?", (user_id,), fetchone=True)
        await query.message.reply_text(f"👤 ID: `{user_id}`\n💰 Số dư: {user[0] if user else 0}đ", parse_mode='Markdown')

    elif data == 'menu_nap':
        await query.message.reply_text(f"💳 **NẠP TỰ ĐỘNG**\n\n**Cách 1: Bank MSB**\nSTK: `80002422042`\nNội dung: `NAP {user_id}`\n\n**Cách 2: Nạp Thẻ**\nTruy cập: thesieure.com", parse_mode='Markdown')

    elif data.startswith('buy_'):
        c_type = data.replace('buy_', '')
        price = 0 if c_type == 'TANTU' else 20000
        user = db_query("SELECT balance FROM users WHERE id = ?", (user_id,), fetchone=True)
        
        if user and user[0] >= price:
            code = db_query("SELECT id, code_val FROM codes WHERE type = ? AND status = 0 LIMIT 1", (c_type,), fetchone=True)
            if code:
                db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id), commit=True)
                db_query("UPDATE codes SET status = 1 WHERE id = ?", (code[0],), commit=True)
                await query.message.reply_text(f"✅ MUA THÀNH CÔNG!\n🎁 Code: `{code[1]}`", parse_mode='Markdown')
            else:
                await query.message.reply_text("❌ Hết hàng trong kho!")
        else:
            await query.message.reply_text("❌ Không đủ số dư!")

    # --- LOGIC ADMIN ---
    elif data == 'admin_panel' and user_id == ADMIN_ID:
        kb = [
            [InlineKeyboardButton("➕ Thêm Code", callback_query_data='adm_add')],
            [InlineKeyboardButton("📊 Thống kê kho", callback_query_data='adm_stats')],
            [InlineKeyboardButton("📢 Thông báo tổng", callback_query_data='adm_bc')]
        ]
        await query.message.reply_text("🛠 BẢNG ĐIỀU KHIỂN ADMIN", reply_markup=InlineKeyboardMarkup(kb))

    elif data == 'adm_stats' and user_id == ADMIN_ID:
        count = db_query("SELECT type, COUNT(*) FROM codes WHERE status = 0 GROUP BY type", fetchall=True)
        txt = "📊 KHO HÀNG HIỆN TẠI:\n"
        for r in count: txt += f"- {r[0]}: {r[1]} mã\n"
        await query.message.reply_text(txt)

    elif data == 'adm_add' and user_id == ADMIN_ID:
        await query.message.reply_text("Gửi code theo định dạng: `LOAI CODE1, CODE2` (Ví dụ: `TANTU ABC, XYZ`)")

# Admin nạp code bằng cách nhắn tin
async def admin_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text
    if " " in text:
        parts = text.split(" ")
        c_type = parts[0].upper()
        codes = "".join(parts[1:]).split(",")
        for c in codes:
            db_query("INSERT INTO codes (type, code_val, status) VALUES (?, ?, 0)", (c_type, c.strip(),), commit=True)
        await update.message.reply_text(f"✅ Đã thêm {len(codes)} mã vào kho {c_type}!")

# --- KHỞI CHẠY ---
def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == '__main__':
    init_db()
    # Chạy Flask Webhook song song với Bot
    Thread(target=run_flask).start()
    
    # Chạy Telegram Bot
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_msg_handler))
    
    print("Bot đang chạy...")
    application.run_polling()
  

import os
import psycopg2
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH ---
TOKEN = "8361903272:AAGTo7mAZgDUn7tgza_rNKVvstMd55Irg"
ADMIN_ID = 7816353760  # Thay bằng ID của bạn
DATABASE_URL = os.environ.get('DATABASE_URL')

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

def get_db_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Tạo bảng nếu chưa có
conn = get_db_conn(); cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, balance INT DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS codes (id SERIAL PRIMARY KEY, type TEXT, code_val TEXT, status INT DEFAULT 0)")
conn.commit(); cur.close(); conn.close()

# Webhook cho Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
async def respond():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

# Webhook cho SePay
@app.route('/webhook/sepay', methods=['POST'])
def sepay():
    data = request.json
    content = data.get('content', '').upper()
    amount = int(data.get('transferAmount', 0))
    if "NAP" in content:
        u_id = content.replace("NAP", "").strip()
        conn = get_db_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, int(u_id)))
        conn.commit(); cur.close(); conn.close()
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={u_id}&text=✅ Đã nạp {amount}đ!")
    return "OK", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO users (id, balance) VALUES (%s, 0) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit(); cur.close(); conn.close()
    
    kb = [[InlineKeyboardButton("🎁 Code Tân Thủ", callback_query_data='buy_TANTU')],
          [InlineKeyboardButton("💳 Nạp Tiền", callback_query_data='nap')]]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 ADMIN: Thống kê", callback_query_data='adm_stats')])
    await update.message.reply_text("🤖 BOT XOCDIA88 ĐÃ SẴN SÀNG", reply_markup=InlineKeyboardMarkup(kb))

# Lệnh Admin nạp code bằng tin nhắn
async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        parts = update.message.text.split(" ", 1) # Cú pháp: TANTU ABC, XYZ
        c_type = parts[0].upper()
        codes = parts[1].split(",")
        conn = get_db_conn(); cur = conn.cursor()
        for c in codes:
            cur.execute("INSERT INTO codes (type, code_val) VALUES (%s, %s)", (c_type, c.strip()))
        conn.commit(); cur.close(); conn.close()
        await update.message.reply_text(f"✅ Đã thêm {len(codes)} mã vào {c_type}")
    except: pass

# Đăng ký xử lý
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_code))

if __name__ == '__main__':
    # QUAN TRỌNG: Không dùng run_polling()
    app.run(host='0.0.0.0', port=10000)
    

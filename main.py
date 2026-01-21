import os
import psycopg2
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CẤU HÌNH BẮT BUỘC ---
TOKEN = "8361903272:AAGTo7mAZgDUn7tgza_rNKVvstMd55Irg"
ADMIN_ID = 7816353760  # Thay ID của bạn vào đây
DATABASE_URL = os.environ.get('DATABASE_URL') # Lấy từ Render Postgres

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# --- DATABASE LOGIC ---
def get_db_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_conn(); cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, balance INT DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS codes (id SERIAL PRIMARY KEY, type TEXT, code_val TEXT, status INT DEFAULT 0)")
    conn.commit(); cur.close(); conn.close()

# --- WEBHOOKS (SEPAY & TELEGRAM) ---
@app.route(f'/{TOKEN}', methods=['POST'])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

@app.route('/webhook/sepay', methods=['POST'])
def sepay_income():
    data = request.json
    content = data.get('content', '').upper()
    amount = int(data.get('transferAmount', 0))
    if "NAP" in content:
        u_id = content.replace("NAP", "").strip()
        conn = get_db_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, int(u_id)))
        conn.commit(); cur.close(); conn.close()
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={u_id}&text=✅ Nạp thành công {amount}đ!")
    return "OK", 200

# --- CHỨC NĂNG USER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO users (id, balance) VALUES (%s, 0) ON CONFLICT DO NOTHING", (user_id,))
    conn.commit(); cur.close(); conn.close()
    
    kb = [
        [InlineKeyboardButton("🎁 Code Tân Thủ (0đ)", callback_query_data='buy_TANTU')],
        [InlineKeyboardButton("💎 Code VIP (20k)", callback_query_data='buy_VIP')],
        [InlineKeyboardButton("💳 Nạp Tiền", callback_query_data='nap')],
        [InlineKeyboardButton("👤 Tài Khoản", callback_query_data='info')]
    ]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 MENU ADMIN", callback_query_data='admin')])
    await update.message.reply_text("🔥 BOT XOCDIA88 TỰ ĐỘNG 🔥", reply_markup=InlineKeyboardMarkup(kb))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    await q.answer()

    if q.data == 'info':
        conn = get_db_conn(); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        b = cur.fetchone()[0]
        cur.close(); conn.close()
        await q.message.reply_text(f"👤 ID: `{user_id}`\n💰 Số dư: {b}đ", parse_mode='Markdown')

    elif q.data.startswith('buy_'):
        ctype = q.data.replace('buy_', '')
        price = 0 if ctype == 'TANTU' else 20000
        conn = get_db_conn(); cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        balance = cur.fetchone()[0]
        
        if balance >= price:
            cur.execute("SELECT id, code_val FROM codes WHERE type = %s AND status = 0 LIMIT 1", (ctype,))
            res = cur.fetchone()
            if res:
                cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (price, user_id))
                cur.execute("UPDATE codes SET status = 1 WHERE id = %s", (res[0],))
                conn.commit()
                await q.message.reply_text(f"✅ Code của bạn: `{res[1]}`", parse_mode='Markdown')
            else: await q.message.reply_text("❌ Kho đã hết code này!")
        else: await q.message.reply_text("❌ Không đủ tiền!")
        cur.close(); conn.close()

# --- LỆNH ADMIN (THÊM CODE) ---
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        # Cú pháp: TANTU mã1, mã2, mã3
        msg = update.message.text
        parts = msg.split(" ", 1)
        type_code = parts[0].upper()
        list_codes = parts[1].split(",")
        conn = get_db_conn(); cur = conn.cursor()
        for c in list_codes:
            cur.execute("INSERT INTO codes (type, code_val) VALUES (%s, %s)", (type_code, c.strip()))
        conn.commit(); cur.close(); conn.close()
        await update.message.reply_text(f"✅ Đã thêm {len(list_codes)} mã vào kho {type_code}")
    except:
        await update.message.reply_text("Sử dụng: `LOẠI CODE1, CODE2`")

# --- CHẠY SERVER ---
if __name__ == '__main__':
    init_db()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))
    
    # Không dùng run_polling() nữa để tránh lỗi Conflict
    app.run(host='0.0.0.0', port=10000)
    

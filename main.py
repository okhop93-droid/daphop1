import logging
import sqlite3
import threading
import os  # Thêm thư viện os để lấy Port từ Render
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from fastapi import FastAPI, Request
import uvicorn

# ==================== CẤU HÌNH HỆ THỐNG ====================
API_TOKEN = '8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU' 
ADMIN_ID = 7816353760 
GAME_LINK = "https://xocdia88.ec"
GIA_CODE = 2000 

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
app = FastAPI()

# ==================== KHỞI TẠO DATABASE ====================
def init_db():
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY AUTOINCREMENT, code_text TEXT, status TEXT DEFAULT 'available')''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, code_text TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Cổng mặc định cho Render
PORT = int(os.environ.get("PORT", 8000))

# Health Check cho Render không bị báo lỗi Deploy
@app.get("/")
async def root():
    return {"status": "Bot is running"}

# ==================== WEBHOOK NẠP TIỀN ====================
@app.post("/webhook")
async def msb_webhook(request: Request):
    data = await request.json()
    try:
        data_body = data.get('data', data)
        description = data_body.get('description', "")
        amount = data_body.get('amount', 0)
        
        if "NAP" in description.upper():
            user_id = int(''.join(filter(str.isdigit, description)))
            conn = sqlite3.connect('xocdia88.db')
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
            conn.close()
            await bot.send_message(user_id, f"<b>✅ NẠP TIỀN THÀNH CÔNG!</b>\n💰 +{amount:,}đ vào tài khoản.")
    except Exception as e:
        print(f"Lỗi Webhook: {e}")
    return {"status": "success"}

# ==================== BOT HANDLERS (Giữ nguyên logic của bạn) ====================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🛒 MUA CODE (2K)"), KeyboardButton("🎁 XEM KHO HÀNG"))
    markup.add(KeyboardButton("👤 TÀI KHOẢN"), KeyboardButton("📜 LỊCH SỬ"))
    markup.add(KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("🔗 LINK GAME"))
    return markup

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await message.reply(f"<b>💎 CHÀO MỪNG ĐẾN VỚI SHOP XOCDIA88</b>\n──────────────────\n🦊 Thử vận may chỉ với: <b>{GIA_CODE:,}đ</b>\n🎁 Nhận ngẫu nhiên code: <b>2k - 88k</b>", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "💰 NẠP TIỀN")
async def nap_tien(message: types.Message):
    await message.reply(f"<b>🏦 HƯỚNG DẪN NẠP TIỀN MSB</b>\n\nSTK: <code>96886693002613</code>\nCTK: <b>NGUYEN THANH HOP</b>\nNội dung: <code>NAP {message.from_user.id}</code>")

@dp.message_handler(lambda message: message.text == "🎁 XEM KHO HÀNG")
async def view_stock(message: types.Message):
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM codes WHERE status = 'available'")
    total = c.fetchone()[0]
    conn.close()
    await message.reply(f"<b>📦 KHO CODE RANDOM</b>\n\n▫️ Đang có: <b>{total}</b> mã code")

@dp.message_handler(lambda message: message.text == "🛒 MUA CODE (2K)")
async def buy_code(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    balance = c.fetchone()[0]
    if balance < GIA_CODE:
        return await message.reply("❌ <b>Bạn không đủ tiền!</b>")
    
    c.execute("SELECT id, code_text FROM codes WHERE status = 'available' ORDER BY RANDOM() LIMIT 1")
    res = c.fetchone()
    if res:
        code_id, code_val = res
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (GIA_CODE, uid))
        c.execute("UPDATE codes SET status = 'sold' WHERE id = ?", (code_id,))
        c.execute("INSERT INTO history (user_id, code_text) VALUES (?, ?)", (uid, code_val))
        conn.commit()
        btn = InlineKeyboardMarkup().add(InlineKeyboardButton("🕹️ VÀO GAME NHẬP NGAY", url=GAME_LINK))
        await message.reply(f"<b>🎉 MUA THÀNH CÔNG!</b>\n🔑 Mã: <code>{code_val}</code>", reply_markup=btn)
    else:
        await message.reply("😔 <b>Kho hết code!</b>")
    conn.close()

# --- ADMIN COMMANDS ---
@dp.message_handler(commands=['add'])
async def add_bulk(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    raw_codes = message.get_args().replace('\n', ' ').split()
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    for code in raw_codes:
        c.execute("INSERT INTO codes (code_text) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    await message.reply(f"✅ Đã nạp {len(raw_codes)} mã.")

# ==================== CHẠY BOT ====================
def run_fastapi():
    # Sử dụng cổng PORT do Render cấp
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    threading.Thread(target=run_fastapi).start()
    executor.start_polling(dp, skip_updates=True)
    

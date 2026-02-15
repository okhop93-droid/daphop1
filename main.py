import logging
import sqlite3
import threading
import os
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

PORT = int(os.environ.get("PORT", 8000))

@app.get("/")
async def root():
    return {"status": "Bot is running"}

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
        logging.error(f"Lỗi Webhook: {e}")
    return {"status": "success"}

# ==================== KEYBOARDS ====================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Đảm bảo văn bản ở đây khớp chính xác với phần Handler bên dưới
    markup.add(KeyboardButton("🛒 MUA CODE (2K)"), KeyboardButton("🎁 XEM KHO HÀNG"))
    markup.add(KeyboardButton("👤 TÀI KHOẢN"), KeyboardButton("📜 LỊCH SỬ"))
    markup.add(KeyboardButton("💰 NẠP TIỀN"), KeyboardButton("🔗 LINK GAME"))
    return markup

# ==================== BOT HANDLERS ====================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await message.reply(f"<b>💎 CHÀO MỪNG ĐẾN VỚI SHOP XOCDIA88</b>\n──────────────────\n🦊 Thử vận may chỉ với: <b>{GIA_CODE:,}đ</b>\n🎁 Nhận ngẫu nhiên code: <b>2k - 88k</b>", reply_markup=main_menu())

# Sửa lỗi không nhận diện được nút bằng cách dùng lambda kiểm tra chuỗi có chứa từ khóa
@dp.message_handler(lambda message: "TÀI KHOẢN" in message.text.upper())
async def user_info(message: types.Message):
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    res = c.fetchone()
    balance = res[0] if res else 0
    conn.close()
    await message.reply(f"<b>👤 THÔNG TIN CỦA BẠN</b>\n\n🆔 ID: <code>{message.from_user.id}</code>\n💰 Số dư: <b>{balance:,}đ</b>")

@dp.message_handler(lambda message: "LỊCH SỬ" in message.text.upper())
async def view_history(message: types.Message):
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT code_text, time FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 5", (message.from_user.id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return await message.reply("<b>📜 LỊCH SỬ</b>\n\nBạn chưa mua mã nào!")
    text = "<b>📜 5 GIAO DỊCH GẦN NHẤT</b>\n\n"
    for r in rows:
        text += f"▫️ Mã: <code>{r[0]}</code>\n⏰ <i>{r[1]}</i>\n\n"
    await message.reply(text)

@dp.message_handler(lambda message: "LINK GAME" in message.text.upper())
async def game_link(message: types.Message):
    btn = InlineKeyboardMarkup().add(InlineKeyboardButton("🕹️ MỞ XOCDIA88", url=GAME_LINK))
    await message.reply("<b>Link vào nhà game chính thức:</b>", reply_markup=btn)

@dp.message_handler(lambda message: "NẠP TIỀN" in message.text.upper())
async def nap_tien(message: types.Message):
    await message.reply(f"<b>🏦 HƯỚNG DẪN NẠP TIỀN MSB</b>\n\nSTK: <code>96886693002613</code>\nCTK: <b>NGUYEN THANH HOP</b>\nNội dung: <code>NAP {message.from_user.id}</code>")

@dp.message_handler(lambda message: "XEM KHO HÀNG" in message.text.upper())
async def view_stock(message: types.Message):
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM codes WHERE status = 'available'")
    total = c.fetchone()[0]
    conn.close()
    await message.reply(f"<b>📦 KHO CODE RANDOM</b>\n\n▫️ Đang có: <b>{total}</b> mã code")

@dp.message_handler(lambda message: "MUA CODE" in message.text.upper())
async def buy_code(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    balance_res = c.fetchone()
    balance = balance_res[0] if balance_res else 0
    if balance < GIA_CODE:
        conn.close()
        return await message.reply("❌ <b>Bạn không đủ tiền!</b>")
    
    c.execute("SELECT id, code_text FROM codes WHERE status = 'available' ORDER BY RANDOM() LIMIT 1")
    res = c.fetchone()
    if res:
        code_id, code_val = res
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (GIA_CODE, uid))
        c.execute("UPDATE codes SET status = 'sold' WHERE id = ?", (code_id,))
        c.execute("INSERT INTO history (user_id, code_text) VALUES (?, ?)", (uid, code_val))
        conn.commit()
        conn.close()
        btn = InlineKeyboardMarkup().add(InlineKeyboardButton("🕹️ VÀO GAME NHẬP NGAY", url=GAME_LINK))
        await message.reply(f"<b>🎉 MUA THÀNH CÔNG!</b>\n🔑 Mã: <code>{code_val}</code>", reply_markup=btn)
    else:
        conn.close()
        await message.reply("😔 <b>Kho hết code!</b>")

# --- ADMIN COMMANDS ---
@dp.message_handler(commands=['add'])
async def add_bulk(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    raw_codes = message.get_args().replace('\n', ' ').split()
    if not raw_codes: return await message.reply("Vui lòng nhập danh sách mã!")
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    for code in raw_codes:
        c.execute("INSERT INTO codes (code_text) VALUES (?)", (code,))
    conn.commit()
    conn.close()
    await message.reply(f"✅ Đã nạp {len(raw_codes)} mã vào kho.")

# ==================== CHẠY BOT ====================
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    threading.Thread(target=run_fastapi).start()
    executor.start_polling(dp, skip_updates=True)
    

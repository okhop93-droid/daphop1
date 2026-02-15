import logging
import sqlite3
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
import uvicorn
import threading

# --- CẤU HÌNH ---
API_TOKEN = '8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU'
ADMIN_ID = 7816353760  # Thay bằng ID Telegram của bạn
GAME_LINK = "https://xocdia88.ec" # Thay bằng link game thật
GIA_CODE = 3000

# Khởi tạo Webhook App (FastAPI)
app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY AUTOINCREMENT, code_text TEXT, value_game TEXT, status TEXT DEFAULT 'available')''')
    conn.commit()
    conn.close()

init_db()

# --- LOGIC WEBHOOK (NHẬN TIỀN MSB) ---
@app.post("/webhook")
async def msb_webhook(request: Request):
    data = await request.json()
    # Giả sử dùng PayOS/SePay, nội dung chuyển khoản là "NAP 123456"
    description = data.get('data', {}).get('description', "")
    amount = data.get('data', {}).get('amount', 0)
    
    if "NAP" in description.upper():
        try:
            uid = int(description.upper().replace("NAP", "").strip())
            conn = sqlite3.connect('xocdia88.db')
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
            conn.commit()
            conn.close()
            await bot.send_message(uid, f"✅ Đã nạp thành công {amount:,}đ vào tài khoản!")
        except:
            pass
    return {"status": "success"}

# --- BOT HANDLERS ---

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛒 Mua Code (3.000đ)", "💰 Nạp Tiền MSB")
    markup.add("👤 Tài Khoản", "🔗 Link Game")
    
    await message.reply(f"🎰 Chào mừng bạn đến với Shop Code Xocdia88!\n💰 Giá mỗi lượt thử vận may: {GIA_CODE:,}đ\n🎁 Cơ hội nhận code: 2k, 5k, 10k... đến 88k!", reply_markup=markup)

@dp.message_handler(lambda message: message.text == "🔗 Link Game")
async def game_link(message: types.Message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Vào Game Ngay 🕹️", url=GAME_LINK))
    await message.reply("Bấm vào nút dưới đây để vào game:", reply_markup=markup)

@dp.message_handler(lambda message: message.text == "💰 Nạp Tiền MSB")
async def nap_tien(message: types.Message):
    msg = (
        "💳 **Thông tin chuyển khoản MSB**\n\n"
        "STK: `96886693002613` (Nguyễn Thanh Hợp)\n"
        f"Nội dung: `NAP {message.from_user.id}`\n\n"
        "⚠️ Chuyển đúng nội dung để được cộng tiền tự động sau 30s!"
    )
    await message.reply(msg, parse_mode="Markdown")

@dp.message_handler(lambda message: message.text == "👤 Tài Khoản")
async def user_info(message: types.Message):
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    balance = c.fetchone()[0]
    conn.close()
    await message.reply(f"🆔 ID: `{message.from_user.id}`\n💰 Số dư: {balance:,} VNĐ", parse_mode="Markdown")

@dp.message_handler(lambda message: message.text == "🛒 Mua Code (3.000đ)")
async def buy_code(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect('xocdia88.db')
    c = conn.cursor()
    
    # Kiểm tra tiền
    c.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    balance = c.fetchone()[0]
    
    if balance < GIA_CODE:
        return await message.reply("❌ Bạn không đủ tiền! Vui lòng nạp thêm.")
    
    # Lấy code ngẫu nhiên từ kho
    c.execute("SELECT id, code_text, value_game FROM codes WHERE status = 'available' ORDER BY RANDOM() LIMIT 1")
    res = c.fetchone()
    
    if res:
        code_id, code_val, game_val = res
        # Trừ tiền & cập nhật trạng thái code
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (GIA_CODE, uid))
        c.execute("UPDATE codes SET status = 'sold' WHERE id = ?", (code_id,))
        conn.commit()
        
        # Gửi kết quả
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Vào Game Nhập Code 🕹️", url=GAME_LINK))
        
        await message.reply(
            f"🎉 **MUA THÀNH CÔNG!**\n\n"
            f"🎁 Giá trị code: **{game_val}**\n"
            f"🔑 Mã Code: `{code_val}`\n\n"
            "Chúc bạn nổ hũ lớn! 🍀", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
    else:
        await message.reply("😔 Xin lỗi, kho code hiện tại đã hết. Vui lòng quay lại sau!")
    
    conn.close()

# --- ADMIN: LỆNH NẠP CODE VÀO KHO ---
@dp.message_handler(commands=['add'])
async def add_stock(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    # Cú pháp: /add 20k ABC-XYZ-123
    try:
        args = message.get_args().split(" ", 1)
        val_game = args[0] # 20k, 88k...
        code_txt = args[1]
        
        conn = sqlite3.connect('xocdia88.db')
        c = conn.cursor()
        c.execute("INSERT INTO codes (code_text, value_game) VALUES (?, ?)", (code_txt, val_game))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Đã thêm code {val_game} thành công!")
    except:
        await message.reply("Sai cú pháp! Dùng: `/add [mệnh_giá] [mã_code]`\nVD: `/add 88k XYZ123`", parse_mode="Markdown")

# Chạy song song FastAPI và Bot
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == '__main__':
    threading.Thread(target=run_fastapi).start()
    executor.start_polling(dp, skip_updates=True)
                    

import telebot # Đã sửa chữ i thường
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- CẤU HÌNH KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run():
    # Sử dụng cổng từ môi trường Render hoặc mặc định 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CẤU HÌNH BOT ---
API_TOKEN = '8475867709:AAGPINZGRgMnZBRDpNZWPGgBof0fY8N-0D4'
ADMIN_ID = 7816353760 

CHANNELS = ['@kiemtienonline48h', '@baogametanthunew', '@xomnguhoc', '@thongbaogamemoi1'] 
MONEY_PER_REF = 5000 
COST_PER_CODE = 10000 

db = {
    "users": {}, 
    "codes": [],
    "game_link": "https://xocdia88.ec"
}

bot = telebot.TeleBot(API_TOKEN)

# --- HÀM KIỂM TRA NHÓM ---
def check_all_channels(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked', 'restricted']:
                return False, channel
        except:
            return False, channel
    return True, None

def verify_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Xác Minh")
    return markup

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Thống Kê", "🎁 Rút Code")
    markup.add("🔗 Lấy Link Mời", "🎮 Link Game")
    if user_id == ADMIN_ID:
        markup.add("🛠 Admin Panel")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in db["users"]:
        args = message.text.split()
        referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        db["users"][user_id] = {'balance': 0, 'invited_by': referrer, 'refs': 0, 'verified': False}
    
    user_data = db["users"][user_id]
    
    if not user_data['verified']:
        list_groups = "\n".join([f"👉 {c}" for c in CHANNELS])
        msg = f"🌟 Chào mừng bạn!\n\nĐể sử dụng Bot, bạn bắt buộc phải tham gia các nhóm sau:\n{list_groups}\n\nSau khi tham gia, hãy nhấn nút bên dưới để xác minh."
        bot.send_message(message.chat.id, msg, reply_markup=verify_menu())
    else:
        bot.send_message(message.chat.id, "✅ Bạn đã xác minh.", reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda msg: msg.text == "✅ Xác Minh")
def verify(message):
    uid = message.from_user.id
    if uid not in db["users"]: return
    user_data = db["users"][uid]

    if user_data['verified']:
        bot.reply_to(message, "⚠️ Bạn đã xác minh rồi!", reply_markup=main_menu(uid))
        return

    is_joined, missing_channel = check_all_channels(uid)
    if is_joined:
        user_data['verified'] = True
        ref_id = user_data['invited_by']
        if ref_id and ref_id in db["users"]:
            db["users"][ref_id]['balance'] += MONEY_PER_REF
            db["users"][ref_id]['refs'] += 1
            try:
                bot.send_message(ref_id, f"🎉 Bạn nhận được {MONEY_PER_REF:,}đ từ bạn bè vừa xác minh thành công!")
            except: pass
        bot.send_message(message.chat.id, f"✅ Xác minh thành công!", reply_markup=main_menu(uid))
    else:
        bot.reply_to(message, f"❌ Chưa đủ nhóm!\n👉 Thiếu: {missing_channel}")

@bot.message_handler(func=lambda msg: msg.text == "📊 Thống Kê")
def statistics(message):
    uid = message.from_user.id
    data = db["users"].get(uid, {'balance': 0, 'refs': 0})
    text = (f"=== 👤 TÀI KHOẢN ===\n🆔 ID: `{uid}`\n💰 Số dư: {data['balance']:,}đ\n👫 Đã mời: {data['refs']} người")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎁 Rút Code")
def redeem_code(message):
    uid = message.from_user.id
    user_data = db["users"].get(uid)
    if user_data['balance'] < COST_PER_CODE:
        bot.reply_to(message, f"❌ Cần tối thiểu {COST_PER_CODE:,}đ để rút code.")
        return
    if not db["codes"]:
        bot.reply_to(message, "📭 Kho code tạm thời hết.")
        return
    code = db["codes"].pop(0)
    user_data['balance'] -= COST_PER_CODE
    bot.send_message(message.chat.id, f"✅ Code: `{code}`\n💰 Còn lại: {user_data['balance']:,}đ", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎮 Link Game")
def send_game_link(message):
    bot.send_message(message.chat.id, f"🚀 **Link Game:**\n{db['game_link']}", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Lấy Link Mời")
def invite_link(message):
    bot.reply_to(message, f"🔗 Link mời:\n`t.me/{bot.get_me().username}?start={message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🛠 Admin Panel" and msg.from_user.id == ADMIN_ID)
def admin_panel(message):
    text = f"🛠 Admin:\n👥 Mem: {len(db['users'])}\n📦 Code kho: {len(db['codes'])}"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['addcode'])
def add_code(message):
    if message.from_user.id == ADMIN_ID:
        new_codes = message.text.split()[1:]
        db["codes"].extend(new_codes)
        bot.reply_to(message, f"📥 Đã thêm {len(new_codes)} code.")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.infinity_polling()
    

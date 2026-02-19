import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- CẤU HÌNH KEEP ALIVE (DÙNG ĐỂ TREO BOT) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CẤU HÌNH BOT ---
API_TOKEN = '8475867709:AAGPINZGRgMnZBRDpNZWPGgBof0fY8N-0D4'
ADMIN_ID = 7816353760 

CHANNELS = ['@kiemtienonline48h', '@baogametanthunew', '@xomnguhoc', '@thongbaogamemoi1'] 
MONEY_PER_REF = 5000 
COST_PER_CODE = 20000

db = {
    "users": {}, 
    "codes": [],
    "game_link": "https://xocdia88.ec"
}

bot = telebot.TeleBot(API_TOKEN)

# --- CÁC HÀM XỬ LÝ (GIỮ NGUYÊN TỪ CODE CỦA BẠN) ---
def check_all_channels(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked', 'restricted']:
                return False, channel
        except Exception:
            return False, channel
    return True, None

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Xác Minh", "📊 Thống Kê")
    markup.add("🎁 Rút Code", "🔗 Lấy Link Mời")
    markup.add("🎮 Link Game")
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
    
    bot.send_message(message.chat.id, "🌟 Chào mừng bạn! Bạn cần tham gia TẤT CẢ các nhóm hệ thống để nhận thưởng.", 
                     reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda msg: msg.text == "✅ Xác Minh")
def verify(message):
    uid = message.from_user.id
    user_data = db["users"].get(uid)
    if user_data['verified']:
        bot.reply_to(message, "⚠️ Tài khoản của bạn đã được xác minh trước đó.")
        return
    is_joined, missing_channel = check_all_channels(uid)
    if is_joined:
        user_data['verified'] = True
        user_data['balance'] += MONEY_PER_REF
        ref_id = user_data['invited_by']
        if ref_id and ref_id in db["users"]:
            db["users"][ref_id]['balance'] += MONEY_PER_REF
            db["users"][ref_id]['refs'] += 1
            try:
                bot.send_message(ref_id, f"🎉 Bạn nhận được {MONEY_PER_REF:,}đ vì bạn bè đã xác minh thành công!")
            except: pass
        bot.reply_to(message, f"✅ Thành công! Bạn nhận được {MONEY_PER_REF:,}đ.")
    else:
        bot.reply_to(message, f"❌ Chưa tham gia đủ nhóm!\n👉 Thiếu nhóm: {missing_channel}")

@bot.message_handler(func=lambda msg: msg.text == "📊 Thống Kê")
def statistics(message):
    uid = message.from_user.id
    data = db["users"].get(uid)
    text = (f"=== 👤 TÀI KHOẢN ===\n🆔 ID: `{uid}`\n💰 Số dư: {data['balance']:,}đ\n👫 Đã mời: {data['refs']} người\n🛠 Trạng thái: {'✅ Đã xác minh' if data['verified'] else '❌ Chưa xác minh'}")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎁 Rút Code")
def redeem_code(message):
    uid = message.from_user.id
    user_data = db["users"].get(uid)
    if not user_data['verified']:
        bot.reply_to(message, "⚠️ Cần xác minh trước!")
        return
    if user_data['balance'] < COST_PER_CODE:
        bot.reply_to(message, f"❌ Cần {COST_PER_CODE:,}đ.")
        return
    if not db["codes"]:
        bot.reply_to(message, "📭 Hết code!")
        return
    code = db["codes"].pop(0)
    user_data['balance'] -= COST_PER_CODE
    bot.send_message(message.chat.id, f"✅ Mã code: `{code}`\n💰 Còn lại: {user_data['balance']:,}đ", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎮 Link Game")
def send_game_link(message):
    bot.send_message(message.chat.id, f"🚀 **Link tải Game:**\n{db['game_link']}", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Lấy Link Mời")
def invite_link(message):
    bot.reply_to(message, f"🔗 Link mời:\n`t.me/{bot.get_me().username}?start={message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🛠 Admin Panel" and msg.from_user.id == ADMIN_ID)
def admin_panel(message):
    text = f"🛠 Admin:\n👥 Mem: {len(db['users'])}\n📦 Code: {len(db['codes'])}"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['addcode'])
def add_code(message):
    if message.from_user.id == ADMIN_ID:
        new_codes = message.text.split()[1:]
        db["codes"].extend(new_codes)
        bot.reply_to(message, f"📥 Đã thêm {len(new_codes)} code.")

# --- KHỞI CHẠY BOT VÀ KEEP ALIVE ---
if __name__ == "__main__":
    keep_alive()  # Kích hoạt máy chủ web để treo bot
    print("Bot is starting...")
    bot.infinity_polling()
    

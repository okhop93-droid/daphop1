import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- CẤU HÌNH KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CẤU HÌNH BOT ---
API_TOKEN = '8475867709:AAGPINZGRgMnZBRDpNZWPGgBof0fY8N-0D4'
ADMIN_ID = 7816353760 

CHANNELS = ['@kiemtienonline48h', '@baogametanthunew', '@xomnguhoc', '@thongbaogamemoi1'] 
MONEY_PER_REF = 5000 
COST_PER_CODE = 10000 # Min rút code là 10k (tương đương 2 ref)

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

# --- MENU TRƯỚC KHI XÁC MINH ---
def verify_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Xác Minh")
    return markup

# --- MENU SAU KHI XÁC MINH (MENU CHÍNH) ---
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
        bot.send_message(message.chat.id, "✅ Bạn đã xác minh. Hãy chọn chức năng bên dưới:", reply_markup=main_menu(user_id))

@bot.message_handler(func=lambda msg: msg.text == "✅ Xác Minh")
def verify(message):
    uid = message.from_user.id
    user_data = db["users"].get(uid)

    if user_data['verified']:
        bot.reply_to(message, "⚠️ Bạn đã xác minh rồi!", reply_markup=main_menu(uid))
        return

    is_joined, missing_channel = check_all_channels(uid)
    if is_joined:
        user_data['verified'] = True
        # Sau khi xác minh thành công mới được cộng tiền cho chính mình và người mời
        user_data['balance'] += 0 # User mới nhận 0đ hoặc tùy bạn chỉnh
        
        ref_id = user_data['invited_by']
        if ref_id and ref_id in db["users"]:
            db["users"][ref_id]['balance'] += MONEY_PER_REF
            db["users"][ref_id]['refs'] += 1
            try:
                bot.send_message(ref_id, f"🎉 Bạn nhận được {MONEY_PER_REF:,}đ vì bạn bè vừa xác minh thành công!")
            except: pass

        bot.send_message(message.chat.id, f"✅ Xác minh thành công! Menu đã được mở khóa.", reply_markup=main_menu(uid))
    else:
        bot.reply_to(message, f"❌ Bạn chưa vào đủ nhóm!\n👉 Bạn còn thiếu nhóm: {missing_channel}\n\nVui lòng vào đủ và nhấn lại Xác Minh.")

@bot.message_handler(func=lambda msg: msg.text == "📊 Thống Kê")
def statistics(message):
    uid = message.from_user.id
    data = db["users"].get(uid)
    text = (f"=== 👤 TÀI KHOẢN ===\n🆔 ID: `{uid}`\n💰 Số dư: {data['balance']:,}đ\n👫 Đã mời: {data['refs']} người\n🛠 Trạng thái: ✅ Đã xác minh")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎁 Rút Code")
def redeem_code(message):
    uid = message.from_user.id
    user_data = db["users"].get(uid)

    if user_data['balance'] < COST_PER_CODE:
        bot.reply_to(message, f"❌ Số dư không đủ!\nMin rút là {COST_PER_CODE:,}đ (Cần mời ít nhất 2 bạn bè).")
        return
    
    if not db["codes"]:
        bot.reply_to(message, "📭 Kho code tạm thời hết, hãy liên hệ Admin!")
        return

    code = db["codes"].pop(0)
    user_data['balance'] -= COST_PER_CODE
    bot.send_message(message.chat.id, f"✅ Đổi code thành công!\n🎁 Mã của bạn: `{code}`\n💰 Số dư còn lại: {user_data['balance']:,}đ", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎮 Link Game")
def send_game_link(message):
    bot.send_message(message.chat.id, f"🚀 **Link tham gia Game:**\n{db['game_link']}", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Lấy Link Mời")
def invite_link(message):
    bot.reply_to(message, f"🔗 Link mời của bạn:\n`t.me/{bot.get_me().username}?start={message.from_user.id}`\n\n(Nhận {MONEY_PER_REF:,}đ cho mỗi bạn bè tham gia đủ nhóm và xác minh).", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🛠 Admin Panel" and msg.from_user.id == ADMIN_ID)
def admin_panel(message):
    text = f"🛠 Admin:\n👥 Tổng mem: {len(db['users'])}\n📦 Code kho: {len(db['codes'])}\n\n👉 Dùng /addcode để thêm mã."
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['addcode'])
def add_code(message):
    if message.from_user.id == ADMIN_ID:
        new_codes = message.text.split()[1:]
        if new_codes:
            db["codes"].extend(new_codes)
            bot.reply_to(message, f"📥 Đã thêm {len(new_codes)} code.")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.infinity_polling()
                                 

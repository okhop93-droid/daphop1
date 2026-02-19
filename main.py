import telebot
from telebot import types

API_TOKEN = '8475867709:AAGPINZGRgMnZBRDpNZWPGgBof0fY8N-0D4'
ADMIN_ID = 7816353760  # Thay ID của bạn

# Danh sách các nhóm/kênh bắt buộc (Sử dụng Username hoặc ID)
# Bot phải là Admin của tất cả các nhóm này
CHANNELS = ['@kiemtienonline48h', '@baogametanthunew', '@xomnguhoc', '@thongbaogamemoi1'] 

MONEY_PER_REF = 5000 
COST_PER_CODE = 20000

db = {
    "users": {}, 
    "codes": [],
    "game_link": "https://xocdia88.ec"
}

bot = telebot.TeleBot(API_TOKEN)

# --- HÀM KIỂM TRA TẤT CẢ NHÓM ---
def check_all_channels(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            # Nếu status là 'left', 'kicked' hoặc 'left' thì coi như chưa vào
            if status in ['left', 'kicked', 'restricted']:
                return False, channel
        except Exception as e:
            # Nếu bot chưa vào nhóm hoặc lỗi ID nhóm
            return False, channel
    return True, None

# --- MENU CHÍNH ---
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

# --- XỬ LÝ XÁC MINH (NHIỀU NHÓM) ---
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
        
        # Cộng tiền cho người mời chỉ khi người được mời xác minh thành công
        ref_id = user_data['invited_by']
        if ref_id and ref_id in db["users"]:
            db["users"][ref_id]['balance'] += MONEY_PER_REF
            db["users"][ref_id]['refs'] += 1
            try:
                bot.send_message(ref_id, f"🎉 Chúc mừng! Bạn nhận được {MONEY_PER_REF:,}đ vì bạn bè của bạn đã tham gia đủ nhóm và xác minh thành công!")
            except: pass

        bot.reply_to(message, f"✅ Tuyệt vời! Bạn đã tham gia đủ nhóm và nhận được {MONEY_PER_REF:,}đ thưởng.")
    else:
        # Thông báo rõ nhóm nào người dùng chưa tham gia
        bot.reply_to(message, f"❌ Bạn chưa tham gia đầy đủ các nhóm!\n👉 Hãy tham gia nhóm {missing_channel} rồi ấn lại Xác Minh.")

# --- RÚT CODE (GIẤU SỐ LƯỢNG) ---
@bot.message_handler(func=lambda msg: msg.text == "🎁 Rút Code")
def redeem_code(message):
    uid = message.from_user.id
    user_data = db["users"].get(uid)

    if not user_data['verified']:
        bot.reply_to(message, "⚠️ Bạn cần tham gia các nhóm và nhấn '✅ Xác Minh' trước.")
        return

    if user_data['balance'] < COST_PER_CODE:
        bot.reply_to(message, f"❌ Số dư không đủ! Cần {COST_PER_CODE:,}đ. Hãy đi mời bạn bè bằng link của bạn.")
        return
    
    if not db["codes"]:
        bot.reply_to(message, "📭 Hiện tại kho code đã phát hết, vui lòng đợi Admin nạp thêm.")
        return

    code = db["codes"].pop(0)
    user_data['balance'] -= COST_PER_CODE
    bot.send_message(message.chat.id, f"✅ Đổi thành công!\n🎁 Code: `{code}`\n💰 Số dư còn lại: {user_data['balance']:,}đ", parse_mode="Markdown")

# --- PHẦN CÒN LẠI GIỮ NGUYÊN ---
@bot.message_handler(func=lambda msg: msg.text == "📊 Thống Kê")
def statistics(message):
    uid = message.from_user.id
    data = db["users"].get(uid)
    text = (f"=== 👤 TÀI KHOẢN ===\n🆔 ID: `{uid}`\n💰 Số dư: {data['balance']:,}đ\n👫 Đã mời: {data['refs']} người\n🛠 Trạng thái: {'✅ Đã xác minh' if data['verified'] else '❌ Chưa xác minh'}")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎮 Link Game")
def send_game_link(message):
    bot.send_message(message.chat.id, f"🚀 **Link tải Game:**\n{db['game_link']}", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔗 Lấy Link Mời")
def invite_link(message):
    bot.reply_to(message, f"🔗 Link giới thiệu của bạn (nhận {MONEY_PER_REF:,}đ/lượt):\n`t.me/{bot.get_me().username}?start={message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🛠 Admin Panel" and msg.from_user.id == ADMIN_ID)
def admin_panel(message):
    text = (f"=== 🛠 QUẢN TRỊ ===\n👥 Thành viên: {len(db['users'])}\n📦 Code kho: {len(db['codes'])}\n📢 Số nhóm bắt buộc: {len(CHANNELS)}\n\n🔹 Thêm code: `/addcode c1 c2` \n🔹 Đổi link: `/setlink http...` ")
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['addcode'])
def add_code(message):
    if message.from_user.id == ADMIN_ID:
        new_codes = message.text.split()[1:]
        if new_codes:
            db["codes"].extend(new_codes)
            bot.reply_to(message, f"📥 Đã nạp thêm {len(new_codes)} mã code.")

@bot.message_handler(commands=['setlink'])
def set_link(message):
    if message.from_user.id == ADMIN_ID:
        new_link = message.text.replace("/setlink ", "").strip()
        db["game_link"] = new_link
        bot.reply_to(message, "✅ Đã cập nhật Link Game.")

bot.infinity_polling()
        

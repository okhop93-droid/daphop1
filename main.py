import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os
import asyncio
import re
import random
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & PHÂN QUYỀN
# ==========================================
API_TOKEN = '8475867709:AAGPINZGRgMnZBRDpNZWPGgBof0fY8N-0D4'
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"

# PHÂN QUYỀN ADMIN
ADMIN_CHINH = [7816353760] # Chủ hệ thống (Toàn quyền)
ADMIN_PHU = [6472034224]             # Admin phụ (Thêm acc, quản lý mem)

MONEY_PER_REF = 3500   
COST_PER_CODE = 10000  
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"
SESSION_FILE = "sessions.txt"

db = {
    "users": {}, 
    "codes": [],
    "channels": ['@kiemtienonline48h', '@baogametanthunew', '@xomnguhoc', '@thongbaogamemoi1'],
    "game_link": "https://xocdia88.ec"
}

PENDING_LOGINS = {}
ACCS = {}
admin_states = {}

bot = telebot.TeleBot(API_TOKEN)
telethon_loop = asyncio.new_event_loop()
logging.basicConfig(level=logging.INFO)

# ==========================================
# 2. HỆ THỐNG CLONE (TELETHON)
# ==========================================
def make_grab_handler(client, name):
    async def handler(ev):
        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                delay = random.uniform(0.1, 0.4)
                await asyncio.sleep(delay)
                try:
                    await ev.click()
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and msgs[0].message:
                        match = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message)
                        if match:
                            code = match.group(1)
                            if code not in db["codes"]:
                                db["codes"].append(code)
                                for adm in (ADMIN_CHINH + ADMIN_PHU):
                                    try: bot.send_message(adm, f"🎊 **HÚP ĐƯỢC CODE MỚI!**\n🔑 Mã: `{code}`\n👤 Nguồn: {name}", parse_mode="Markdown")
                                    except: pass
                except: pass
    return handler

async def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            for line in f.read().splitlines():
                if not line.strip(): continue
                try:
                    c = TelegramClient(StringSession(line), API_ID, API_HASH)
                    await c.connect()
                    if await c.is_user_authorized():
                        me = await c.get_me()
                        ACCS[me.first_name] = c
                        c.add_event_handler(make_grab_handler(c, me.first_name), events.NewMessage(chats=BOT_GAME_TARGET))
                except: pass

def start_telethon():
    asyncio.set_event_loop(telethon_loop)
    telethon_loop.run_until_complete(load_sessions())
    telethon_loop.run_forever()

Thread(target=start_telethon, daemon=True).start()

# ==========================================
# 3. GIAO DIỆN MENU
# ==========================================
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Thống Kê", "🎁 Rút Giftcode")
    markup.add("🔗 Link Mời", "🎮 Link Game")
    if uid in ADMIN_CHINH or uid in ADMIN_PHU:
        markup.add("🛠 Admin Panel", "📱 Dàn Clone")
        markup.add("➕ Thêm Clone")
    return markup

def admin_panel_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if uid in ADMIN_CHINH:
        markup.add("📢 Gửi Thông Báo", "📢 Quản Lý Nhóm")
    markup.add("👥 Danh Sách Mem", "🔙 Quay Lại")
    return markup

def group_manage_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Thêm Nhóm", "➖ Xóa Nhóm")
    markup.add("🔙 Quay Lại Admin")
    return markup

# ==========================================
# 4. XỬ LÝ NGƯỜI DÙNG
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in db["users"]:
        args = message.text.split()
        referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        db["users"][uid] = {'balance': 0, 'invited_by': referrer, 'refs': 0, 'verified': False}
    
    if not db["users"][uid]['verified']:
        list_groups = "\n".join([f"🔹 {c}" for c in db["channels"]])
        msg = f"👋 **Chào mừng bạn!**\n\nTham gia các kênh sau để xác minh:\n{list_groups}"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ Xác Minh Ngay")
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "✨ Hệ thống đã sẵn sàng!", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda msg: msg.text == "✅ Xác Minh Ngay")
def verify(message):
    uid = message.from_user.id
    for channel in db["channels"]:
        try:
            status = bot.get_chat_member(channel, uid).status
            if status in ['left', 'kicked']:
                return bot.reply_to(message, f"❌ Bạn chưa tham gia kênh: {channel}")
        except: pass
    
    db["users"][uid]['verified'] = True
    ref_id = db["users"][uid]['invited_by']
    if ref_id and ref_id in db["users"]:
        db["users"][ref_id]['balance'] += MONEY_PER_REF
        db["users"][ref_id]['refs'] += 1
        try: bot.send_message(ref_id, f"🎉 **+{MONEY_PER_REF:,}đ** từ bạn bè!")
        except: pass
    bot.send_message(message.chat.id, "✅ Xác minh thành công!", reply_markup=main_menu(uid))

# ==========================================
# 5. XỬ LÝ ADMIN & TRẠNG THÁI (STATE)
# ==========================================
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    uid = message.from_user.id
    text = message.text
    state = admin_states.get(uid)

    # --- CHẶN XỬ LÝ THEO TRẠNG THÁI ---
    if state == "WAIT_PHONE":
        if text == "❌ Huỷ": admin_states.pop(uid); return bot.send_message(message.chat.id, "Đã huỷ", reply_markup=main_menu(uid))
        async def ask_code():
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            try:
                sent = await client.send_code_request(text)
                PENDING_LOGINS[uid] = {"p": text, "h": sent.phone_code_hash, "c": client}
                admin_states[uid] = "WAIT_OTP"
                bot.send_message(message.chat.id, "📩 **Nhập mã OTP:**", parse_mode="Markdown")
            except Exception as e: bot.send_message(message.chat.id, f"❌ Lỗi: {e}"); admin_states.pop(uid)
        asyncio.run_coroutine_threadsafe(ask_code(), telethon_loop); return

    if state == "WAIT_OTP":
        data = PENDING_LOGINS.get(uid)
        async def confirm():
            try:
                await data["c"].sign_in(data["p"], text, phone_code_hash=data["h"])
                ss = data["c"].session.save()
                with open(SESSION_FILE, "a") as f: f.write(ss + "\n")
                me = await data["c"].get_me()
                ACCS[me.first_name] = data["c"]
                data["c"].add_event_handler(make_grab_handler(data["c"], me.first_name), events.NewMessage(chats=BOT_GAME_TARGET))
                bot.send_message(message.chat.id, f"✅ Đã thêm: {me.first_name}", reply_markup=main_menu(uid))
            except Exception as e: bot.send_message(message.chat.id, f"❌ Lỗi: {e}")
            admin_states.pop(uid)
        asyncio.run_coroutine_threadsafe(confirm(), telethon_loop); return

    if state == "WAIT_BROADCAST":
        admin_states.pop(uid)
        for user in db["users"].keys():
            try: bot.send_message(user, f"📢 **THÔNG BÁO:**\n\n{text}", parse_mode="Markdown")
            except: pass
        return bot.send_message(message.chat.id, "✅ Đã gửi!", reply_markup=admin_panel_menu(uid))

    if state == "WAIT_ADD_GROUP":
        db["channels"].append(text)
        admin_states.pop(uid)
        return bot.send_message(message.chat.id, f"✅ Đã thêm {text}", reply_markup=group_manage_menu())

    if state == "WAIT_DEL_GROUP":
        if text in db["channels"]: db["channels"].remove(text)
        admin_states.pop(uid)
        return bot.send_message(message.chat.id, f"✅ Đã xoá {text}", reply_markup=group_manage_menu())

    # --- XỬ LÝ MENU BẤM ---
    if text == "📊 Thống Kê":
        user = db["users"].get(uid, {'balance': 0, 'refs': 0})
        bot.send_message(message.chat.id, f"💰 Số dư: **{user['balance']:,}đ**\n👫 Đã mời: `{user['refs']}`", parse_mode="Markdown")
    
    elif text == "🎁 Rút Giftcode":
        user = db["users"].get(uid)
        if user['balance'] < COST_PER_CODE: return bot.reply_to(message, "❌ Không đủ 10.000đ (3 ref)")
        if not db["codes"]: return bot.reply_to(message, "📭 Hết code, chờ clone săn thêm!")
        code = db["codes"].pop(0)
        user['balance'] -= COST_PER_CODE
        bot.send_message(message.chat.id, f"🎁 Code: `{code}`", parse_mode="Markdown")

    elif text == "🔗 Link Mời":
        bot.send_message(message.chat.id, f"🔗 Link: `https://t.me/{bot.get_me().username}?start={uid}`\n🎁 Thưởng: {MONEY_PER_REF:,}đ/ref", parse_mode="Markdown")

    elif text == "🛠 Admin Panel" and (uid in ADMIN_CHINH or uid in ADMIN_PHU):
        bot.send_message(message.chat.id, f"🛠 **BẢNG QUẢN TRỊ**\n📦 Code kho: {len(db['codes'])}", reply_markup=admin_panel_menu(uid))

    elif text == "📢 Quản Lý Nhóm" and uid in ADMIN_CHINH:
        list_grp = "\n".join(db["channels"])
        bot.send_message(message.chat.id, f"📝 **Danh sách nhóm hiện tại:**\n{list_grp}", reply_markup=group_manage_menu())

    elif text == "➕ Thêm Nhóm" and uid in ADMIN_CHINH:
        admin_states[uid] = "WAIT_ADD_GROUP"
        bot.send_message(message.chat.id, "Nhập Username nhóm (VD: @abc):", reply_markup=types.ReplyKeyboardRemove())

    elif text == "➖ Xóa Nhóm" and uid in ADMIN_CHINH:
        admin_states[uid] = "WAIT_DEL_GROUP"
        bot.send_message(message.chat.id, "Nhập chính xác Username nhóm muốn xoá:", reply_markup=types.ReplyKeyboardRemove())

    elif text == "📢 Gửi Thông Báo" and uid in ADMIN_CHINH:
        admin_states[uid] = "WAIT_BROADCAST"
        bot.send_message(message.chat.id, "Nhập nội dung thông báo:", reply_markup=types.ReplyKeyboardRemove())

    elif text == "➕ Thêm Clone" and (uid in ADMIN_CHINH or uid in ADMIN_PHU):
        admin_states[uid] = "WAIT_PHONE"
        bot.send_message(message.chat.id, "Nhập SĐT (VD: 849xxx):", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Huỷ"))

    elif text == "📱 Dàn Clone":
        msg = "📱 Workers: " + ", ".join(ACCS.keys()) if ACCS else "Chưa có clone."
        bot.send_message(message.chat.id, msg)

    elif text == "👥 Danh Sách Mem" and (uid in ADMIN_CHINH or uid in ADMIN_PHU):
        bot.send_message(message.chat.id, f"👥 Tổng số thành viên: `{len(db['users'])}`", parse_mode="Markdown")

    elif text == "🔙 Quay Lại Admin":
        bot.send_message(message.chat.id, "Quay lại bảng quản trị", reply_markup=admin_panel_menu(uid))

    elif text == "🔙 Quay Lại":
        bot.send_message(message.chat.id, "Menu chính", reply_markup=main_menu(uid))

# ==========================================
# 6. KHỞI CHẠY
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.infinity_polling()
                         

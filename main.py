import asyncio
import sqlite3
import re
import os
import random
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession

# ===== CẤU HÌNH HỆ THỐNG =====
API_ID = int(os.environ.get("API_ID", 36437338))
API_HASH = os.environ.get("API_HASH", "18d34c7efc396d277f3db62baa078efc")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8537896639:AAGDnV1rpRi1jW9WZNR7_Bf6QRsKKPkcs9M")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 7816353760))

DB_FILE = "rental_service.db"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

# Cấu hình các gói thuê
RENT_PACKAGES = {
    "1day": {"price": 10000, "days": 1, "text": "10k / 1 Ngày"},
    "5day": {"price": 50000, "days": 5, "text": "50k / 5 Ngày"},
    "10day": {"price": 100000, "days": 10, "text": "100k / 10 Ngày"}
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== DATABASE CORE =====
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
        # Bảng lưu clone của từng khách
        c.execute('''CREATE TABLE IF NOT EXISTS my_clones (
            phone TEXT PRIMARY KEY, 
            owner_id INTEGER, 
            session TEXT, 
            expiry TEXT,
            status TEXT DEFAULT 'ACTIVE')''')
        conn.commit()

def db_exec(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute(query, params); conn.commit()

def db_fetch(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.cursor().execute(query, params).fetchall()

# ===== LOGIC ĐẬP HỘP RIÊNG BIỆT =====
RUNNING_WORKERS = {} # Lưu trữ các client đang chạy

async def worker_grab_loop(client, phone, owner_id):
    logger.info(f"🚀 Worker {phone} của khách {owner_id} bắt đầu săn!")
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.4))
                try:
                    await ev.click()
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        # Gửi thẳng về cho chủ sở hữu clone
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` HÚP ĐƯỢC CODE!**\n🔑 Mã của bạn: `{code}`")
                except: pass

# ===== BOT CHÍNH (GIAO DIỆN KHÁCH) =====
bot = TelegramClient(StringSession(), API_ID, API_HASH)
PENDING_LOGINS = {}

def get_main_menu(uid):
    return [
        [TButton.inline("➕ THÊM CLONE CỦA TÔI", b"add_clone"), TButton.inline("⏳ GIA HẠN/THUÊ", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 DANH SÁCH CLONE", b"list_my_clones")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    if not db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,)):
        db_exec("INSERT INTO users (user_id) VALUES (?)", (uid,))
    await e.respond("👋 **CHÀO MỪNG BẠN ĐẾN VỚI HỆ THỐNG THUÊ TREO CLONE ĐẬP HỘP!**\n\nBạn nạp clone của chính bạn vào, bot sẽ treo và báo code về cho bạn.", buttons=get_main_menu(uid))

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid = e.sender_id
    data = e.data.decode()

    if data == "me":
        bal = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))[0][0]
        await e.edit(f"👤 **THÔNG TIN CỦA BẠN**\n🆔 ID: `{uid}`\n💰 Số dư: **{bal:,}đ**", buttons=[[TButton.inline("🔙 Quay lại", b"menu")]])

    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_pkg_{k}")] for k, v in RENT_PACKAGES.items()]
        btns.append([TButton.inline("🔙 Quay lại", b"menu")])
        await e.edit("💎 **CHỌN GÓI THUÊ HỆ THỐNG TREO CLONE:**", buttons=btns)

    elif data.startswith("buy_pkg_"):
        pkg_id = data.replace("buy_pkg_", "")
        pkg = RENT_PACKAGES[pkg_id]
        user_bal = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))[0][0]
        
        if user_bal < pkg['price']:
            return await e.answer("❌ Số dư không đủ!", alert=True)
            
        # Lưu ý: Ở đây là thuê "slot" treo, hoặc cộng thêm ngày cho toàn bộ clone của user
        db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (pkg['price'], uid))
        # Cộng ngày hết hạn cho các clone của user này
        new_expiry = (datetime.now() + timedelta(days=pkg['days'])).strftime("%Y-%m-%d %H:%M:%S")
        db_exec("UPDATE my_clones SET expiry = ?, status='ACTIVE' WHERE owner_id=?", (new_expiry, uid))
        
        await e.respond(f"✅ Thuê thành công gói **{pkg['text']}**!\nCác clone của bạn đã được gia hạn.")

    elif data == "add_clone":
        await e.respond("📱 Gửi số điện thoại clone của bạn (định dạng 84...): \nSử dụng lệnh: `/addacc 84xxxxxxxxx`")

    elif data == "list_my_clones":
        clones = db_fetch("SELECT phone, expiry, status FROM my_clones WHERE owner_id=?", (uid,))
        if not clones: return await e.answer("Bạn chưa có clone nào!", alert=True)
        msg = "📱 **CLONE CỦA BẠN:**\n"
        for p, ex, st in clones:
            msg += f"▪️ `{p}` - Hạn: `{ex}` ({st})\n"
        await e.respond(msg)

    elif data == "deposit":
        qr_url = f"https://img.vietqr.io/image/MSB-96886693002613-compact2.png?amount=50000&addInfo=NAP%20{uid}"
        await e.edit(f"🏦 **NẠP TIỀN TỰ ĐỘNG**\n\nSTK: `96886693002613` (MSB)\nChủ TK: NGUYEN THANH HOP\nNội dung: `NAP {uid}`", buttons=[[TButton.url("🖼 QUÉT MÃ QR", qr_url)], [TButton.inline("🔙 Quay lại", b"menu")]])

    elif data == "menu":
        await e.edit("🤖 **DANH MỤC HỆ THỐNG**", buttons=get_main_menu(uid))

# --- LOGIC THÊM ACC CHO THÀNH VIÊN ---
@bot.on(events.NewMessage(pattern=r"/addacc (.+)"))
async def add_acc_member(e):
    phone = e.pattern_match.group(1).strip()
    # Kiểm tra xem có clone nào còn hạn không mới cho add (hoặc cho add rồi mới thuê)
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        PENDING_LOGINS[e.sender_id] = {"p": phone, "h": sent.phone_code_hash, "c": client}
        await e.reply(f"📩 Mã OTP đã gửi tới `{phone}`\nNhập: `/otp <mã>`")
    except Exception as ex: await e.reply(f"❌ Lỗi: {ex}")

@bot.on(events.NewMessage(pattern=r"/otp (\d+)"))
async def otp_member(e):
    uid = e.sender_id
    if uid not in PENDING_LOGINS: return
    otp = e.pattern_match.group(1)
    data = PENDING_LOGINS[uid]
    try:
        await data['c'].sign_in(data['p'], otp, phone_code_hash=data['h'])
        ss = data['c'].session.save()
        # Mặc định cho 1 giờ dùng thử hoặc bắt thuê mới chạy
        expiry = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        db_exec("INSERT OR REPLACE INTO my_clones (phone, owner_id, session, expiry) VALUES (?, ?, ?, ?)", 
               (data['p'], uid, ss, expiry))
        
        asyncio.create_task(worker_grab_loop(data['c'], data['p'], uid))
        await e.reply(f"✅ Đã kết nối Clone `{data['p']}` thành công! Bot bắt đầu đập hộp cho bạn.")
        del PENDING_LOGINS[uid]
    except Exception as ex: await e.reply(f"❌ OTP Sai hoặc lỗi: {ex}")

# ===== SEPAY WEBHOOK & RUNNER =====
app = Flask(__name__)
main_loop = None

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    match = re.search(r'NAP\s+(\d+)', data.get("content", "").upper())
    amount = int(data.get("transferAmount", 0))
    if match and amount > 0:
        uid = int(match.group(1))
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
        if main_loop: asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 Đã nạp thành công `+{amount:,}đ`!"), main_loop)
    return jsonify({"status": "ok"}), 200

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    init_db()
    await bot.start(bot_token=BOT_TOKEN)
    
    # Load lại các clone cũ còn hạn
    active_clones = db_fetch("SELECT phone, session, owner_id FROM my_clones WHERE expiry > ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    for p, s, o in active_clones:
        try:
            c = TelegramClient(StringSession(s), API_ID, API_HASH)
            await c.connect()
            asyncio.create_task(worker_grab_loop(c, p, o))
        except: pass
        
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080, use_reloader=False), daemon=True).start()
    asyncio.run(runner())
        

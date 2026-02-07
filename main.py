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

# Thông tin ngân hàng MSB
STK_MSB = "96886693002613"
TEN_CHU_TK = "NGUYEN THANH HOP"

DB_FILE = "rental_service.db"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

# Cấu hình gói thuê
RENT_PACKAGES = {
    "1day": {"price": 10000, "days": 1, "text": "💎 10k / 1 Ngày"},
    "5day": {"price": 50000, "days": 5, "text": "💎 50k / 5 Ngày"},
    "10day": {"price": 100000, "days": 10, "text": "💎 100k / 10 Ngày"}
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== DATABASE CORE =====
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
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

# ===== LOGIC ĐẬP HỘP (RIÊNG BIỆT) =====
async def worker_grab_loop(client, phone, owner_id):
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        res = db_fetch("SELECT expiry FROM my_clones WHERE phone=?", (phone,))
        if not res or datetime.strptime(res[0][0], "%Y-%m-%d %H:%M:%S") < datetime.now():
            await client.disconnect()
            return

        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.3))
                try:
                    await ev.click()
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` ĐÃ ĐẬP TRÚNG!**\n🔑 Code của bạn: `{code}`")
                except: pass

# ===== BOT CHÍNH =====
bot = TelegramClient(StringSession(), API_ID, API_HASH)
PENDING_LOGINS = {}

def get_main_menu(uid):
    return [
        [TButton.inline("➕ THÊM ACC CLONE", b"add_clone"), TButton.inline("⏳ GIA HẠN THUÊ", b"rent_pkg")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"deposit")],
        [TButton.inline("📱 CLONE CỦA TÔI", b"list_my_clones")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    if not db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,)):
        db_exec("INSERT INTO users (user_id) VALUES (?)", (uid,))
    await e.respond("🦅 **HỆ THỐNG THUÊ BOT TREO CLONE**", buttons=get_main_menu(uid))

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid = e.sender_id
    data = e.data.decode()

    if data == "me":
        bal = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))[0][0]
        await e.edit(f"👤 **THÔNG TIN**\n🆔 ID: `{uid}`\n💰 Số dư: **{bal:,}đ**", buttons=[[TButton.inline("🔙 Quay lại", b"menu")]])

    elif data == "rent_pkg":
        btns = [[TButton.inline(v['text'], f"buy_pkg_{k}")] for k, v in RENT_PACKAGES.items()]
        btns.append([TButton.inline("🔙 Quay lại", b"menu")])
        await e.edit("💎 **CHỌN GÓI THUÊ:**", buttons=btns)

    elif data.startswith("buy_pkg_"):
        pkg_id = data.replace("buy_pkg_", "")
        pkg = RENT_PACKAGES[pkg_id]
        user_bal = db_fetch("SELECT balance FROM users WHERE user_id=?", (uid,))[0][0]
        if user_bal < pkg['price']:
            return await e.answer("❌ Số dư không đủ!", alert=True)
        db_exec("UPDATE users SET balance = balance - ? WHERE user_id=?", (pkg['price'], uid))
        clones = db_fetch("SELECT phone, expiry FROM my_clones WHERE owner_id=?", (uid,))
        for p, ex in clones:
            current_expiry = datetime.strptime(ex, "%Y-%m-%d %H:%M:%S")
            if current_expiry < datetime.now(): current_expiry = datetime.now()
            new_expiry = (current_expiry + timedelta(days=pkg['days'])).strftime("%Y-%m-%d %H:%M:%S")
            db_exec("UPDATE my_clones SET expiry = ?, status='ACTIVE' WHERE phone=?", (new_expiry, p))
        await e.respond(f"✅ Đã thanh toán gói **{pkg['text']}** thành công!")

    elif data == "add_clone":
        await e.respond("📱 Gửi số điện thoại clone (84...): `/addacc 84xxxxxxxxx`")

    elif data == "list_my_clones":
        clones = db_fetch("SELECT phone, expiry FROM my_clones WHERE owner_id=?", (uid,))
        if not clones: return await e.answer("Bạn chưa có clone nào!", alert=True)
        msg = "📱 **CLONE CỦA BẠN:**\n"
        for p, ex in clones:
            msg += f"▪️ `{p}` - Hết hạn: `{ex}`\n"
        await e.respond(msg)

    elif data == "deposit":
        # Sửa sang thông tin MSB
        qr_url = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount=10000&addInfo=NAP%20{uid}&accountName={TEN_CHU_TK}"
        await e.edit(
            f"🏦 **NẠP TIỀN TỰ ĐỘNG (MSB)**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 STK: `{STK_MSB}`\n"
            f"👤 Chủ TK: **{TEN_CHU_TK}**\n"
            f"📝 Nội dung: `NAP {uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Lưu ý: Phải ghi đúng nội dung để được cộng tiền tự động!*",
            buttons=[[TButton.url("🖼 QUÉT MÃ QR", qr_url)], [TButton.inline("🔙 Quay lại", b"menu")]]
        )

    elif data == "menu":
        await e.edit("🤖 **MENU CHÍNH**", buttons=get_main_menu(uid))

# --- LOGIC THÊM ACC ---
@bot.on(events.NewMessage(pattern=r"/addacc (.+)"))
async def add_acc_member(e):
    phone = e.pattern_match.group(1).strip()
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        PENDING_LOGINS[e.sender_id] = {"p": phone, "h": sent.phone_code_hash, "c": client}
        await e.reply(f"📩 OTP gửi tới `{phone}`. Nhập: `/otp <mã>`")
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
        expiry = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        db_exec("INSERT OR REPLACE INTO my_clones (phone, owner_id, session, expiry) VALUES (?, ?, ?, ?)", (data['p'], uid, ss, expiry))
        asyncio.create_task(worker_grab_loop(data['c'], data['p'], uid))
        await e.reply(f"✅ Đã thêm Clone `{data['p']}`. Dùng thử 1 giờ.")
        del PENDING_LOGINS[uid]
    except Exception as ex: await e.reply(f"❌ OTP Sai: {ex}")

# ===== WEBHOOK NẠP TIỀN (SEPAY) =====
app = Flask(__name__)
main_loop = None

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    if not data: return jsonify({"status": "error"}), 400
    content = data.get("content", "").upper()
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content)
    if match and amount > 0:
        uid = int(match.group(1))
        db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
        if main_loop: asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 Nạp thành công `+{amount:,}đ`!"), main_loop)
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "ignored"}), 200

@app.route('/')
def home(): return "OK"

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    init_db()
    await bot.start(bot_token=BOT_TOKEN)
    active = db_fetch("SELECT phone, session, owner_id FROM my_clones WHERE expiry > ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    for p, s, o in active:
        try:
            c = TelegramClient(StringSession(s), API_ID, API_HASH)
            await c.connect()
            asyncio.create_task(worker_grab_loop(c, p, o))
        except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), use_reloader=False), daemon=True).start()
    asyncio.run(runner())
    

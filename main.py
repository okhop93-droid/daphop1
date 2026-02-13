import asyncio
import sqlite3
import re
import os
import random
import logging
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession

# ===== CẤU HÌNH HỆ THỐNG =====
API_ID = int(os.environ.get("API_ID", 32709944))
API_HASH = os.environ.get("API_HASH", "380d4e77de6daaa56fcff460fe9f2e4b")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 7816353760))

BASE_DIR = "/data" if os.path.exists("/data") else os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "business_data.db")
SESSION_FILE = os.path.join(BASE_DIR, "sessions.txt")
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

PRICE_PER_CODE = 5000
REF_BONUS = 500
ACCS = {} 
PENDING_LOGINS = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== DATABASE CORE =====
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, ref_by INTEGER, total_bought INTEGER DEFAULT 0, join_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY, source_acc TEXT, status TEXT DEFAULT 'NEW', buyer_id INTEGER, date_added TEXT, date_sold TEXT)''')
        conn.commit()

def db_exec(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute(query, params); conn.commit()

def db_fetch(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.cursor().execute(query, params).fetchall()

# ===== HÀM ĐẬP HỘP CHUYÊN NGHIỆP =====
async def grab_loop(client, name):
    logger.info(f"✨ Worker [{name}] đã vào vị trí săn code!")
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                delay = random.uniform(0.1, 0.3)
                await asyncio.sleep(delay)
                try:
                    await ev.click()
                    logger.info(f"⚡️ [{name}] Đã nhấn đập hộp sau {delay:.2f}s")
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and msgs[0].message:
                        match = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message)
                        if match:
                            code = match.group(1)
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            db_exec("INSERT INTO codes (code, source_acc, date_added) VALUES (?, ?, ?)", (code, name, now))
                            log_text = (
                                f"🎊 **HÚP ĐƯỢC GIFTCODE MỚI!**\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"🔑 Mã: `{code}`\n"
                                f"👤 Nguồn: **{name}**\n"
                                f"⏰ Thời gian: {now}\n"
                                f"━━━━━━━━━━━━━━━━━━"
                            )
                            await bot.send_message(ADMIN_ID, log_text)
                except Exception as e:
                    logger.error(f"❌ Lỗi đập hộp [{name}]: {e}")

# ===== BOT CHÍNH (SHOP) =====
bot = TelegramClient(StringSession(), API_ID, API_HASH)

def get_main_menu(uid):
    btns = [
        [TButton.inline("🛒 MUA CODE", b"buy"), TButton.inline("📦 KHO HÀNG", b"stock")],
        [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🤝 GIỚI THIỆU", b"ref")],
        [TButton.inline("🏦 NẠP TIỀN", b"deposit")]
    ]
    if uid == ADMIN_ID: 
        btns.append([TButton.inline("📱 DÀN CLONE", b"list_acc"), TButton.inline("➕ THÊM ACC", b"add_acc_btn")])
        btns.append([TButton.inline("📊 THỐNG KÊ", b"stats")])
    return btns

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    args = e.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if not db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,)):
        db_exec("INSERT INTO users (user_id, balance, ref_by, join_date) VALUES (?, 0, ?, ?)", (uid, ref_id, datetime.now().strftime("%Y-%m-%d")))
    
    await e.respond(
        f"👋 **CHÀO MỪNG BẠN ĐẾN VỚI AUTO SHOP!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Hệ thống đập hộp & bán Code tự động 24/7\n"
        f"💎 Giá: `{PRICE_PER_CODE:,}đ` / 1 Giftcode\n"
        f"⚡️ Trạng thái: **Hoạt động**\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=get_main_menu(uid)
    )

@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    
    user_data = db_fetch("SELECT balance, total_bought, ref_by, join_date FROM users WHERE user_id=?", (uid,))
    if not user_data:
        return await e.answer("❌ Vui lòng sử dụng /start để đăng ký!", alert=True)
    balance, total_bought, ref_by, join_date = user_data[0]

    if data == "menu":
        await e.edit("🤖 **DANH MỤC HỆ THỐNG**", buttons=get_main_menu(uid))
    elif data == "stock":
        c = db_fetch("SELECT COUNT(*) FROM codes WHERE status='NEW'")[0][0]
        await e.answer(f"📦 Hiện đang có {c} mã sẵn sàng giao!", alert=True)
    elif data == "me":
        msg = (f"👤 **THÔNG TIN CÁ NHÂN**\n━━━━━━━━━━━━━━━━━━━━\n🆔 ID: `{uid}`\n💰 Số dư: **{balance:,}đ**\n🛍 Đã mua: `{total_bought}` mã\n🗓 Tham gia: `{join_date}`\n━━━━━━━━━━━━━━━━━━━━")
        await e.edit(msg, buttons=[[TButton.inline("🔙 Quay lại", b"menu")]])
    elif data == "ref":
        me = await bot.get_me()
        ref_link = f"https://t.me/{me.username}?start={uid}"
        msg = (f"🤝 **GIỚI THIỆU NHẬN THƯỞNG**\n━━━━━━━━━━━━━━━━━━━━\n🎁 Mỗi lượt giới thiệu bạn bè mua code, bạn nhận ngay: **{REF_BONUS:,}đ**\n\n🔗 Link giới thiệu:\n`{ref_link}`\n━━━━━━━━━━━━━━━━━━━━")
        await e.edit(msg, buttons=[[TButton.inline("🔙 Quay lại", b"menu")]])
    elif data == "stats":
        if uid != ADMIN_ID: return
        t_users = db_fetch("SELECT COUNT(*) FROM users")[0][0]
        t_codes = db_fetch("SELECT COUNT(*) FROM codes")[0][0]
        s_codes = db_fetch("SELECT COUNT(*) FROM codes WHERE status='SOLD'")[0][0]
        n_codes = t_codes - s_codes
        msg = (f"📊 **THỐNG KÊ HỆ THỐNG**\n━━━━━━━━━━━━━━━━━━━━\n👥 Tổng khách hàng: `{t_users}`\n📦 Tổng mã đã săn: `{t_codes}`\n🛒 Đã bán: `{s_codes}`\n💎 Còn tồn kho: `{n_codes}`\n💰 Doanh thu dự tính: **{s_codes * PRICE_PER_CODE:,}đ**\n━━━━━━━━━━━━━━━━━━━━")
        await e.edit(msg, buttons=[[TButton.inline("🔙 Quay lại", b"menu")]])
    elif data == "add_acc_btn":
        await e.respond("📱 Gửi số điện thoại theo định dạng: `/addacc 84...`\n(Ví dụ: `/addacc 84988xxxxxx`)")
    elif data == "list_acc":
        if uid != ADMIN_ID: return
        msg = "📱 **TRẠNG THÁI DÀN WORKER**\n━━━━━━━━━━━━━\n"
        if not ACCS: msg += "❌ Chưa có tài khoản nào Online."
        for name, acc_obj in ACCS.items():
            st = "✅ Online" if acc_obj['c'].is_connected() else "❌ Offline"
            msg += f"▪️ {name}: {st}\n"
        await e.respond(msg)
    elif data == "deposit":
        qr_url = f"https://img.vietqr.io/image/MSB-96886693002613-compact2.png?amount=50000&addInfo=NAP%20{uid}&accountName=NGUYEN%20THANH%20HOP"
        await e.edit(
            f"🏦 **HƯỚNG DẪN NẠP TIỀN**\n"
            f"━━━━━━━━━━━━━\n"
            f"💳 **MSB (Hàng Hải)**: `96886693002613`\n"
            f"👤 **Chủ TK**: NGUYEN THANH HOP\n"
            f"📝 **Nội dung**: `NAP {uid}`\n"
            f"━━━━━━━━━━━━━\n"
            f"⚠️ *Lưu ý: Hệ thống cộng tiền tự động sau 10s-30s!*",
            buttons=[[TButton.url("🖼 QUÉT MÃ QR", qr_url)], [TButton.inline("🔙 Quay lại", b"menu")]]
        )
    elif data == "buy":
        if balance < PRICE_PER_CODE: return await e.answer("❌ Số dư không đủ, vui lòng nạp thêm!", alert=True)
        res = db_fetch("SELECT code FROM codes WHERE status='NEW' LIMIT 1")
        if not res: return await e.answer("⚠️ Hàng trong kho đã hết, quay lại sau!", alert=True)
        code = res[0][0]
        db_exec("UPDATE users SET balance = balance - ?, total_bought = total_bought + ? WHERE user_id=?", (PRICE_PER_CODE, 1, uid))
        db_exec("UPDATE codes SET status='SOLD', buyer_id=?, date_sold=? WHERE code=?", (uid, datetime.now().strftime("%Y-%m-%d"), code))
        if ref_by: db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (REF_BONUS, ref_by))
        await e.respond(f"✅ **MUA THÀNH CÔNG!**\n🎁 Mã Giftcode của bạn là: `{code}`")
        await e.answer("Đã giao hàng thành công!")

# --- LOGIC ADMIN DÀN ACC ---
@bot.on(events.NewMessage(from_users=ADMIN_ID, pattern=r"/addacc (.+)"))
async def add_acc_cmd(e):
    phone = e.pattern_match.group(1).strip()
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        PENDING_LOGINS[ADMIN_ID] = {"p": phone, "h": sent.phone_code_hash, "c": client}
        await e.reply(f"📩 Đã gửi mã OTP đến số `{phone}`\nNhập mã bằng cách gõ: `/otp <mã_số>`")
    except Exception as ex:
        await e.reply(f"❌ Lỗi: {ex}")

@bot.on(events.NewMessage(from_users=ADMIN_ID, pattern=r"/otp (\d+)"))
async def otp_cmd(e):
    if ADMIN_ID not in PENDING_LOGINS: return await e.reply("❌ Vui lòng sử dụng lệnh `/addacc` trước!")
    otp = e.pattern_match.group(1)
    data = PENDING_LOGINS[ADMIN_ID]
    client = data["c"]
    try:
        await client.sign_in(data["p"], otp, phone_code_hash=data["h"])
        session_str = client.session.save()
        with open(SESSION_FILE, "a") as f: f.write(session_str + "\n")
        me = await client.get_me()
        ACCS[me.first_name] = {'c': client}
        asyncio.create_task(grab_loop(client, me.first_name))
        await e.reply(f"✅ Đăng nhập thành công Worker: **{me.first_name}**!")
        del PENDING_LOGINS[ADMIN_ID]
    except Exception as ex: await e.reply(f"❌ Lỗi xác thực: {ex}")

@bot.on(events.NewMessage(from_users=ADMIN_ID, pattern=r"/congtien (\d+) (\d+)"))
async def pay_cmd(e):
    tid, amt = e.pattern_match.group(1), e.pattern_match.group(2)
    db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, tid))
    await e.reply(f"✅ Đã cộng {int(amt):,}đ cho khách `{tid}`")
    try: await bot.send_message(int(tid), f"💰 Tài khoản của bạn đã được cộng: **{int(amt):,}đ**!")
    except: pass

# ===== KHỞI CHẠY & SEPAY WEBHOOK =====
app = Flask(__name__)
main_loop = None 

@app.route('/')
def home(): return "SYSTEM OPERATIONAL"

@app.route('/sepay-webhook', methods=['POST'])
def sepay_webhook():
    data = request.json
    if not data: return jsonify({"status": "no_data"}), 400
    content = data.get("content", "")
    amount = int(data.get("transferAmount", 0))
    match = re.search(r'NAP\s+(\d+)', content.upper())
    if match and amount > 0:
        uid = int(match.group(1))
        user = db_fetch("SELECT user_id FROM users WHERE user_id=?", (uid,))
        if user:
            db_exec("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
            msg = f"💰 **NẠP TIỀN TỰ ĐỘNG THÀNH CÔNG**\n━━━━━━━━━━━━━\n✅ Số dư đã cộng: `+{amount:,}đ`\n👤 Tài khoản: `{uid}`"
            asyncio.run_coroutine_threadsafe(bot.send_message(uid, msg), main_loop)
            asyncio.run_coroutine_threadsafe(bot.send_message(ADMIN_ID, f"🔔 **BIẾN ĐỘNG SỐ DƯ (MSB)**\n{msg}"), main_loop)
            return jsonify({"status": "success"}), 200
    return jsonify({"status": "ignored"}), 200

async def runner():
    global main_loop
    main_loop = asyncio.get_event_loop()
    init_db()
    await bot.start(bot_token=BOT_TOKEN)
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            for s in f.read().splitlines():
                if not s.strip(): continue
                try:
                    c = TelegramClient(StringSession(s), API_ID, API_HASH)
                    await c.connect()
                    if await c.is_user_authorized():
                        me = await c.get_me()
                        ACCS[me.first_name] = {'c': c}
                        asyncio.create_task(grab_loop(c, me.first_name))
                except: pass
    logger.info("🚀 Bot Shop & Workers Online!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # Flask: use_reloader=False để tránh khởi chạy bot 2 lần gây lỗi gửi 2 tin nhắn
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), use_reloader=False), daemon=True).start()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(runner())
        

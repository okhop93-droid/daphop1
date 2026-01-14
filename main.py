import asyncio, random, re, os, json
from datetime import datetime, timedelta # Đã đảm bảo import timedelta ở đây
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button, functions
from telethon.sessions import StringSession

# ===== CẤU HÌNH =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8290293625:AAFSVHI_UZV39fymFauEi7OYChF9KRC4F0M"
BOT_GAME = "xocdia88_bot_uytin_bot"

# --- CẤU HÌNH KINH DOANH ---
SUPER_ADMIN_ID = 7816353760  # ID Admin để nạp tiền
GIA_GOI_NGAY = 5000          # Giá 5k/ngày

SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"
OWNERS_FILE = "owners.json"
USERS_FILE = "users.json"

# ===== SERVER ẢO =====
app = Flask(__name__)
@app.route("/")
def home(): return "BOT SERVICE ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# ===== BIẾN HỆ THỐNG =====
ACCS = {}           
TOTAL_CODE = 0      
CODES_DB = {}       
PENDING_LOGIN = {}  
OWNERS_DB = {}      
USERS_DB = {}

# ===== QUẢN LÝ DATABASE =====
def save_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_data():
    global CODES_DB, TOTAL_CODE, OWNERS_DB, USERS_DB
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f: 
            CODES_DB = json.load(f)
            TOTAL_CODE = len(set(CODES_DB.values()))
    if os.path.exists(OWNERS_FILE):
        with open(OWNERS_FILE) as f: OWNERS_DB = json.load(f)
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f: USERS_DB = json.load(f)

def get_user(user_id):
    uid = str(user_id)
    if uid not in USERS_DB:
        USERS_DB[uid] = {"balance": 0, "expiry": None}
        save_file(USERS_FILE, USERS_DB)
    return USERS_DB[uid]

def check_expiry(user_id):
    user = get_user(user_id)
    if not user["expiry"]: return False
    try:
        exp_time = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
        return datetime.now() < exp_time
    except: return False

# --- HÀM ĐÃ SỬA LỖI ---
def add_expiry(user_id, days):
    user = get_user(user_id)
    now = datetime.now()
    
    if user["expiry"]:
        try:
            current_exp = datetime.strptime(user["expiry"], "%Y-%m-%d %H:%M:%S")
            start_time = current_exp if current_exp > now else now
        except: start_time = now
    else:
        start_time = now
    
    # Sử dụng timedelta(days=days) thay vì from_days lỗi
    new_exp = start_time + timedelta(days=days)
    
    USERS_DB[str(user_id)]["expiry"] = new_exp.strftime("%Y-%m-%d %H:%M:%S")
    save_file(USERS_FILE, USERS_DB)
    return new_exp

# ===== LUỒNG ĐẬP HỘP =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"] 

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not ev.reply_markup: return
        btn = next((b for r in ev.reply_markup.rows for b in r.buttons 
                    if any(x in b.text.lower() for x in ["đập","hộp"])), None)
        if not btn: return

        owner_id = acc.get("owner_id")
        if owner_id and not check_expiry(owner_id):
            return 

        try:
            await asyncio.sleep(random.uniform(0.1, 0.4))
            await ev.click()
            await asyncio.sleep(2.5) 

            msgs = await client.get_messages(BOT_GAME, limit=1)
            if msgs and msgs[0].message:
                raw_text = msgs[0].message
                match = re.search(r'là:\s*([A-Z0-9]+)', raw_text)
                
                if match:
                    gift_code = match.group(1)
                    if gift_code != acc.get("last"):
                        acc["last"] = gift_code
                        TOTAL_CODE += 1
                        CODES_DB[str(acc["id"])] = gift_code
                        save_file(CODES_FILE, CODES_DB)
                        
                        if owner_id:
                            msg_rieng = (
                                f"🎉 **HÚP CODE THÀNH CÔNG!**\n"
                                f"👤 Acc: **{acc['name']}**\n"
                                f"🎁 Code: `{gift_code}`\n"
                                f"⏰ Lúc: `{datetime.now().strftime('%H:%M:%S')}`"
                            )
                            try: await admin.send_message(owner_id, msg_rieng)
                            except: pass
        except Exception as e:
            print(f"❌ Lỗi TK {acc['stt']}: {e}")

# ===== ADMIN BOT =====
admin = TelegramClient("admin", API_ID, API_HASH)

def menu_main(user_id):
    user = get_user(user_id)
    bal = "{:,.0f}".format(user['balance'])
    
    if check_expiry(user_id):
        status_icon = "🟢"
        exp_txt = user['expiry']
    else:
        status_icon = "🔴"
        exp_txt = "Đã hết hạn"

    txt = (
        f"🤖 **HỆ THỐNG AUTO GAME VIP**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 ID: `{user_id}`\n"
        f"💰 Số dư: `{bal} vnđ`\n"
        f"⏳ Hạn dùng: {status_icon} `{exp_txt}`\n"
        f"📦 Giá gói: `{GIA_GOI_NGAY:,.0f} vnđ / 1 ngày`"
    )
    
    return txt, [
        [Button.inline(f"🛒 Mua Gói 1 Ngày ({GIA_GOI_NGAY//1000}k)", b"buy_1")],
        [Button.inline("📦 Quản Lý Acc", b"acc"), Button.inline("💵 Nạp Tiền", b"deposit")],
        [Button.inline("📊 Thống Kê", b"stat"), Button.inline("➕ Thêm Acc", b"add")]
    ]

@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    txt, btns = menu_main(e.sender_id)
    await e.respond(txt, buttons=btns)

@admin.on(events.CallbackQuery)
async def cb(e):
    sender_id = e.sender_id
    user = get_user(sender_id)
    my_accs = [a for a in ACCS.values() if a.get('owner_id') == sender_id]

    if e.data == b"back":
        txt, btns = menu_main(sender_id)
        await e.edit(txt, buttons=btns)

    elif e.data == b"deposit":
        msg = (
            f"💳 **HƯỚNG DẪN NẠP TIỀN**\n\n"
            f"🏦 Ngân hàng: **MB Bank**\n"
            f"💳 STK: `0123456789` (Thay STK của bạn)\n"
            f"👤 Tên: **ADMIN**\n"
            f"📝 Nội dung: `NAP {sender_id}`\n\n"
            f"👉 Sau khi chuyển khoản, vui lòng nhắn tin Admin để được duyệt."
        )
        await e.edit(msg, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"buy_1":
        if user['balance'] >= GIA_GOI_NGAY:
            USERS_DB[str(sender_id)]['balance'] -= GIA_GOI_NGAY
            add_expiry(sender_id, 1)
            await e.answer("✅ Mua thành công 1 ngày!", alert=True)
            txt, btns = menu_main(sender_id)
            await e.edit(txt, buttons=btns)
        else:
            await e.answer("❌ Số dư không đủ! Vui lòng nạp thêm.", alert=True)

    elif e.data == b"add":
        if not check_expiry(sender_id):
            await e.answer("❌ Dịch vụ hết hạn, vui lòng mua gói!", alert=True)
            return
        await e.edit("➕ **THÊM ACC**\nNhập: `/login SĐT`", buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"acc":
        if not my_accs:
            await e.edit("📭 Chưa có Acc nào.", buttons=[[Button.inline("⬅️ Quay lại", b"back")]])
        else:
            txt = "📑 **ACC CỦA BẠN:**\n"
            for a in my_accs: txt += f"• {a['name']} ({a['status']})\n"
            await e.edit(txt, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

    elif e.data == b"stat":
        txt = "📊 **THỐNG KÊ**\n"
        for a in my_accs: txt += f"• {a['name']}: `{a.get('last') or '...'}`\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])

@admin.on(events.NewMessage(pattern=r"/nap (\d+) (\d+)"))
async def add_fund(e):
    if e.sender_id != SUPER_ADMIN_ID: return
    try:
        target_id, amount = e.pattern_match.group(1), int(e.pattern_match.group(2))
        user = get_user(target_id)
        USERS_DB[str(target_id)]['balance'] += amount
        save_file(USERS_FILE, USERS_DB)
        await e.respond(f"✅ Đã cộng {amount:,}đ cho `{target_id}`.")
        try: await admin.send_message(int(target_id), f"💳 Tài khoản đã được cộng {amount:,}đ")
        except: pass
    except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    if not check_expiry(e.sender_id):
        await e.respond("🚫 Dịch vụ hết hạn!")
        return
    try:
        phone = "".join(filter(str.isdigit, e.text.split(" ", 1)[1]))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        PENDING_LOGIN[e.sender_id] = {"c": c, "p": phone, "h": sent.phone_code_hash}
        await e.respond(f"📩 Nhập OTP: `/otp <code>`")
    except: await e.respond("❌ Lỗi login.")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp_handler(e):
    data = PENDING_LOGIN.get(e.sender_id)
    if not data: return
    try:
        await data["c"].sign_in(data["p"], "".join(filter(str.isdigit, e.text)), phone_code_hash=data["h"])
        save_session(data["c"].session.save())
        me = await data["c"].get_me()
        OWNERS_DB[str(me.id)] = e.sender_id
        save_file(OWNERS_FILE, OWNERS_DB)
        new_stt = len(ACCS) + 1
        ACCS[me.id] = {
            "id": me.id, "stt": new_stt, "client": data["c"],
            "name": me.first_name, "status": "ONLINE 🟢", "last": None, "owner_id": e.sender_id
        }
        asyncio.create_task(grab_loop(ACCS[me.id]))
        await e.respond(f"✅ Thành công: {me.first_name}")
        del PENDING_LOGIN[e.sender_id]
    except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        if sess not in f.read(): f.write(sess + "\n")

async def main():
    load_data()
    print("🤖 Bot đang chạy...")
    await admin.start(bot_token=BOT_TOKEN)
    
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            for i, s in enumerate(f.read().splitlines(), 1):
                if not s.strip(): continue
                try:
                    c = TelegramClient(StringSession(s), API_ID, API_HASH)
                    await c.connect()
                    if await c.is_user_authorized():
                        me = await c.get_me()
                        owner = OWNERS_DB.get(str(me.id))
                        ACCS[me.id] = {
                            "id": me.id, "stt": i, "client": c, "name": me.first_name, 
                            "status": "ONLINE 🟢", "last": CODES_DB.get(str(me.id)), "owner_id": owner
                        }
                        asyncio.create_task(grab_loop(ACCS[me.id]))
                except: pass
    await admin.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
    

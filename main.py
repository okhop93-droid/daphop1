import asyncio, random, re, os, json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ================== CẤU HÌNH ==================
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8003350771:AAG2dlCVCxuSXJRgr4bBAyyyIW63kYuNA2M"
BOT_GAME = "xocdia88_bot_uytin_bot"

USERS_FILE = "users.json"
BOT_CODE_FILE = "bot_codes.json"

BANK_API_URL = "https://api-bank-demo.com/check_payment"  # đổi thành API bank thật
BANK_API_KEY = "API_KEY_CỦA_BẠN"

PACKS = {
    "20k": timedelta(days=7),
    "100k": timedelta(days=30)
}

# ================== FLASK KEEP ALIVE ==================
app = Flask(__name__)
@app.route("/")
def home():
    return "BOT ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# ================== STATE ==================
USERS = {}   # user_id -> {"expire": datetime, "session": str, "acc_name": str, "last_code": str}
BOT_CODES = [] # Kho code
TOTAL_CODE = 0

# ================== HELPER ==================
def save_users():
    with open(USERS_FILE,"w") as f:
        json.dump({str(k):{"expire":v["expire"].isoformat(),
                           "session":v["session"],
                           "acc_name":v["acc_name"],
                           "last_code":v.get("last_code","")} for k,v in USERS.items()}, f, indent=2)

def load_users():
    global USERS
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            data = json.load(f)
            USERS = {int(k):{"expire":datetime.fromisoformat(v["expire"]),
                             "session":v["session"],
                             "acc_name":v["acc_name"],
                             "last_code":v.get("last_code","")} for k,v in data.items()}

def save_bot_codes():
    with open(BOT_CODE_FILE,"w") as f:
        json.dump({"codes": BOT_CODES}, f, indent=2)

def load_bot_codes():
    global BOT_CODES
    if os.path.exists(BOT_CODE_FILE):
        with open(BOT_CODE_FILE,"r") as f:
            BOT_CODES = json.load(f).get("codes", [])

def has_access(user_id):
    now = datetime.utcnow()
    return user_id in USERS and USERS[user_id]["expire"] > now

def get_remaining_days(user_id):
    if user_id not in USERS: return 0
    delta = USERS[user_id]["expire"] - datetime.utcnow()
    return max(delta.days,0)

def store_code_to_bot(user_id, acc_name, code):
    BOT_CODES.append({
        "code": code,
        "user_id": user_id,
        "acc_name": acc_name,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_bot_codes()

async def send_code_to_user(user_id, acc_name, code):
    await admin.send_message(
        user_id,
        f"🎁 CODE MỚI\n👤 Acc: {acc_name}\n🔐 Code: `{code}`"
    )

# ================== ADMIN BOT ==================
admin = TelegramClient("admin", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("📦 Acc", b"acc"), Button.inline("📄 Kho Code", b"bot_codes")],
        [Button.inline("📊 Thống kê", b"stat"), Button.inline("♻️ Restart", b"restart")]
    ]

@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    await e.respond(f"🤖 BOT ĐẬP HỘP KINH DOANH\nNgười dùng: {len(USERS)}\nTổng code: {len(BOT_CODES)}",
                    buttons=menu())

@admin.on(events.CallbackQuery)
async def cb(e):
    now = datetime.utcnow()
    if e.data == b"acc":
        txt = "📦 DANH SÁCH USER\n"
        for u in USERS.values():
            txt += f"- {u['acc_name']} | Hạn: {u['expire']} | Ngày còn lại: {get_remaining_days(u)}\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"bot_codes":
        if not BOT_CODES:
            txt = "📄 Kho code trống"
        else:
            txt = "📄 KHO CODE BOT (mới nhất 20)\n"
            for c in BOT_CODES[-20:]:
                txt += f"- `{c['code']}` | {c['acc_name']} | {c['time']}\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"stat":
        total_users = len(USERS)
        active_users = sum(1 for u in USERS.values() if u["expire"]>now)
        expired_users = total_users - active_users
        total_codes = len(BOT_CODES)
        today_codes = sum(1 for c in BOT_CODES if c["time"].startswith(now.strftime("%Y-%m-%d")))
        expiring_soon = sum(1 for u in USERS.values() if 0 < (u["expire"] - now).days <=2)

        txt = (
            f"📊 THỐNG KÊ BOT KINH DOANH 📊\n\n"
            f"👤 Tổng user: {total_users}\n"
            f"✅ User còn hạn: {active_users}\n"
            f"⏳ User hết hạn: {expired_users}\n"
            f"⚠️ User sắp hết hạn (<2 ngày): {expiring_soon}\n\n"
            f"🎁 Tổng code: {total_codes}\n"
            f"🌟 Code hôm nay: {today_codes}\n\n"
            f"⏰ Thời gian: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

    elif e.data == b"restart":
        await e.edit("♻️ Restart...")
        os._exit(0)

    elif e.data == b"back":
        await e.edit("🤖 MENU", buttons=menu())

# ================== LOGIN SESSION USER ==================
@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    try:
        session_str = e.text.split(" ",1)[1].strip()
        c = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await c.connect()
        me = await c.get_me()
        USERS[e.sender_id] = {
            "expire": datetime.utcnow(),
            "session": session_str,
            "acc_name": me.first_name,
            "last_code": ""
        }
        save_users()
        await e.respond(f"✅ Kích hoạt thành công acc {me.first_name}. Hãy nạp tiền để sử dụng bot.")
    except:
        await e.respond("❌ SESSION không hợp lệ")

# ================== NẠP TIỀN QUA BANK ==================
@admin.on(events.NewMessage(pattern="/nap"))
async def nap_handler(e):
    args = e.text.split(" ",1)
    if len(args)<2 or args[1] not in PACKS:
        await e.respond("❌ Gói không hợp lệ. Gửi /nap 20k hoặc /nap 100k")
        return
    pack = args[1]
    payment_url = f"{BANK_API_URL}?user={e.sender_id}&amount={pack}&key={BANK_API_KEY}"
    await e.respond(f"💳 Thanh toán gói {pack} tại link:\n{payment_url}\nSau khi thanh toán hãy bấm /check để cập nhật.")

@admin.on(events.NewMessage(pattern="/check"))
async def check_payment(e):
    user_id = e.sender_id
    # TODO: gọi API bank thực sự
    paid_pack = "20k" # giả lập
    duration = PACKS[paid_pack]

    if user_id in USERS:
        USERS[user_id]["expire"] += duration
        save_users()
        await e.respond(f"✅ Thanh toán thành công! Thời gian sử dụng còn {get_remaining_days(user_id)} ngày.")
    else:
        await e.respond("❌ Bạn chưa đăng nhập SESSION acc.")

# ================== GRAB HỘP USER ==================
async def grab_loop(user_id):
    user = USERS[user_id]
    client = TelegramClient(StringSession(user["session"]), API_ID, API_HASH)
    await client.connect()

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if datetime.utcnow() > user["expire"]:
            return
        if not ev.reply_markup: return

        btn = next(
            (b for r in ev.reply_markup.rows for b in r.buttons
             if any(x in b.text.lower() for x in ["đập","hộp","mở"])),
            None
        )
        if not btn:
            return

        try:
            await asyncio.sleep(random.uniform(0.5,1.2))
            await ev.click()
            await asyncio.sleep(1.2)

            msg = await client.get_messages(BOT_GAME, limit=1)
            if msg and msg[0].message:
                matches = re.findall(r"code.*?:\s*([A-Z0-9]+)", msg[0].message, re.I)
                for code in matches:
                    if code != user.get("last_code"):
                        user["last_code"] = code
                        store_code_to_bot(user_id, user["acc_name"], code)
                        await send_code_to_user(user_id, user["acc_name"], code)
        except Exception as ex:
            print(f"❌ Lỗi grab acc {user['acc_name']}: {ex}")

# ================== KHỞI ĐỘNG GRAB TẤT CẢ USER ==================
async def start_grab_users():
    load_users()
    load_bot_codes()
    for user_id in USERS:
        asyncio.create_task(grab_loop(user_id))

# ================== MAIN ==================
async def main():
    await admin.start(bot_token=BOT_TOKEN)
    await start_grab_users()
    await admin.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio, json, random, re, os
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ===== CONFIG =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8003350771:AAG2dlCVCxuSXJRgr4bBAyyyIW63kYuNA2M"
BOT_GAME = "xocdia88_bot_uytin_bot"
ADMINS = [7816353760]  # user_id admin

USERS_FILE = "users.json"
BOT_CODES_FILE = "bot_codes.json"

PACKS = {
    "20k": timedelta(days=7),
    "100k": timedelta(days=30)
}

# ===== STATE =====
USERS = {}        # user_id -> {"expire": datetime, "session": str, "acc_name": str, "last_code": str}
BOT_CODES = []    # kho code trung tâm

# ===== HELPER =====
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

def save_codes():
    with open(BOT_CODES_FILE,"w") as f:
        json.dump({"codes": BOT_CODES}, f, indent=2)

def has_access(user_id):
    return user_id in USERS and USERS[user_id]["expire"] > datetime.utcnow()

def remaining_days(user_id):
    if not has_access(user_id): return 0
    return max((USERS[user_id]["expire"] - datetime.utcnow()).days,0)

def store_code(user_id, acc_name, code):
    BOT_CODES.append({
        "code": code,
        "user_id": user_id,
        "acc_name": acc_name,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_codes()

def stats_codes():
    today = datetime.utcnow().date()
    this_week = today - timedelta(days=today.weekday())
    this_month = today.replace(day=1)

    count_today = sum(1 for c in BOT_CODES if datetime.strptime(c["time"],"%Y-%m-%d %H:%M:%S").date() == today)
    count_week = sum(1 for c in BOT_CODES if datetime.strptime(c["time"],"%Y-%m-%d %H:%M:%S").date() >= this_week)
    count_month = sum(1 for c in BOT_CODES if datetime.strptime(c["time"],"%Y-%m-%d %H:%M:%S").date() >= this_month)

    return f"📊 Thống kê code\n🎁 Hôm nay: {count_today}\n🎁 Tuần này: {count_week}\n🎁 Tháng này: {count_month}\n🎁 Tổng: {len(BOT_CODES)}"

# ===== MENU =====
def admin_menu():
    return [
        [Button.inline("📦 Danh sách user", b"list_user")],
        [Button.inline("📄 Kho code", b"list_code")],
        [Button.inline("📊 Thống kê code", b"stat_code")],
        [Button.inline("♻️ Restart", b"restart")]
    ]

def user_menu(user_id):
    days = remaining_days(user_id)
    return [
        [Button.inline(f"🎁 Xem code ({days} ngày còn lại)", b"view_code")],
        [Button.inline("💳 Nạp tiền", b"nap")],
        [Button.inline("📝 Nhập SESSION", b"login")]
    ]

# ===== BOT =====
bot = TelegramClient("bot_business", API_ID, API_HASH)

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    sender = event.sender_id
    if sender in ADMINS:
        await event.respond("🤖 MENU ADMIN", buttons=admin_menu())
    else:
        await event.respond("🤖 MENU USER", buttons=user_menu(sender))

# ===== LOGIN THỦ CÔNG =====
@bot.on(events.NewMessage(pattern="/login"))
async def login_handler(event):
    sender = event.sender_id
    args = event.text.split(" ",1)
    if len(args)<2:
        await event.respond("❌ Vui lòng gửi SESSION sau /login SESSION_STRING")
        return
    session_str = args[1].strip()
    try:
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()
        me = await client.get_me()
        USERS[sender] = {
            "expire": datetime.utcnow(),
            "session": session_str,
            "acc_name": me.first_name,
            "last_code": ""
        }
        save_users()
        asyncio.create_task(grab_loop(sender))
        await event.respond(f"✅ Kích hoạt thành công acc {me.first_name}. Hãy nạp tiền để sử dụng bot.")
    except:
        await event.respond("❌ SESSION không hợp lệ")

# ===== NẠP TIỀN (FAKE DEMO) =====
@bot.on(events.NewMessage(pattern="/nap"))
async def nap_handler(event):
    sender = event.sender_id
    args = event.text.split(" ",1)
    if len(args)<2 or args[1] not in PACKS:
        await event.respond("❌ Gói không hợp lệ. Gửi /nap 20k hoặc /nap 100k")
        return
    pack = args[1]
    duration = PACKS[pack]
    if sender in USERS:
        USERS[sender]["expire"] += duration
        save_users()
        await event.respond(f"✅ Thanh toán gói {pack} thành công! Thời gian sử dụng còn {remaining_days(sender)} ngày.")
    else:
        await event.respond("❌ Bạn chưa đăng nhập SESSION acc.")

# ===== GRAB HỘP USER =====
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
                        store_code(user_id, user["acc_name"], code)
                        await bot.send_message(user_id, f"🎁 CODE MỚI\nAcc: {user['acc_name']}\nCode: `{code}`")
        except Exception as ex:
            print(f"❌ Lỗi grab acc {user['acc_name']}: {ex}")

# ===== CALLBACK NÚT =====
@bot.on(events.CallbackQuery)
async def callback(event):
    sender = event.sender_id
    data = event.data.decode("utf-8")

    # === Admin only ===
    if data in ["list_user","list_code","stat_code","restart"] and sender not in ADMINS:
        await event.answer("❌ Bạn không có quyền", alert=True)
        return

    # Admin
    if data == "list_user":
        txt = "📦 DANH SÁCH USER\n"
        for u in USERS.values():
            txt += f"- {u['acc_name']} | Hạn: {u['expire']} | Ngày còn lại: {remaining_days(sender)}\n"
        await event.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])
    elif data == "list_code":
        txt = "📄 KHO CODE BOT\n"
        for c in BOT_CODES[-20:]:
            txt += f"- `{c['code']}` | {c['acc_name']} | {c['time']}\n"
        await event.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])
    elif data == "stat_code":
        txt = stats_codes()
        await event.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])
    elif data == "restart":
        await event.edit("♻️ Restart...")
        os._exit(0)

    # User
    elif data == "view_code":
        user_codes = [c for c in BOT_CODES if c["user_id"]==sender]
        if not user_codes:
            await event.answer("❌ Chưa có code nào", alert=True)
        else:
            txt = "🎁 CODE MỚI NHẤT\n"
            for c in user_codes[-5:]:
                txt += f"- `{c['code']}` | {c['time']}\n"
            await event.answer(txt, alert=True)
    elif data == "nap":
        await event.answer("💳 Nạp tiền: gửi /nap 20k hoặc /nap 100k", alert=True)
    elif data == "login":
        await event.answer("📝 Nhập SESSION bằng /login SESSION_STRING", alert=True)
    elif data == "back":
        if sender in ADMINS:
            await event.edit("🤖 MENU ADMIN", buttons=admin_menu())
        else:
            await event.edit("🤖 MENU USER", buttons=user_menu(sender))

# ===== ALERT USER SẮP HẾT HẠN =====
async def alert_expire_users():
    while True:
        for user_id, u in USERS.items():
            days_left = remaining_days(user_id)
            if 0 < days_left <= 2:
                try:
                    await bot.send_message(user_id,
                        f"⚠️ Hạn sử dụng của bạn sắp hết ({days_left} ngày còn lại), vui lòng nạp tiền để tiếp tục sử dụng bot.")
                except:
                    pass
        await asyncio.sleep(3600)  # mỗi 1h

# ===== BACKUP TỰ ĐỘNG =====
async def auto_backup():
    while True:
        try:
            with open("users_backup.json","w") as f:
                json.dump({str(k):{"expire":v["expire"].isoformat(),
                                   "session":v["session"],
                                   "acc_name":v["acc_name"],
                                   "last_code":v.get("last_code","")} for k,v in USERS.items()}, f, indent=2)
            with open("bot_codes_backup.json","w") as f:
                json.dump({"codes": BOT_CODES}, f, indent=2)
            print("💾 Backup USERS + BOT_CODES thành công")
        except Exception as e:
            print("❌ Lỗi backup:", e)
        await asyncio.sleep(21600)  # 6h

# ===== START GRAB TẤT CẢ USER =====
async def start_grab_users():
    load_users()
    for user_id in USERS:
        asyncio.create_task(grab_loop(user_id))

# ===== MAIN =====
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await start_grab_users()
    asyncio.create_task(alert_expire_users())
    asyncio.create_task(auto_backup())
    print("Bot kinh doanh nâng cao chạy thành công!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

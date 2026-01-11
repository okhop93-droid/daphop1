import asyncio, json, random, re, os
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from binascii import Error as BinAsciiError

# ===== CONFIG =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8003350771:AAG2dlCVCxuSXJRgr4bBAyyyIW63kYuNA2M"
BOT_GAME = "xocdia88_bot_uytin_bot"
ADMINS = [7816353760]  # ID admin

USERS_FILE = "users.json"
CODES_FILE = "bot_codes.json"

PACKS = {
    "20k": timedelta(days=7),
    "100k": timedelta(days=30)
}

# ===== STATE =====
USERS = {}   # user_id -> data
CODES = []   # kho code

# ===== LOAD / SAVE =====
def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump({str(k):{
            "expire": v["expire"].isoformat(),
            "session": v["session"],
            "acc": v["acc"],
            "last_code": v.get("last_code","")
        } for k,v in USERS.items()}, f, indent=2)

def load_users():
    global USERS
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            data = json.load(f)
            for uid, v in data.items():
                try:
                    USERS[int(uid)] = {
                        "expire": datetime.fromisoformat(v["expire"]),
                        "session": v["session"],
                        "acc": v["acc"],
                        "last_code": v.get("last_code","")
                    }
                except Exception as e:
                    print(f"❌ Lỗi load user {uid}: {e}")

def save_codes():
    with open(CODES_FILE,"w") as f:
        json.dump(CODES, f, indent=2)

# ===== HELPER =====
def remain(uid):
    if uid not in USERS: return 0
    return max((USERS[uid]["expire"] - datetime.utcnow()).days, 0)

def has_active(uid):
    return uid in USERS and USERS[uid]["expire"] > datetime.utcnow()

# ===== BOT =====
bot = TelegramClient("biz_bot", API_ID, API_HASH)

# ===== MENUS =====
def admin_menu():
    return [
        [Button.inline("📦 User", b"admin_users")],
        [Button.inline("📄 Kho code", b"admin_codes")],
        [Button.inline("📊 Thống kê", b"admin_stat")],
        [Button.inline("♻️ Restart", b"restart")]
    ]

def user_menu(uid):
    return [
        [Button.inline("➕ Nạp acc (SESSION)", b"add_acc")],
        [Button.inline("💳 Nạp tiền", b"nap")],
        [Button.inline(f"🎁 Code của tôi ({remain(uid)} ngày)", b"my_code")]
    ]

# ===== START =====
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    if e.sender_id in ADMINS:
        await e.respond("🤖 MENU ADMIN", buttons=admin_menu())
    else:
        await e.respond("🤖 MENU USER", buttons=user_menu(e.sender_id))

# ===== CALLBACK =====
@bot.on(events.CallbackQuery)
async def cb(e):
    uid = e.sender_id
    data = e.data.decode()

    # ===== USER =====
    if data == "add_acc":
        await e.answer("Gửi: /add SESSION_STRING", alert=True)

    elif data == "nap":
        await e.answer("Nạp: /nap 20k hoặc /nap 100k", alert=True)

    elif data == "my_code":
        user_codes = [c for c in CODES if c["uid"] == uid]
        if not user_codes:
            await e.answer("Chưa có code", alert=True)
        else:
            txt = "🎁 CODE CỦA BẠN\n"
            for c in user_codes[-5:]:
                txt += f"- `{c['code']}` | {c['time']}\n"
            await e.answer(txt, alert=True)

    # ===== ADMIN =====
    elif uid in ADMINS:
        if data == "admin_users":
            txt = "📦 USER\n"
            for u in USERS.values():
                txt += f"- {u['acc']} | {u['expire']}\n"
            if e.message.text != txt:
                await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

        elif data == "admin_codes":
            txt = "📄 KHO CODE\n"
            for c in CODES[-20:]:
                txt += f"- `{c['code']}` | {c['acc']} | {c['time']}\n"
            if e.message.text != txt:
                await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

        elif data == "admin_stat":
            txt = f"📊 THỐNG KÊ\n👤 User: {len(USERS)}\n🎁 Code: {len(CODES)}"
            if e.message.text != txt:
                await e.edit(txt, buttons=[[Button.inline("⬅️ Back", b"back")]])

        elif data == "restart":
            os._exit(0)

    elif data == "back":
        if uid in ADMINS:
            await e.edit("🤖 MENU ADMIN", buttons=admin_menu())
        else:
            await e.edit("🤖 MENU USER", buttons=user_menu(uid))

# ===== ADD ACC =====
@bot.on(events.NewMessage(pattern="/add "))
async def add_acc(e):
    uid = e.sender_id
    sess = e.text.split(" ",1)[1].strip()

    try:
        client = TelegramClient(StringSession(sess), API_ID, API_HASH)
        await client.connect()
        me = await client.get_me()
        await client.disconnect()

        USERS[uid] = {
            "session": sess,
            "acc": me.first_name,
            "expire": datetime.utcnow(),
            "last_code": ""
        }
        save_users()
        asyncio.create_task(grab_loop(uid))
        await e.respond(f"✅ Nạp acc `{me.first_name}` thành công")
    except (BinAsciiError, ValueError):
        await e.respond("❌ SESSION sai hoặc không hợp lệ")
    except Exception as ex:
        await e.respond(f"❌ Lỗi khác: {ex}")

# ===== NẠP TIỀN =====
@bot.on(events.NewMessage(pattern="/nap "))
async def nap(e):
    uid = e.sender_id
    pack = e.text.split(" ",1)[1].strip()
    if pack not in PACKS:
        await e.respond("Sai gói")
        return
    if uid not in USERS:
        await e.respond("❌ Bạn chưa nạp acc")
        return
    USERS[uid]["expire"] += PACKS[pack]
    save_users()
    await e.respond(f"✅ Đã cộng {PACKS[pack].days} ngày")

# ===== GRAB CODE =====
async def grab_loop(uid):
    u = USERS[uid]
    try:
        client = TelegramClient(StringSession(u["session"]), API_ID, API_HASH)
        await client.connect()
    except:
        print(f"❌ User {uid} session lỗi, bỏ qua")
        return

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not has_active(uid): return
        if not ev.reply_markup: return

        btn = next((b for r in ev.reply_markup.rows for b in r.buttons
                    if "đập" in b.text.lower()), None)
        if not btn: return

        await asyncio.sleep(random.uniform(0.5,1))
        await ev.click()
        await asyncio.sleep(1)

        msg = await client.get_messages(BOT_GAME, limit=1)
        if msg and msg[0].message:
            m = re.search(r"code.*?:\s*([A-Z0-9]+)", msg[0].message, re.I)
            if m:
                code = m.group(1)
                if code != u.get("last_code",""):
                    u["last_code"] = code
                    CODES.append({
                        "uid": uid,
                        "acc": u["acc"],
                        "code": code,
                        "time": datetime.utcnow().strftime("%d/%m %H:%M")
                    })
                    save_codes()
                    await bot.send_message(uid, f"🎁 CODE: `{code}`")

# ===== MAIN =====
async def main():
    load_users()
    await bot.start(bot_token=BOT_TOKEN)
    for uid in USERS:
        asyncio.create_task(grab_loop(uid))
    print("BOT CHẠY OK")
    await bot.run_until_disconnected()

asyncio.run(main())    try:
        client = TelegramClient(StringSession(sess), API_ID, API_HASH)
        await client.connect()
        me = await client.get_me()

        USERS[uid] = {
            "session": sess,
            "acc": me.first_name,
            "expire": datetime.utcnow(),
            "last_code": ""
        }
        save_users()
        asyncio.create_task(grab_loop(uid))
        await e.respond(f"✅ Nạp acc `{me.first_name}` thành công")
    except:
        await e.respond("❌ SESSION sai")

# ===== NẠP TIỀN =====
@bot.on(events.NewMessage(pattern="/nap "))
async def nap(e):
    uid = e.sender_id
    pack = e.text.split(" ",1)[1]
    if pack not in PACKS:
        await e.respond("Sai gói")
        return
    USERS[uid]["expire"] += PACKS[pack]
    save_users()
    await e.respond(f"✅ Đã cộng {PACKS[pack].days} ngày")

# ===== GRAB CODE =====
async def grab_loop(uid):
    u = USERS[uid]
    client = TelegramClient(StringSession(u["session"]), API_ID, API_HASH)
    await client.connect()

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not has_active(uid): return
        if not ev.reply_markup: return

        btn = next((b for r in ev.reply_markup.rows for b in r.buttons
                    if "đập" in b.text.lower()), None)
        if not btn: return

        await asyncio.sleep(random.uniform(0.5,1))
        await ev.click()
        await asyncio.sleep(1)

        msg = await client.get_messages(BOT_GAME, limit=1)
        if msg and msg[0].message:
            m = re.search(r"code.*?:\s*([A-Z0-9]+)", msg[0].message, re.I)
            if m:
                code = m.group(1)
                if code != u["last_code"]:
                    u["last_code"] = code
                    CODES.append({
                        "uid": uid,
                        "acc": u["acc"],
                        "code": code,
                        "time": datetime.utcnow().strftime("%d/%m %H:%M")
                    })
                    save_codes()
                    await bot.send_message(uid, f"🎁 CODE: `{code}`")

# ===== MAIN =====
async def main():
    load_users()
    await bot.start(bot_token=BOT_TOKEN)
    for uid in USERS:
        asyncio.create_task(grab_loop(uid))
    print("BOT CHẠY OK")
    await bot.run_until_disconnected()

asyncio.run(main())

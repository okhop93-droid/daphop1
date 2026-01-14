import asyncio, random, re, os, json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events, Button, functions
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ===== CẤU HÌNH =====
API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "13602653:8EoNH1vZ2lVDxlC1UIgXP1X0ImqSBkBo8Ei7nCxz"
BOT_GAME = "xocdia88_bot_uytin_bot"
SESSION_FILE = "sessions.txt"
CODES_FILE = "codes.json"
LOG_GROUP = -1002984339626  # Đảm bảo ID này là chính xác

# ===== KEEP ALIVE =====
app = Flask(__name__)
@app.route("/")
def home(): return "BOT ONLINE"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()

# ===== BIẾN HỆ THỐNG =====
ACCS = {}           
TOTAL_CODE = 0
CODES_DB = {}       
PENDING_LOGIN = {}  

# ===== QUẢN LÝ FILE =====
def save_session(sess):
    with open(SESSION_FILE, "a+") as f:
        f.seek(0)
        content = f.read()
        if sess not in content:
            f.write(sess + "\n")

def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(CODES_DB, f, indent=2)

# ===== LUỒNG ĐẬP HỘP (TỰ GỬI VÀO NHÓM) =====
async def grab_loop(acc):
    global TOTAL_CODE
    client = acc["client"] 

    @client.on(events.NewMessage(chats=BOT_GAME))
    async def handler(ev):
        if not ev.reply_markup: return
        btn = next((b for r in ev.reply_markup.rows for b in r.buttons 
                    if any(x in b.text.lower() for x in ["đập","hộp"])), None)
        if not btn: return

        try:
            # Click đập hộp với delay ngẫu nhiên cực thấp
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await ev.click()
            
            # Đợi Bot Game trả lời
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
                        
                        # --- TÀI KHOẢN CLONE TỰ GỬI MÃ VÀO NHÓM ---
                        msg_nhom = (f"🎁 **LỤM ĐƯỢC QUÀ!**\n"
                                   f"━━━━━━━━━━━━━━━━━━\n"
                                   f"👤 Acc {acc['stt']}: **{acc['name']}**\n"
                                   f"🗝 Code: `{gift_code}`\n"
                                   f"⏰ Lúc: {datetime.now().strftime('%H:%M:%S')}")
                        
                        try:
                            # Thử gửi thẳng vào nhóm
                            await client.send_message(LOG_GROUP, msg_nhom)
                        except Exception:
                            # Nếu gửi lỗi, thử tự Join nhóm rồi gửi lại
                            try:
                                await client(functions.channels.JoinChannelRequest(channel=LOG_GROUP))
                                await asyncio.sleep(1)
                                await client.send_message(LOG_GROUP, msg_nhom)
                            except Exception as e:
                                # Nếu vẫn lỗi thì báo về Admin để kiểm tra
                                await admin.send_message(7816353760, f"⚠️ Acc {acc['stt']} lỗi gửi nhóm: {e}")

                        # Lưu database
                        CODES_DB[str(acc["id"])] = gift_code
                        save_codes()
        except Exception as e:
            print(f"❌ Lỗi TK {acc['stt']}: {e}")

# ===== ADMIN BOT =====
admin = TelegramClient("admin_bot", API_ID, API_HASH)

def menu():
    return [
        [Button.inline("📦 Danh Sách Acc", b"acc"), Button.inline("📊 Thống kê", b"stat")],
        [Button.inline("➕ Nạp Acc", b"add"), Button.inline("🧪 Test Acc", b"test")]
    ]

@admin.on(events.NewMessage(pattern="/start"))
async def start(e):
    if e.sender_id != 7816353760: return
    await e.respond(f"🤖 **HỆ THỐNG ĐẬP HỘP**\n📦 Đang chạy: `{len(ACCS)}` Acc\n🎁 Tổng mã: `{TOTAL_CODE}`", buttons=menu())

@admin.on(events.CallbackQuery)
async def cb(e):
    if e.data == b"acc":
        txt = "📑 **DANH SÁCH TÀI KHOẢN:**\n"
        for a in ACCS.values():
            txt += f"• **STT {a['stt']}**: {a['name']} ({a['status']})\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])
    elif e.data == b"stat":
        txt = f"📊 **THỐNG KÊ CHI TIẾT**\n━━━━━━━━━━━━━━\n🎁 Tổng mã húp: `{TOTAL_CODE}`\n\n"
        for a in ACCS.values():
            last_code = a.get('last') or "Chưa có"
            txt += f"• **TK {a['stt']}**: `{last_code}`\n"
        await e.edit(txt, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])
    elif e.data == b"add":
        await e.edit("➕ **NẠP ACC MỚI**\nSử dụng lệnh: `/login SĐT` (VD: `/login 84123...`)", buttons=[[Button.inline("⬅️ Quay lại", b"back")]])
    elif e.data == b"test":
        await e.edit("🧪 **ĐANG KIỂM TRA...**")
        res = "🧪 **KẾT QUẢ KIỂM TRA:**\n"
        for a in ACCS.values():
            try:
                if await a['client'].is_user_authorized(): a['status'] = "ONLINE 🟢"
                else: a['status'] = "OFFLINE 🔴"
            except: a['status'] = "LỖI ⚠️"
            res += f"• **TK {a['stt']}**: {a['status']}\n"
        await e.edit(res, buttons=[[Button.inline("⬅️ Quay lại", b"back")]])
    elif e.data == b"back":
        await e.edit(f"🤖 **MENU QUẢN LÝ**", buttons=menu())

# ===== XỬ LÝ NẠP ACC =====
@admin.on(events.NewMessage(pattern="/login"))
async def login_handler(e):
    try:
        phone = "".join(filter(str.isdigit, e.text.split(" ", 1)[1]))
        c = TelegramClient(StringSession(), API_ID, API_HASH)
        await c.connect()
        sent = await c.send_code_request(phone)
        PENDING_LOGIN[e.sender_id] = {"c": c, "p": phone, "h": sent.phone_code_hash}
        await e.respond(f"📩 OTP gửi tới `+{phone}`. Nhập `/otp <mã>`")
    except: await e.respond("❌ Sai định dạng /login")

@admin.on(events.NewMessage(pattern="/otp"))
async def otp_handler(e):
    data = PENDING_LOGIN.get(e.sender_id)
    if not data: return
    try:
        code = "".join(filter(str.isdigit, e.text))
        await data["c"].sign_in(data["p"], code, phone_code_hash=data["h"])
        save_session(data["c"].session.save())
        me = await data["c"].get_me()
        
        new_stt = len(ACCS) + 1
        ACCS[me.id] = {
            "id": me.id, "stt": new_stt, "client": data["c"],
            "name": me.first_name, "status": "ONLINE 🟢", "last": None
        }
        asyncio.create_task(grab_loop(ACCS[me.id]))
        await e.respond(f"✅ **Thành công!** TK {new_stt} ({me.first_name}) đang chạy.")
        del PENDING_LOGIN[e.sender_id]
    except Exception as ex: await e.respond(f"❌ Lỗi: {ex}")

async def main():
    if os.path.exists(CODES_FILE):
        global CODES_DB, TOTAL_CODE
        with open(CODES_FILE) as f: 
            try:
                CODES_DB = json.load(f)
                TOTAL_CODE = len(CODES_DB)
            except: pass

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
                        ACCS[me.id] = {
                            "id": me.id, "stt": i, "client": c,
                            "name": me.first_name, "status": "ONLINE 🟢",
                            "last": None
                        }
                        asyncio.create_task(grab_loop(ACCS[me.id]))
                        print(f"✅ Đã load Acc {i}: {me.first_name}")
                except: continue
    await admin.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
                

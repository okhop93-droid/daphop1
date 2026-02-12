import asyncio, re, logging, random, os
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from supabase import create_client, Client
from quart import Quart, request, jsonify

# ================= CẤU HÌNH =================
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"

STK_MSB = "96886693002613" 
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot" 
PRICE_PER_DAY = 20000 
ADMIN_ID = 7816353760 
MAX_CLONES = 80 # Giới hạn 80 acc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)
active_tasks = {} 

# ================= HELPERS =================
def db_get_user(uid):
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            now_iso = datetime.now(timezone.utc).isoformat()
            supabase.table("users").insert({"user_id": uid, "balance": 0, "bot_expiry": now_iso}).execute()
            return {"user_id": uid, "balance": 0, "bot_expiry": now_iso}
        return res.data[0]
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return None

# ================= WORKER LOOP (ANTI-NGỎM) =================
async def run_clone_worker(session_str, phone, owner_id):
    task_key = f"{owner_id}_{phone}"
    if not session_str: return
    
    # Cấu hình client với khả năng tự kết nối lại cực mạnh
    client = TelegramClient(
        StringSession(session_str), 
        API_ID, API_HASH,
        connection_retries=None, # Thử lại vô hạn lần
        retry_delay=5,           # Cách 5s thử lại
        auto_reconnect=True
    )
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logging.warning(f"Acc {phone} hết hạn session.")
            return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            try:
                user = db_get_user(owner_id)
                exp = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
                if exp < datetime.now(timezone.utc):
                    await client.disconnect()
                    return
            except: pass

            if ev.reply_markup:
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.3, 0.8)) # Tốc độ đập
                    try:
                        await ev.click()
                        await asyncio.sleep(1.5)
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        if msgs and "là:" in msgs[0].message:
                            code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                            supabase.table("history").insert({"user_id": owner_id, "phone": phone, "code": code}).execute()
                            await bot.send_message(owner_id, f"🎊 **MÃ TRÚNG:** `{code}`\n📱 Acc: `{phone}`")
                    except Exception as e:
                        logging.error(f"Click Error: {e}")
        
        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Worker {phone} crashed: {e}")
    finally:
        if task_key in active_tasks: del active_tasks[task_key]
        if client.is_connected(): await client.disconnect()

# ================= GIAO DIỆN (BEAUTIFUL MENU) =================
def get_main_menu(uid):
    user = db_get_user(uid)
    exp_dt = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
    is_active = exp_dt > datetime.now(timezone.utc)
    
    status_icon = "🟢" if is_active else "🔴"
    status_text = "ĐANG HOẠT ĐỘNG" if is_active else "HẾT HẠN/CHƯA THUÊ"
    exp_str = exp_dt.strftime('%H:%M - %d/%m/%Y')

    txt = (
        f"        ✨ **CLONE VIP SYSTEM** ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **ID:** `{uid}`\n"
        f"💰 **Số dư:** `{user['balance']:,} VNĐ`\n"
        f"⏱ **Trạng thái:** {status_icon} `{status_text}`\n"
        f"📅 **Hết hạn:** `{exp_str}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 *Lưu ý: Thuê bot để kích hoạt các acc clone của bạn.*"
    )
    btns = [
        [TButton.inline("⚡ THUÊ / GIA HẠN BOT (20K)", b"rent_bot")],
        [TButton.inline("➕ THÊM ACC", b"add_clone"), TButton.inline("📱 QUẢN LÝ ACC", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("📜 LỊCH SỬ MÃ", b"history")],
        [TButton.url("🤝 LIÊN HỆ ADMIN", "https://t.me/nth_dev")]
    ]
    if int(uid) == ADMIN_ID: btns.append([TButton.inline("🛠 QUẢN TRỊ VIÊN", b"adm_main")])
    return txt, btns

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    txt, btns = get_main_menu(e.sender_id)
    await e.respond(txt, buttons=btns)

# ================= CALLBACK HANDLER =================
@bot.on(events.CallbackQuery)
async def callback_handler(e):
    uid, data = e.sender_id, e.data.decode()
    
    if data == "back":
        txt, btns = get_main_menu(uid)
        await e.edit(txt, buttons=btns)

    elif data == "rent_bot":
        user = db_get_user(uid)
        if user['balance'] < PRICE_PER_DAY:
            return await e.answer("❌ Số dư không đủ 20,000đ!", alert=True)
        
        old_exp = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
        new_exp = max(old_exp, datetime.now(timezone.utc)) + timedelta(days=1)
        
        supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY, "bot_expiry": new_exp.isoformat()}).eq("user_id", uid).execute()
        await e.answer("✅ Kích hoạt thành công!", alert=True)
        
        # Start clones
        clones = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        for c in clones.data:
            t_key = f"{uid}_{c['phone']}"
            if t_key not in active_tasks:
                active_tasks[t_key] = asyncio.create_task(run_clone_worker(c['session'], c['phone'], uid))
        
        txt, btns = get_main_menu(uid)
        await e.edit(txt, buttons=btns)

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        count = len(res.data)
        msg = f"📱 **DANH SÁCH ACC ({count}/{MAX_CLONES}):**\n\n"
        btns = []
        for c in res.data:
            msg += f"✅ `{c['phone']}`\n"
            btns.append([TButton.inline(f"🗑 Xóa {c['phone']}", f"del_{c['id']}")])
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(msg, buttons=btns)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("🗑 Đã xóa!", alert=True)
        await callback_handler(e)

    elif data == "dep_menu":
        btns = [[TButton.inline(f"💵 {a:,} VNĐ", f"p_{a}")] for a in [20000, 50000, 100000, 500000]]
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit("🏦 **CHỌN MỆNH GIÁ NẠP:**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        txt = (
            f"📥 **THÔNG TIN CHUYỂN KHOẢN**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Ngân hàng: **MSB**\n"
            f"🔢 STK: `{STK_MSB}`\n"
            f"💰 Số tiền: `{int(amt):,} VNĐ`\n"
            f"📝 Nội dung: `NAP {uid}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Lưu ý: Hệ thống nạp tự động 24/7.*"
        )
        await e.edit(txt, buttons=[[TButton.url("📲 MỞ QR CODE", qr)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

    elif data == "adm_main" and int(uid) == ADMIN_ID:
        u_all = supabase.table("users").select("balance").execute().data
        cl_cnt = supabase.table("my_clones").select("id", count="exact").execute().count
        txt = f"🛠 **ADMIN PANEL**\n\n👥 Tổng User: `{len(u_all)}`\n📱 Tổng Clone: `{cl_cnt}`"
        btns = [[TButton.inline("➕ CỘNG TIỀN", b"adm_add_bal")], [TButton.inline("📢 THÔNG BÁO", b"adm_bc")], [TButton.inline("🔙", b"back")]]
        await e.edit(txt, buttons=btns)

# ================= THÊM ACC (GIỚI HẠN 80) =================
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_conv(e):
    uid = e.sender_id
    # Check giới hạn 80
    res = supabase.table("my_clones").select("id", count="exact").eq("owner_id", uid).execute()
    if res.count >= MAX_CLONES:
        return await e.answer(f"❌ Bạn đã đạt giới hạn tối đa {MAX_CLONES} acc!", alert=True)

    async with bot.conversation(uid, timeout=300) as conv:
        try:
            p_msg = await conv.send_message("📞 **Vui lòng nhập SĐT (+84...):**")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            
            new_cl = TelegramClient(StringSession(), API_ID, API_HASH)
            await new_cl.connect()
            await new_cl.send_code_request(phone)
            
            await conv.send_message("📩 **Nhập mã OTP vừa gửi về Telegram:**")
            otp = (await conv.get_response()).text.strip()
            
            try:
                await new_cl.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **Nhập mật khẩu 2FA của bạn:**")
                await new_cl.sign_in(password=(await conv.get_response()).text.strip())
            
            sess = new_cl.session.save()
            supabase.table("my_clones").insert({"owner_id": uid, "phone": phone, "session": sess}).execute()
            
            user = db_get_user(uid)
            if datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00')) > datetime.now(timezone.utc):
                active_tasks[f"{uid}_{phone}"] = asyncio.create_task(run_clone_worker(sess, phone, uid))
                await conv.send_message(f"✅ Đã thêm `{phone}`. Bot đang chạy!")
            else:
                await conv.send_message(f"✅ Đã thêm `{phone}`. Hãy thuê bot để kích hoạt.")
            await new_cl.disconnect() 
        except Exception as err:
            await conv.send_message(f"❌ Thất bại: {err}")

# ================= WEBHOOK & MAIN =================
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        u = db_get_user(uid)
        if u:
            supabase.table("users").update({"balance": u['balance'] + amt}).eq("user_id", uid).execute()
            bot.loop.create_task(bot.send_message(uid, f"✅ **NẠP TIỀN THÀNH CÔNG!**\n💰 +`{amt:,} VNĐ`\nCảm ơn bạn đã sử dụng dịch vụ!"))
    return jsonify({"ok": True}), 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    # Khởi động lại tất cả acc
    try:
        users = supabase.table("users").select("*").execute()
        user_expiry = {u['user_id']: datetime.fromisoformat(u['bot_expiry'].replace('Z', '+00:00')) for u in users.data}
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            expiry = user_expiry.get(c['owner_id'])
            if expiry and expiry > datetime.now(timezone.utc):
                active_tasks[f"{c['owner_id']}_{c['phone']}"] = asyncio.create_task(run_clone_worker(c['session'], c['phone'], c['owner_id']))
    except: pass
    print(">>> BOT IS RUNNING <<<")
    await asyncio.gather(bot.run_until_disconnected(), app.run_task(host='0.0.0.0', port=10000))

if __name__ == '__main__':
    asyncio.run(main())
            

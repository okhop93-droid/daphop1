import asyncio, re, logging, random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from supabase import create_client, Client
from quart import Quart, request, jsonify

# ================= CẤU HÌNH (GIỮ NGUYÊN) =================
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"

STK_MSB = "96886693002613" 
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot" 
PRICE_PER_DAY = 10000 
ADMIN_ID = 7816353760 

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)

# Quản lý các task đang chạy
active_tasks = {} 

# ================= HELPERS =================
def db_get_user(uid):
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
            return {"user_id": uid, "balance": 0}
        return res.data[0]
    except Exception:
        return {"user_id": uid, "balance": 0}

# ================= WORKER LOOP =================
async def run_clone_worker(session_str, phone, owner_id, clone_id):
    task_key = f"{owner_id}_{phone}"
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized(): return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            try:
                # Kiểm tra hạn thuê bot realtime
                res = supabase.table("my_clones").select("expiry").eq("id", clone_id).execute()
                if not res.data: 
                    await client.disconnect()
                    return
                
                exp = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
                if exp < datetime.now(timezone.utc):
                    await bot.send_message(owner_id, f"⚠️ **HẾT HẠN THUÊ:** Clone `{phone}` đã dừng. Hãy gia hạn để tiếp tục đập hộp!")
                    await client.disconnect()
                    return
            except: pass

            # Logic đập hộp tự động
            if ev.reply_markup:
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    try:
                        await ev.click()
                        await asyncio.sleep(2)
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        if msgs and "là:" in msgs[0].message:
                            code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                            supabase.table("history").insert({"user_id": owner_id, "phone": phone, "code": code}).execute()
                            await bot.send_message(owner_id, f"🎊 **MÃ TRÚNG:** `{code}`\n📱 Clone: `{phone}`")
                    except: pass

        await client.run_until_disconnected()
    except Exception: pass
    finally:
        if task_key in active_tasks: del active_tasks[task_key]
        if client.is_connected(): await client.disconnect()

# ================= MENU STYLING =================
def get_main_menu(uid):
    user = db_get_user(uid)
    txt = (
        f"🌟 **HỆ THỐNG QUẢN LÝ CLONE** 🌟\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 **ID:** `{uid}`\n"
        f"💰 **Số dư:** `{user['balance']:,} VNĐ`\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    btns = [
        [TButton.inline("➕ THÊM CLONE (MIỄN PHÍ)", b"add_clone")],
        [TButton.inline("📱 DANH SÁCH & THUÊ BOT", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("📜 LỊCH SỬ", b"history")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]
    if int(uid) == ADMIN_ID: btns.append([TButton.inline("🛠 ADMIN PANEL", b"adm_main")])
    return txt, btns

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    txt, btns = get_main_menu(e.sender_id)
    await e.respond(txt, buttons=btns)

# ================= CALLBACK HANDLER =================
@bot.on(events.CallbackQuery)
async def callback_handler(e):
    uid, data = e.sender_id, e.data.decode()
    try: await e.answer()
    except: pass

    if data == "back":
        txt, btns = get_main_menu(uid)
        await e.edit(txt, buttons=btns)

    elif data == "history":
        res = supabase.table("history").select("*").eq("user_id", uid).order("created_at", desc=True).limit(10).execute()
        msg = "📜 **LỊCH SỬ ĂN MÃ GẦN NHẤT:**\n\n"
        if res.data:
            for i in res.data: msg += f"✅ `{i['code']}` | 📱 {i['phone'][-4:]}\n"
        else: msg += "_Chưa có dữ liệu._"
        await e.edit(msg, buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.edit("❌ Bạn chưa có clone nào. Hãy thêm clone trước!", buttons=[[TButton.inline("🔙", b"back")]])
        
        btns = []
        for c in res.data:
            exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            status = "🔴 CHƯA THUÊ" if exp <= datetime.now(timezone.utc) else "🟢 ĐANG CHẠY"
            btns.append([TButton.inline(f"{status} | {c['phone']}", f"mng_{c['id']}")])
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit("📱 **DANH SÁCH CLONE:**\n\nBấm vào từng acc để thuê Bot đập hộp.", buttons=btns)

    elif data.startswith("mng_"):
        cid = data.split("_")[1]
        c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
        exp_dt = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
        exp_str = exp_dt.strftime('%H:%M %d/%m/%Y') if exp_dt > datetime.now(timezone.utc) else "Đã hết hạn/Chưa thuê"
        
        txt = f"⚙️ **CLONE:** `{c['phone']}`\n━━━━━━━━━━━━━\n⏳ Hạn thuê Bot: `{exp_str}`"
        btns = [[TButton.inline(f"⏳ THUÊ BOT 24H ({PRICE_PER_DAY:,}đ)", f"ren_{cid}")],
                [TButton.inline("🗑 XÓA CLONE", f"del_{cid}")],
                [TButton.inline("🔙 QUAY LẠI", b"list_clones")]]
        await e.edit(txt, buttons=btns)

    elif data.startswith("ren_"):
        cid = data.split("_")[1]
        user = db_get_user(uid)
        if user['balance'] < PRICE_PER_DAY: return await e.answer("❌ Số dư không đủ 10,000đ!", alert=True)
        
        c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
        old_exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
        # Nếu đã hết hạn thì tính từ hiện tại, nếu còn hạn thì cộng dồn
        new_exp = max(old_exp, datetime.now(timezone.utc)) + timedelta(days=1)
        
        supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", uid).execute()
        supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("id", cid).execute()
        
        await e.answer("✅ Thuê Bot thành công! Acc đã bắt đầu làm việc.", alert=True)
        
        # Kích hoạt acc chạy ngay lập tức
        task_key = f"{uid}_{c['phone']}"
        if task_key not in active_tasks:
            active_tasks[task_key] = asyncio.create_task(run_clone_worker(c['session'], c['phone'], uid, cid))
        await callback_handler(e)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("🗑 Đã xóa clone!", alert=True)
        await callback_handler(e)

    elif data == "dep_menu":
        btns = [[TButton.inline(f"💰 {a:,} VNĐ", f"p_{a}")] for a in [20000, 50000, 100000, 200000]]
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit("🏦 **NẠP TIỀN HỆ THỐNG:**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"📥 **THÔNG TIN NẠP:**\nSTK: `{STK_MSB}` (MSB)\nTiền: `{int(amt):,} VNĐ`\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 QUÉT MÃ QR", qr)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

    elif data == "adm_main" and int(uid) == ADMIN_ID:
        u_all = supabase.table("users").select("balance").execute().data
        cl_cnt = supabase.table("my_clones").select("id", count="exact").execute().count
        txt = f"🛠 **ADMIN PANEL**\nUsers: `{len(u_all)}` | Clones: `{cl_cnt}`\nTổng tiền: `{sum(u['balance'] for u in u_all):,} VNĐ`"
        btns = [[TButton.inline("➕ CỘNG TIỀN", b"adm_add_bal")], [TButton.inline("📢 THÔNG BÁO", b"adm_bc")], [TButton.inline("🔙", b"back")]]
        await e.edit(txt, buttons=btns)

    elif data == "adm_add_bal" and int(uid) == ADMIN_ID:
        async with bot.conversation(uid) as conv:
            await conv.send_message("👉 Nhập ID người dùng:")
            tid = (await conv.get_response()).text.strip()
            await conv.send_message("👉 Nhập số tiền:")
            amt = (await conv.get_response()).text.strip()
            if amt.isdigit():
                u = db_get_user(tid)
                supabase.table("users").update({"balance": u['balance'] + int(amt)}).eq("user_id", tid).execute()
                await conv.send_message("✅ Đã cộng tiền!")
                await bot.send_message(int(tid), f"🎉 Bạn được Admin cộng `{int(amt):,} VNĐ`!")

# ================= THÊM CLONE (MIỄN PHÍ) =================
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_conv(e):
    # Đã bỏ phần check số dư và trừ tiền ở đây
    async with bot.conversation(e.sender_id, timeout=300) as conv:
        try:
            await conv.send_message("📞 **Nhập SĐT Clone (+84...):**")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            new_cl = TelegramClient(StringSession(), API_ID, API_HASH)
            await new_cl.connect()
            await new_cl.send_code_request(phone)
            await conv.send_message("📩 **Nhập OTP:**")
            otp = (await conv.get_response()).text.strip()
            try: await new_cl.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **Nhập 2FA:**")
                await new_cl.sign_in(password=(await conv.get_response()).text.strip())
            
            # Mặc định khi thêm acc là HẾT HẠN (không có thời gian thuê)
            exp = datetime.now(timezone.utc).isoformat()
            
            # Lưu vào DB mà không trừ tiền
            res = supabase.table("my_clones").insert({
                "owner_id": e.sender_id, 
                "phone": phone, 
                "session": new_cl.session.save(), 
                "expiry": exp
            }).execute()
            
            # KHÔNG tạo task run_clone_worker ở đây vì chưa thuê bot
            await conv.send_message(f"✅ Đã thêm acc `{phone}` thành công!\n\n👉 Bây giờ hãy vào mục **Danh sách & Thuê Bot** để kích hoạt gói đập hộp.")
            await new_cl.disconnect() # Ngắt kết nối luôn để chờ gia hạn
        except Exception as err: await conv.send_message(f"❌ Lỗi: {err}")

# ================= WEBHOOK & MAIN =================
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        u = db_get_user(uid)
        supabase.table("users").update({"balance": u['balance'] + amt}).eq("user_id", uid).execute()
        bot.loop.create_task(bot.send_message(uid, f"✅ Nạp thành công +{amt:,}đ!"))
    return jsonify({"ok": True}), 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    # Chỉ khởi động lại những acc nào CÒN HẠN thuê bot
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            if datetime.fromisoformat(c['expiry'].replace('Z', '+00:00')) > datetime.now(timezone.utc):
                active_tasks[f"{c['owner_id']}_{c['phone']}"] = asyncio.create_task(run_clone_worker(c['session'], c['phone'], c['owner_id'], c['id']))
    except: pass
    await asyncio.gather(bot.run_until_disconnected(), app.run_task(host='0.0.0.0', port=10000))

if __name__ == '__main__':
    asyncio.run(main())
                            

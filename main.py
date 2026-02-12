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
PRICE_PER_DAY = 20000 
ADMIN_ID = 7816353760 

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)
active_tasks = {} 

# ================= HELPERS =================
def db_get_user(uid):
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            # Tạo user mới với mặc định chưa có hạn bot (expiry là hiện tại)
            now_iso = datetime.now(timezone.utc).isoformat()
            supabase.table("users").insert({"user_id": uid, "balance": 0, "bot_expiry": now_iso}).execute()
            return {"user_id": uid, "balance": 0, "bot_expiry": now_iso}
        return res.data[0]
    except Exception:
        return None

# ================= WORKER LOOP =================
async def run_clone_worker(session_str, phone, owner_id):
    task_key = f"{owner_id}_{phone}"
    if not session_str: return
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized(): return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            try:
                # Kiểm tra hạn dùng Bot của CHỦ SỞ HỮU (User)
                user = db_get_user(owner_id)
                exp = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
                if exp < datetime.now(timezone.utc):
                    await bot.send_message(owner_id, f"⚠️ **HẾT HẠN THUÊ BOT:** Các acc (bao gồm `{phone}`) đã dừng!")
                    await client.disconnect()
                    return
            except: pass

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
                            await bot.send_message(owner_id, f"🎊 **MÃ MỚI:** `{code}` | Acc: `{phone}`")
                    except: pass
        await client.run_until_disconnected()
    except: pass
    finally:
        if task_key in active_tasks: del active_tasks[task_key]
        if client.is_connected(): await client.disconnect()

# ================= MENU STYLING =================
def get_main_menu(uid):
    user = db_get_user(uid)
    exp_dt = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
    status = "🟢 ĐANG THUÊ" if exp_dt > datetime.now(timezone.utc) else "🔴 HẾT HẠN"
    exp_str = exp_dt.strftime('%H:%M %d/%m/%Y') if status == "🟢 ĐANG THUÊ" else "Chưa thuê"

    txt = (
        f"🌟 **HỆ THỐNG QUẢN LÝ BOT** 🌟\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Số dư:** `{user['balance']:,} VNĐ`\n"
        f"⏳ **Hạn Bot:** `{exp_str}` ({status})\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    btns = [
        [TButton.inline("⏳ THUÊ/GIA HẠN BOT (20K/NGÀY)", b"rent_bot")],
        [TButton.inline("➕ THÊM ACC (FREE)", b"add_clone"), TButton.inline("📱 D.SÁCH ACC", b"list_clones")],
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

    elif data == "rent_bot":
        user = db_get_user(uid)
        if user['balance'] < PRICE_PER_DAY:
            return await e.answer("❌ Bạn cần tối thiểu 20,000đ để thuê bot!", alert=True)
        
        old_exp = datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00'))
        new_exp = max(old_exp, datetime.now(timezone.utc)) + timedelta(days=1)
        
        supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY, "bot_expiry": new_exp.isoformat()}).eq("user_id", uid).execute()
        await e.answer("✅ Gia hạn Bot thành công! Tất cả acc đã bắt đầu chạy.", alert=True)
        
        # Sau khi gia hạn, kích hoạt lại tất cả acc của User này nếu chưa chạy
        clones = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        for c in clones.data:
            t_key = f"{uid}_{c['phone']}"
            if t_key not in active_tasks:
                active_tasks[t_key] = asyncio.create_task(run_clone_worker(c['session'], c['phone'], uid))
        
        txt, btns = get_main_menu(uid)
        await e.edit(txt, buttons=btns)

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.edit("❌ Chưa có acc nào.", buttons=[[TButton.inline("🔙 Quay lại", b"back")]])
        msg = "📱 **DANH SÁCH ACC CỦA BẠN:**\n\n"
        btns = []
        for c in res.data:
            msg += f"• `{c['phone']}`\n"
            btns.append([TButton.inline(f"🗑 Xóa {c['phone']}", f"del_{c['id']}")])
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(msg, buttons=btns)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("🗑 Đã xóa acc!", alert=True)
        await callback_handler(e)

    elif data == "history":
        res = supabase.table("history").select("*").eq("user_id", uid).order("created_at", desc=True).limit(10).execute()
        msg = "📜 **LỊCH SỬ ĂN MÃ:**\n\n"
        if res.data:
            for i in res.data: msg += f"✅ `{i['code']}` | {i['phone'][-4:]}\n"
        else: msg += "_Chưa có dữ liệu._"
        await e.edit(msg, buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

    elif data == "dep_menu":
        btns = [[TButton.inline(f"💰 {a:,} VNĐ", f"p_{a}")] for a in [20000, 50000, 100000, 200000]]
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit("🏦 **NẠP TIỀN:**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"📥 **THÔNG TIN NẠP:**\nSTK: `{STK_MSB}` (MSB)\nTiền: `{int(amt):,} VNĐ`\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 MỞ QR", qr)], [TButton.inline("🔙", b"dep_menu")]])

    # --- ADMIN PANEL ---
    elif data == "adm_main" and int(uid) == ADMIN_ID:
        u_all = supabase.table("users").select("balance").execute().data
        cl_cnt = supabase.table("my_clones").select("id", count="exact").execute().count
        txt = f"🛠 **ADMIN PANEL**\nUsers: `{len(u_all)}` | Clones: `{cl_cnt}`"
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
                if u:
                    supabase.table("users").update({"balance": u['balance'] + int(amt)}).eq("user_id", tid).execute()
                    await conv.send_message("✅ Đã cộng tiền!")
                    try: await bot.send_message(int(tid), f"🎉 Bạn được cộng `{int(amt):,} VNĐ`!")
                    except: pass

    elif data == "adm_bc" and int(uid) == ADMIN_ID:
        async with bot.conversation(uid) as conv:
            await conv.send_message("📢 Nhập thông báo:")
            msg = (await conv.get_response()).text
            users = supabase.table("users").select("user_id").execute()
            for u in users.data:
                try: await bot.send_message(int(u['user_id']), msg)
                except: pass
            await conv.send_message("✅ Đã gửi!")

# ================= THÊM ACC (FREE) =================
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_conv(e):
    async with bot.conversation(e.sender_id, timeout=300) as conv:
        try:
            await conv.send_message("📞 **SĐT Acc (+84...):**")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            new_cl = TelegramClient(StringSession(), API_ID, API_HASH)
            await new_cl.connect()
            await new_cl.send_code_request(phone)
            await conv.send_message("📩 **Nhập OTP:**")
            otp = (await conv.get_response()).text.strip()
            try: await new_cl.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA:**")
                await new_cl.sign_in(password=(await conv.get_response()).text.strip())
            
            sess = new_cl.session.save()
            supabase.table("my_clones").insert({"owner_id": e.sender_id, "phone": phone, "session": sess}).execute()
            
            # Nếu User đang còn hạn thuê Bot thì cho acc chạy luôn
            user = db_get_user(e.sender_id)
            if datetime.fromisoformat(user['bot_expiry'].replace('Z', '+00:00')) > datetime.now(timezone.utc):
                active_tasks[f"{e.sender_id}_{phone}"] = asyncio.create_task(run_clone_worker(sess, phone, e.sender_id))
                await conv.send_message(f"✅ Đã thêm `{phone}` và Bot đã bắt đầu chạy!")
            else:
                await conv.send_message(f"✅ Đã thêm `{phone}`. (Bot đang hết hạn, hãy gia hạn để acc hoạt động)")
            await new_cl.disconnect() 
        except Exception as err: await conv.send_message(f"❌ Lỗi: {err}")

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
            bot.loop.create_task(bot.send_message(uid, f"✅ Nạp thành công +{amt:,}đ!"))
    return jsonify({"ok": True}), 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    # Khởi động lại tất cả acc của những người CÒN HẠN THUÊ
    try:
        users = supabase.table("users").select("*").execute()
        user_expiry = {u['user_id']: datetime.fromisoformat(u['bot_expiry'].replace('Z', '+00:00')) for u in users.data}
        
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            expiry = user_expiry.get(c['owner_id'])
            if expiry and expiry > datetime.now(timezone.utc):
                active_tasks[f"{c['owner_id']}_{c['phone']}"] = asyncio.create_task(run_clone_worker(c['session'], c['phone'], c['owner_id']))
    except: pass
    await asyncio.gather(bot.run_until_disconnected(), app.run_task(host='0.0.0.0', port=10000))

if __name__ == '__main__':
    asyncio.run(main())
    

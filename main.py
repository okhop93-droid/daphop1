import asyncio, re, logging, random
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
PRICE_PER_DAY = 10000 
ADMIN_ID = 7816353760 

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)
active_tasks = {} 

# ================= DATABASE HELPERS =================
def db_get_user(uid):
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
            return {"user_id": uid, "balance": 0}
        return res.data[0]
    except Exception as e:
        logging.error(f"DB Error User: {e}")
        return {"user_id": uid, "balance": 0}

def db_log_history(uid, phone, code):
    try:
        supabase.table("history").insert({"user_id": uid, "phone": phone, "code": code}).execute()
    except Exception as e: logging.error(f"History Error: {e}")

# ================= WORKER LOOP =================
async def run_clone_worker(session_str, phone, owner_id, clone_id):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized(): return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            try:
                # Kiểm tra hạn dùng realtime
                res = supabase.table("my_clones").select("expiry").eq("id", clone_id).execute()
                if not res.data: 
                    await client.disconnect()
                    return
                
                exp = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
                if exp < datetime.now(timezone.utc):
                    await bot.send_message(owner_id, f"⚠️ Clone {phone} hết hạn!")
                    await client.disconnect()
                    return
            except: pass

            if ev.reply_markup:
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.3, 1.5))
                    try:
                        await ev.click()
                        await asyncio.sleep(2)
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        if "là:" in msgs[0].message:
                            code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                            db_log_history(owner_id, phone, code)
                            await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                    except: pass
        await client.run_until_disconnected()
    except Exception as e: logging.error(f"Worker {phone} Error: {e}")
    finally:
        if client.is_connected(): await client.disconnect()

# ================= MENU =================
def get_main_menu(uid):
    user = db_get_user(uid)
    txt = f"👑 **HỆ THỐNG AUTO VIP**\n💰 Số dư: **{user['balance']:,} VNĐ**"
    btns = [
        [TButton.inline(f"➕ THÊM CLONE (10k/ngày)", b"add_clone")],
        [TButton.inline("📱 QUẢN LÝ CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("📜 LỊCH SỬ", b"history")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]
    if int(uid) == ADMIN_ID: btns.append([TButton.inline("🛠 ADMIN PANEL", b"adm_main")])
    return txt, btns

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    txt, btns = get_main_menu(e.sender_id)
    await e.respond(txt, buttons=btns)

# ================= CALLBACK HANDLER (FIXED) =================
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
        msg = "📜 **10 MÃ TRÚNG GẦN NHẤT:**\n\n"
        for i in res.data: msg += f"✅ `{i['code']}` | 📱 {i['phone'][-4:]}\n"
        await e.edit(msg if res.data else "📭 Chưa có mã nào.", buttons=[[TButton.inline("🔙", b"back")]])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.edit("📭 Bạn chưa có Clone.", buttons=[[TButton.inline("🔙", b"back")]])
        btns = [[TButton.inline(f"⚙️ {c['phone']}", f"mng_{c['id']}")] for c in res.data]
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit("📱 **DANH SÁCH CLONE:**", buttons=btns)

    elif data.startswith("mng_"):
        cid = data.split("_")[1]
        c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
        exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00')).strftime('%H:%M %d/%m')
        txt = f"⚙️ **CLONE:** `{c['phone']}`\n⏳ Hạn: `{exp}`"
        btns = [
            [TButton.inline("⏳ GIA HẠN (10k/ngày)", f"ren_{cid}")],
            [TButton.inline("🗑 XÓA", f"del_{cid}")],
            [TButton.inline("🔙", b"list_clones")]
        ]
        await e.edit(txt, buttons=btns)

    elif data.startswith("ren_"):
        cid = data.split("_")[1]
        user = db_get_user(uid)
        if user['balance'] < PRICE_PER_DAY: return await e.answer("❌ Không đủ tiền!", alert=True)
        c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
        new_exp = max(datetime.fromisoformat(c['expiry'].replace('Z', '+00:00')), datetime.now(timezone.utc)) + timedelta(days=1)
        supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", uid).execute()
        supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("id", cid).execute()
        await e.answer("✅ Đã gia hạn thêm 24h!", alert=True)
        await callback_handler(e)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("✅ Đã xóa!", alert=True)
        await e.edit("📱 **DANH SÁCH CLONE:**", buttons=[[TButton.inline("🔙", b"list_clones")]])

    elif data == "dep_menu":
        btns = [[TButton.inline(f"{a:,}đ", f"p_{a}")] for a in [10000, 20000, 50000, 100000]]
        btns.append([TButton.inline("🔙", b"back")])
        await e.edit("🏦 **CHỌN MỆNH GIÁ:**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        await e.edit(f"📥 **NẠP {int(amt):,}đ**\nSTK: `{STK_MSB}` (MSB)\nNội dung: `NAP {uid}`", 
                     buttons=[[TButton.url("📲 MỞ APP", qr)], [TButton.inline("🔙", b"dep_menu")]])

    elif data == "adm_main" and int(uid) == ADMIN_ID:
        u_c = supabase.table("users").select("user_id", count="exact").execute().count
        c_c = supabase.table("my_clones").select("id", count="exact").execute().count
        await e.edit(f"🛠 **ADMIN**\nUsers: `{u_c}` | Clones: `{c_c}`", 
                     buttons=[[TButton.inline("📢 BROADCAST", b"adm_bc")], [TButton.inline("🔙", b"back")]])

    elif data == "adm_bc" and int(uid) == ADMIN_ID:
        async with bot.conversation(uid) as conv:
            await conv.send_message("📢 Nhập nội dung cần gửi (Text/Ảnh):")
            msg = await conv.get_response()
            users = supabase.table("users").select("user_id").execute()
            for u in users.data:
                try: await bot.send_message(int(u['user_id']), msg)
                except: pass
            await conv.send_message("✅ Đã gửi xong!")

# ================= ADD CLONE (CONVERSATION) =================
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_conv(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY: return await e.answer("❌ Cần 10.000 VNĐ!", alert=True)

    async with bot.conversation(e.sender_id, timeout=300) as conv:
        try:
            await conv.send_message("📞 Nhập SĐT Clone (VD: +84...):")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            new_cl = TelegramClient(StringSession(), API_ID, API_HASH)
            await new_cl.connect()
            await new_cl.send_code_request(phone)
            await conv.send_message("📩 Nhập mã OTP:")
            otp = (await conv.get_response()).text.strip()
            try:
                await new_cl.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 Nhập 2FA:")
                await new_cl.sign_in(password=(await conv.get_response()).text.strip())
            
            # Lưu DB & Trừ tiền
            exp = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            res = supabase.table("my_clones").insert({
                "owner_id": e.sender_id, "phone": phone, "session": new_cl.session.save(), "expiry": exp
            }).execute()
            
            asyncio.create_task(run_clone_worker(new_cl.session.save(), phone, e.sender_id, res.data[0]['id']))
            await conv.send_message(f"✅ Đã thêm `{phone}`!")
        except Exception as err: await conv.send_message(f"❌ Lỗi: {err}")

# ================= WEBHOOK =================
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        u = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if u.data:
            new_bal = u.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            bot.loop.create_task(bot.send_message(uid, f"✅ Nạp thành công +{amt:,}đ!"))
    return jsonify({"ok": True}), 200

@app.route('/')
async def h(): return "Bot Online", 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            if datetime.fromisoformat(c['expiry'].replace('Z', '+00:00')) > datetime.now(timezone.utc):
                asyncio.create_task(run_clone_worker(c['session'], c['phone'], c['owner_id'], c['id']))
    except: pass
    await asyncio.gather(bot.run_until_disconnected(), app.run_task(host='0.0.0.0', port=10000))

if __name__ == '__main__':
    asyncio.run(main())
            

import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from supabase import create_client, Client

# ===== CẤU HÌNH HỆ THỐNG =====
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"
STK_MSB = "96886693002613"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"
PRICE_PER_DAY = 10000

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# --- HELPER FUNCTIONS ---
def db_get_user(uid):
    res = supabase.table("users").select("*").eq("user_id", uid).execute()
    if not res.data:
        supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
        return {"user_id": uid, "balance": 0}
    return res.data[0]

# --- LOGIC ĐẬP HỘP (STAY ALIVE) ---
async def worker_grab_loop(client, phone, owner_id):
    try:
        if not client.is_connected():
            await client.connect()
        
        if not await client.is_user_authorized():
            logging.error(f"Session {phone} is invalid.")
            return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
            if not res.data: return
            
            expiry = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
            if expiry < datetime.now(timezone.utc):
                await client.disconnect()
                return

            if ev.reply_markup:
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.1, 0.4))
                    try:
                        await ev.click()
                        await asyncio.sleep(1.5)
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        if msgs and "là:" in msgs[0].message:
                            code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                            await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                    except: pass
        
        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Worker Error {phone}: {e}")

# --- GIAO DIỆN (UI UPGRADE) ---
def main_menu_text(user):
    return (
        f"👑 **HỆ THỐNG CLONE VIP** 👑\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Người dùng: `{user['user_id']}`\n"
        f"💰 Số dư hiện tại: **{user['balance']:,} VNĐ**\n"
        f"📅 Hôm nay: {datetime.now().strftime('%d/%m/%Y')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *Trạng thái: Máy chủ hoạt động ổn định*"
    )

def main_btns():
    return [
        [TButton.inline("➕ THÊM ACC MỚI", b"add_clone")],
        [TButton.inline("📱 DANH SÁCH CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("👤 VÍ CỦA TÔI", b"me")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    await e.respond(main_menu_text(user), buttons=main_btns())

# --- CALLBACK HANDLER ---
@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid, data = e.sender_id, e.data.decode()
    
    if data == "back":
        user = db_get_user(uid)
        await e.edit(main_menu_text(user), buttons=main_btns())
    
    elif data == "dep_menu":
        btns = [
            [TButton.inline("💸 10.000đ", b"p_10000"), TButton.inline("💸 20.000đ", b"p_20000")],
            [TButton.inline("💸 50.000đ", b"p_50000"), TButton.inline("💸 100.000đ", b"p_100000")],
            [TButton.inline("🔙 QUAY LẠI", b"back")]
        ]
        await e.edit("🏦 **HỆ THỐNG NẠP TIỀN TỰ ĐỘNG**\n\n*Vui lòng chọn mệnh giá bạn muốn nạp:*", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        txt = (f"📥 **THÔNG TIN CHUYỂN KHOẢN**\n\n"
               f"🏦 Ngân hàng: **MSB**\n"
               f"🔢 STK: `{STK_MSB}`\n"
               f"💰 Số tiền: **{int(amt):,} VNĐ**\n"
               f"📝 Nội dung: `NAP {uid}`\n\n"
               f"⚠️ *Lưu ý: Phải nhập đúng nội dung để được cộng tiền tự động.*")
        await e.edit(txt, buttons=[[TButton.url("📲 MỞ APP BANK", qr)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

    elif data == "me":
        user = db_get_user(uid)
        await e.edit(f"👤 **HỒ SƠ CỦA BẠN**\n\n🆔 ID: `{uid}`\n💰 Số dư: **{user['balance']:,} VNĐ**\n🎁 Hạng: **Thành viên**", 
                     buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data:
            return await e.answer("❌ Bạn chưa có tài khoản nào đang thuê!", alert=True)
        
        txt = "📱 **QUẢN LÝ CLONE CỦA BẠN**\n\n"
        btns = []
        for c in res.data:
            exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            status = "✅" if exp > datetime.now(timezone.utc) else "❌"
            txt += f"{status} `{c['phone']}` | Hết hạn: {exp.strftime('%H:%M %d/%m')}\n"
            btns.append([TButton.inline(f"🗑 Xóa {c['phone']}", f"del_{c['id']}")])
        
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(txt, buttons=btns)

    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("✅ Đã xóa clone khỏi hệ thống!", alert=True)
        # Refresh lại danh sách
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data: return await e.edit("📭 Hết danh sách.", buttons=[TButton.inline("🔙 QUAY LẠI", b"back")])
        await cb_handler(e)

# --- THÊM ACC LOGIC ---
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_process(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY:
        return await e.answer(f"❌ Số dư không đủ {PRICE_PER_DAY:,} VNĐ", alert=True)

    async with bot.conversation(e.sender_id) as conv:
        try:
            await conv.send_message("📞 **Bước 1:** Nhập số điện thoại (VD: +84123456789):")
            phone = (await conv.get_response()).text.strip().replace(" ", "")
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            await client.send_code_request(phone)
            await conv.send_message("📩 **Bước 2:** Nhập mã OTP (5 chữ số) từ Telegram:")
            otp = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **Bước 3:** Tài khoản có 2FA. Nhập mật khẩu:")
                pwd = (await conv.get_response()).text.strip()
                await client.sign_in(password=pwd)

            # Hoàn tất
            session_str = client.session.save()
            expiry_date = datetime.now(timezone.utc) + timedelta(days=1)
            
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            supabase.table("my_clones").insert({
                "owner_id": e.sender_id, "phone": phone, 
                "session": session_str, "expiry": expiry_date.isoformat()
            }).execute()

            await conv.send_message(f"✅ **KÍCH HOẠT THÀNH CÔNG!**\nClone `{phone}` đã bắt đầu làm việc.")
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id))
            
        except Exception as ex:
            await conv.send_message(f"❌ **LỖI:** {str(ex)}\nVui lòng thử lại.")

# --- WEBHOOK SEPAY ---
app = Flask(__name__)
@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    d = request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if res.data:
            new_bal = res.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"✅ **NẠP TIỀN THÀNH CÔNG!**\n💰 +{amt:,} VNĐ\nChúc bạn chơi vui vẻ!"), asyncio.get_event_loop())
    return jsonify({"status": "ok"}), 200

# --- KHỞI CHẠY ---
async def start_all_clones():
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
            asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
    except: pass

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await start_all_clones()
    print(">>> BOT ĐÃ SẴN SÀNG! <<<")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    asyncio.get_event_loop().run_until_complete(main())
    

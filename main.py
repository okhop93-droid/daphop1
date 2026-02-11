import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from supabase import create_client, Client
from quart import Quart, request, jsonify

# =====================================================
# CẤU HÌNH HỆ THỐNG (THAY ĐỔI THÔNG TIN CỦA BẠN Ở ĐÂY)
# =====================================================
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"

STK_MSB = "96886693002613" # Số tài khoản nhận tiền
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot" # Bot game mục tiêu
PRICE_PER_DAY = 10000 # Giá 1 ngày (10k)

# ID Admin (Quan trọng: Phải đúng ID Telegram của bạn)
ADMIN_ID = 7816353760 

# =====================================================

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)
active_clients = {} # Lưu trạng thái các clone đang chạy

# --- DATABASE HELPERS ---
def db_get_user(uid):
    """Lấy thông tin user, nếu chưa có thì tạo mới"""
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
            return {"user_id": uid, "balance": 0}
        return res.data[0]
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return {"user_id": uid, "balance": 0}

def db_update_balance(uid, new_balance):
    supabase.table("users").update({"balance": new_balance}).eq("user_id", uid).execute()

# --- WORKER LOOP (BOT CON ĐI ĐẬP HỘP) ---
async def worker_grab_loop(client, phone, owner_id):
    try:
        if not client.is_connected(): await client.connect()
        if not await client.is_user_authorized(): return
        
        active_clients[phone] = True
        
        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            # 1. Kiểm tra hạn sử dụng mỗi khi có tin nhắn mới
            try:
                res = supabase.table("my_clones").select("expiry").eq("phone", phone).execute()
                if not res.data: return # Clone đã bị xóa khỏi DB
                
                exp = datetime.fromisoformat(res.data[0]['expiry'].replace('Z', '+00:00'))
                if exp < datetime.now(timezone.utc):
                    await bot.send_message(owner_id, f"⚠️ **Clone {phone} đã hết hạn!**\nVui lòng gia hạn để tiếp tục chạy.")
                    active_clients[phone] = False
                    await client.disconnect()
                    return
            except: pass

            # 2. Logic đập hộp
            if ev.reply_markup:
                # Tìm nút có chữ "đập"
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.1, 0.4)) # Delay tránh ban
                    try:
                        await ev.click()
                        await asyncio.sleep(1.5)
                        # Lấy tin nhắn kết quả
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        if msgs and "là:" in msgs[0].message:
                            # Regex lấy mã code
                            code_match = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message)
                            if code_match:
                                code = code_match.group(1)
                                # Lưu lịch sử
                                supabase.table("history").insert({
                                    "user_id": owner_id, 
                                    "phone": phone, 
                                    "code": code
                                }).execute()
                                # Báo về bot chính
                                await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                    except Exception as e:
                        logging.error(f"Error clicking: {e}")

        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Worker Error {phone}: {e}")
        active_clients[phone] = False

# --- GIAO DIỆN (BUTTONS) ---
def main_btns(uid):
    btns = [
        [TButton.inline(f"➕ THÊM CLONE ({int(PRICE_PER_DAY/1000)}k/ngày)", b"add_clone")],
        [TButton.inline("📱 QUẢN LÝ CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("👤 VÍ / LỊCH SỬ", b"me")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]
    # Kiểm tra chính xác ID Admin
    if int(uid) == int(ADMIN_ID):
        btns.append([TButton.inline("🛠 MENU QUẢN TRỊ VIÊN", b"adm_main")])
    return btns

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user = db_get_user(e.sender_id)
    txt = (
        f"👑 **HỆ THỐNG CLONE VIP** 👑\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 ID: `{e.sender_id}`\n"
        f"💰 Số dư: **{user['balance']:,} VNĐ**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"⚡ *Hệ thống auto đập hộp siêu tốc, ổn định!*"
    )
    await e.respond(txt, buttons=main_btns(e.sender_id))

# --- XỬ LÝ CALLBACK (NÚT BẤM) ---
@bot.on(events.CallbackQuery)
async def cb_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    await e.answer() # Fix lỗi quay vòng tròn

    # 1. Quay lại Menu chính
    if data == "back":
        user = db_get_user(uid)
        txt = f"👑 **HỆ THỐNG CLONE VIP**\n💰 Số dư: **{user['balance']:,} VNĐ**"
        await e.edit(txt, buttons=main_btns(uid))

    # 2. Menu Nạp tiền
    elif data == "dep_menu":
        btns = [
            [TButton.inline("💸 10.000đ", b"p_10000"), TButton.inline("💸 20.000đ", b"p_20000")],
            [TButton.inline("💸 50.000đ", b"p_50000"), TButton.inline("💸 100.000đ", b"p_100000")],
            [TButton.inline("🔙 QUAY LẠI", b"back")]
        ]
        await e.edit("🏦 **CHỌN MỆNH GIÁ NẠP:**", buttons=btns)

    elif data.startswith("p_"):
        amt = data.split("_")[1]
        qr = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
        txt = (
            f"📥 **THÔNG TIN CHUYỂN KHOẢN**\n\n"
            f"🏦 Ngân hàng: **MSB**\n"
            f"💳 STK: `{STK_MSB}`\n"
            f"💰 Số tiền: **{int(amt):,} VNĐ**\n"
            f"📝 Nội dung: `NAP {uid}`\n\n"
            f"⚠️ _Vui lòng nhập đúng nội dung để cộng tiền tự động_"
        )
        await e.edit(txt, buttons=[[TButton.url("📲 MỞ APP NGÂN HÀNG", qr)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

    # 3. Xem Ví & Lịch sử
    elif data == "me":
        user = db_get_user(uid)
        try:
            # Lấy 10 mã trúng gần nhất
            res = supabase.table("history").select("*").eq("user_id", uid).order("created_at", desc=True).limit(10).execute()
            history_txt = ""
            if res.data:
                for h in res.data:
                    t = datetime.fromisoformat(h['created_at'].replace('Z', '+00:00')).strftime('%H:%M %d/%m')
                    history_txt += f"🎁 `{h['code']}` - {t} ({h['phone']})\n"
            else:
                history_txt = "_Chưa có mã trúng nào._"
        except Exception:
            history_txt = "⚠️ _Chưa tạo bảng history trong Database._"

        txt = (
            f"👤 **THÔNG TIN CÁ NHÂN**\n"
            f"💰 Số dư: **{user['balance']:,} VNĐ**\n"
            f"➖➖➖➖➖➖➖➖\n"
            f"🔑 **LỊCH SỬ TRÚNG GẦN ĐÂY:**\n"
            f"{history_txt}"
        )
        await e.edit(txt, buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

    # 4. Danh sách Clone
    elif data == "list_clones":
        res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
        if not res.data:
            return await e.edit("❌ Bạn chưa thêm tài khoản nào!", buttons=[[TButton.inline("➕ THÊM NGAY", b"add_clone")], [TButton.inline("🔙 QUAY LẠI", b"back")]])
        
        txt = "📱 **QUẢN LÝ DANH SÁCH CLONE**\nChọn tài khoản để gia hạn hoặc xóa:\n\n"
        btns = []
        for c in res.data:
            exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            # Kiểm tra sống/chết và còn hạn/hết hạn
            status_icon = "🟢" if active_clients.get(c['phone']) and exp > now else "🔴"
            exp_str = exp.strftime('%d/%m %H:%M')
            
            txt += f"{status_icon} `{c['phone']}` (Hết hạn: {exp_str})\n"
            btns.append([TButton.inline(f"⚙️ Cài đặt {c['phone']}", f"mng_{c['id']}")])
            
        btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
        await e.edit(txt, buttons=btns)

    # 5. Menu Quản lý từng Clone (Gia hạn/Xóa)
    elif data.startswith("mng_"):
        cid = data.split("_")[1]
        try:
            c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
            exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            status = "ĐANG CHẠY" if exp > datetime.now(timezone.utc) else "ĐÃ HẾT HẠN"
            
            txt = (
                f"⚙️ **CÀI ĐẶT CLONE**\n"
                f"📱 SĐT: `{c['phone']}`\n"
                f"⏳ Hết hạn: `{exp.strftime('%H:%M %d/%m/%Y')}`\n"
                f"📊 Trạng thái: **{status}**"
            )
            btns = [
                [TButton.inline(f"⏳ GIA HẠN 1 NGÀY ({int(PRICE_PER_DAY/1000)}k)", f"ren_{cid}")],
                [TButton.inline("🗑 XÓA CLONE NÀY", f"del_{cid}")],
                [TButton.inline("🔙 DANH SÁCH", b"list_clones")]
            ]
            await e.edit(txt, buttons=btns)
        except:
            await e.edit("❌ Clone này không tồn tại hoặc đã bị xóa.", buttons=[[TButton.inline("🔙", b"list_clones")]])

    # 6. Xử lý Gia hạn
    elif data.startswith("ren_"):
        cid = data.split("_")[1]
        user = db_get_user(uid)
        
        if user['balance'] < PRICE_PER_DAY:
            return await e.answer(f"❌ Số dư không đủ! Cần {PRICE_PER_DAY:,}đ để gia hạn.", alert=True)
            
        try:
            # Lấy thông tin clone
            c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
            current_exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            # Nếu hết hạn rồi thì tính từ bây giờ, nếu còn hạn thì cộng dồn
            new_exp = max(current_exp, now) + timedelta(days=1)
            
            # Trừ tiền
            db_update_balance(uid, user['balance'] - PRICE_PER_DAY)
            
            # Update DB
            supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("id", cid).execute()
            
            await e.answer(f"✅ Gia hạn thành công! Hạn mới: {new_exp.strftime('%d/%m %H:%M')}", alert=True)
            # Load lại menu clone đó
            await cb_handler(e) # Gọi lại hàm xử lý để refresh giao diện
            
            # Thông báo cho user biết tiền đã trừ
            await bot.send_message(uid, f"💸 **TRỪ TIỀN:** -{PRICE_PER_DAY:,} VNĐ\nLý do: Gia hạn clone `{c['phone']}`")
            
        except Exception as ex:
            await e.answer(f"❌ Lỗi: {ex}", alert=True)

    # 7. Xử lý Xóa Clone
    elif data.startswith("del_"):
        cid = data.split("_")[1]
        supabase.table("my_clones").delete().eq("id", cid).execute()
        await e.answer("✅ Đã xóa clone khỏi hệ thống!", alert=True)
        # Quay về danh sách
        data = "list_clones" # Hack để nó nhảy về logic list_clones
        await cb_handler(e)

    # ===============================================
    # LOGIC ADMIN (Đã fix)
    # ===============================================
    elif data == "adm_main":
        if int(uid) != int(ADMIN_ID): return
        
        # Thống kê
        users_count = supabase.table("users").select("user_id", count="exact").execute().count
        clones_count = supabase.table("my_clones").select("id", count="exact").execute().count
        
        txt = (
            f"🛠 **BẢNG ĐIỀU KHIỂN ADMIN**\n\n"
            f"👥 Tổng thành viên: `{users_count}`\n"
            f"📱 Tổng Clone đang chạy: `{clones_count}`\n"
        )
        btns = [
            [TButton.inline("📋 XEM LIST CLONE", b"adm_list")],
            [TButton.inline("📢 GỬI THÔNG BÁO (BROADCAST)", b"adm_cast")],
            [TButton.inline("🔙 QUAY LẠI", b"back")]
        ]
        await e.edit(txt, buttons=btns)

    elif data == "adm_list":
        if int(uid) != int(ADMIN_ID): return
        res = supabase.table("my_clones").select("*").execute()
        txt = "📋 **DANH SÁCH TOÀN BỘ CLONE:**\n"
        for c in res.data:
            txt += f"- `{c['phone']}` (User: `{c['owner_id']}`)\n"
        await e.edit(txt[:4000], buttons=[[TButton.inline("🔙", b"adm_main")]])
        
    elif data == "adm_cast":
        if int(uid) != int(ADMIN_ID): return
        await e.respond("📢 **NHẬP NỘI DUNG THÔNG BÁO:**\nReply tin nhắn này để gửi cho toàn bộ thành viên.")
        # Logic nhận tin nhắn reply sẽ nằm ở phần conversation bên dưới hoặc handle riêng

# --- TÍNH NĂNG ADD CLONE (Conversation) ---
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_flow(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY:
        return await e.answer(f"❌ Số dư không đủ! Cần {PRICE_PER_DAY:,} VNĐ", alert=True)

    async with bot.conversation(e.sender_id, timeout=300) as conv:
        try:
            await conv.send_message("📞 **BƯỚC 1:** Nhập số điện thoại (VD: +84987654321):")
            resp = await conv.get_response()
            phone = resp.text.strip().replace(" ", "")

            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            try:
                await client.send_code_request(phone)
            except Exception as ex:
                return await conv.send_message(f"❌ Lỗi gửi mã: {ex}")

            await conv.send_message("📩 **BƯỚC 2:** Nhập mã OTP Telegram vừa gửi về:")
            otp = (await conv.get_response()).text.strip()

            try:
                await client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **BƯỚC 3:** Tài khoản có 2FA. Vui lòng nhập mật khẩu:")
                pwd = (await conv.get_response()).text.strip()
                await client.sign_in(password=pwd)
            except Exception as ex:
                return await conv.send_message(f"❌ Đăng nhập thất bại: {ex}")

            # Lưu session
            session_str = client.session.save()
            expiry_date = datetime.now(timezone.utc) + timedelta(days=1)

            # Trừ tiền & Lưu DB
            db_update_balance(e.sender_id, user['balance'] - PRICE_PER_DAY)
            supabase.table("my_clones").insert({
                "owner_id": e.sender_id,
                "phone": phone,
                "session": session_str,
                "expiry": expiry_date.isoformat()
            }).execute()

            await conv.send_message(f"✅ **KÍCH HOẠT THÀNH CÔNG!**\n📱 Clone `{phone}` đã bắt đầu chạy.\n💸 Đã trừ: {PRICE_PER_DAY:,} VNĐ")
            
            # Khởi chạy worker ngay lập tức
            asyncio.create_task(worker_grab_loop(client, phone, e.sender_id))

        except asyncio.TimeoutError:
            await conv.send_message("❌ Hết thời gian thao tác. Vui lòng thử lại.")
        except Exception as ex:
            await conv.send_message(f"❌ Lỗi không xác định: {ex}")

# --- TÍNH NĂNG BROADCAST CHO ADMIN ---
@bot.on(events.NewMessage(func=lambda e: e.is_reply))
async def broadcast_handler(e):
    if e.sender_id != ADMIN_ID: return
    reply_msg = await e.get_reply_message()
    if "NHẬP NỘI DUNG THÔNG BÁO" in reply_msg.message:
        msg_to_send = e.message.message
        users = supabase.table("users").select("user_id").execute()
        
        count = 0
        status_msg = await e.respond("⏳ Đang gửi tin nhắn...")
        
        for u in users.data:
            try:
                await bot.send_message(int(u['user_id']), f"📢 **THÔNG BÁO HỆ THỐNG:**\n\n{msg_to_send}")
                count += 1
                await asyncio.sleep(0.1) # Tránh flood
            except: pass
            
        await status_msg.edit(f"✅ Đã gửi thông báo tới {count} thành viên!")

# --- WEBHOOK SEPAY (NẠP TIỀN TỰ ĐỘNG) ---
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    content = d.get("content", "").upper()
    # Tìm cú pháp NAP {uid}
    m = re.search(r'NAP\s+(\d+)', content)
    
    if m:
        uid = int(m.group(1))
        amt = int(d.get("transferAmount", 0))
        
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if res.data:
            new_bal = res.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            
            # Gửi thông báo cho user
            bot.loop.create_task(bot.send_message(uid, f"✅ **NẠP TIỀN THÀNH CÔNG!**\n💰 Số tiền: +{amt:,} VNĐ\n💳 Số dư mới: {new_bal:,} VNĐ"))
            
            # Gửi thông báo cho Admin
            bot.loop.create_task(bot.send_message(ADMIN_ID, f"📢 **DOANH THU MỚI:**\nUser `{uid}` vừa nạp `{amt:,}` VNĐ"))
            
    return jsonify({"status": "ok"}), 200

@app.route('/')
async def index():
    return "Bot is running perfectly!", 200

# --- KHỞI CHẠY HỆ THỐNG ---
async def main():
    print(">>> ĐANG KHỞI ĐỘNG BOT...")
    await bot.start(bot_token=BOT_TOKEN)
    
    # Khôi phục các clone từ Database khi khởi động lại
    try:
        clones = supabase.table("my_clones").select("*").execute()
        count = 0
        for c in clones.data:
            try:
                cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
                asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
                count += 1
            except: pass
        print(f">>> ĐÃ KHÔI PHỤC {count} CLONE.")
    except Exception as e:
        print(f"Lỗi khôi phục clone: {e}")

    # Chạy Web Server (Webhook) và Bot song song
    await asyncio.gather(
        bot.run_until_disconnected(),
        app.run_task(host='0.0.0.0', port=10000)
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
                        

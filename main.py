import asyncio, re, logging, random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from supabase import create_client, Client
from quart import Quart, request, jsonify

# ================= CẤU HÌNH (ĐIỀN ĐÚNG 100%) =================
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" 
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA" # Thay đúng Key của bạn
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"

STK_MSB = "96886693002613" # STK nhận tiền
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot" # Bot game mục tiêu
PRICE_PER_DAY = 10000 # Giá 10k/ngày
ADMIN_ID = 7816353760 # ID Admin

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)
app = Quart(__name__)

# Quản lý luồng chạy ngầm (Để có thể kill task khi xóa clone)
active_tasks = {} 

# ================= HELPER FUNCTIONS =================
def db_get_user(uid):
    """Lấy thông tin user, auto tạo nếu chưa có"""
    try:
        res = supabase.table("users").select("*").eq("user_id", uid).execute()
        if not res.data:
            supabase.table("users").insert({"user_id": uid, "balance": 0}).execute()
            return {"user_id": uid, "balance": 0}
        return res.data[0]
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return {"user_id": uid, "balance": 0}

def db_log_history(uid, phone, code):
    """Ghi lịch sử trúng thưởng"""
    try:
        supabase.table("history").insert({
            "user_id": uid, "phone": phone, "code": code
        }).execute()
    except Exception as e: logging.error(f"History Error: {e}")

# ================= WORKER LOOP (BOT CON) =================
async def run_clone_worker(session_str, phone, owner_id, clone_id):
    """Hàm chạy ngầm cho từng Clone"""
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logging.warning(f"Clone {phone} hết hạn session.")
            return

        @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
        async def handler(ev):
            # 1. Kiểm tra hạn sử dụng (Check Realtime)
            try:
                # Lấy info mới nhất từ DB để check hạn
                res = supabase.table("my_clones").select("expiry").eq("id", clone_id).execute()
                if not res.data: 
                    await client.disconnect() # Bị xóa khỏi DB
                    return
                
                exp_str = res.data[0]['expiry'].replace('Z', '+00:00')
                expiry = datetime.fromisoformat(exp_str)
                
                if expiry < datetime.now(timezone.utc):
                    # Hết hạn -> Ngắt kết nối & Báo Admin
                    await bot.send_message(owner_id, f"⚠️ **Clone {phone} đã hết hạn!**\nVui lòng gia hạn để bot chạy tiếp.")
                    await client.disconnect()
                    return
            except Exception: pass

            # 2. Logic Đập hộp
            if ev.reply_markup:
                btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
                if btn:
                    await asyncio.sleep(random.uniform(0.5, 2.0)) # Delay tránh ban
                    try:
                        await ev.click()
                        await asyncio.sleep(2)
                        # Check kết quả
                        msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                        last_msg = msgs[0].message
                        if "là:" in last_msg:
                            code_match = re.search(r'là:\s*([A-Z0-9]+)', last_msg)
                            if code_match:
                                code = code_match.group(1)
                                db_log_history(owner_id, phone, code)
                                await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` ĂN MÃ!**\n🔑 Code: `{code}`")
                    except Exception as e:
                        logging.error(f"Click Error: {e}")

        # Giữ kết nối
        await client.run_until_disconnected()
        
    except Exception as e:
        logging.error(f"Worker Crash {phone}: {e}")
    finally:
        if client.is_connected(): await client.disconnect()

# ================= MENU & GIAO DIỆN =================
def get_main_menu(uid):
    user = db_get_user(uid)
    txt = (
        f"👑 **HỆ THỐNG AUTO GAME VIP** 👑\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 ID: `{uid}`\n"
        f"💰 Số dư: **{user['balance']:,} VNĐ**\n"
        f"➖➖➖➖➖➖➖➖➖➖"
    )
    btns = [
        [TButton.inline(f"➕ THÊM CLONE ({int(PRICE_PER_DAY/1000)}k/ngày)", b"add_clone")],
        [TButton.inline("📱 QUẢN LÝ CLONE", b"list_clones")],
        [TButton.inline("🏦 NẠP TIỀN", b"dep_menu"), TButton.inline("📜 LỊCH SỬ ĂN MÃ", b"history")],
        [TButton.url("💬 HỖ TRỢ", "https://t.me/nth_dev")]
    ]
    if str(uid) == str(ADMIN_ID):
        btns.append([TButton.inline("🛠 ADMIN PANEL", b"adm_main")])
    return txt, btns

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    txt, btns = get_main_menu(e.sender_id)
    await e.respond(txt, buttons=btns)

# ================= XỬ LÝ NÚT BẤM (CALLBACK) =================
@bot.on(events.CallbackQuery)
async def callback_handler(e):
    uid = e.sender_id
    data = e.data.decode()
    
    # QUAN TRỌNG: Answer ngay lập tức để không bị xoay vòng tròn
    try: await e.answer() 
    except: pass

    try:
        # --- NHÓM 1: ĐIỀU HƯỚNG CƠ BẢN ---
        if data == "back":
            txt, btns = get_main_menu(uid)
            await e.edit(txt, buttons=btns)

        # --- NHÓM 2: LỊCH SỬ ---
        elif data == "history":
            # Lấy 10 record mới nhất
            res = supabase.table("history").select("*").eq("user_id", uid).order("created_at", desc=True).limit(10).execute()
            msg = "📜 **LỊCH SỬ 10 MÃ GẦN NHẤT:**\n\n"
            if res.data:
                for item in res.data:
                    t = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')).strftime('%H:%M %d/%m')
                    msg += f"✅ `{item['code']}` | 📱 {item['phone'][-4:]} | 🕒 {t}\n"
            else:
                msg += "_Chưa có mã nào được ăn._"
            await e.edit(msg, buttons=[[TButton.inline("🔙 QUAY LẠI", b"back")]])

        # --- NHÓM 3: QUẢN LÝ CLONE ---
        elif data == "list_clones":
            res = supabase.table("my_clones").select("*").eq("owner_id", uid).execute()
            if not res.data:
                return await e.edit("📭 **Bạn chưa có Clone nào!**", buttons=[[TButton.inline("➕ THÊM NGAY", b"add_clone")], [TButton.inline("🔙 QUAY LẠI", b"back")]])
            
            txt = "📱 **DANH SÁCH CLONE:**\nChọn clone để gia hạn hoặc xóa:\n\n"
            btns = []
            for c in res.data:
                # Check hạn
                exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
                is_expired = exp < datetime.now(timezone.utc)
                status = "🔴 HẾT HẠN" if is_expired else "🟢 ĐANG CHẠY"
                
                txt += f"📱 `{c['phone']}` ({status})\n"
                btns.append([TButton.inline(f"⚙️ Cài đặt {c['phone']}", f"mng_{c['id']}")])
            
            btns.append([TButton.inline("🔙 QUAY LẠI", b"back")])
            await e.edit(txt, buttons=btns)

        elif data.startswith("mng_"):
            cid = data.split("_")[1]
            c = supabase.table("my_clones").select("*").eq("id", cid).execute().data[0]
            exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
            
            info = (
                f"⚙️ **CÀI ĐẶT CLONE:** `{c['phone']}`\n"
                f"⏳ Hết hạn: `{exp.strftime('%H:%M %d/%m/%Y')}`\n"
            )
            sub_btns = [
                [TButton.inline(f"⏳ GIA HẠN 1 NGÀY (-{int(PRICE_PER_DAY/1000)}k)", f"ren_{cid}")],
                [TButton.inline("🗑 XÓA VĨNH VIỄN", f"del_{cid}")],
                [TButton.inline("🔙 QUAY LẠI", b"list_clones")]
            ]
            await e.edit(info, buttons=sub_btns)

        # --- NHÓM 4: LOGIC GIA HẠN (Hard Logic) ---
        elif data.startswith("ren_"):
            cid = data.split("_")[1]
            user = db_get_user(uid)
            
            if user['balance'] < PRICE_PER_DAY:
                return await e.answer(f"❌ Bạn thiếu tiền! Cần {PRICE_PER_DAY:,} VNĐ", alert=True)

            # Lấy info clone
            c_res = supabase.table("my_clones").select("*").eq("id", cid).execute()
            if not c_res.data: return await e.answer("❌ Clone không tồn tại!", alert=True)
            clone = c_res.data[0]
            
            # Tính toán ngày mới
            current_exp = datetime.fromisoformat(clone['expiry'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            new_exp = max(current_exp, now) + timedelta(days=1) # Logic: Nếu hết hạn thì tính từ bây giờ, nếu chưa thì cộng dồn
            
            # Update DB (User trừ tiền, Clone tăng hạn)
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", uid).execute()
            supabase.table("my_clones").update({"expiry": new_exp.isoformat()}).eq("id", cid).execute()
            
            await e.answer(f"✅ Gia hạn thành công!\nHạn mới: {new_exp.strftime('%d/%m %H:%M')}", alert=True)
            
            # Reload lại giao diện quản lý
            await callback_handler(e) # Gọi đệ quy để refresh nút
            
            # Báo tin nhắn riêng
            await bot.send_message(uid, f"💸 **TRỪ TIỀN GIA HẠN:** -{PRICE_PER_DAY:,} VNĐ\n📱 Clone: `{clone['phone']}`")
            if str(ADMIN_ID) != str(uid):
                await bot.send_message(ADMIN_ID, f"📢 User `{uid}` vừa gia hạn clone `{clone['phone']}`.")

        # --- NHÓM 5: LOGIC XÓA CLONE (Kill Task) ---
        elif data.startswith("del_"):
            cid = data.split("_")[1]
            # 1. Lấy số điện thoại trước khi xóa để kill task
            c_res = supabase.table("my_clones").select("phone").eq("id", cid).execute()
            if c_res.data:
                phone = c_res.data[0]['phone']
                
                # 2. Xóa trong DB
                supabase.table("my_clones").delete().eq("id", cid).execute()
                
                # 3. Kill Task đang chạy ngầm (Quan trọng)
                task_key = f"{uid}_{phone}" # Key giả định, logic quản lý task cần nâng cao nếu nhiều user
                # Ở version simple này, worker loop sẽ tự động disconnect khi check DB không thấy record (ở lần nhận tin nhắn tới).
                
                await e.answer("✅ Đã xóa Clone thành công!", alert=True)
                data = "list_clones" # Chuyển hướng về list
                await callback_handler(e)

        # --- NHÓM 6: NẠP TIỀN ---
        elif data == "dep_menu":
            btns = [
                [TButton.inline("10.000đ", b"p_10000"), TButton.inline("20.000đ", b"p_20000")],
                [TButton.inline("50.000đ", b"p_50000"), TButton.inline("100.000đ", b"p_100000")],
                [TButton.inline("🔙 QUAY LẠI", b"back")]
            ]
            await e.edit("🏦 **CHỌN MỆNH GIÁ MUỐN NẠP:**", buttons=btns)
            
        elif data.startswith("p_"):
            amt = data.split("_")[1]
            qr_link = f"https://img.vietqr.io/image/MSB-{STK_MSB}-compact2.png?amount={amt}&addInfo=NAP%20{uid}"
            msg = (
                f"💳 **THÔNG TIN CHUYỂN KHOẢN**\n\n"
                f"🏦 Ngân hàng: **MSB**\n"
                f"🔢 STK: `{STK_MSB}`\n"
                f"💰 Số tiền: `{int(amt):,} VNĐ`\n"
                f"✍️ Nội dung: `NAP {uid}`\n\n"
                f"⚠️ Hệ thống tự động cộng tiền trong 1-2 phút."
            )
            await e.edit(msg, buttons=[[TButton.url("📲 MỞ APP BANK", qr_link)], [TButton.inline("🔙 QUAY LẠI", b"dep_menu")]])

        # --- NHÓM 7: ADMIN PANEL ---
        elif data == "adm_main":
            if str(uid) != str(ADMIN_ID): return
            
            # Thống kê nhanh
            users = supabase.table("users").select("user_id", count="exact").execute().count
            clones = supabase.table("my_clones").select("id", count="exact").execute().count
            
            msg = f"🛠 **ADMIN CONTROL**\n👥 Users: `{users}`\n🤖 Clones: `{clones}`"
            btns = [
                [TButton.inline("📋 LIST ALL CLONES", b"adm_list")],
                [TButton.inline("📢 GỬI THÔNG BÁO", b"adm_broadcast")],
                [TButton.inline("🔙 BACK", b"back")]
            ]
            await e.edit(msg, buttons=btns)
        
        elif data == "adm_list":
            if str(uid) != str(ADMIN_ID): return
            res = supabase.table("my_clones").select("*").execute()
            txt = "📋 **ALL CLONES:**\n"
            for c in res.data: txt += f"- `{c['phone']}` (User: `{c['owner_id']}`)\n"
            # Cắt ngắn nếu quá dài
            await e.edit(txt[:4000], buttons=[[TButton.inline("🔙", b"adm_main")]])

    except Exception as ex:
        logging.error(f"Callback Error: {ex}")
        await e.answer(f"❌ Có lỗi xảy ra: {str(ex)}", alert=True)

# ================= TÍNH NĂNG THÊM CLONE & BROADCAST =================

# 1. Thêm Clone (Sử dụng Conversation an toàn)
@bot.on(events.CallbackQuery(data=b"add_clone"))
async def add_clone_conv(e):
    user = db_get_user(e.sender_id)
    if user['balance'] < PRICE_PER_DAY:
        return await e.answer(f"❌ Bạn cần {PRICE_PER_DAY:,} VNĐ để thêm mới!", alert=True)

    # Bắt đầu hội thoại
    async with bot.conversation(e.sender_id, timeout=300) as conv:
        try:
            # Bước 1: Hỏi SĐT
            msg1 = await conv.send_message("📞 **Nhập số điện thoại Clone:**\n(Ví dụ: +84912345678)")
            resp_phone = await conv.get_response()
            phone = resp_phone.text.strip().replace(" ", "")

            # Init Client mới
            new_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await new_client.connect()
            
            try:
                await new_client.send_code_request(phone)
            except Exception as api_err:
                return await conv.send_message(f"❌ Lỗi gửi mã Telegram: {api_err}")

            # Bước 2: Hỏi OTP
            await conv.send_message(f"📩 **Nhập mã OTP gửi về {phone}:**")
            resp_otp = await conv.get_response()
            otp = resp_otp.text.strip()

            # Bước 3: Đăng nhập
            try:
                await new_client.sign_in(phone, otp)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **Tài khoản có 2FA. Nhập mật khẩu:**")
                resp_pwd = await conv.get_response()
                pwd = resp_pwd.text.strip()
                await new_client.sign_in(password=pwd)
            except PhoneCodeInvalidError:
                return await conv.send_message("❌ Mã OTP sai. Hủy thao tác.")

            # Thành công -> Lưu DB
            session_str = new_client.session.save()
            expiry_date = datetime.now(timezone.utc) + timedelta(days=1)
            
            # Trừ tiền & Insert
            supabase.table("users").update({"balance": user['balance'] - PRICE_PER_DAY}).eq("user_id", e.sender_id).execute()
            
            res_ins = supabase.table("my_clones").insert({
                "owner_id": e.sender_id, "phone": phone, 
                "session": session_str, "expiry": expiry_date.isoformat()
            }).execute()
            
            clone_id = res_ins.data[0]['id']

            await conv.send_message(f"✅ **THÊM CLONE THÀNH CÔNG!**\n📱 `{phone}` đã bắt đầu chạy.\n💸 Đã trừ: {PRICE_PER_DAY:,} VNĐ")
            
            # Khởi chạy Worker ngay
            task = asyncio.create_task(run_clone_worker(session_str, phone, e.sender_id, clone_id))
            active_tasks[f"{e.sender_id}_{phone}"] = task

        except asyncio.TimeoutError:
            await conv.send_message("❌ Quá thời gian nhập liệu.")
        except Exception as err:
            await conv.send_message(f"❌ Lỗi: {err}")

# 2. Admin Broadcast (Sử dụng Conversation an toàn)
@bot.on(events.CallbackQuery(data=b"adm_broadcast"))
async def admin_broadcast_conv(e):
    if str(e.sender_id) != str(ADMIN_ID): return
    
    async with bot.conversation(e.sender_id) as conv:
        await conv.send_message("📢 **NHẬP NỘI DUNG THÔNG BÁO:**\n(Gửi tin nhắn text hoặc ảnh để gửi cho TOÀN BỘ thành viên)")
        resp = await conv.get_response()
        msg_content = resp.message
        
        await conv.send_message("⏳ Đang gửi...")
        
        # Lấy danh sách user
        users = supabase.table("users").select("user_id").execute()
        count = 0
        for u in users.data:
            try:
                await bot.send_message(int(u['user_id']), msg_content)
                count += 1
                await asyncio.sleep(0.05)
            except: pass
        
        await conv.send_message(f"✅ Đã gửi xong cho {count} người!")

# ================= WEBHOOK & MAIN =================
@app.route('/sepay-webhook', methods=['POST'])
async def webhook():
    d = await request.json
    content = d.get("content", "").upper()
    m = re.search(r'NAP\s+(\d+)', content)
    if m:
        uid = int(m.group(1))
        amt = int(d.get("transferAmount", 0))
        
        user_res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        if user_res.data:
            new_bal = user_res.data[0]['balance'] + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", uid).execute()
            
            bot.loop.create_task(bot.send_message(uid, f"✅ **NẠP TIỀN THÀNH CÔNG!**\n💰 +{amt:,} VNĐ\n💳 Số dư mới: {new_bal:,} VNĐ"))
            bot.loop.create_task(bot.send_message(ADMIN_ID, f"📢 User `{uid}` nạp `{amt:,}` VNĐ"))
            
    return jsonify({"success": True}), 200

@app.route('/')
async def home(): return "Bot Alive!", 200

async def main():
    print(">>> BOT STARTING...")
    await bot.start(bot_token=BOT_TOKEN)
    
    # Khôi phục các Clone từ DB
    print(">>> RESTORING CLONES...")
    clones = supabase.table("my_clones").select("*").execute()
    for c in clones.data:
        # Kiểm tra hạn trước khi chạy
        exp = datetime.fromisoformat(c['expiry'].replace('Z', '+00:00'))
        if exp > datetime.now(timezone.utc):
            task = asyncio.create_task(run_clone_worker(c['session'], c['phone'], c['owner_id'], c['id']))
            active_tasks[f"{c['owner_id']}_{c['phone']}"] = task
            print(f" -> Started: {c['phone']}")
        else:
            print(f" -> Expired: {c['phone']}")

    await asyncio.gather(
        bot.run_until_disconnected(),
        app.run_task(host='0.0.0.0', port=10000)
    )

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
    

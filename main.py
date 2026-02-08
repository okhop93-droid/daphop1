import asyncio, re, os, random, logging
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify
from telethon import TelegramClient, events, Button as TButton
from telethon.sessions import StringSession
from supabase import create_client, Client

# ===== CẤU HÌNH ĐÃ FIX THEO ẢNH CỦA BẠN =====
SUPABASE_URL = "https://qaptttdmntjwsizodhdv.supabase.co" # Đã sửa theo ảnh thực tế
SUPABASE_KEY = "sb_publishable_095TgJvOydJ-T9XzMg7ZYg_gr_a1LcA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_ID = 36437338
API_HASH = "18d34c7efc396d277f3db62baa078efc"
BOT_TOKEN = "8361903272:AAFcJMZZ0ykvrFBoH0TYP7h7SlwHbim56tU"
BOT_GAME_TARGET = "xocdia88_bot_uytin_bot"

logging.basicConfig(level=logging.INFO)
bot = TelegramClient(StringSession(), API_ID, API_HASH)

# --- WORKER ĐẬP HỘP ---
async def worker_grab_loop(client, phone, owner_id):
    @client.on(events.NewMessage(chats=BOT_GAME_TARGET))
    async def handler(ev):
        if ev.reply_markup:
            btn = next((b for r in ev.reply_markup.rows for b in r.buttons if "đập" in b.text.lower()), None)
            if btn:
                await asyncio.sleep(random.uniform(0.1, 0.4))
                try:
                    await ev.click()
                    await asyncio.sleep(2.0)
                    msgs = await client.get_messages(BOT_GAME_TARGET, limit=1)
                    if msgs and "là:" in msgs[0].message:
                        code = re.search(r'là:\s*([A-Z0-9]+)', msgs[0].message).group(1)
                        await bot.send_message(owner_id, f"🎊 **CLONE `{phone}` TRÚNG!**\n🔑 Code: `{code}`")
                except: pass

# --- CHỐNG SPAM 2 TIN (QUAN TRỌNG) ---
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    try:
        # Lấy số dư thực tế từ DB
        res = supabase.table("users").select("balance").eq("user_id", e.sender_id).execute()
        bal = res.data[0]['balance'] if res.data else 0
        
        await e.respond(f"🦅 **TREO CLONE ONLINE**\n💰 Ví: **{bal:,}đ**", 
            buttons=[
                [TButton.inline("➕ THÊM ACC", b"add"), TButton.inline("⏳ GIA HẠN", b"rent")],
                [TButton.inline("👤 VÍ TIỀN", b"me"), TButton.inline("🏦 NẠP TIỀN", b"dep")],
                [TButton.inline("📱 CLONE CỦA TÔI", b"list")]
            ])
    except Exception as ex:
        logging.error(f"Lỗi DB: {ex}")
    
    # Lệnh này cực kỳ quan trọng để ngăn bản bot cũ phản hồi đè lên
    raise events.StopPropagation 

# --- WEB SERVER FIX PORT RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "BOT IS LIVE"

@app.route('/sepay-webhook', methods=['POST'])
def webhook():
    d = request.json
    m = re.search(r'NAP\s+(\d+)', d.get("content", "").upper())
    if m:
        uid, amt = int(m.group(1)), int(d.get("transferAmount", 0))
        res = supabase.table("users").select("balance").eq("user_id", uid).execute()
        new_bal = (res.data[0]['balance'] if res.data else 0) + amt
        supabase.table("users").upsert({"user_id": uid, "balance": new_bal}).execute()
        asyncio.run_coroutine_threadsafe(bot.send_message(uid, f"💰 +{amt:,}đ thành công!"), asyncio.get_event_loop())
    return jsonify({"status": "ok"}), 200

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot started successfully.")
    
    # Tự khởi động lại các clone đang treo
    try:
        clones = supabase.table("my_clones").select("*").execute()
        for c in clones.data:
            try:
                cl = TelegramClient(StringSession(c['session']), API_ID, API_HASH)
                await cl.connect()
                asyncio.create_task(worker_grab_loop(cl, c['phone'], c['owner_id']))
            except: pass
    except: pass
    
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # Chạy Web Server trong luồng riêng để Render không báo lỗi Port
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
        

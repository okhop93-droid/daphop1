import os, asyncio, sqlite3, requests
from telethon import TelegramClient, events
from flask import Flask
from threading import Thread

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

SEPAY_API = "https://api.sepay.vn/api/v1/transactions"
SEPAY_KEY = os.getenv("SEPAY_API_KEY")

CHECK_DELAY = 5  # giây
# =========================================

# ================= DATABASE ===============
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
  tg_id INTEGER PRIMARY KEY,
  balance INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS txs(
  txid TEXT PRIMARY KEY
)
""")
db.commit()
# =========================================

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ================= USER ===================
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    cur.execute("INSERT OR IGNORE INTO users (tg_id,balance) VALUES (?,0)", (uid,))
    db.commit()

    await e.reply(
        "💰 NẠP TIỀN TỰ ĐỘNG\n\n"
        "👉 Chuyển khoản và ghi chú:\n"
        f"🔑 {uid}\n\n"
        "⚠️ Ghi ĐÚNG Telegram ID để được cộng tiền"
    )

@bot.on(events.NewMessage(pattern="/balance"))
async def balance(e):
    cur.execute("SELECT balance FROM users WHERE tg_id=?", (e.sender_id,))
    bal = cur.fetchone()[0]
    await e.reply(f"💰 Số dư: {bal:,}đ")

# ================= CORE ===================
def is_paid(txid):
    cur.execute("SELECT 1 FROM txs WHERE txid=?", (txid,))
    return cur.fetchone()

def save_tx(txid):
    cur.execute("INSERT INTO txs VALUES (?)", (txid,))
    db.commit()

def add_money(uid, amount):
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE tg_id=?",
        (amount, uid)
    )
    db.commit()

async def check_sepay():
    headers = {
        "Authorization": f"Bearer {SEPAY_KEY}"
    }

    while True:
        try:
            res = requests.get(SEPAY_API, headers=headers, timeout=10).json()
            txs = res["data"]["transactions"]

            for tx in txs:
                if tx["transactionType"] != "IN":
                    continue

                remark = str(tx["description"]).strip()
                if not remark.isdigit():
                    continue

                uid = int(remark)
                amount = int(tx["amount"])
                txid = f"sepay_{tx['id']}"

                if is_paid(txid):
                    continue

                cur.execute("SELECT 1 FROM users WHERE tg_id=?", (uid,))
                if not cur.fetchone():
                    continue

                add_money(uid, amount)
                save_tx(txid)

                await bot.send_message(
                    uid,
                    f"✅ Nạp tiền thành công\n💰 +{amount:,}đ"
                )

        except Exception as e:
            print("SEPAY ERROR:", e)

        await asyncio.sleep(CHECK_DELAY)

# ================= KEEP ALIVE =============
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

def run_web():
    app.run(host="0.0.0.0", port=10000)

Thread(target=run_web).start()

bot.loop.create_task(check_sepay())
bot.run_until_disconnected()

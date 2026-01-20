import os, asyncio, sqlite3, requests
from telethon import TelegramClient, events, Button
from flask import Flask
from threading import Thread

# ========= ENV =========
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
SEPAY_KEY = os.getenv("SEPAY_API_KEY")

SEPAY_API = "https://api.sepay.vn/api/v1/transactions"
CHECK_DELAY = 5
# =======================

# ========= DB ==========
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
  tg_id INTEGER PRIMARY KEY,
  balance INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS banks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  owner TEXT,
  acc TEXT,
  qr TEXT,
  active INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS txs(
  txid TEXT PRIMARY KEY
)
""")
db.commit()
# =======================

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ========= USER =========
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,0)", (uid,))
    db.commit()

    cur.execute("SELECT id,name FROM banks WHERE active=1")
    banks = cur.fetchall()

    if not banks:
        await e.reply("❌ Chưa có bank")
        return

    buttons = [[Button.inline(f"🏦 {b[1]}", data=f"bank_{b[0]}")] for b in banks]

    await e.reply(
        "💰 NẠP TIỀN\n👉 Chọn ngân hàng:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"bank_"))
async def choose_bank(e):
    bank_id = int(e.data.decode().split("_")[1])
    uid = e.sender_id

    cur.execute("SELECT name,owner,acc,qr FROM banks WHERE id=?", (bank_id,))
    name, owner, acc, qr = cur.fetchone()

    msg = (
        f"🏦 {name}\n"
        f"👤 {owner}\n"
        f"💳 {acc}\n\n"
        "👉 Nội dung chuyển khoản:\n"
        f"{uid}"
    )

    await e.edit(msg)
    if qr:
        await bot.send_file(uid, qr)

@bot.on(events.NewMessage(pattern="/balance"))
async def balance(e):
    cur.execute("SELECT balance FROM users WHERE tg_id=?", (e.sender_id,))
    bal = cur.fetchone()[0]
    await e.reply(f"💰 Số dư: {bal:,}đ")

# ========= ADMIN =========
@bot.on(events.NewMessage(pattern="/addbank"))
async def addbank(e):
    if e.sender_id != ADMIN_ID:
        return
    try:
        _, name, owner, acc, qr = e.raw_text.split(maxsplit=4)
        cur.execute(
            "INSERT INTO banks (name,owner,acc,qr,active) VALUES (?,?,?,?,1)",
            (name, owner, acc, qr)
        )
        db.commit()
        await e.reply("✅ Đã thêm bank")
    except:
        await e.reply("❌ /addbank TEN CHUTK STK QR_URL")

# ========= CORE =========
def paid(txid):
    cur.execute("SELECT 1 FROM txs WHERE txid=?", (txid,))
    return cur.fetchone()

def save_tx(txid):
    cur.execute("INSERT INTO txs VALUES (?)", (txid,))
    db.commit()

def add_money(uid, amt):
    cur.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amt, uid))
    db.commit()

async def check_sepay():
    headers = {"Authorization": f"Bearer {SEPAY_KEY}"}
    while True:
        try:
            res = requests.get(SEPAY_API, headers=headers, timeout=10).json()
            for tx in res["data"]["transactions"]:
                if tx["transactionType"] != "IN":
                    continue

                remark = str(tx["description"]).strip()
                if not remark.isdigit():
                    continue

                uid = int(remark)
                amount = int(tx["amount"])
                txid = f"sepay_{tx['id']}"

                if paid(txid):
                    continue

                cur.execute("SELECT 1 FROM users WHERE tg_id=?", (uid,))
                if not cur.fetchone():
                    continue

                add_money(uid, amount)
                save_tx(txid)

                await bot.send_message(
                    uid,
                    f"✅ Nạp thành công\n💰 +{amount:,}đ"
                )
        except Exception as e:
            print("SEPAY ERR:", e)

        await asyncio.sleep(CHECK_DELAY)

# ========= KEEP ALIVE =========
app = Flask(__name__)
@app.route("/")
def home():
    return "OK"

Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()

bot.loop.create_task(check_sepay())
bot.run_until_disconnected()

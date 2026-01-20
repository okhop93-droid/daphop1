import asyncio, re, sqlite3, random, requests
from telethon import TelegramClient, events
from flask import Flask
from threading import Thread

# ====== CẤU HÌNH ======
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # telegram id admin

CHECK_DELAY = 5  # giây

# ====== DATABASE ======
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
  tg_id INTEGER PRIMARY KEY,
  deposit_id TEXT UNIQUE,
  balance INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS banks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  acc_no TEXT,
  api_url TEXT,
  active INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS txs(
  txid TEXT PRIMARY KEY
)
""")

db.commit()

# ====== BOT ======
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def gen_deposit_id():
    return str(random.randint(100000, 999999))

# ====== USER ======
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    cur.execute("SELECT deposit_id FROM users WHERE tg_id=?", (uid,))
    row = cur.fetchone()

    if not row:
        did = gen_deposit_id()
        cur.execute(
            "INSERT INTO users VALUES (?,?,0)",
            (uid, did)
        )
        db.commit()
    else:
        did = row[0]

    cur.execute("SELECT name, acc_no FROM banks WHERE active=1")
    banks = cur.fetchall()

    msg = (
        "💰 NẠP TIỀN TỰ ĐỘNG\n\n"
        "👉 Ghi chú khi chuyển khoản:\n"
        f"🔑 {did}\n\n"
    )

    if banks:
        msg += "🏦 BANK HỖ TRỢ:\n"
        for b in banks:
            msg += f"- {b[0]} | STK: {b[1]}\n"
    else:
        msg += "⚠️ Chưa có bank nào được thêm"

    await e.reply(msg)

@bot.on(events.NewMessage(pattern="/balance"))
async def balance(e):
    cur.execute("SELECT balance FROM users WHERE tg_id=?", (e.sender_id,))
    bal = cur.fetchone()[0]
    await e.reply(f"💰 Số dư: {bal}đ")

# ====== ADMIN ======
@bot.on(events.NewMessage(pattern="/addbank"))
async def addbank(e):
    if e.sender_id != ADMIN_ID:
        return

    try:
        _, name, acc, api = e.raw_text.split(maxsplit=3)
        cur.execute(
            "INSERT INTO banks (name, acc_no, api_url, active) VALUES (?,?,?,1)",
            (name, acc, api)
        )
        db.commit()
        await e.reply(f"✅ Đã thêm bank {name}")
    except:
        await e.reply("❌ Sai cú pháp\n/addbank TEN STK API_URL")

@bot.on(events.NewMessage(pattern="/banks"))
async def banks(e):
    cur.execute("SELECT name, acc_no FROM banks WHERE active=1")
    rows = cur.fetchall()
    if not rows:
        await e.reply("❌ Chưa có bank")
        return
    msg = "🏦 BANK ĐANG CHẠY:\n"
    for r in rows:
        msg += f"- {r[0]} | {r[1]}\n"
    await e.reply(msg)

# ====== CORE LOGIC ======
def is_done(txid):
    cur.execute("SELECT 1 FROM txs WHERE txid=?", (txid,))
    return cur.fetchone()

def save_tx(txid):
    cur.execute("INSERT INTO txs VALUES (?)", (txid,))
    db.commit()

def add_money(uid, amt):
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE tg_id=?",
        (amt, uid)
    )
    db.commit()

async def check_banks():
    while True:
        cur.execute("SELECT name, api_url FROM banks WHERE active=1")
        banks = cur.fetchall()

        for name, api in banks:
            try:
                data = requests.get(api, timeout=10).json()
                for tx in data["data"]["history"]:
                    if tx["dcSign"] != "C":
                        continue

                    txid = f"{name}_{tx['coreSn']}"
                    if is_done(txid):
                        continue

                    remark = tx["remark"]

                    cur.execute(
                        "SELECT tg_id FROM users WHERE ? LIKE '%' || deposit_id || '%'",
                        (remark,)
                    )
                    row = cur.fetchone()
                    if not row:
                        continue

                    uid = row[0]
                    amount = tx["amount"]

                    add_money(uid, amount)
                    save_tx(txid)

                    await bot.send_message(
                        uid,
                        f"✅ Nạp tiền thành công\n"
                        f"🏦 {name}\n"
                        f"💰 +{amount}đ"
                    )
            except Exception as e:
                print(name, e)

        await asyncio.sleep(CHECK_DELAY)

# ====== KEEP ALIVE ======
app = Flask(__name__)
@app.route("/")
def home():
    return "OK"

def run_web():
    app.run(host="0.0.0.0", port=10000)

Thread(target=run_web).start()
bot.loop.create_task(check_banks())
bot.run_until_disconnected()

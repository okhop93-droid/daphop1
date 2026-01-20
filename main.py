import os, asyncio, sqlite3
from telethon import TelegramClient, events, Button
from flask import Flask, request, jsonify
from threading import Thread

# ===== ENV =====
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ===== DB =====
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

# ===== BOT =====
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===== USER =====
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,0)", (uid,))
    db.commit()

    cur.execute("SELECT id,name FROM banks WHERE active=1")
    banks = cur.fetchall()

    if not banks:
        await e.reply("❌ Chưa có ngân hàng nạp tiền")
        return

    buttons = [[Button.inline(f"🏦 {b[1]}", data=f"bank_{b[0]}")] for b in banks]
    await e.reply("💰 NẠP TIỀN\nChọn ngân hàng:", buttons=buttons)

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
        "📌 Ghi chú chuyển khoản:\n"
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

# ===== ADMIN =====
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
        await e.reply("✅ Đã thêm ngân hàng")
    except:
        await e.reply("❌ /addbank TEN_NH CHU_TK STK QR_URL")

# ===== CORE =====
def paid(txid):
    cur.execute("SELECT 1 FROM txs WHERE txid=?", (txid,))
    return cur.fetchone()

def save_tx(txid):
    cur.execute("INSERT INTO txs VALUES (?)", (txid,))
    db.commit()

def add_money(uid, amt):
    cur.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amt, uid))
    db.commit()

# ===== WEBHOOK =====
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

@app.route("/sepay", methods=["POST"])
def sepay_hook():
    data = request.json

    if data.get("transactionType") != "IN":
        return jsonify(ok=True)

    note = str(data.get("description", "")).strip()
    if not note.isdigit():
        return jsonify(ok=True)

    uid = int(note)
    txid = "sepay_" + str(data["id"])
    amount = int(data["amount"])

    if paid(txid):
        return jsonify(ok=True)

    cur.execute("SELECT 1 FROM users WHERE tg_id=?", (uid,))
    if not cur.fetchone():
        return jsonify(ok=True)

    add_money(uid, amount)
    save_tx(txid)

    asyncio.run_coroutine_threadsafe(
        bot.send_message(uid, f"✅ Nạp thành công\n💰 +{amount:,}đ"),
        bot.loop
    )

    return jsonify(ok=True)

Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
bot.run_until_disconnected()

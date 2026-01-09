from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio, random
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT = 'xocdia88_bot_uytin_bot'

# Chỉ giữ lại Session của ACC 2 (Duy Khiêm)
SESSION_ACC2 = '1BVtsOJEBu7d4nbO-iggb0fMc3YmCHEn84ExMGjwFvuLTEVZz2rAUWI8ZAUm-1xb3v_z9sWw77k_EJfnnSF6x17KZx_TIBBiiCOckGlusoEPhYb1Ta-Dw4xJf-t_vA6pCyLSS1B7Zc-n4I5z3aKNv4t903xy2X1Xal4w4SIjDyigwSA_SxHVcVXF360fGB8tUND0qYNJ-DupLJHucJN9v8ewlv2j81e658glX7DVOSYtge90MhqOoe6mk236xkPndMTd5PECg9h_j9_d5yJp6HD3R7LTFBG-t-kQcg8K8Yzwer2ez_CI7fig9MegWle1aaFIOVjykX7Oo1V-UcjrnU3hzP3AnWMQ='

app = Flask('')
@app.route('/')
def home(): return "ACC_2_ONLY_RUNNING"

async def main():
    # Chạy Web Server để giữ app sống
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    
    print("🚀 ĐANG KHỞI CHẠY DUY NHẤT ACC 2 (DUY KHIÊM)...", flush=True)
    
    try:
        client = TelegramClient(StringSession(SESSION_ACC2), API_ID, API_HASH)
        await client.start()
        print("✅ ACC 2 ĐÃ ONLINE - CHẾ ĐỘ CHẠY ĐƠN LẺ!", flush=True)

        @client.on(events.NewMessage(chats=BOT))
        async def work(e):
            if e.reply_markup:
                for row in e.reply_markup.rows:
                    for btn in row.buttons:
                        if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                            await asyncio.sleep(random.uniform(0.1, 0.4))
                            try:
                                await e.click()
                                print("💰 ACC 2 VỪA HÚP QUÀ THÀNH CÔNG!", flush=True)
                            except: pass

        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ LỖI ACC 2: {e}", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
    

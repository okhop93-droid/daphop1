from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio, random, datetime
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626  # ID Nhóm log của bạn

# Session của ACC 2 (Duy Khiêm)
SESSION_ACC2 = '1BVtsOJEBu7d4nbO-iggb0fMc3YmCHEn84ExMGjwFvuLTEVZz2rAUWI8ZAUm-1xb3v_z9sWw77k_EJfnnSF6x17KZx_TIBBiiCOckGlusoEPhYb1Ta-Dw4xJf-t_vA6pCyLSS1B7Zc-n4I5z3aKNv4t903xy2X1Xal4w4SIjDyigwSA_SxHVcVXF360fGB8tUND0qYNJ-DupLJHucJN9v8ewlv2j81e658glX7DVOSYtge90MhqOoe6mk236xkPndMTd5PECg9h_j9_d5yJp6HD3R7LTFBG-t-kQcg8K8Yzwer2ez_CI7fig9MegWle1aaFIOVjykX7Oo1V-UcjrnU3hzP3AnWMQ='

app = Flask('')
@app.route('/')
def home(): return "DUY_KHIEM_ONLINE"

async def main():
    # Khởi động Web Server để giữ app không bị ngủ (Idle) trên Koyeb
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    
    print("🚀 ĐANG KHỞI CHẠY ACC 2 (DUY KHIÊM) + GỬI LOG...", flush=True)
    
    try:
        client = TelegramClient(StringSession(SESSION_ACC2), API_ID, API_HASH)
        await client.start()
        
        # Gửi thông báo chào sân vào nhóm
        await client.send_message(GR_LOG, f"🔔 [ACC 2] Duy Khiêm đã lên sóng và bắt đầu canh quà!")
        print("✅ ĐÃ ONLINE VÀ BÁO VỀ NHÓM!", flush=True)

        @client.on(events.NewMessage(chats=BOT))
        async def work(e):
            if e.reply_markup:
                for row in e.reply_markup.rows:
                    for btn in row.buttons:
                        if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                            # Delay nhẹ để né quét bot
                            await asyncio.sleep(random.uniform(0.1, 0.4))
                            try:
                                await e.click()
                                # Gửi báo cáo thành tích về nhóm
                                await client.send_message(GR_LOG, f"💰 [ACC 2] Duy Khiêm vừa HÚP QUÀ thành công!")
                                print("💰 ĐÃ HÚP QUÀ & BÁO VỀ NHÓM!", flush=True)
                            except: pass

        await client.run_until_disconnected()
    except Exception as e:
        # Nếu lỗi sẽ in ra log để bạn kiểm tra trong Console
        print(f"❌ LỖI ACC 2: {e}", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
    

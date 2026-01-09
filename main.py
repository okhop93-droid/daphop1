from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from flask import Flask
from threading import Thread

# ================= CẤU HÌNH 4 TÀI KHOẢN ĐÃ TỐI ƯU =================
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'

SESSIONS = [
    '1BVtsOHcBu8TACaW1Ta75fOIb_gLv298uIs1nOu94n9C_T29JOIIvLNieuEj9dLOGhPkrYaRlNjr36yrxYUEnAAh_rB-Ltz1qhPfSeoFaA8KegGww8wQH4flVJYDyznYZwIiJKd2Pzm0DkO0o3hyymZYk2HqyG6C4uc6TO1JHGlfuglZZ5OIlEJmhMtFiktHuMcsMaDZuk3GHH_XerhoIzaa4dMVR6ygGWobvoxBYUqnsvlMH8Z7Y7_UGsvMfWkbpsqHp32W2EU6qQZAfEmWOgqE-8ICRDa91nxbYIx_5cRLKdGu1mozMva2gb4FmRXspwGgZgHE_HXg7L4jaaakkLmZhinmJSZc=', # TK 1
    '1BVtsOGwBu0vOnj7QDGk-8z2W8xZIJijPnE84fBY97pPnxw2OO0Q2nyVKDffyQqfHYnS1B0UBlU36RYhXDJIVktVX2EaUVOCHInNzLcW3fXOW6HK1PSdB2Eryu3urciF0HLZacVsRonlcri6ZQ3FEfVMLoD8t1x8e3QmarOx7PsEwp6I76T97w5mxcqPAVlI3mNkpkvmLQDkvfB20Y32eivSB9MSx60LKeRhDKgAUCK3B9Y1N9LhfTRL4FvST4UzqNns6rRu0igFqwj_hGNZI1hHc1anvglivQs26lpIhyPB1n0sStinWi1OgUk-Jl3ISSBw083wFsXAU1cghy6DBuyy2krs28qg=', # TK 2
    '1BVtsOK4Bu51MyphJzUwhW96UwtebS2W-i8XBb3vQ7czXBYGiFA3Ld5DPeGZnbIvnFt9TM0RZbDY-Mr-IUFOPZY0NZ3q4-fMR6A4SZZz08BxPtdNT5PSK9RopS4wX44QG0xR-SczdzWnpiuMQtWt_smH8zb-hx5TEonTg6ZPjHTu_toEQ1zbNEADY9NZ8ebf7k4P0CLAg1jFTttqEZPp9m-Qt2upSORdzXiZOopKvfljIoXf-_520W95c73c_bqmFO8JlCuR2JRhvOMOZyKyCo32Lg4L1Gx8cPxm_oIre7rmjl8gDc_aKoszUYyCeaXFtp0sgOSPtLz2e3Qg2LEHSpK_hCOrVlNw=', # TK 3
    '1BVtsOK4BuwpGq_faVDlXlljoL4tjxj1r_9DbzkOjXAdAQTB0RyUfsIjmxU3EhchOLOEH2T34w7q_OP-ZF2O-q7v7uHSPU3kwlDMeA5GmJDT06tkrqfnXoML3KGH84zNmlvHLjRBYTk7MeSUC_8b-jQOI07lsRkfWvDdOOXdrFGIf_DwXvzoRwfe4CECFu10F2xpUj52g9F_wl3j5wJXSwfRewPJBP6CFt9fIJFujbZkH9kdyuGozrs5oY9BXVw2EtnwMfhBKzf_liysPqlDIRjA53y_GtO19J-dLVDhGwpRdTq174dA_i5j8z-y8CYiFTm4hSwNTqoXMyC4UuYOjBjg6ra6U53A='  # TK 4
]

TARGET_BOT = 'xocdia88_bot_uytin_bot' 
GROUP_TARGET = -1002984339626 
# ==============================================================

async def start_bot(session_str, account_no):
    client = TelegramClient(
        StringSession(session_str), 
        API_ID, API_HASH,
        connection_retries=None,
        retry_delay=15,
        auto_reconnect=True,
        device_model=f"DapHop_V{account_no}",
        system_version="Android 14"
    )
    
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ TK {account_no} ({me.first_name}) - ĐÃ ONLINE!")

        @client.on(events.NewMessage(chats=TARGET_BOT))
        async def handler(event):
            if event.reply_markup:
                for row in event.reply_markup.rows:
                    for button in row.buttons:
                        if "Đập Hộp" in button.text:
                            # Delay nhẹ để né lỗi nghẽn lệnh
                            await asyncio.sleep(account_no * 0.5)
                            try:
                                await event.click()
                                print(f"--- [TK {account_no}] Click thành công! ---")
                            except Exception: pass
            
            if any(word in event.raw_text for word in ["Code", "Mã", "quà"]):
                await client.send_message(GROUP_TARGET, f"🎁 [TK {account_no}] QUÀ:\n{event.raw_text}")

        await client.run_until_disconnected()
    except Exception as e:
        print(f"⚠️ TK {account_no} tạm dừng: {e}")

# Flask để giữ Koyeb sống
app = Flask('')
@app.route('/')
def home(): return "Bot 4 tài khoản đang trực chiến 24/7!"

def run_flask(): app.run(host='0.0.0.0', port=8080)

async def main():
    # FIX QUAN TRỌNG: Khởi động các acc cách nhau 10 giây để tránh lỗi Timestamp
    print("🚀 Đang khởi động đội hình...")
    for i, session in enumerate(SESSIONS):
        if len(session) > 50:
            asyncio.create_task(start_bot(session, i + 1))
            await asyncio.sleep(10) # Chờ 10s mới bật acc tiếp theo
    
    # Giữ cho script luôn chạy
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    

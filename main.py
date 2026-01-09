from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from flask import Flask
from threading import Thread

# ================= CẤU HÌNH 4 TÀI KHOẢN ĐÃ FIX =================
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
# =============================================================

async def start_bot(session_str, account_no):
    client = TelegramClient(
        StringSession(session_str), 
        API_ID, API_HASH,
        connection_retries=None, # Tự động kết nối lại vĩnh viễn
        retry_delay=15,         # Chờ 15 giây nếu gặp lỗi mạng
        auto_reconnect=True,
        device_model=f"DapHop_V{account_no}", # Fix lỗi 2 IP bằng cách giả lập model khác nhau
        system_version="Android 14"
    )
    
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ TK {account_no} ({me.first_name}) - ĐÃ ONLINE VÀ FIX LỖI!")

        @client.on(events.NewMessage(chats=TARGET_BOT))
        async def handler(event):
            # Tự động click Đập Hộp
            if event.reply_markup:
                for row in event.reply_markup.rows:
                    for button in row.buttons:
                        if "Đập Hộp" in button.text:
                            # Delay tăng dần theo số thứ tự TK để tránh spam
                            await asyncio.sleep(account_no * 0.4)
                            try:
                                await event.click()
                                print(f"--- [TK {account_no}] Đã nhấn đập hộp thành công! ---")
                            except Exception as click_err:
                                print(f"Lỗi click TK {account_no}: {click_err}")
            
            # Gửi thông báo về nhóm
            if any(word in event.raw_text for word in ["Code", "Mã", "quà"]):
                await client.send_message(GROUP_TARGET, f"🎁 [TK {account_no}] LẤY ĐƯỢC QUÀ:\n\n{event.raw_text}")

        await client.run_until_disconnected()
    except Exception as e:
        print(f"⚠️ TK {account_no} dừng do: {e}")

# Phần Flask giữ cho Koyeb không tắt
app = Flask('')
@app.route('/')
def home(): return "Bot đang chạy ổn định với 4 tài khoản!"

def run_flask(): app.run(host='0.0.0.0', port=8080)

async def main():
    # Chỉ chạy những session có dữ liệu
    tasks = [start_bot(s, i + 1) for i, s in enumerate(SESSIONS) if len(s) > 50]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    asyncio.run(main())
    

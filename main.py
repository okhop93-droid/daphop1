from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from flask import Flask
from threading import Thread
import os

# ================= CẤU HÌNH 10 TÀI KHOẢN =================
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'

SESSIONS = [
    '1BVtsOHcBu8TACaW1Ta75fOIb_gLv298uIs1nOu94n9C_T29JOIIvLNieuEj9dLOGhPkrYaRlNjr36yrxYUEnAAh_rB-Ltz1qhPfSeoFaA8KegGww8wQH4flVJYDyznYZwIiJKd2Pzm0DkO0o3hyymZYk2HqyG6C4uc6TO1JHGlfuglZZ5OIlEJmhMtFiktHuMcsMaDZuk3GHH_XerhoIzaa4dMVR6ygGWobvoxBYUqnsvlMH8Z7Y7_UGsvMfWkbpsqHp32W2EU6qQZAfEmWOgqE-8ICRDa91nxbYIx_5cRLKdGu1mozMva2gb4FmRXspwGgZgHE_HXg7L4jaaakkLmZhinmJSZc=',
    '1BVtsOGwBu0vOnj7QDGk-8z2W8xZIJijPnE84fBY97pPnxw2OO0Q2nyVKDffyQqfHYnS1B0UBlU36RYhXDJIVktVX2EaUVOCHInNzLcW3fXOW6HK1PSdB2Eryu3urciF0HLZacVsRonlcri6ZQ3FEfVMLoD8t1x8e3QmarOx7PsEwp6I76T97w5mxcqPAVlI3mNkpkvmLQDkvfB20Y32eivSB9MSx60LKeRhDKgAUCK3B9Y1N9LhfTRL4FvST4UzqNns6rRu0igFqwj_hGNZI1hHc1anvglivQs26lpIhyPB1n0sStinWi1OgUk-Jl3ISSBw083wFsXAU1cghy6DBuyy2krs28qg=',
    '1BVtsOMABu1kfzNAPqjziS6UaVJ5B00wpU9p0LFqF2iswM9wfYs_OGy9Y8QrXVyyphVdIHeSsa3Zdy035v08qS1bvxJBRDFbRKm08kOifsASyietVxbepB_-UuxHTnhFr48qP_SxcGbXqjyN4SAPJmJUGdGXrujbebzj0Q5iWvq4PTAKI84loYAe1q_K3rJ5Lqerm3SCre8nNWE02HaCHdy6GOWLkbEY5LKgEfDoKRSsgs7LM9NTFXNDjQm9GNO4UZERAvTjIijwCydSCm4sEqyNNMGC1hWeI88BGn_V9Buxq33q24CrPyh7JGdaiU6lVCzZSLBsjSVyYR55rR6kOWLV0Bhmd9b8=',
    '1BVtsOGgBuw51zegyV3ruS4iLSpBRYPklUjcw9DPcL61QA6NK-HjF3XHNhSTVmsFxcF4kiR6pa2-RSsn_A7NL-3I2zrFw-QG9z2vB8hstD9lwrNtAGMBPEUGGjtzNDZRVpk27XjYx-WAQJ8PM-cHtrxTERXu6msuDd5xafYwWLM0_j8_R0ilVze9CUGv5G6Od1DdvehXJpB8JVPqZ7mNNSY8lwGHHBQT0CcovY75hAqS6lVDVfTfGkAF1cQpWn3X4NEfggX7khcvyMIMP6t2vqoloou8gCrOo-O9j7EAbORUotaRwEU-otaBUz3P-hmhYPj8h4ZrXN_qt9gUz58wUGI81K9n4C3U=',
    '1BVtsOJgBu44Cnn7A6SnsKZQFLi0BRJXv68YeVLiy6aFJGZQBCe99jwwOshpYEixwaKkP6RYgsJU9D2q6aoFKz-BRMLFx6Idj2CeCWh-SagQEv6OTU0F8v5YQLmqz85MoEDM1DNKRjzMUwdzVTXR4YvrqCX38AjaIXeZ3ycLPoO8tVbZp3kavvka1cXxpHMlhpotyT0cxsIR_ypxh4thFND5KcSWx7ZR6hwZavb4yJ7VsjbXMO4WSPiwJSeFaWjImjf9iIDi_qBsxbanBEF7euBbSBwqgycfV8c_YWIt6LBRaUT_2-rshWN3JMVNwzoGZxBNsbOIiP66E6kCGCY1JRCDpsfWPt3Q=',
    '1BVtsOIIBu1sYauL40270RyO_2yFPTJjnnTVpJwaSCn28BQzNpPI_hLrH-Xyq5_QIYSCTUMCaGZBFrCp_W4Ol_U7T7Haet8hJBiWp_B3QQYGEln5O7qMeoX_63cKS6CvvtAWB5lz8Wper_aElOju_FTloh2rVMRISTYG6uvUBPb3lpJnlpbVGnYPHSR5jhO9TbRbv_TmoIZhTufSb9JoEgnxZ_21mZT64DN4VYcKwMui_bC9ecrcAXLRozIH1phsui7jgoe-vpa6yn2t3nSdmUMjB_Nm5VYKFt9ziN5aQ_lAtwIUA3CMnlKqgDfzEhVGB-6E0CiV0pdJiDk_9x0gbycquC7jgrg8=',
    '1BVtsOIIBu2Iz3Zw6TLch2lCEQNnj339UK5lGFYsK1I_85eNbSKOU8BeT-o4sxUtzX5v94JabIzQTbd5MKwEeVXE5UIEJCyoqiqsDDsDo6VLxU0ixgEpLxWrjP1Qp0dhvjjGtxhhMwoiZdAB2wTQ_7G3YsY2R8712NRjm9MIE3V2KgRMnpjwdeVbfOPhvMF7g8aWDKb067fX1ofLCdeztadS_UxWMKGP20vMVRuPT-AJ8uSdg1zAMkzVWGhh5urPErlDGfFBnrfGBL6bYBSz120Ux_L6Kx5rIu4qodPI6pHgFBl5zRzDgIblEDuX1o6GkkZNdaq2z4Vd5HUYImBTjZhnziRFr-FQ=',
    '1BVtsOIIBu7wNEzZ8FLg9TAapqZKM4MG3tp2EaoY1X36iNHZk1xLkiNjEmEsrcktIPzdptyYUwIFr8D1qX0d1xSRIKfWbjt7O88njsOrwEJF6xYSpF6E1rUvVgdTYany0R1M0ugsXkteyBgTsn2rAqA6o8mB2BZ8r0QC0oWBj1a2ejkqybHBkIP6NVITz3x08zFZCgd1RtLjNZIJL57h9E_1gt7vWYy8bTA6ytLtwnKjLyXMagxBa3VS-5r726ztTZJdx4HszeSaSJ9canUcPYp1V1wHwt_cz_iwDZPAsEU8x_tXNWbDxkQKSxxcrdTrsWryeMp6YaLKwfBqrYJijz7YYVaR977E=',
    '1BVtsOIIBuyYFu_9I1AJNGF41H7LTcLGU-VTvChqBP0YHtZAiAH-QzijK4-dkdS5sP2yAkiioUDfldDKiGO_dJlpxCBJtMwzqE6BsOqnTfH0i9H4KzQlz7un1wQPzv_GfBxwnlBo65aupcLgRHOprnFZRTYpQVTqL4U5n2nSvSBj4ifiKt7vwxfyJMR6u2h4NmSClb6ey1nHswH8uijTDl19z8Y6wMUqBDunmqbOXWBNXRX13ReZadMgvBY2aQZsuj-cAZxr2QCWGFxxb5KDJUgRKVkE20NlTmLWXPnJyPKuVs8tF3Vzyalz5Uw5VY4-dBeClRhMSeF4aZfvc3R1DydNh-N_smao=',
    '1BVtsOIIBu2Xxc_PHjyxRQiV5mEWutcdKbRS21ZTOAothKUjabgyr_YLHvx4IY-DeMl8fUoEzbSogmaXv_ODk9VTP643y1_ONMfifvhKoUGHiwOoUgd5uZSKSYYbAvYyyQ340tBmtJwMtgmybsUIeOBZHL-x19vLoyQgVegY0rggtp9R9CYgGwWGgPhvbWLm0UTEl-uZomon3Su7SIljKEN6TzRbKTVBMNxX9cvVl-cYQABqGhlptJSo36trvZviuQmCKQOT1g4FK2bWQXIB9-Yd2NejwhzSpHRU3oJ8kR2UbGUEV-_tUoC4Hv_DKtxLdJm3UGJ8bv1Z3KE0HzRjKBzgdxGXRt20='
]

TARGET_BOT = 'xocdia88_bot_uytin_bot' 
GROUP_TARGET = -1002984339626 
# ========================================================

async def start_bot(session_str, account_no):
    try:
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        
        @client.on(events.NewMessage(chats=TARGET_BOT))
        async def handler(event):
            # 1. Tự động nhấn nút "Đập Hộp"
            if event.reply_markup:
                for row in event.reply_markup.rows:
                    for button in row.buttons:
                        if "Đập Hộp" in button.text:
                            await event.click()
                            print(f"--- [TK {account_no}] Đã nhấn đập hộp! ---")
            
            # 2. Lấy nội dung chứa Code và bắn sang nhóm
            msg_text = event.raw_text
            if any(word in msg_text for word in ["Code", "Mã", "quà"]):
                try:
                    await client.send_message(GROUP_TARGET, f"🎁 [TK {account_no}] ĐẬP ĐƯỢC QUÀ:\n\n{msg_text}")
                    print(f"--- [TK {account_no}] Đã gửi code sang nhóm ---")
                except: pass

        await client.start()
        print(f"--- Tài khoản {account_no} đã Online ---")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Lỗi tài khoản {account_no}: {e}")

app = Flask('')
@app.route('/')
def home(): return "Đang chạy 10 tài khoản trực chiến 24/7!"

def run_flask(): app.run(host='0.0.0.0', port=8080)

async def main():
    tasks = [start_bot(s, i + 1) for i, s in enumerate(SESSIONS)]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    asyncio.run(main())
    

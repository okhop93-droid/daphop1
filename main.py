import sys
import asyncio
import random
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ================= CẤU HÌNH VIP =================
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'

# Danh sách 10 mã Session của bạn
SESSIONS = [
    '1BVtsOJEBu4kG50S18lXaCW2WgazYHri_nQ7No7pEvAxAtZSPK1Og1pT-dsF5wRFQZk7L-y8Kc3cxXinB2ycVFTA4hofF2KWtr_ZETKrgg4HIHtT8XC1DoCA3-Jf-81DZOgiWcm073yMmZaf-IAr6lqau_jemhFJxDlGeReerknWjbuGWkWcmmkL58n77y8w5gpzPW4eQa8zGNSj_aSzWxh9yvqW5AWTXz-vOd5chvBajTff3h2zLYrp0I62naR3QDFXU85_kRXMyN8ilHeb81wUvkD53TG1FeZw7m3pfJ3nolY5qHuXEfkbnbkXfrBA36A_e7qiUOREKyxHZ4Hy1LqQlS55qPbk=', # Tk 1
    '1BVtsOJEBu7d4nbO-iggb0fMc3YmCHEn84ExMGjwFvuLTEVZz2rAUWI8ZAUm-1xb3v_z9sWw77k_EJfnnSF6x17KZx_TIBBiiCOckGlusoEPhYb1Ta-Dw4xJf-t_vA6pCyLSS1B7Zc-n4I5z3aKNv4t903xy2X1Xal4w4SIjDyigwSA_SxHVcVXF360fGB8tUND0qYNJ-DupLJHucJN9v8ewlv2j81e658glX7DVOSYtge90MhqOoe6mk236xkPndMTd5PECg9h_j9_d5yJp6HD3R7LTFBG-t-kQcg8K8Yzwer2ez_CI7fig9MegWle1aaFIOVjykX7Oo1V-UcjrnU3hzP3AnWMQ=', # Tk 2
    '1BVtsOGcBuxzFnKdXNI5K13vOzlr56j1oyL_Y5iRuAhQtqrmPMXDlribDHr9Mlat1SVmwMQVhqnPL9SUvt9fr67KlPYOVC9QaOWCC_jOMup28gzzfNSathxzsXZpWz3fuOYkC7oKmRrWSPKaXJY2EZ_CZ-LOZnXYGW0a9A_H-PCd4rlR_SRGGbfi3iVk_5XBy6F5TLrmZewDw4smHpAWvvpecX7xqi9dX9cwSeoP7K21GIa682L4jmDe6eDAqoql2_wzw_EiaXQBfs5V8d-4Skg2k3pcWDKepX8X2FjvTxoxqcnnGd1sbz_PQ7PDbFTmrjUK0LUUwFcVyeg-72znuiqF0drcM5vE=', # Tk 3
    '1BVtsOGcBuyFC40crecyVmWCrjFj9PFcPfG1avi-mv4xerriqyA3078weQMCM1VY7Pot1PEQG71bJMjQPlWc7fMH-q3Nyhl7DxzSS9ssmL2x7R3nltBYa3SKCLn0oVFrcRhT9DDNCvFjSbAymWU-pClbfQqXBSeQXKoPMBvSlix_zchPD6Et7QqilFJoLufPccDNbqyz8gERj9rSW7vPCbSZ9wh3fAs21RaMUDfEZMnuUqxFahMEhpeXGdaQwjqpxFmckRBuYPD5lxM9HAEo-wOWe03btt2InYsK7ZDLrEelDUPoQYbVh9PlFvzaGY_2AL_13nd1mLP4KIDgZ06Q9uE59zcvYePE=', # Tk 4
    '1BVtsOGcBuzyVyvXbxiPNdpj5RPqLk-E6gZXVwbqK8g-cXzyex07NwtYz-qt3-REqO3Y6irW0Y8hBn0GC2AFuGFfeg2ynkkGge0lrg-_LJs352R_XXi1NfTM2Z9xcY3GqZSF3Ba_6XwvbEghVoll4we0od92fkr-7mjuYdhLJuy8xl_Wj2-3IYNfGDr2OlPk5Nrwe3ZfB7StATiFboVgn0iJnl7h7Cvh4gdNiYaGk0UwIKfuzQSKJwPx8L377ZuYV6y1Sc9F98sGB6VLfuTka4UZ3dN0vp_0O1c75SZbj7TqkT4YvG7wvHJsq2s75ywT4ORydCLJB9mdMab5LtlJEuOiEIZ_3wPg=', # Tk 5
    '1BVtsOGcBu57PR8dI6acv6JRD0asmxtPmmKqwrMv6_cSISZ9azTffPTIkG_gzQGdH5WinEQn_adhx5p7986IH6dd_dlKHpR58sdzEFsOVh-2tQwBF-Zbe7giIlPSELm7Heb9LammXzBLtGeh7EvGuHFH8YZQVHLJftZdtlyyfNqFdm9t4f9S82MZwH02Nf3St6qJtRS3jQkmI9q2ZEXTkfKHEqxMLH48dAb4FiWD_0PKXXnarzVmozuxZerPPzTsh6HbxZO41HrVNUknrLKvMoKNuVInMHDYRW3Uba0LK3zOS-kFwC0T7lPzOCQImGRDrtEb8BymbK443aodxed-QYKkHvZVu3Z4=', # Tk 6
    '1BVtsOGcBu09aUtxaV0LuvQ9QFsRcuLf0UB_zdftNqfW2y5VVNaPQX5WBwXeKsTa1JVaWNH9Ke4Mje7fILiAh365Hx70wynodI_7HLLPphe0PvMpOOD4ygmBqMZvdPcih9rIZ2_RIYjY6ZRkeflU3ouCVW6evy9oHhS6_nhPnXX3dNmibfbvH6FlfcJQa837Hg9WwDLDonMqYpVMT_P4U_x4Hq0LwTrKoUcwQw-bBlQH_3pgRDUYLWbEZ8rM7yPi8uKVOC1Nc1fJwntC6fsAfJeZsZMykR-i3W3LCVdRhf2Jy4Yw3LQYQ7o0Zzz31Vt8uGTXZPQG6eIutNVeC_RNL40bJ0x5kLwc=', # Tk 7
    '1BVtsOGcBu5WplDJSVRn8EYslTyiYpN7-V12ICXB1BTgp7nFs5n6-AQC-Xq7hBPi1D4Q1oZJlaCzxfSSqfe2xYRt24KGquwMu4sr1UwA9--QNaG9jjvEbt-T1MnrjfifVK_1fSn8kB08l-5DegwyTxMFLQ9SehsYU_cTG4wHfE_OGgQzU5VSELO7Vi7V1PRG0v2VmZ6pu-ec96jRTeFROrQOIN0VZIyVrjIIp68oBWiXidNnWrV8RMKO9dVRdnj6vQtl5E7_Pa6pR51RyM2IN-BSn78lDVlpT2vkOS4yV6kF8Y3pE-MtgJv56amDM4kl3Ib-5tf4-4uy4fCcc8SBXsmbccTnngks=', # Tk 8
    '1BVtsOGcBu5CqSdan-uhZSxpn7GoJL-bKB9pbMCt828Y-BPEQLToGvUiBpJhQL70R9DEHirs5abNcAb52Mn_kMxYK9V4I6ou4ebWCjPhHtClNUIW3cmImkf8vyzucNieQafwNUJ7MvVJWRsh3gvI-nn0Y2_ebEUopSVVyOCxWMccE2yYyHPZ6mR6q4ESKa2blN9pt9biWsBg45VDbBU0BBSBNvHGuc24-2C4T8K4WP8ZcU-GYiUW2RCsnMO_YvjIfuJNtYW384UUxba3q5qF6YWlmBtmxlRp5S3f0DKiZgxy9FOHCUZYCqKgOii76Yp0xcO35-5DOKoUjd2fJb-gfklagQjFWVhw=', # Tk 9
    '1BVtsOIIBu2Xxc_PHjyxRQiV5mEWutcdKbRS21ZTOAothKUjabgyr_YLHvx4IY-DeMl8fUoEzbSogmaXv_ODk9VTP643y1_ONMfifvhKoUGHiwOoUgd5uZSKSYYbAvYyyQ340tBmtJwMtgmybsUIeOBZHL-x19vLoyQgVegY0rggtp9R9CYgGwWGgPhvbWLm0UTEl-uZomon3Su7SIljKEN6TzRbKTVBMNxX9cvVl-cYQABqGhlptJSo36trvZviuQmCKQOT1g4FK2bWQXIB9-Yd2NejwhzSpHRU3oJ8kR2UbGUEV-_tUoC4Hv_DKtxLdJm3UGJ8bv1Z3KE0HzRjKBzgdxGXRt20='  # Tk 10
]

TARGET_BOT = 'xocdia88_bot_uytin_bot'
GROUP_TARGET = -1002984339626
processed_msgs = set()

# Hàm in log bắt buộc hiện ngay lập tức
def log(msg):
    print(msg, flush=True)

async def start_bot(session_str, account_no):
    # Random thiết bị "xịn"
    models = ["iPhone 15 Pro Max", "Samsung S24 Ultra", "Google Pixel 8", "iPad Pro M2"]
    
    client = TelegramClient(
        StringSession(session_str), API_ID, API_HASH,
        device_model=random.choice(models),
        system_version="17.2",
        auto_reconnect=True,
        connection_retries=None
    )
    
    try:
        await client.start()
        # Gửi tin nhắn về "Saved Messages" để chủ acc biết
        try:
            me = await client.get_me()
            await client.send_message('me', f"🤖 [TK {account_no}] {me.first_name} đã Online trên Koyeb!")
        except: pass
        
        log(f"✅ [TK {account_no}] KẾT NỐI THÀNH CÔNG! ĐANG RÌNH MỒI...")

        @client.on(events.NewMessage(chats=TARGET_BOT))
        async def handler(event):
            global processed_msgs
            
            # Log ngay khi thấy Bot mục tiêu động đậy
            log(f"👀 [TK {account_no}] Thấy {TARGET_BOT} nhắn gì đó...")

            if event.message.id in processed_msgs: return
            
            if event.reply_markup:
                for row in event.reply_markup.rows:
                    for button in row.buttons:
                        # Bắt từ khóa siêu nhạy
                        txt = button.text.lower()
                        if "đập" in txt or "hộp" in txt or "quà" in txt or "mở" in txt:
                            processed_msgs.add(event.message.id)
                            
                            # Delay siêu thực (Acc 1 nhanh nhất, Acc 10 chậm hơn)
                            delay = account_no * random.uniform(0.2, 0.5)
                            log(f"⚡ [TK {account_no}] PHÁT HIỆN QUÀ! Bấm sau {delay:.2f}s")
                            
                            await asyncio.sleep(delay)
                            try:
                                await event.click()
                                log(f"🚀 [TK {account_no}] >>> ĐÃ CLICK ĐẬP HỘP! <<<")
                                # Báo cáo ngay về Saved Messages nếu ăn được
                                await client.send_message('me', f"✅ [TK {account_no}] Vừa đập hộp xong!")
                            except Exception as e:
                                log(f"❌ [TK {account_no}] Click xịt: {e}")
            
            # Bắt Code quà
            if any(w in event.raw_text.lower() for w in ["code", "mã", "gift"]):
                try:
                    await client.send_message(GROUP_TARGET, f"🎁 [TK {account_no}] CÓ CODE: {event.raw_text}")
                except: pass

        await client.run_until_disconnected()
    except Exception as e:
        log(f"⚠️ [TK {account_no}] LỖI: {e}")

# --- Server ảo giữ Koyeb sống ---
app = Flask('')
@app.route('/')
def home(): return "<h1>BOT ĐANG CHẠY 24/7 - DO NOT SLEEP</h1>"

def run_flask():
    # Tắt log rác của Flask để đỡ rối mắt
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=8080)

async def main():
    log("➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖")
    log("🚀 HỆ THỐNG ĐANG KHỞI ĐỘNG CHẾ ĐỘ VIP...")
    log(f"📋 Đã nạp {len(SESSIONS)} tài khoản.")
    log("➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖")
    
    tasks = []
    for i, session in enumerate(SESSIONS):
        if len(session) > 50:
            # Acc đầu tiên chạy ngay lập tức, không chờ
            if i == 0:
                log(f"🔌 Đang kết nối TK {i+1} (Máy chủ)...")
                tasks.append(asyncio.create_task(start_bot(session, i + 1)))
            else:
                # Các acc sau chờ 30s để an toàn
                wait = 30
                log(f"⏳ TK {i+1} đang xếp hàng (Đợi {wait}s)...")
                await asyncio.sleep(wait)
                log(f"🔌 Đang kết nối TK {i+1}...")
                tasks.append(asyncio.create_task(start_bot(session, i + 1)))
                
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    

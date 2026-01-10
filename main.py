import re, asyncio, random, datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# --- CẤU HÌNH ---
API_ID = 36437338
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_GAME = 'xocdia88_bot_uytin_bot'
GR_LOG = -1002984339626

# DANH SÁCH CHÍNH XÁC 9 SESSION
SESSIONS = [
    "1BVtsOHQBu8Szrd3DILRLXgTu1KI_MObfryHm9_xJ0i0RKKBKk55AmVvKC53rIT_ohuLY3NcL20h_8O5tgIs63Gr8VYMb5VxWe2dbvQxpCDMSE-r8utT5qS__921767tAxH_YgELFZzAY_YPBdIjXNOIablNAZ5s42Pv-Udi1WptLq7m80b5o9Ed-dtl6MD0uXopHuW2jrfExZCZTPS1LbAsRuvnYG_chmFp9td4uz4T3sFUMDjgP7Jfu0aNeHlOGSIBmOzmHiURxM5nLK4QUNXruIsT_g5Rawt2vPrrXwG8eFk1ADEIi85DyYy2uPwxCOJ9yAthKsGKrjflQFKggPcNaimxnqoU=", # Tk 1
    "1BVtsOHQBu0tsu7kP9woTfa1GNU9wLR_FBhhnmM-egVjgs-BqnpGqw-lREFifIUxai8V3qOBNThDAhZ6zmjVbEne-ytTl4xXa-tqGJE3tjhJj4vXXO74Sel6VGVNsnlRCnGi97vEmkcQ8FLq1InLpiH9dzZNkCN8rCsMokXjvoEV7q3bL8a9AkC-ndZ6X1oj6DPvl_ech8HhxeiGcbKACtGDG2mjpwZe4JHVfOzaxbOYExzDR3lW9Mo2uuoqczhBLfU6l0lR6XTifeCf55281om1x3UkjY7RaX7V0Rzh4h9lqTsZEO8V5qvZ6EGKwktDfBRFmEWQgngv7dCZ5KNcp7TlvoAr9HGs=", # Tk 2
    "1BVtsOHQBu3D5imOAlgzBkeYVDgdv18oVLXID7sGFkeKCcLTn-Hmnp-8Rg0DjSpobM82Tc6gjku8ARtt7nXmgUWhlW1RNDb4tya_qJP6A4Noyin6Bdomg_kRe_jQmUCocwm2C4j6mhTFcmhOTxGZYKraen9OmY29gwxrDSbCgn-rOcEkxaKzQ_cx8NvCf6jIIVlAp1Paobh0TWMdK0kqfF3tMQwJ5v8dv8LIWgImpPRUXkbCJRAEgFn-_wvR53AesFPKmZCFLnn4UA7mMPhJz42UjvSGCUT2nf6uthUA4IEhyAfgEAZrg99N_7RVwLFK9NowJaXJW1qbu5lfm4P9tqyF8SbHzIUs=", # Tk 3
    "1BVtsOHQBuwa6Atqhx6EeHNMmlO3Z8q4zl2cUESMtai8nvUVCKp6wIutzwFFdVeM9auXP6IZfF502tngQ0Gt9F4UW7FQ4TixsXrQwu4jxZnLi3rpDC7sf9tcwY9_BpnBbVbDVQHm0PgECQ9O9me8gTKIutqQDMC44I0H-lebcSruykMfHjLGws3hFU8lJs0gWo2JFIPwZqQkf05JQYfH9XshRGYX0cKvVPID4SB0CFXs05v1j_2RE35yXOgJ0N0hMxe93H4LQ4w0h1CaHKH90_6jwSGj1BLHL8pfvhJ23KkR0ZfJcE4UcFfE5nJwzUNhbrBgA0FRyij5EOStekOQxbvmzta3kPVg=", # Tk 4
    "1BVtsOHQBuxbmE40dQ7wJDJpShsTOSLWJpUR8DMlfXWTkyMeQ_xggeoHEWXqp-JR-qU6UbECIRfk3zuDmvfoepWXlCmxvkoeqcITKot0J68_CeZjZ94KCsurYus7-zzwCy39ecLcOs7eZYwChC3saVduEH0t70B_3_pA9hf0sDRP9G1W_fIq9phXo-bbRElrwTUSNTJv-js2HkfoY40dm6L-Q0REh_xntMGBVCQ-zz6APLpIxsjCFL_SjvfT6bV3cTFUlhV8SaXFTBShmxi1-dxj5TNMoc8gUvoF6L65Y95d_ubi-pS60SBXrT2bsfvqPaeFyWAIitidIopbjHQ7iSpEUBIDP-xQ=", # Tk 5
    "1BVtsOHQBu6AdotZaWZ8gSHmyuolE31aYqOgZ2kMycpcPFTUXJze5aJokRxhXUaxcuH9BV6JhMC2A5oC0FVpALb14JWwNIhA8vCzqHajMEGntn5jmZg1Uj__LMHNLacxtfbSSqgVJQbHv1ann71WH2ntjM9BjN3QuK1WYEgC_GGmwNoKv3zCf-CsROhsMknCKP2Uv0OAADf_0Od-Tm0OoG3RTj5ZLPJ_Shsgehi-Ao4O7akRMoU_nCccfDxrLeQdYXnc6MN4JwtSe2e4O0FCGvecgHs7DFeL9TuGKvjCSHD_Eh7xFes3-4iRNzKuklpAYebuYyhJaW0FYexd-A4kNRpwQ7JoICB8=", # Tk 6
    "1BVtsOHQBu5RbwC6xA0x8Ns7_fIc5E6ECblVi5moEnFwCPygedh7dMIEf8DIMLQe083R_2rUzR2Mltt5S4M3xfZI97I0qWSw3Dz3JvzLupP2RqDrKQjs3Vpzn9YkpM5i6hL5pW8H0bfTXPj4KHXhv8ba7OhqEpII9-FmYATncqsI1fCUO672twVGHN2tkSiGoHjYto7ozPdqvhaQpAEKxfipP_DcJn1jfoeV9i7f4cVE4nq-S-BM0q4Tot5GXo53cZx8C27ZTel09dnWLSAlQW90Og49SXCQjG48Zjexvvtti0DO5I_z1vK1bQCXib0fvxujZBI6D6m35a4NTP7OjAKe5m1uT0mg=", # Tk 7
    "1BVtsOHQBuzFK-kULpFBD5AYNgV46knd3auBAdIx8ItoFOU1Hin8NGYUdLijMzZZvTqjAV2vdcibeiUR7Wn3sYnXntnmgfIXhiiscTTD7NN4PjGC93zBj4qmToYZe7xqchMu-1WCD-RV31rkvO4DRb_nRri25q7wSQZ69t839NhHR1kpBFn0GvTkcUpvq6FwcWDoCFz4b_GHsNxbXeT7f5TIXhi-RDGyQGvqpYMHahk049wHCJRKMU4e98POliyEh3qm8mDpAtQ9_Dbh6UiU2PuB58lHcgjXoYh6ziyBIEbZ3B7HwryrK0vXlYMWH3Ippj2F6Ilm_vwq2LtAE0ZiZExg5u8xhsYY=", # Tk 8
    "1BVtsOHQBuyp1l966t_AwCVSzSk4NypjhmiUhocVcpqIgASjI6ac8PJRra3NUsKkSxdxeXcz8TLV60GBwK_sCKoqW8r7Vt2xeqCI2GD3GkuP8fwrb5nVUWtDMfAbsuB_tCHxAFFi4IyWHNTUpOplpfNUiEiiO1CZ9HUCWGVb9bLgeWQ7D14hdMXw6NHERz21R2E_XFbEQ3AoAEVRgyH8aZuodqPdXw-LKmWWbT06kia0M1IooE8tKY4VdD_xYVx-FHndN6TkJ4_27HxrPNch_jkIR4eBHoUnE7759tCALmzyJ3oiBzJEidodOMlLLLvoGU81PkEoJ_mKwdhxKIqtw5PDlSAcHPf4="  # Tk 9
]

app = Flask('')
@app.route('/')
def home(): return "9ACC_STABLE_ALIVE"

async def start_acc(session_str, acc_no):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Acc {acc_no} ({me.first_name}) ONLINE!")
        await client.send_message(GR_LOG, f"🟢 [HỆ THỐNG] Acc {acc_no} ({me.first_name}) đã kết nối thành công.")

        @client.on(events.NewMessage(chats=BOT_GAME))
        async def work(e):
            # Lọc mã code tự động
            if "Mã code của bạn là:" in e.raw_text:
                match = re.search(r"Mã code của bạn là:\s*([A-Z0-9]+)", e.raw_text)
                if match:
                    await client.send_message(GR_LOG, f"💌 Acc {acc_no} ({me.first_name}): `{match.group(1)}`")

            # Tự động đập hộp
            if e.reply_markup:
                for row in e.reply_markup.rows:
                    for btn in row.buttons:
                        if any(x in btn.text for x in ["Đập", "Hộp", "Mở"]):
                            # Delay ngẫu nhiên để né Telegram quét
                            await asyncio.sleep(acc_no * random.uniform(0.3, 0.7))
                            try:
                                await e.click()
                                await client.send_message(GR_LOG, f"💰 Acc {acc_no} ({me.first_name}) húp quà!")
                            except: pass
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Acc {acc_no} Lỗi: {e}")
        # Tự động thông báo lỗi về nhóm để bạn biết mà xử lý
        try: await client.send_message(GR_LOG, f"⚠️ Acc {acc_no} bị lỗi: {e}")
        except: pass

async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    tasks = []
    for i, s in enumerate(SESSIONS, 1):
        tasks.append(start_acc(s, i))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
                    

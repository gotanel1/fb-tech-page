#!/usr/bin/env python3
"""
สคริปต์ช่วยแลก Token ของ Facebook ให้เป็น "Page Access Token แบบไม่มีวันหมดอายุ"

วิธีใช้:
    python tools/get_token.py

จะถาม 3 อย่าง แล้วพ่น Page ID + Page Token ที่พร้อมเอาไปใส่ .env / GitHub Secrets
(รายละเอียดแต่ละค่าหาได้จากไหน อ่านใน SETUP.md ขั้นตอนที่ 5)
"""
from __future__ import annotations

import sys

import requests

VERSION = "v26.0"
BASE = f"https://graph.facebook.com/{VERSION}"


def die(msg: str) -> None:
    print(f"\n[ผิดพลาด] {msg}")
    sys.exit(1)


def api(path: str, **params) -> dict:
    resp = requests.get(f"{BASE}/{path}", params=params, timeout=45)
    data = resp.json()
    if "error" in data:
        die(data["error"].get("message", str(data)))
    return data


def main() -> None:
    print("=" * 62)
    print(" แลก Token ให้เป็น Page Access Token แบบถาวร")
    print("=" * 62)

    app_id = input("App ID           : ").strip()
    app_secret = input("App Secret       : ").strip()
    short_token = input("User Token สั้น  : ").strip()

    if not (app_id and app_secret and short_token):
        die("กรอกไม่ครบทั้ง 3 ช่อง")

    print("\n[1/3] แลกเป็น User Token แบบยาว (อายุ 60 วัน)...")
    long_user = api(
        "oauth/access_token",
        grant_type="fb_exchange_token",
        client_id=app_id,
        client_secret=app_secret,
        fb_exchange_token=short_token,
    )["access_token"]
    print("      สำเร็จ")

    print("[2/3] ตรวจสอบบัญชี...")
    me = api("me", fields="id,name", access_token=long_user)
    print(f"      บัญชี: {me.get('name')}")

    print("[3/3] ดึงรายชื่อเพจที่คุณเป็นแอดมิน...")
    pages = api("me/accounts", fields="id,name,access_token,tasks",
                access_token=long_user).get("data", [])
    if not pages:
        die("ไม่พบเพจเลย — ตอนกด Generate Access Token ในขั้นตอนที่ 4\n"
            "     ต้องติ๊กเพจของคุณในหน้าที่เด้งขึ้นมาด้วย และต้องให้สิทธิ์ครบ 5 อัน:\n"
            "     pages_show_list, pages_manage_posts, pages_read_engagement,\n"
            "     pages_manage_engagement, pages_manage_metadata")

    print(f"\nพบ {len(pages)} เพจ:")
    for i, page in enumerate(pages, 1):
        print(f"  [{i}] {page['name']}  (id {page['id']})")

    if len(pages) == 1:
        chosen = pages[0]
    else:
        idx = input("\nเลือกเพจหมายเลข: ").strip()
        try:
            chosen = pages[int(idx) - 1]
        except (ValueError, IndexError):
            die("หมายเลขไม่ถูกต้อง")

    print("\n" + "=" * 62)
    print(" เรียบร้อย! เอา 2 ค่านี้ไปใส่ .env และ GitHub Secrets")
    print("=" * 62)
    print(f"\nFB_PAGE_ID={chosen['id']}")
    print(f"\nFB_PAGE_TOKEN={chosen['access_token']}")
    print("\n" + "=" * 62)
    print("หมายเหตุ: Page Token ที่ได้จาก Long-lived User Token จะไม่มีวันหมดอายุ")
    print("ยกเว้นคุณเปลี่ยนรหัสผ่าน Facebook หรือถอนสิทธิ์แอปเอง")
    print("อย่าเอา token นี้ไป commit ขึ้น GitHub เด็ดขาด")
    print("=" * 62)


if __name__ == "__main__":
    main()

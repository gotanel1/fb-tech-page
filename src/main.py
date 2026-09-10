#!/usr/bin/env python3
"""ตัวหลัก: ดึงข่าว -> ให้ AI เขียน -> โพสต์ขึ้นเพจ"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import news                        # noqa: E402
from config import Config          # noqa: E402
from facebook import FacebookError, PageClient   # noqa: E402
from state import PostedStore      # noqa: E402
from writer import write_post      # noqa: E402

LINE = "=" * 62


def run(dry_run: bool, limit: int | None) -> int:
    cfg = Config.load()
    if dry_run:
        cfg.dry_run = True
    if limit:
        cfg.posts_per_run = limit

    print(LINE)
    print(f"โหมด: {'ทดลอง (ไม่โพสต์จริง)' if cfg.dry_run else 'โพสต์จริง'}")
    print(f"จะโพสต์ {cfg.posts_per_run} ชิ้น | สไตล์: {cfg.post_style}")
    print(LINE)

    if not cfg.dry_run:
        cfg.require_for_posting()

    articles = news.collect(cfg)
    if not articles:
        print("ไม่มีข่าวใหม่ในรอบนี้ — จบการทำงาน")
        return 0

    store = PostedStore()
    client = None
    if not cfg.dry_run:
        client = PageClient(cfg.fb_page_id, cfg.fb_page_token, cfg.graph_version)
        page = client.whoami()
        print(f"เชื่อมต่อเพจสำเร็จ: {page.get('name')} (id {page.get('id')})\n")
    elif cfg.gemini_api_key:
        print("มี GEMINI_API_KEY — จะให้ AI เขียนจริงแต่ไม่โพสต์\n")

    published = 0
    for art in articles:
        if published >= cfg.posts_per_run:
            break
        if store.seen(art.url, art.title):
            continue

        print(LINE)
        print(f"ข่าว: {art.title}")
        print(f"จาก: {art.source} | อายุ {art.age_hours:.1f} ชม. | คะแนน {art.score:.2f}")
        print(f"ลิงก์: {art.url}")

        try:
            news.enrich(art)
            if not cfg.gemini_api_key:
                print("\n[ข้ามขั้นเขียน] ยังไม่ได้ตั้ง GEMINI_API_KEY")
                print(f"ตัวอย่างเนื้อหาที่จะส่งให้ AI:\n{(art.body or art.summary)[:400]}...")
                published += 1
                continue

            message = write_post(cfg, art)
        except Exception as exc:                              # noqa: BLE001
            print(f"[ผิดพลาด] เขียนโพสต์ไม่สำเร็จ: {exc}")
            continue

        print("\n--- โพสต์ที่ AI เขียน ---")
        print(message)
        print("--- จบโพสต์ ---\n")

        if cfg.dry_run:
            published += 1
            continue

        try:
            if cfg.post_style == "link":
                post_id = client.publish(message, link=art.url)
            else:
                post_id = client.publish(message)
                try:
                    client.comment(post_id, f"อ่านข่าวเต็ม ๆ ที่นี่ 👇\n{art.url}")
                except FacebookError as exc:
                    print(f"[เตือน] คอมเมนต์ลิงก์ไม่สำเร็จ: {exc}")
        except FacebookError as exc:
            print(f"[ผิดพลาด] โพสต์ไม่สำเร็จ: {exc}")
            continue

        print(f"โพสต์สำเร็จ! post id = {post_id}")
        store.add(url=art.url, title=art.title, source=art.source, fb_post_id=post_id)
        store.save()
        published += 1

    print(LINE)
    print(f"เสร็จสิ้น: {published}/{cfg.posts_per_run} โพสต์")
    if published == 0:
        print("ไม่มีอะไรให้โพสต์ (ข่าวทั้งหมดเคยโพสต์ไปแล้ว)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="บอทโพสต์ข่าวเทคลงเพจ Facebook")
    parser.add_argument("--dry-run", action="store_true", help="ทดลองรันโดยไม่โพสต์จริง")
    parser.add_argument("--limit", type=int, help="จำนวนโพสต์ในรอบนี้")
    args = parser.parse_args()
    try:
        return run(args.dry_run, args.limit)
    except SystemExit:
        raise
    except Exception:                                         # noqa: BLE001
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""ให้ Gemini เขียนโพสต์ภาษาไทยจากข่าวต้นทาง"""
from __future__ import annotations

import re
import time

import requests

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 90

SYSTEM = """คุณคือคนเขียนคอนเทนต์ให้เพจข่าวเทคโนโลยีภาษาไทย
เขียนโพสต์ Facebook 1 โพสต์จากข่าวที่ได้รับ โดยยึดตามคู่มือสไตล์ด้านล่างอย่างเคร่งครัด

--- คู่มือสไตล์ของเพจ ---
{style}
--- จบคู่มือ ---

ข้อกำหนดผลลัพธ์:
- ตอบกลับมาเป็นตัวโพสต์ล้วน ๆ พร้อมโพสต์ได้ทันที
- ห้ามใส่คำอธิบาย ห้ามใส่หัวข้อกำกับ ห้ามใส่เครื่องหมายคำพูดครอบ
- ห้ามใส่ URL ใด ๆ ในโพสต์
- เขียนเป็นภาษาไทยทั้งหมด ยกเว้นศัพท์เทคนิคและชื่อเฉพาะ"""

USER = """หัวข้อข่าว: {title}
แหล่งข่าว: {source}
หมวด: {tag}

เนื้อหาข่าว:
{body}

เขียนโพสต์ Facebook ภาษาไทยจากข่าวนี้"""


def _strip(text: str) -> str:
    """เก็บกวาดผลลัพธ์ให้พร้อมโพสต์"""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n|\n```$", "", text).strip()
    if len(text) > 2 and text[0] in "\"'“" and text[-1] in "\"'”":
        text = text[1:-1].strip()
    # Facebook ไม่รองรับ markdown
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.M)
    text = text.replace("—", " ")
    # ตัด URL ที่หลุดมา
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def write_post(cfg, art) -> str:
    prompt = USER.format(
        title=art.title,
        source=art.source,
        tag=art.tag,
        body=(art.body or art.summary)[:6000],
    )
    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM.format(style=cfg.style_guide)}]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        },
    }
    url = ENDPOINT.format(model=cfg.gemini_model)
    headers = {
        "x-goog-api-key": cfg.gemini_api_key,
        "Content-Type": "application/json",
    }

    last_error = ""
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                time.sleep(8 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
            cleaned = _strip(text)
            if len(cleaned) >= 80:
                return cleaned
            last_error = f"ผลลัพธ์สั้นเกินไป ({len(cleaned)} ตัวอักษร)"
        except Exception as exc:                              # noqa: BLE001
            last_error = str(exc)[:300]
        time.sleep(4 * (attempt + 1))

    raise RuntimeError(f"Gemini เขียนโพสต์ไม่สำเร็จ: {last_error}")

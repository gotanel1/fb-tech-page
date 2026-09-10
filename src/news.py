"""ดึงข่าวจาก RSS หลายแหล่ง แล้วจัดอันดับว่าอันไหนน่าโพสต์ที่สุด"""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from state import title_key, url_key

UA = "Mozilla/5.0 (compatible; TechPageBot/1.0; +https://github.com)"
TIMEOUT = 20


@dataclass
class Article:
    title: str
    url: str
    summary: str
    source: str
    tag: str
    published: datetime
    score: float = 0.0
    body: str = ""

    @property
    def age_hours(self) -> float:
        delta = datetime.now(timezone.utc) - self.published
        return delta.total_seconds() / 3600


def _clean(raw: str, limit: int = 1200) -> str:
    text = BeautifulSoup(raw or "", "html.parser").get_text(" ")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:limit]


def _published(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_feed(feed_cfg: dict, max_age_hours: int) -> list[Article]:
    url = feed_cfg["url"]
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:                                  # noqa: BLE001
        print(f"  [ข้าม] {feed_cfg['name']}: {exc}")
        return []

    out: list[Article] = []
    for entry in parsed.entries[:30]:
        link = (entry.get("link") or "").strip()
        title = _clean(entry.get("title", ""), 300)
        if not link or not title:
            continue
        published = _published(entry)
        if published > datetime.now(timezone.utc):
            published = datetime.now(timezone.utc)
        art = Article(
            title=title,
            url=link,
            summary=_clean(
                entry.get("summary")
                or (entry.get("content") or [{}])[0].get("value", "")
            ),
            source=feed_cfg["name"],
            tag=feed_cfg.get("tag", "general"),
            published=published,
        )
        if art.age_hours <= max_age_hours:
            out.append(art)
    print(f"  [ok] {feed_cfg['name']}: {len(out)} ข่าวใหม่")
    return out


def score(art: Article, feed_cfg: dict, boost: dict[str, float]) -> float:
    """ยิ่งใหม่ + ยิ่งตรงกับคีย์เวิร์ดที่เพจสนใจ = คะแนนยิ่งสูง"""
    freshness = max(0.15, 1.0 - (art.age_hours / 72.0))
    value = freshness * float(feed_cfg.get("weight", 1.0))

    haystack = f"{art.title} {art.summary}".lower()
    multiplier = 1.0
    for word, factor in boost.items():
        if word in haystack:
            multiplier = max(multiplier, factor)
    value *= multiplier

    # มีเนื้อหาย่อพอสมควร = เขียนโพสต์ได้ดีกว่า
    if len(art.summary) > 250:
        value *= 1.1
    elif len(art.summary) < 80:
        value *= 0.75
    return value


def blocked(art: Article, blocklist: list[str]) -> bool:
    low = art.title.lower()
    return any(word in low for word in blocklist)


def collect(cfg) -> list[Article]:
    print("ดึงข่าวจาก RSS...")
    articles: list[Article] = []
    for feed_cfg in cfg.feeds:
        for art in fetch_feed(feed_cfg, cfg.max_age_hours):
            if blocked(art, cfg.blocklist):
                continue
            art.score = score(art, feed_cfg, cfg.boost)
            articles.append(art)

    # ตัดข่าวซ้ำภายในรอบเดียวกัน (URL เดียวกันจากหลายฟีด)
    seen: set[str] = set()
    unique: list[Article] = []
    for art in sorted(articles, key=lambda a: a.score, reverse=True):
        keys = (url_key(art.url), title_key(art.title))
        if keys[0] in seen or keys[1] in seen:
            continue
        seen.update(keys)
        unique.append(art)

    print(f"รวมข่าวที่ใช้ได้ {len(unique)} ชิ้น\n")
    return unique


def enrich(art: Article) -> None:
    """ถ้า RSS ให้เนื้อหามาน้อย ลองเข้าไปดึงเนื้อข่าวจริงมาเพิ่ม (ไม่สำเร็จก็ไม่เป็นไร)"""
    if len(art.summary) > 600:
        art.body = art.summary
        return
    try:
        resp = requests.get(art.url, timeout=TIMEOUT, headers={"User-Agent": UA})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for junk in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            junk.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 60)
        art.body = re.sub(r"\s+", " ", text)[:4000] or art.summary
    except Exception:                                         # noqa: BLE001
        art.body = art.summary

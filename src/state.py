"""เก็บประวัติว่าโพสต์อะไรไปแล้วบ้าง เพื่อไม่ให้โพสต์ซ้ำ"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "state" / "posted.json"

KEEP_DAYS = 45
_TRACKING = re.compile(r"^(utm_|fbclid|gclid|ref|source)", re.I)


def canonical_url(url: str) -> str:
    """ตัด query string ที่เป็น tracking ออก เพื่อให้ URL เดียวกันนับเป็นอันเดียวกัน"""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    kept = [
        kv for kv in parts.query.split("&")
        if kv and not _TRACKING.match(kv.split("=", 1)[0])
    ]
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, "&".join(kept), ""))


def url_key(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode()).hexdigest()[:16]


def title_key(title: str) -> str:
    """ลายนิ้วมือของหัวข้อ: ตัดคำเล็กคำน้อยออก เหลือแต่คำหลักเรียงตามตัวอักษร"""
    words = re.findall(r"[a-z0-9ก-๙]+", title.lower())
    stop = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "is",
            "with", "at", "by", "from", "its", "new", "this", "that"}
    core = sorted({w for w in words if w not in stop and len(w) > 2})[:8]
    return hashlib.sha1(" ".join(core).encode()).hexdigest()[:16]


class PostedStore:
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self.entries: list[dict] = []
        if path.exists():
            try:
                self.entries = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.entries = []
        self._urls = {e.get("url_key") for e in self.entries}
        self._titles = {e.get("title_key") for e in self.entries}

    def seen(self, url: str, title: str) -> bool:
        return url_key(url) in self._urls or title_key(title) in self._titles

    def add(self, *, url: str, title: str, source: str, fb_post_id: str = "") -> None:
        entry = {
            "url_key": url_key(url),
            "title_key": title_key(title),
            "url": canonical_url(url),
            "title": title[:200],
            "source": source,
            "fb_post_id": fb_post_id,
            "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.entries.append(entry)
        self._urls.add(entry["url_key"])
        self._titles.add(entry["title_key"])

    def save(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
        kept = []
        for e in self.entries:
            try:
                when = datetime.fromisoformat(e.get("posted_at", ""))
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
            except ValueError:
                when = datetime.now(timezone.utc)
            if when >= cutoff:
                kept.append(e)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8"
        )

"""โหลดค่า config ทั้งหมดจาก .env และ feeds.yaml"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "y"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


@dataclass
class Config:
    fb_page_id: str = ""
    fb_page_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    posts_per_run: int = 1
    max_age_hours: int = 36
    post_style: str = "comment"       # "comment" | "link"
    dry_run: bool = False
    graph_version: str = "v26.0"
    feeds: list = field(default_factory=list)
    blocklist: list = field(default_factory=list)
    boost: dict = field(default_factory=dict)
    style_guide: str = ""

    @classmethod
    def load(cls) -> "Config":
        with open(ROOT / "feeds.yaml", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        style_path = ROOT / "style.md"
        style = style_path.read_text(encoding="utf-8") if style_path.exists() else ""

        return cls(
            fb_page_id=os.getenv("FB_PAGE_ID", "").strip(),
            fb_page_token=os.getenv("FB_PAGE_TOKEN", "").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip(),
            posts_per_run=_int("POSTS_PER_RUN", 1),
            max_age_hours=_int("MAX_AGE_HOURS", 36),
            post_style=os.getenv("POST_STYLE", "comment").strip().lower(),
            dry_run=_bool("DRY_RUN", False),
            graph_version=os.getenv("FB_GRAPH_VERSION", "v26.0").strip(),
            feeds=data.get("feeds", []),
            blocklist=[w.lower() for w in data.get("blocklist", [])],
            boost={k.lower(): float(v) for k, v in (data.get("boost") or {}).items()},
            style_guide=style,
        )

    def require_for_posting(self) -> None:
        missing = [n for n, v in [
            ("FB_PAGE_ID", self.fb_page_id),
            ("FB_PAGE_TOKEN", self.fb_page_token),
            ("GEMINI_API_KEY", self.gemini_api_key),
        ] if not v]
        if missing:
            raise SystemExit(
                "ขาดค่า config: " + ", ".join(missing)
                + "\nดูวิธีตั้งค่าได้ที่ SETUP.md"
            )

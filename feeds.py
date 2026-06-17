from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import json
from pathlib import Path
from re import sub
from typing import Iterable

import feedparser
import httpx


DEFAULT_FEEDS = {
    "NASDAQ IPO Calendar RSS": "https://www.nasdaq.com/feed/rssoutbound?category=IPOs",
    "SEC press releases": "https://www.sec.gov/news/pressreleases.rss",
    "Yahoo Finance news RSS": "https://finance.yahoo.com/news/rssindex",
    "TechCrunch AI RSS": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI RSS": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Crunchbase News RSS": "https://news.crunchbase.com/feed/",
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; us-stock-substack-bot/1.0; "
        "+https://github.com/)"
    ),
}


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: str


def clean_text(value: str, limit: int = 700) -> str:
    text = sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    text = sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "..."


def item_from_entry(entry: dict, source: str) -> NewsItem:
    return NewsItem(
        title=clean_text(entry.get("title", "Untitled"), limit=220),
        link=entry.get("link", "").strip(),
        summary=clean_text(
            entry.get("summary") or entry.get("description") or entry.get("subtitle") or "",
        ),
        source=source,
        published=entry.get("published") or entry.get("updated") or "",
    )


def dedupe_items(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.link or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def load_feeds_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return DEFAULT_FEEDS
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Feed config must be a JSON object: {path}")
    return {str(name): str(url) for name, url in data.items()}


def fetch_feed(source: str, url: str, per_feed_limit: int = 5) -> list[NewsItem]:
    response = httpx.get(url, headers=REQUEST_HEADERS, follow_redirects=True, timeout=20)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items = [
        item_from_entry(entry, source)
        for entry in parsed.entries[:per_feed_limit]
        if entry.get("title") and entry.get("link")
    ]
    return items


def fetch_news(
    feeds: dict[str, str] | None = None,
    per_feed_limit: int = 5,
    total_limit: int = 20,
) -> list[NewsItem]:
    selected_feeds = feeds or DEFAULT_FEEDS
    all_items: list[NewsItem] = []
    for source, url in selected_feeds.items():
        try:
            all_items.extend(fetch_feed(source, url, per_feed_limit=per_feed_limit))
        except Exception as exc:
            print(f"Warning: failed to fetch {source}: {exc}")
    return dedupe_items(all_items)[:total_limit]

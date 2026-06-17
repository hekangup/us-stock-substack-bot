from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from feeds import fetch_news, load_feeds_config
from writer import build_mock_articles, generate_article, load_prompt_template, write_draft


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an English Substack-style Markdown draft from public RSS feeds.",
    )
    parser.add_argument("--date", default=date.today().isoformat(), help="Draft date, YYYY-MM-DD.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum RSS items to include.")
    parser.add_argument("--per-feed-limit", type=int, default=5, help="Maximum items per RSS feed.")
    parser.add_argument(
        "--drafts-dir",
        type=Path,
        default=ROOT / "drafts",
        help="Directory where English Markdown drafts are written.",
    )
    parser.add_argument(
        "--drafts-cn-dir",
        type=Path,
        default=ROOT / "drafts_cn",
        help="Directory where Chinese Markdown drafts are written in mock mode.",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=ROOT / "prompts" / "daily_brief.md",
        help="Markdown prompt template.",
    )
    parser.add_argument(
        "--feeds",
        type=Path,
        default=ROOT / "feeds.json",
        help="JSON file containing RSS feed names and URLs.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Generate a local Markdown draft from RSS items without calling OpenAI.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    feeds = load_feeds_config(args.feeds)
    news_items = fetch_news(feeds=feeds, per_feed_limit=args.per_feed_limit, total_limit=args.limit)
    prompt_template = load_prompt_template(args.prompt)
    try:
        if args.mock:
            article, chinese_article = build_mock_articles(news_items, args.date)
        else:
            article = generate_article(news_items, prompt_template, args.date)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"Error: {exc}") from exc
    output_path = write_draft(article, args.drafts_dir, args.date)
    print(f"Draft written to {output_path}")
    if args.mock:
        cn_output_path = write_draft(chinese_article, args.drafts_cn_dir, args.date)
        print(f"Chinese draft written to {cn_output_path}")


if __name__ == "__main__":
    main()

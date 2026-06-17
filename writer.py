from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI, OpenAIError

from feeds import NewsItem


DEFAULT_MODEL = "gpt-5.5"


def ensure_api_key() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your API key, "
            "or set OPENAI_API_KEY in GitHub Actions secrets."
        )
    if api_key == "your_openai_api_key_here":
        raise RuntimeError(
            "OPENAI_API_KEY is still the example placeholder. Add a real OpenAI API key "
            "to .env or set OPENAI_API_KEY in the shell."
        )


def load_prompt_template(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_article_input(items: list[NewsItem], prompt_template: str, iso_date: str) -> str:
    source_notes = []
    for index, item in enumerate(items, start=1):
        source_notes.append(
            "\n".join(
                [
                    f"{index}. Title: {item.title}",
                    f"   Source: {item.source}",
                    f"   Published: {item.published or 'Unknown'}",
                    f"   Link: {item.link}",
                    f"   RSS summary: {item.summary or 'No summary provided.'}",
                ]
            )
        )

    return "\n\n".join(
        [
            prompt_template,
            f"Draft date: {iso_date}",
            "Source material from public RSS feeds:",
            "\n\n".join(source_notes),
            (
                "Important: Do not reproduce full articles. Use only the titles, links, "
                "and RSS summaries above to write original summaries and commentary."
            ),
        ]
    )


def generate_article(
    items: list[NewsItem],
    prompt_template: str,
    iso_date: str,
    model: str | None = None,
) -> str:
    if not items:
        raise ValueError("No news items were fetched from RSS feeds.")

    ensure_api_key()
    client = OpenAI()
    try:
        response = client.responses.create(
            model=model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            input=build_article_input(items, prompt_template, iso_date),
        )
    except OpenAIError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc
    return response.output_text.strip()


def build_mock_article(items: list[NewsItem], iso_date: str) -> str:
    if not items:
        raise ValueError("No news items were fetched from RSS feeds.")

    lines = [
        f"# Daily US IPO & AI Market Brief - {iso_date}",
        "",
        "## 1. IPO Watch",
        "",
    ]
    ipo_items = [
        item
        for item in items
        if any(keyword in item.title.lower() for keyword in ["ipo", "listing", "public", "stock"])
    ]
    for item in ipo_items[:5] or items[:3]:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - Source: {item.source}",
                f"  - Summary: {item.summary or 'No RSS summary provided.'}",
                f"  - Link: {item.link}",
            ]
        )

    lines.extend(["", "## 2. AI Sector Moves", ""])
    ai_items = [
        item
        for item in items
        if any(keyword in (item.title + " " + item.summary).lower() for keyword in ["ai", "artificial intelligence", "chip", "semiconductor"])
    ]
    for item in ai_items[:5] or items[:3]:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - Source: {item.source}",
                f"  - Summary: {item.summary or 'No RSS summary provided.'}",
            ]
        )

    lines.extend(
        [
            "",
            "## 3. Market Signal",
            "",
            "- This mock draft uses live RSS inputs but does not call OpenAI.",
            "- Treat these bullets as a source review scaffold, not final editorial analysis.",
            "",
            "## 4. My Take",
            "",
            "- Add original commentary here after reviewing the source list.",
            "- Watch whether IPO-related headlines cluster around AI infrastructure, software, or consumer demand.",
            "",
            "## 5. Sources",
            "",
        ]
    )
    for item in items:
        lines.append(f"- [{item.title}]({item.link}) - {item.source}")
    return "\n".join(lines).strip()


def draft_path_for_date(drafts_dir: Path, iso_date: str) -> Path:
    return drafts_dir / f"{iso_date}.md"


def write_draft(markdown: str, drafts_dir: Path, iso_date: str) -> Path:
    drafts_dir.mkdir(parents=True, exist_ok=True)
    output_path = draft_path_for_date(drafts_dir, iso_date)
    output_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return output_path

from pathlib import Path

import pytest

from feeds import NewsItem
from writer import (
    build_article_input,
    build_mock_articles,
    build_mock_article,
    draft_path_for_date,
    ensure_api_key,
    filter_effective_items,
    load_prompt_template,
)


def test_build_article_input_includes_sources_without_full_text():
    items = [
        NewsItem(
            title="Robotics startup files for IPO",
            link="https://example.com/robotics-ipo",
            summary="The company reported faster revenue growth and widening losses.",
            source="Example Markets",
            published="2026-06-16",
        )
    ]

    prompt = build_article_input(items, "Write a concise brief.", "2026-06-16")

    assert "Robotics startup files for IPO" in prompt
    assert "https://example.com/robotics-ipo" in prompt
    assert "Do not reproduce full articles" in prompt
    assert "Write a concise brief." in prompt
    assert "Draft date: 2026-06-16" in prompt


def test_draft_path_for_date_uses_iso_filename(tmp_path):
    assert draft_path_for_date(tmp_path, "2026-06-16") == tmp_path / "2026-06-16.md"


def test_load_prompt_template_reads_markdown(tmp_path):
    prompt_file = tmp_path / "daily_brief.md"
    prompt_file.write_text("Daily brief instructions", encoding="utf-8")

    assert load_prompt_template(prompt_file) == "Daily brief instructions"


def test_ensure_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        ensure_api_key()


def test_ensure_api_key_rejects_example_placeholder(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key_here")

    with pytest.raises(RuntimeError, match="real OpenAI API key"):
        ensure_api_key()


def test_build_mock_article_outputs_markdown_with_sources():
    items = [
        NewsItem(
            title=f"AI optical parts maker {index} eyes Hong Kong listing",
            link=f"https://example.com/ai-listing-{index}",
            summary="The company is considering a large public listing.",
            source="Yahoo Finance news RSS",
            published="2026-06-17",
        )
        for index in range(5)
    ]

    article = build_mock_article(items, "2026-06-17")

    assert "# Daily US IPO & AI Market Brief - 2026-06-17" in article
    assert "## 1. IPO Watch" in article
    assert "AI optical parts maker 0 eyes Hong Kong listing" in article
    assert "https://example.com/ai-listing-0" in article


def test_filter_effective_items_dedupes_and_requires_relevant_news():
    duplicate = NewsItem(
        title="AI startup files for IPO",
        link="https://example.com/ai-ipo",
        summary="The company builds AI infrastructure.",
        source="Example",
        published="2026-06-17",
    )
    irrelevant = NewsItem(
        title="Weather update",
        link="https://example.com/weather",
        summary="Rain is expected.",
        source="Example",
        published="2026-06-17",
    )

    items = filter_effective_items([duplicate, duplicate, irrelevant])

    assert items == [duplicate]


def test_build_mock_articles_returns_insufficient_news_for_too_few_items():
    items = [
        NewsItem(f"AI startup {index} files for IPO", f"https://example.com/{index}", "AI IPO news.", "Example", "")
        for index in range(4)
    ]

    english, chinese = build_mock_articles(items, "2026-06-17")

    assert english == "insufficient news"
    assert chinese == "insufficient news"


def test_build_mock_articles_outputs_english_and_chinese_without_investment_advice():
    items = [
        NewsItem("AI startup files for IPO", "https://example.com/ai-ipo", "AI infrastructure company files.", "Feed", ""),
        NewsItem("Chip company plans listing", "https://example.com/chip", "Semiconductor listing watch.", "Feed", ""),
        NewsItem("New AI product launches", "https://example.com/product", "AI product expansion.", "Feed", ""),
        NewsItem("Startup funding points to AI demand", "https://example.com/funding", "Funding signal.", "Feed", ""),
        NewsItem("Public market appetite improves", "https://example.com/market", "Market signal.", "Feed", ""),
    ]

    english, chinese = build_mock_articles(items, "2026-06-17")

    assert "This is not financial advice." in english
    assert "这不是投资建议。" in chinese
    assert "## 5. Sources" in english
    assert "## 5. 来源" in chinese
    assert english.count("https://example.com/ai-ipo") == 1
    assert chinese.count("https://example.com/ai-ipo") == 1
    forbidden_terms = ["Buy", "Sell", "Hold", "Target price", "target prices", "目标价", "仓位建议"]
    assert not any(term in english for term in forbidden_terms)
    assert not any(term in chinese for term in forbidden_terms)

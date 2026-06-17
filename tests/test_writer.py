from pathlib import Path

import pytest

from feeds import NewsItem
from writer import (
    build_article_input,
    build_mock_article,
    draft_path_for_date,
    ensure_api_key,
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
            title="AI optical parts maker eyes Hong Kong listing",
            link="https://example.com/ai-listing",
            summary="The company is considering a large public listing.",
            source="Yahoo Finance news RSS",
            published="2026-06-17",
        )
    ]

    article = build_mock_article(items, "2026-06-17")

    assert "# Daily US IPO & AI Market Brief - 2026-06-17" in article
    assert "## 1. IPO Watch" in article
    assert "AI optical parts maker eyes Hong Kong listing" in article
    assert "https://example.com/ai-listing" in article

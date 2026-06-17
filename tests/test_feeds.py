from feeds import NewsItem, dedupe_items, item_from_entry


def test_item_from_entry_strips_html_summary():
    entry = {
        "title": "AI IPO window reopens",
        "link": "https://example.com/ai-ipo",
        "summary": "<p>Chip startups are testing public markets.</p>",
        "published": "Tue, 16 Jun 2026 12:00:00 GMT",
    }

    item = item_from_entry(entry, source="Example Feed")

    assert item == NewsItem(
        title="AI IPO window reopens",
        link="https://example.com/ai-ipo",
        summary="Chip startups are testing public markets.",
        source="Example Feed",
        published="Tue, 16 Jun 2026 12:00:00 GMT",
    )


def test_dedupe_items_prefers_first_link():
    first = NewsItem("IPO A", "https://example.com/a", "Summary", "Feed 1", "")
    duplicate = NewsItem("IPO A again", "https://example.com/a", "Other", "Feed 2", "")
    second = NewsItem("IPO B", "https://example.com/b", "Summary", "Feed 1", "")

    assert dedupe_items([first, duplicate, second]) == [first, second]

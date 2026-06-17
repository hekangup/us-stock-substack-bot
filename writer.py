from __future__ import annotations

import os
from pathlib import Path
import re

from openai import OpenAI, OpenAIError

from feeds import NewsItem


DEFAULT_MODEL = "gpt-5.5"
MIN_EFFECTIVE_NEWS = 5
RISK_NOTE_EN = "This is not financial advice."
RISK_NOTE_CN = "这不是投资建议。"
RELEVANCE_KEYWORDS = [
    "ipo",
    "listing",
    "listed",
    "new stock",
    "public market",
    "ai",
    "artificial intelligence",
    "chip",
    "semiconductor",
    "startup",
    "funding",
    "venture",
    "market",
]
INVESTMENT_ADVICE_TERMS = [
    "buy",
    "sell",
    "hold",
    "target price",
    "price target",
    "how to play",
    "目标价",
    "买入",
    "卖出",
    "持有",
    "仓位",
]


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


def _item_text(item: NewsItem) -> str:
    return f"{item.title} {item.summary}".lower()


def _has_any_keyword(value: str, keywords: list[str]) -> bool:
    text = value.lower()
    for keyword in keywords:
        if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text):
            return True
    return False


def filter_effective_items(items: list[NewsItem]) -> list[NewsItem]:
    unique: list[NewsItem] = []
    seen: set[str] = set()
    for item in items:
        key = item.link or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        text = _item_text(item)
        if not _has_any_keyword(text, RELEVANCE_KEYWORDS):
            continue
        if _has_any_keyword(text, INVESTMENT_ADVICE_TERMS):
            continue
        unique.append(item)
    return unique


def _take_matching(
    items: list[NewsItem],
    used: set[str],
    keywords: list[str],
    limit: int,
) -> list[NewsItem]:
    selected: list[NewsItem] = []
    for item in items:
        key = item.link or item.title.lower()
        if key in used:
            continue
        if not _has_any_keyword(_item_text(item), keywords):
            continue
        selected.append(item)
        used.add(key)
        if len(selected) == limit:
            break
    return selected


def _take_remaining(items: list[NewsItem], used: set[str], limit: int) -> list[NewsItem]:
    selected: list[NewsItem] = []
    for item in items:
        key = item.link or item.title.lower()
        if key in used:
            continue
        selected.append(item)
        used.add(key)
        if len(selected) == limit:
            break
    return selected


def _summary_line(item: NewsItem) -> str:
    return item.summary or "No RSS summary provided."


def _source_lines(items: list[NewsItem]) -> list[str]:
    return [f"- [{item.title}]({item.link}) - {item.source}" for item in items]


def build_mock_article(items: list[NewsItem], iso_date: str) -> str:
    english, _ = build_mock_articles(items, iso_date)
    return english


def build_mock_articles(items: list[NewsItem], iso_date: str) -> tuple[str, str]:
    effective_items = filter_effective_items(items)
    if len(effective_items) < MIN_EFFECTIVE_NEWS:
        return "insufficient news", "insufficient news"

    return (
        build_english_mock_article(effective_items, iso_date),
        build_chinese_mock_article(effective_items, iso_date),
    )


def build_english_mock_article(items: list[NewsItem], iso_date: str) -> str:
    used: set[str] = set()
    ipo_items = _take_matching(items, used, ["ipo", "listing", "listed", "new stock", "public market"], 5)
    ai_items = _take_matching(items, used, ["ai", "artificial intelligence", "chip", "semiconductor"], 5)
    market_items = _take_matching(items, used, ["market", "funding", "venture", "startup"], 5)
    if not market_items:
        market_items = _take_remaining(items, used, 3)
    lines = [
        f"# Daily US IPO & AI Market Brief - {iso_date}",
        "",
        f"> {RISK_NOTE_EN} This draft is limited to news summaries, trend observations, and risk notes.",
        "",
        "## 1. IPO Watch",
        "",
    ]
    for item in ipo_items:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - Source: {item.source}",
                f"  - Summary: {_summary_line(item)}",
                "  - Observation: Watch whether this headline points to renewed public-market appetite or stricter disclosure expectations.",
            ]
        )

    lines.extend(["", "## 2. AI Sector Moves", ""])
    for item in ai_items:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - Source: {item.source}",
                f"  - Summary: {_summary_line(item)}",
                "  - Observation: The key question is whether the news reflects durable AI adoption, infrastructure demand, or only short-term branding.",
            ]
        )

    lines.extend(["", "## 3. Market Signal", ""])
    if not market_items:
        lines.extend(
            [
                "- No separate market-signal item remained after IPO and AI categorization.",
                "- Trend observation: review the source list for whether attention is clustering around listings, AI products, or infrastructure themes.",
                "- Risk note: a thin news set can make daily conclusions noisy.",
            ]
        )
    for item in market_items:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - Source: {item.source}",
                f"  - Summary: {_summary_line(item)}",
                "  - Risk note: Treat this as context for market sentiment, not a trading instruction.",
            ]
        )
    lines.extend([
        "",
        "## 4. Risk Notes",
        "",
        f"- {RISK_NOTE_EN}",
        "- This mock draft uses live RSS inputs but does not call OpenAI.",
        "- Review facts and links before publishing.",
        "- The draft avoids trading calls, price forecasts, portfolio sizing, and personalized investment recommendations.",
        "",
        "## 5. Sources",
        "",
    ])
    lines.extend(_source_lines(items))
    return "\n".join(lines).strip()


def build_chinese_mock_article(items: list[NewsItem], iso_date: str) -> str:
    used: set[str] = set()
    ipo_items = _take_matching(items, used, ["ipo", "listing", "listed", "new stock", "public market"], 5)
    ai_items = _take_matching(items, used, ["ai", "artificial intelligence", "chip", "semiconductor"], 5)
    market_items = _take_matching(items, used, ["market", "funding", "venture", "startup"], 5)
    if not market_items:
        market_items = _take_remaining(items, used, 3)

    lines = [
        f"# 每日美股 IPO 与 AI 市场简报 - {iso_date}",
        "",
        f"> {RISK_NOTE_CN} 本文只做新闻摘要、趋势观察和风险提示。",
        "",
        "## 1. IPO 观察",
        "",
    ]
    for item in ipo_items:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - 来源：{item.source}",
                f"  - 摘要：{_summary_line(item)}",
                "  - 观察：关注这条新闻是否反映公开市场风险偏好回升，或对披露质量提出更高要求。",
            ]
        )

    lines.extend(["", "## 2. AI 行业动态", ""])
    for item in ai_items:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - 来源：{item.source}",
                f"  - 摘要：{_summary_line(item)}",
                "  - 观察：重点看它指向的是 AI 真实采用、基础设施需求，还是短期概念包装。",
            ]
        )

    lines.extend(["", "## 3. 市场信号", ""])
    if not market_items:
        lines.extend(
            [
                "- IPO 和 AI 栏目已覆盖当天主要有效新闻，没有剩余的独立市场信号条目。",
                "- 趋势观察：可以从来源列表继续判断市场注意力是否集中在上市、AI 产品或基础设施主题上。",
                "- 风险提示：新闻样本较薄时，每日结论容易有噪音。",
            ]
        )
    for item in market_items:
        lines.extend(
            [
                f"- **{item.title}**",
                f"  - 来源：{item.source}",
                f"  - 摘要：{_summary_line(item)}",
                "  - 风险提示：这只能作为市场情绪背景，不能作为交易指令。",
            ]
        )

    lines.extend([
        "",
        "## 4. 风险提示",
        "",
        f"- {RISK_NOTE_CN}",
        "- 本 mock 草稿使用真实 RSS 输入，但不会调用 OpenAI。",
        "- 发布前需要人工核对事实和来源链接。",
        "- 本文避免交易判断、价格预测、持仓比例和个性化投资建议。",
        "",
        "## 5. 来源",
        "",
    ])
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

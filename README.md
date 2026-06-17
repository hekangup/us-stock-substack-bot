# US Stock Substack Bot

每天从公开 RSS 源抓取美股 IPO、新股和 AI 行业新闻的标题、链接、摘要，然后调用 OpenAI API 生成一篇英文 Substack Markdown 草稿。

项目只使用 RSS 中公开提供的标题、链接和摘要，不复制新闻全文。生成内容定位为摘要和评论，不自动发布。

## 项目结构

```text
us-stock-substack-bot/
├── main.py
├── feeds.py
├── feeds.json
├── writer.py
├── prompts/
│   └── daily_brief.md
├── drafts/
├── drafts_cn/
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── .github/
    └── workflows/
        daily.yml
```

## 本地运行

```bash
cd us-stock-substack-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```bash
OPENAI_API_KEY=你的 OpenAI API Key
OPENAI_MODEL=gpt-5.5
```

生成今天的草稿：

```bash
python main.py
```

生成指定日期的草稿：

```bash
python main.py --date 2026-06-16
```

如果 OpenAI API 暂时没有额度，可以先用真实 RSS 生成本地测试草稿：

```bash
python main.py --mock
```

`--mock` 模式会生成英文和中文两个 Markdown 骨架，只做新闻摘要、趋势观察和风险提示，不写交易建议、目标价或仓位建议。如果有效新闻少于 5 条，输出内容会是：

```text
insufficient news
```

输出文件位于：

```text
drafts/YYYY-MM-DD.md
drafts_cn/YYYY-MM-DD.md
```

## GitHub Actions 自动运行

工作流文件位于 `.github/workflows/daily.yml`，默认每天 UTC 12:00 运行一次，也支持手动 `workflow_dispatch`。

当前工作流默认运行 mock 模式：

```bash
python main.py --mock
```

它只抓 RSS 并生成中英文 Markdown 骨架，不调用 OpenAI API，也不自动发布。

在 GitHub 仓库中添加 Secret：

```text
OPENAI_API_KEY
```

可选添加 Repository Variable：

```text
OPENAI_MODEL
```

Actions 只会生成 Markdown 草稿并上传为 artifact，不会自动提交、不自动发布到 Substack。

## 修改 RSS 源

RSS 源集中配置在 `feeds.json` 中。默认包含：

```text
NASDAQ IPO Calendar RSS
SEC press releases
Yahoo Finance news RSS
TechCrunch AI RSS
The Verge AI RSS
Crunchbase News RSS
```

如果某个 RSS 地址失效，脚本会打印警告并继续使用其它来源。你可以直接修改 `feeds.json`，也可以运行时指定另一个配置文件：

```bash
python main.py --feeds path/to/feeds.json
```

## 测试

```bash
pytest
```

## 注意

- `.env` 已写入 `.gitignore`，不要提交真实 API Key。
- `drafts/*.md` 和 `drafts_cn/*.md` 默认忽略，避免把自动生成草稿直接提交到 GitHub。
- 生成内容是公开 RSS 摘要基础上的新闻摘要、趋势观察和风险提示，不构成投资建议。

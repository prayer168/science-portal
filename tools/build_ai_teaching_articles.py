from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


DATE_RE = re.compile(r"^日期：\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ORDERED_RE = re.compile(r"^\d+\.\s+(.+)$")
UNORDERED_RE = re.compile(r"^[-*]\s+(.+)$")
URL_RE = re.compile(r"https?://[^\s<]+")


def normalize_date(match: re.Match[str]) -> tuple[str, str]:
    year, month, day = match.groups()
    iso = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    zh = f"{int(year):04d} 年 {int(month):02d} 月 {int(day):02d} 日"
    return iso, zh


def trim_rules(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    while out and out[0].strip() == "---":
        out.pop(0)
        while out and not out[0].strip():
            out.pop(0)
    while out and out[-1].strip() == "---":
        out.pop()
        while out and not out[-1].strip():
            out.pop()
    return out


def inline_markdown(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    def linkify(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in "。。，、；;：:）)]}":
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        return f'<a href="{html.escape(raw, quote=True)}" target="_blank" rel="noopener">{raw}</a>{trailing}'

    return URL_RE.sub(linkify, escaped)


def flush_paragraph(parts: list[str], output: list[str]) -> None:
    if not parts:
        return
    body = "<br>".join(inline_markdown(part.rstrip()) for part in parts)
    output.append(f"<p>{body}</p>")
    parts.clear()


def render_markdown(lines: list[str]) -> str:
    output: list[str] = []
    paragraph: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_paragraph(paragraph, output)
            i += 1
            continue
        if stripped == "---":
            flush_paragraph(paragraph, output)
            output.append("<hr>")
            i += 1
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            flush_paragraph(paragraph, output)
            level = min(len(heading.group(1)) + 1, 6)
            output.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            i += 1
            continue

        ordered = ORDERED_RE.match(stripped)
        if ordered:
            flush_paragraph(paragraph, output)
            items: list[str] = []
            while i < len(lines):
                item_match = ORDERED_RE.match(lines[i].strip())
                if not item_match:
                    break
                items.append(f"<li>{inline_markdown(item_match.group(1))}</li>")
                i += 1
            output.append("<ol>" + "".join(items) + "</ol>")
            continue

        unordered = UNORDERED_RE.match(stripped)
        if unordered:
            flush_paragraph(paragraph, output)
            items = []
            while i < len(lines):
                item_match = UNORDERED_RE.match(lines[i].strip())
                if not item_match:
                    break
                items.append(f"<li>{inline_markdown(item_match.group(1))}</li>")
                i += 1
            output.append("<ul>" + "".join(items) + "</ul>")
            continue

        if stripped.startswith(">"):
            flush_paragraph(paragraph, output)
            quote = stripped.lstrip(">").strip()
            output.append(f"<blockquote>{inline_markdown(quote)}</blockquote>")
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph(paragraph, output)
    return "\n".join(output)


def extract_articles(source: Path) -> list[dict[str, str | list[str]]]:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    markers: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines):
        match = DATE_RE.match(line.strip())
        if match:
            iso, zh = normalize_date(match)
            markers.append((idx, iso, zh))
    if not markers:
        raise ValueError("No article date markers found.")

    articles: list[dict[str, str | list[str]]] = []
    for pos, (date_idx, iso, zh) in enumerate(markers):
        next_idx = markers[pos + 1][0] if pos + 1 < len(markers) else len(lines)
        start_idx = date_idx
        previous_nonblank = date_idx - 1
        while previous_nonblank >= 0 and not lines[previous_nonblank].strip():
            previous_nonblank -= 1
        if previous_nonblank >= 0 and HEADING_RE.match(lines[previous_nonblank].strip()):
            start_idx = previous_nonblank

        chunk = trim_rules(lines[start_idx:next_idx])
        title = ""
        body_lines: list[str] = []
        for line in chunk:
            if DATE_RE.match(line.strip()):
                continue
            heading = HEADING_RE.match(line.strip())
            if heading and not title and len(heading.group(1)) == 1:
                title = heading.group(2).strip()
                continue
            body_lines.append(line)
        if not title:
            title = f"AI 教學文章 {iso}"
        body_lines = trim_rules(body_lines)
        articles.append({"date": iso, "date_zh": zh, "title": title, "body_lines": body_lines})

    return articles


def article_html(title: str, date_zh: str, body: str) -> str:
    page_title = html.escape(f"{title}｜黑熊老師自然科學數位教材中心", quote=False)
    title_html = html.escape(title, quote=False)
    date_html = html.escape(date_zh, quote=False)
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <link rel="icon" href="../../favicon.png">
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0d1117;
      --panel: #161b22;
      --card: #1a1d24;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --accent-2: #1dd1a1;
      --warm: #ff9f43;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif;
      line-height: 1.85;
      background:
        radial-gradient(circle at 20% 0%, rgba(29, 209, 161, .12), transparent 32rem),
        linear-gradient(180deg, #0d1117 0%, #11151d 100%);
      color: var(--text);
    }}
    a {{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    .site-header {{
      border-bottom: 1px solid var(--border);
      background: rgba(13, 17, 23, .86);
      backdrop-filter: blur(16px);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    .header-inner {{
      width: min(960px, calc(100vw - 32px));
      margin: 0 auto;
      min-height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--text);
      text-decoration: none;
      font-weight: 800;
      letter-spacing: .02em;
    }}
    .brand img {{ width: 34px; height: 34px; border-radius: 8px; }}
    .nav-links {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
    .nav-links a {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 4px 10px;
      color: var(--text);
      text-decoration: none;
      background: rgba(22, 27, 34, .76);
      font-size: 13px;
      font-weight: 700;
    }}
    main {{
      width: min(860px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 36px 0 56px;
    }}
    .article-head {{
      padding: 22px 0 24px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 26px;
    }}
    .eyebrow {{
      color: var(--accent-2);
      font-size: 13px;
      font-weight: 800;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(26px, 5vw, 42px);
      line-height: 1.28;
      letter-spacing: 0;
      color: #f0f6fc;
    }}
    .date {{
      margin-top: 14px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 700;
    }}
    article {{
      background: rgba(22, 27, 34, .72);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: clamp(20px, 4vw, 36px);
    }}
    article h2 {{
      margin: 34px 0 12px;
      color: #f0f6fc;
      font-size: 23px;
      line-height: 1.4;
      border-left: 4px solid var(--warm);
      padding-left: 12px;
      letter-spacing: 0;
    }}
    article h3 {{
      margin: 26px 0 10px;
      color: #f0f6fc;
      font-size: 18px;
      letter-spacing: 0;
    }}
    article p {{ margin: 0 0 1.05em; }}
    article ul, article ol {{ padding-left: 1.5em; margin: 0 0 1.1em; }}
    article li {{ margin: .35em 0; }}
    blockquote {{
      margin: 1.2em 0;
      border-left: 4px solid var(--accent);
      padding: .1em 0 .1em 1em;
      color: #c9d1d9;
      background: rgba(88, 166, 255, .08);
    }}
    hr {{ border: 0; border-top: 1px solid var(--border); margin: 28px 0; }}
    .footer-note {{
      width: min(860px, calc(100vw - 32px));
      margin: 0 auto 36px;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }}
    @media (max-width: 640px) {{
      .header-inner {{ align-items: flex-start; flex-direction: column; padding: 12px 0; }}
      .nav-links {{ justify-content: flex-start; }}
      article {{ padding: 18px; }}
      article h2 {{ font-size: 20px; }}
    }}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="../../index.html">
        <img src="../../favicon.png" alt="">
        <span>黑熊老師自然科學數位教材中心</span>
      </a>
      <nav class="nav-links" aria-label="文章導覽">
        <a href="../../index.html#教學文章">教學文章</a>
        <a href="../../index.html">教材中心</a>
      </nav>
    </div>
  </header>
  <main>
    <div class="article-head">
      <div class="eyebrow">AI 與教學／自然科學教育文章</div>
      <h1>{title_html}</h1>
      <div class="date">{date_html}</div>
    </div>
    <article>
{body}
    </article>
  </main>
  <div class="footer-note">© 2026 陳賢宗｜本文章供教育用途閱讀與教學參考。</div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out-dir", default=Path("articles/ai-teaching"), type=Path)
    parser.add_argument("--data-file", default=Path("data/ai-teaching-articles.js"), type=Path)
    args = parser.parse_args()

    articles = extract_articles(args.source)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.data_file.parent.mkdir(parents=True, exist_ok=True)

    manifest = []
    for article in articles:
        date = str(article["date"])
        title = str(article["title"])
        date_zh = str(article["date_zh"])
        body = render_markdown(article["body_lines"])  # type: ignore[arg-type]
        path = args.out_dir / f"{date}.html"
        path.write_text(article_html(title, date_zh, body), encoding="utf-8")
        manifest.append({
            "cat": "教學文章",
            "name": f"{date}｜{title}",
            "url": f"articles/ai-teaching/{date}.html",
            "icon": "📄",
        })

    data = "window.AI_TEACHING_ARTICLES = "
    data += json.dumps(manifest, ensure_ascii=False, indent=2)
    data += ";\n"
    args.data_file.write_text(data, encoding="utf-8")
    print(f"Generated {len(articles)} article pages and {args.data_file}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

from build_ai_teaching_articles import article_html, render_markdown


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(sys.argv[1]).resolve()
ARTICLE_DIR = ROOT / "articles" / "pbl"
MANIFEST = ROOT / "data" / "ai-teaching-articles.js"
SIGNATURE = re.compile(r"陳賢宗與AI協作編撰｜(\d{4})年(\d{2})月(\d{2})日\s*$")


def excerpt(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    selected = " ".join(p for p in paragraphs if not p.startswith("#") and not p.startswith("陳賢宗與AI"))
    selected = re.sub(r"\*\*|[*`\[\]]", "", selected)
    return selected[:117].rstrip() + "…"


def main() -> None:
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    previous = MANIFEST.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";")
    manifest = json.loads(previous)
    for source in sorted(SOURCE_DIR.glob("2026-*.md")):
        raw = source.read_text(encoding="utf-8-sig")
        lines = raw.splitlines()
        title_match = next((re.match(r"^#\s+(.+)$", line) for line in lines if line.startswith("# ")), None)
        if not title_match:
            raise ValueError(f"Missing H1 in {source.name}")
        title = title_match.group(1).strip()
        date = source.name[:10]
        duplicate = next((item for item in manifest if item.get("name", "").endswith("｜" + title)), None)
        if duplicate and duplicate.get("url") != f"articles/pbl/{date}.html":
            raise ValueError(f"Duplicate title already exists: {title}")
        sig = SIGNATURE.search(raw)
        if not sig:
            raise ValueError(f"Missing required author signature in {source.name}")
        signature_date = f"{sig.group(1)} 年 {sig.group(2)} 月 {sig.group(3)} 日"
        date_zh = f"{int(date[:4])} 年 {int(date[5:7]):02d} 月 {int(date[8:10]):02d} 日"
        # Keep source Markdown alongside generated HTML for future edits and full-text provenance.
        shutil.copyfile(source, ARTICLE_DIR / source.name)
        content = "\n".join(line for line in lines if not SIGNATURE.match(line.strip()))
        rendered = render_markdown(content.splitlines())
        page = article_html(title, date_zh, rendered)
        description = html.escape(excerpt(raw), quote=True)
        canonical = f"https://prayer168.github.io/science-portal/articles/pbl/{date}.html"
        metadata = (f'  <meta name="description" content="{description}">\n'
                    f'  <link rel="canonical" href="{canonical}">\n'
                    f'  <meta property="og:title" content="{html.escape(title, quote=True)}">\n'
                    f'  <meta property="og:description" content="{description}">\n'
                    f'  <meta property="og:url" content="{canonical}">\n  <title>')
        page = page.replace("  <title>", metadata, 1)
        page = page.replace('<div class="eyebrow">AI 與教學／自然科學教育文章</div>', '<div class="eyebrow">PBL 教學設計</div>')
        page = page.replace(f'<div class="date">{date_zh}</div>', f'<div class="date">{date_zh}｜作者：陳賢宗與 AI 協作編撰｜分類：PBL 教學設計</div>')
        page = page.replace("</article>", f'<p class="signature">陳賢宗與AI協作編撰｜{signature_date}</p>\n    </article>')
        page = page.replace("    hr {", "    .signature { margin-top: 2rem; color: var(--muted); font-weight: 700; text-align: right; }\n    a { overflow-wrap: anywhere; }\n    hr {")
        (ARTICLE_DIR / f"{date}.html").write_text(page, encoding="utf-8")
        item = {"cat": "教學文章", "name": f"{date}｜{title}", "url": f"articles/pbl/{date}.html", "icon": "📄"}
        manifest = [entry for entry in manifest if not (entry.get("url") == item["url"] or entry.get("name") == item["name"])]
        manifest.append(item)
    teaching = [x for x in manifest if x.get("cat") == "教學文章"]
    other = [x for x in manifest if x.get("cat") != "教學文章"]
    teaching.sort(key=lambda x: x["name"][:10], reverse=True)
    MANIFEST.write_text("window.AI_TEACHING_ARTICLES = " + json.dumps(teaching + other, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print(f"Imported {len(list(SOURCE_DIR.glob('2026-*.md')))} PBL articles")


if __name__ == "__main__":
    main()

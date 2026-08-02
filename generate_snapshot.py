# -*- coding: utf-8 -*-
"""
直近(既定24時間)の新着論文をまとめた、SNS共有カード風の画像
(docs/snapshot.png)と、それを表示するだけの単独ページ(docs/snapshot.html)
を生成する。

GitHub Pagesでこのリポジトリを公開していれば、
  https://<アカウント>.github.io/<リポジトリ名>/snapshot.png
  https://<アカウント>.github.io/<リポジトリ名>/snapshot.html
が安定したURLになる。researchmapなどのプロフィールページから、この
どちらかのURLにリンクしておけば、日々の自動更新がそのまま反映される。

日本語を描画するため、Noto Sans CJK フォントが必要(Ubuntu/GitHub Actions
では apt install fonts-noto-cjk で導入できる)。見つからない場合は
Pillowのデフォルトフォント(日本語非対応)にフォールバックする。

使い方:
    python generate_snapshot.py
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    DB_PATH,
    SNAPSHOT_LOOKBACK_HOURS,
    SNAPSHOT_OUTPUT_PATH,
    SNAPSHOT_PAGE_PATH,
    SNAPSHOT_MAX_HEADLINES,
    KEYWORDS,
    AUTHOR_WATCHLIST,
)
from db import get_conn
from keyword_utils import matched_keywords
from author_utils import matched_authors

BASE_DIR = Path(__file__).resolve().parent

WIDTH, HEIGHT = 1200, 630
MARGIN = 60

COLOR_BG = (250, 249, 247)
COLOR_TEXT = (43, 43, 40)
COLOR_MUTED = (138, 132, 120)
COLOR_ACCENT = (122, 92, 62)
COLOR_LINE = (229, 225, 218)
COLOR_TIER = {
    0: (197, 194, 186),
    1: (217, 185, 92),
    2: (217, 138, 58),
    3: (193, 68, 43),
}

_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-{weight}.ttc",
]


def _load_font(weight, size):
    for template in _FONT_CANDIDATES:
        path = Path(template.format(weight=weight))
        if path.exists():
            return ImageFont.truetype(str(path), size, index=0)
    # 見つからない場合はデフォルトフォント(日本語は文字化けする点に注意)
    return ImageFont.load_default()


def _truncate(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    while text and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]
    return text + ellipsis


def _collect_recent_articles(conn, since):
    """直近の記事を、ハイライトの強さ(tier)が高い順に並べて返す。"""
    rows = conn.execute(
        "SELECT title, journal, abstract, authors FROM articles WHERE fetched_at >= ?",
        (since,),
    ).fetchall()

    items = []
    for title, journal, abstract, authors in rows:
        kw_hits = matched_keywords(title, abstract, KEYWORDS)
        author_hits = matched_authors(authors, AUTHOR_WATCHLIST)
        tier = min(3, len(kw_hits))
        if author_hits:
            tier = max(tier, 1)
        items.append(
            {
                "title": title or "(タイトル不明)",
                "journal": journal or "",
                "tier": tier,
                "kw_count": len(kw_hits),
            }
        )

    items.sort(key=lambda x: (-x["tier"], -x["kw_count"]))
    return items


def build_snapshot():
    conn = get_conn(DB_PATH)
    since = (
        datetime.now(timezone.utc) - timedelta(hours=SNAPSHOT_LOOKBACK_HOURS)
    ).strftime("%Y-%m-%d %H:%M:%S")
    items = _collect_recent_articles(conn, since)
    conn.close()

    total = len(items)
    headlines = items[:SNAPSHOT_MAX_HEADLINES]

    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    font_title = _load_font("Bold", 40)
    font_date = _load_font("Regular", 22)
    font_stat = _load_font("Bold", 56)
    font_stat_label = _load_font("Regular", 22)
    font_headline = _load_font("Regular", 26)
    font_meta = _load_font("Regular", 18)
    font_footer = _load_font("Regular", 16)

    # ヘッダー
    draw.text((MARGIN, 44), "journalfeed", font=font_title, fill=COLOR_ACCENT)
    today_str = datetime.now().strftime("%Y年%m月%d日")
    date_w = draw.textlength(today_str, font=font_date)
    draw.text((WIDTH - MARGIN - date_w, 58), today_str, font=font_date, fill=COLOR_MUTED)

    # 大きな件数表示
    stat_y = 120
    if total > 0:
        stat_text = str(total)
        draw.text((MARGIN, stat_y), stat_text, font=font_stat, fill=COLOR_TEXT)
        stat_w = draw.textlength(stat_text, font=font_stat)
        draw.text(
            (MARGIN + stat_w + 14, stat_y + 22),
            "件の新着論文",
            font=font_stat_label,
            fill=COLOR_MUTED,
        )
    else:
        draw.text(
            (MARGIN, stat_y + 20),
            "本日の新着はありません",
            font=font_stat_label,
            fill=COLOR_MUTED,
        )

    line_y = stat_y + 90
    draw.line([(MARGIN, line_y), (WIDTH - MARGIN, line_y)], fill=COLOR_LINE, width=1)

    # 見出しリスト
    y = line_y + 26
    line_height = 56
    max_text_width = WIDTH - MARGIN * 2 - 40

    for item in headlines:
        color = COLOR_TIER.get(item["tier"], COLOR_TIER[0])
        draw.ellipse([(MARGIN, y + 8), (MARGIN + 14, y + 22)], fill=color)

        title = item["title"].replace("\n", " ")
        title_text = _truncate(draw, title, font_headline, max_text_width)
        draw.text((MARGIN + 26, y), title_text, font=font_headline, fill=COLOR_TEXT)
        draw.text((MARGIN + 26, y + 30), item["journal"], font=font_meta, fill=COLOR_MUTED)

        y += line_height

    if total > SNAPSHOT_MAX_HEADLINES:
        more_text = f"他 {total - SNAPSHOT_MAX_HEADLINES} 件..."
        draw.text((MARGIN + 26, y), more_text, font=font_meta, fill=COLOR_MUTED)

    draw.text((MARGIN, HEIGHT - 40), "journalfeed が自動生成", font=font_footer, fill=COLOR_MUTED)

    out_path = BASE_DIR / SNAPSHOT_OUTPUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)

    page_path = BASE_DIR / SNAPSHOT_PAGE_PATH
    page_path.parent.mkdir(parents=True, exist_ok=True)
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>journalfeed スナップショット</title>
<style>
  body {{
    margin: 0;
    padding: 2rem 1rem;
    background: #faf9f7;
    display: flex;
    flex-direction: column;
    align-items: center;
    font-family: "Hiragino Sans", "Yu Gothic", "Segoe UI", sans-serif;
  }}
  img {{
    max-width: 100%;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  }}
  a {{
    margin-top: 1.2rem;
    color: #7a5c3e;
    font-size: 0.9rem;
    text-decoration: none;
  }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <img src="{out_path.name}" alt="journalfeed スナップショット">
  <a href="index.html">全件のレポートを見る →</a>
</body>
</html>
"""
    page_path.write_text(html, encoding="utf-8")

    print(f"{total} 件を対象にスナップショットを生成しました。")
    print(f"画像: {out_path}")
    print(f"ページ: {page_path}")
    return out_path


if __name__ == "__main__":
    build_snapshot()

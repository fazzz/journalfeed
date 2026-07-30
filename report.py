# -*- coding: utf-8 -*-
"""
Step3: DB内の直近の記事(fetched_at基準)をジャーナルごとにまとめ、
静的HTMLレポートを生成する。

summary_ja が入っていればそれを表示し、無ければ状況に応じて
「要約待ち」「abstract取得待ち」「abstractが無いため要約なし」を表示する。
LLM要約(Step2)をまだ実行していなくても、そのまま実行できる。

使い方:
    python report.py
"""

import re
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    DB_PATH,
    REPORT_OUTPUT_DIR,
    REPORT_LOOKBACK_DAYS,
    DOCS_OUTPUT_PATH,
    KEYWORDS,
    JOURNAL_HOT_MIN_HIT_RATIO,
    JOURNAL_HOT_MIN_HITS,
    AUTHOR_WATCHLIST,
)
from db import get_conn, recent_articles_for_report
from keyword_utils import matched_keywords
from author_utils import matched_authors
from journal_abbrev import load_abbreviations

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"


def _slugify(text):
    """ジャーナル名をアンカーリンク用のIDに変換する。"""
    slug = re.sub(r"[^a-zA-Z0-9\-]+", "-", (text or "").strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "journal"


def _hit_tier(hit_count):
    if hit_count <= 0:
        return 0
    if hit_count == 1:
        return 1
    if hit_count == 2:
        return 2
    return 3


def _build_article_view(row):
    (
        doi,
        journal,
        title,
        authors,
        pub_date,
        link,
        abstract,
        abstract_status,
        summary_ja,
        fetched_at,
    ) = row

    if summary_ja:
        summary_text = summary_ja
        summary_kind = "ok"
    elif abstract_status == "unavailable":
        summary_text = "abstractが取得できなかったため、要約はありません(タイトルのみ)。"
        summary_kind = "none"
    elif abstract:
        summary_text = "abstractは取得済みです。要約はまだ生成されていません。"
        summary_kind = "pending"
    else:
        summary_text = "abstract取得待ちです。"
        summary_kind = "pending"

    matched = matched_keywords(title, abstract, KEYWORDS)
    hit_count = len(matched)

    author_matches = matched_authors(authors, AUTHOR_WATCHLIST)
    author_hit_count = len(author_matches)

    # 表示用のtier: キーワードによる色分けはそのままに、著者ウォッチにヒットした
    # 記事は(キーワードが0件でも)最低でもtier1相当の見た目になるよう底上げする。
    display_tier = _hit_tier(hit_count)
    if author_hit_count > 0:
        display_tier = max(display_tier, 1)

    return {
        "doi": doi,
        "journal": journal,
        "title": title or "(タイトル不明)",
        "authors": authors,
        "pub_date": pub_date,
        "link": link or f"https://doi.org/{doi}",
        "abstract": abstract,
        "summary": summary_text,
        "summary_kind": summary_kind,
        "keyword_hits": matched,
        "hit_count": hit_count,
        "hit_tier": _hit_tier(hit_count),
        "author_hits": author_matches,
        "author_hit_count": author_hit_count,
        "display_tier": display_tier,
    }


def build_report():
    conn = get_conn(DB_PATH)
    since = (
        datetime.now(timezone.utc) - timedelta(days=REPORT_LOOKBACK_DAYS)
    ).strftime("%Y-%m-%d %H:%M:%S")
    rows = recent_articles_for_report(conn, since)
    conn.close()

    articles = [_build_article_view(r) for r in rows]

    grouped_dict = OrderedDict()
    for a in sorted(articles, key=lambda a: a["journal"] or ""):
        grouped_dict.setdefault(a["journal"] or "(誌名不明)", []).append(a)

    abbreviations = load_abbreviations()

    grouped = []
    seen_slugs = set()
    for journal, items in grouped_dict.items():
        slug = _slugify(journal)
        base_slug, i = slug, 2
        while slug in seen_slugs:
            slug = f"{base_slug}-{i}"
            i += 1
        seen_slugs.add(slug)

        total_hits = sum(a["hit_count"] for a in items)
        hit_articles = sum(1 for a in items if a["hit_count"] > 0)
        hit_ratio = hit_articles / len(items) if items else 0
        is_hot = (
            hit_ratio >= JOURNAL_HOT_MIN_HIT_RATIO or total_hits >= JOURNAL_HOT_MIN_HITS
        )

        display_name = abbreviations.get(journal, journal)

        grouped.append(
            {
                "journal": journal,
                "display_name": display_name,
                "slug": slug,
                "articles": items,
                "count": len(items),
                "total_hits": total_hits,
                "hit_articles": hit_articles,
                "is_hot": is_hot,
            }
        )

    # ヒットの多いジャーナルほど上に来るよう並べ替える(同率ならジャーナル名順を維持)
    grouped.sort(key=lambda g: (-g["total_hits"], g["journal"] or ""))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")

    today_str = datetime.now().strftime("%Y-%m-%d")
    html = template.render(
        grouped=grouped,
        generated_at=today_str,
        lookback_days=REPORT_LOOKBACK_DAYS,
        total_count=len(articles),
    )

    out_dir = BASE_DIR / REPORT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    dated_path = out_dir / f"report_{today_str}.html"
    dated_path.write_text(html, encoding="utf-8")

    latest_path = out_dir / "latest.html"
    latest_path.write_text(html, encoding="utf-8")

    docs_path = BASE_DIR / DOCS_OUTPUT_PATH
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(html, encoding="utf-8")

    print(f"{len(articles)} 件を {len(grouped)} 誌ぶんまとめました。")
    print(f"生成しました: {dated_path}")
    print(f"最新版: {latest_path}")
    print(f"GitHub Pages公開用: {docs_path}")
    return dated_path


if __name__ == "__main__":
    build_report()

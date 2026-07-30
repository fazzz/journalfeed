# -*- coding: utf-8 -*-
"""
journalfeed Step1: 以下3系統から新着論文を取得し、SQLiteに保存する(DOIで重複排除)。

  1. ジャーナル (JOURNALS): Crossref API を ISSN で絞り込み
  2. プリプリントサーバー (PREPRINT_SOURCES): Crossref API を DOIプレフィックスで絞り込み
     (bioRxiv・ChemRxivなど、Crossrefに登録されているもの)
  3. arXiv (ARXIV_CATEGORIES): arXiv専用API(Crossref非登録のため別ルート)

ジャーナルは全件保存するが、プリプリント(2・3)は誌名による絞り込みが効かず
量が多くなりやすいため、KEYWORDSに MIN_KEYWORD_HITS_FOR_PREPRINTS 件以上
ヒットしたものだけを保存する。

使い方:
    python main.py
"""

import time

from config import (
    JOURNALS,
    FILTERED_JOURNALS,
    PREPRINT_SOURCES,
    ARXIV_CATEGORIES,
    ARXIV_MAX_RESULTS,
    DB_PATH,
    LOOKBACK_DAYS,
    ROWS_PER_QUERY,
    CROSSREF_REQUEST_INTERVAL,
    KEYWORDS,
    MIN_KEYWORD_HITS_FOR_PREPRINTS,
    AUTHOR_WATCHLIST,
)
from db import get_conn, insert_article
from crossref_client import fetch_new_works, fetch_new_works_by_prefix, default_from_date
from arxiv_client import fetch_new_arxiv, arxiv_date_range
from keyword_utils import matched_keywords
from author_utils import matched_authors


def _ingest(conn, label, works):
    """works(辞書のリスト)をDBに保存する。戻り値は (新規件数, 対象件数)。"""
    new_count = 0
    for w in works:
        if not w.get("doi"):
            continue
        is_new = insert_article(
            conn,
            journal=label,
            doi=w["doi"],
            title=w["title"],
            authors=w["authors"],
            pub_date=w["pub_date"],
            link=w["link"],
            abstract=w["abstract"],
        )
        if is_new:
            new_count += 1
            title = w["title"] or "(no title)"
            print(f"    + 新規: {title[:60]}")
    return new_count, len(works)


def _filter_by_keywords(works, min_hits):
    """タイトル・アブストラクトにKEYWORDSがmin_hits件以上ヒットするか、
    著者ウォッチリストに載っている著者の記事だけを残す
    (プリプリント向けのノイズ削減フィルタ)。"""
    kept = []
    for w in works:
        kw_hits = matched_keywords(w.get("title"), w.get("abstract"), KEYWORDS)
        author_hits = matched_authors(w.get("authors"), AUTHOR_WATCHLIST)
        if len(kw_hits) >= min_hits or author_hits:
            kept.append(w)
    return kept


def run():
    conn = get_conn(DB_PATH)
    from_date = default_from_date(LOOKBACK_DAYS)
    total_new = 0
    total_seen = 0

    # --- 1. ジャーナル (Crossref / ISSN) ---
    for j in JOURNALS:
        journal, issn = j["journal"], j["issn"]
        print(f"[fetch] {journal} (ISSN {issn}) since {from_date}")
        try:
            works = fetch_new_works(issn, from_date, rows=ROWS_PER_QUERY)
        except Exception as e:
            print(f"  取得失敗: {e}")
            continue
        print(f"  {len(works)} 件取得")
        n, s = _ingest(conn, journal, works)
        total_new += n
        total_seen += s
        time.sleep(CROSSREF_REQUEST_INTERVAL)

    # --- 2. ISSN指定だがキーワードフィルタを適用するジャーナル ---
    for j in FILTERED_JOURNALS:
        journal, issn = j["journal"], j["issn"]
        print(f"[fetch] {journal} (ISSN {issn}, キーワードフィルタあり) since {from_date}")
        try:
            works = fetch_new_works(issn, from_date, rows=ROWS_PER_QUERY)
        except Exception as e:
            print(f"  取得失敗: {e}")
            continue
        print(f"  {len(works)} 件取得(フィルタ前)")
        works = _filter_by_keywords(works, MIN_KEYWORD_HITS_FOR_PREPRINTS)
        print(f"  {len(works)} 件がキーワード{MIN_KEYWORD_HITS_FOR_PREPRINTS}件以上ヒット")
        n, s = _ingest(conn, journal, works)
        total_new += n
        total_seen += s
        time.sleep(CROSSREF_REQUEST_INTERVAL)

    # --- 3. プリプリントサーバー (Crossref / DOIプレフィックス) ---
    for p in PREPRINT_SOURCES:
        label = p["journal"]
        prefix = p["prefix"]
        institution_filter = p.get("institution_filter")
        print(f"[fetch] {label} (prefix {prefix}) since {from_date}")
        try:
            works = fetch_new_works_by_prefix(
                prefix, from_date, rows=ROWS_PER_QUERY, institution_filter=institution_filter
            )
        except Exception as e:
            print(f"  取得失敗: {e}")
            continue
        print(f"  {len(works)} 件取得(フィルタ前)")
        works = _filter_by_keywords(works, MIN_KEYWORD_HITS_FOR_PREPRINTS)
        print(f"  {len(works)} 件がキーワード{MIN_KEYWORD_HITS_FOR_PREPRINTS}件以上ヒット")
        n, s = _ingest(conn, label, works)
        total_new += n
        total_seen += s
        time.sleep(CROSSREF_REQUEST_INTERVAL)

    # --- 4. arXiv (専用API) ---
    arxiv_from, arxiv_to = arxiv_date_range(LOOKBACK_DAYS)
    for category in ARXIV_CATEGORIES:
        label = f"arXiv: {category}"
        print(f"[fetch] {label} ({arxiv_from}〜{arxiv_to})")
        try:
            works = fetch_new_arxiv(category, arxiv_from, arxiv_to, max_results=ARXIV_MAX_RESULTS)
        except Exception as e:
            print(f"  取得失敗: {e}")
            continue
        print(f"  {len(works)} 件取得(フィルタ前)")
        works = _filter_by_keywords(works, MIN_KEYWORD_HITS_FOR_PREPRINTS)
        print(f"  {len(works)} 件がキーワード{MIN_KEYWORD_HITS_FOR_PREPRINTS}件以上ヒット")
        n, s = _ingest(conn, label, works)
        total_new += n
        total_seen += s
        time.sleep(1)  # arXivのレート制限(3req/sec)に配慮

    print(f"\n合計 {total_seen} 件確認、{total_new} 件を新規保存しました。")
    conn.close()


if __name__ == "__main__":
    run()

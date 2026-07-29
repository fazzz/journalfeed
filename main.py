# -*- coding: utf-8 -*-
"""
Step1: 各ジャーナルのRSSフィードを巡回し、新着記事をCrossrefで補完してSQLiteに保存する。

使い方:
    python main.py
"""

from config import FEEDS, DB_PATH, CROSSREF_REQUEST_INTERVAL
from db import get_conn, insert_article
from fetch_rss import fetch_feed_entries
from crossref_enrich import fetch_metadata_polite


def run():
    conn = get_conn(DB_PATH)
    total_new = 0
    total_seen = 0

    for feed in FEEDS:
        journal = feed["journal"]
        url = feed["url"]
        print(f"[fetch] {journal}: {url}")

        try:
            entries = fetch_feed_entries(url)
        except Exception as e:
            print(f"  取得失敗: {e}")
            continue

        print(f"  {len(entries)} 件のエントリを取得")

        for entry in entries:
            total_seen += 1
            doi = entry["doi"]

            if doi is None:
                # DOIが取れない場合は、リンクをキー代わりにする(重複判定は甘くなる)
                doi = entry["link"] or entry["title"]

            title = entry["title"]
            authors = None
            abstract = entry["summary"]
            pub_date = entry["published"]

            # Crossrefで補完(DOIがそれらしい形式のときだけ試みる)
            if entry["doi"]:
                meta = fetch_metadata_polite(entry["doi"], CROSSREF_REQUEST_INTERVAL)
                if meta:
                    title = meta["title"] or title
                    authors = meta["authors"]
                    abstract = meta["abstract"] or abstract
                    pub_date = meta["pub_date"] or pub_date

            is_new = insert_article(
                conn,
                journal=journal,
                doi=doi,
                title=title,
                authors=authors,
                pub_date=pub_date,
                link=entry["link"],
                abstract=abstract,
            )
            if is_new:
                total_new += 1
                print(f"    + 新規: {title[:60]}")

    print(f"\n合計 {total_seen} 件確認、{total_new} 件を新規保存しました。")
    conn.close()


if __name__ == "__main__":
    run()

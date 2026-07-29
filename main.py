# -*- coding: utf-8 -*-
"""
journalfeed Step1: 指定ジャーナル(ISSN)についてCrossref APIで新着論文を取得し、
SQLiteに保存する(DOIで重複排除)。

使い方:
    python main.py
"""

import time

from config import (
    JOURNALS,
    DB_PATH,
    LOOKBACK_DAYS,
    ROWS_PER_QUERY,
    CROSSREF_REQUEST_INTERVAL,
)
from db import get_conn, insert_article
from crossref_client import fetch_new_works, default_from_date


def run():
    conn = get_conn(DB_PATH)
    from_date = default_from_date(LOOKBACK_DAYS)
    total_new = 0
    total_seen = 0

    for j in JOURNALS:
        journal = j["journal"]
        issn = j["issn"]
        print(f"[fetch] {journal} (ISSN {issn}) since {from_date}")

        try:
            works = fetch_new_works(issn, from_date, rows=ROWS_PER_QUERY)
        except Exception as e:
            print(f"  取得失敗: {e}")
            continue

        print(f"  {len(works)} 件取得")

        for w in works:
            total_seen += 1
            if not w["doi"]:
                continue
            is_new = insert_article(
                conn,
                journal=journal,
                doi=w["doi"],
                title=w["title"],
                authors=w["authors"],
                pub_date=w["pub_date"],
                link=w["link"],
                abstract=w["abstract"],
            )
            if is_new:
                total_new += 1
                title = w["title"] or "(no title)"
                print(f"    + 新規: {title[:60]}")

        time.sleep(CROSSREF_REQUEST_INTERVAL)

    print(f"\n合計 {total_seen} 件確認、{total_new} 件を新規保存しました。")
    conn.close()


if __name__ == "__main__":
    run()

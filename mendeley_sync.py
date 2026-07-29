# -*- coding: utf-8 -*-
"""
DB内でまだMendeleyに登録していない記事(mendeley_added = 0)を、
Mendeleyライブラリに登録する。

事前に `python mendeley_auth.py` を一度実行しておくこと。

使い方:
    python mendeley_sync.py
"""

import time

from config import DB_PATH, MENDELEY_REQUEST_INTERVAL
from db import get_conn, unsynced_to_mendeley, mark_mendeley_synced
from mendeley_client import get_valid_access_token, add_document


def _extract_year(pub_date):
    if not pub_date:
        return None
    try:
        return int(pub_date.split("-")[0])
    except (ValueError, IndexError):
        return None


def run():
    conn = get_conn(DB_PATH)
    targets = unsynced_to_mendeley(conn)
    print(f"Mendeley未登録の記事: {len(targets)} 件")

    if not targets:
        conn.close()
        return

    access_token = get_valid_access_token()

    done = 0
    for doi, journal, title, authors, pub_date, abstract in targets:
        try:
            add_document(
                access_token,
                title=title,
                journal=journal,
                authors_str=authors,
                year=_extract_year(pub_date),
                doi=doi,
                abstract=abstract,
            )
        except Exception as e:
            print(f"  登録失敗 ({doi}): {e}")
            time.sleep(MENDELEY_REQUEST_INTERVAL)
            continue

        mark_mendeley_synced(conn, doi)
        done += 1
        label = (title or doi)[:60]
        print(f"  + 登録: {label}")
        time.sleep(MENDELEY_REQUEST_INTERVAL)

    print(f"\n{done}/{len(targets)} 件をMendeleyに登録しました。")
    conn.close()


if __name__ == "__main__":
    run()

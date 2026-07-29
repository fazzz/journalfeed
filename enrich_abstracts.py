# -*- coding: utf-8 -*-
"""
Step1.5: DB内でabstractが空の記事について、OpenAlex APIでDOI単体lookupを行い
abstractを補完する。

Crossrefからは(特にElsevier・ACSの記事は)abstractがほとんど取得できないため、
abstractのカバー率が高いOpenAlexで穴埋めする。

使い方:
    python enrich_abstracts.py
"""

import time

from config import DB_PATH, OPENALEX_API_KEY, OPENALEX_REQUEST_INTERVAL
from db import get_conn, articles_missing_abstract, update_abstract
from openalex_client import get_abstract_by_doi


def run():
    conn = get_conn(DB_PATH)
    targets = articles_missing_abstract(conn)
    print(f"abstract未取得の記事: {len(targets)} 件")

    filled = 0
    for doi, title in targets:
        try:
            abstract = get_abstract_by_doi(doi, OPENALEX_API_KEY)
        except Exception as e:
            print(f"  取得失敗 ({doi}): {e}")
            time.sleep(OPENALEX_REQUEST_INTERVAL)
            continue

        if abstract:
            update_abstract(conn, doi, abstract)
            filled += 1
            label = (title or doi)[:60]
            print(f"  + 補完: {label}")

        time.sleep(OPENALEX_REQUEST_INTERVAL)

    print(f"\n{filled}/{len(targets)} 件のabstractを補完しました。")
    conn.close()


if __name__ == "__main__":
    run()

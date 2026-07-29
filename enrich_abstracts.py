# -*- coding: utf-8 -*-
"""
Step1.5: DB内でabstractが空の記事について、OpenAlex APIでDOI単体lookupを行い
abstractを補完する。

方針(C -> B):
  - 見つかればabstractを埋めて abstract_status = 'found' にする
  - 見つからず、かつ fetched_at から ABSTRACT_GIVEUP_DAYS 日以上経っている場合は
    abstract_status = 'unavailable' にし、以降は再取得を試みない
    (Step2のLLM要約ではタイトルのみ扱いとして要約対象から除外する)
  - まだ猶予期間内なら何もしない(次回この関数を再実行したときにまた試す)

このスクリプトは毎日の巡回(main.py)の後に定期的に再実行することを想定している。
何度実行しても安全(冪等)。

使い方:
    python enrich_abstracts.py
"""

from datetime import datetime, timedelta, timezone
import time

from config import DB_PATH, OPENALEX_API_KEY, OPENALEX_REQUEST_INTERVAL, ABSTRACT_GIVEUP_DAYS
from db import get_conn, articles_pending_abstract, mark_abstract_found, mark_abstract_unavailable
from openalex_client import get_abstract_by_doi


def _is_past_giveup(fetched_at_str, giveup_days):
    try:
        fetched_at = datetime.fromisoformat(fetched_at_str)
    except (TypeError, ValueError):
        return False
    now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    return now_naive_utc - fetched_at > timedelta(days=giveup_days)


def run():
    conn = get_conn(DB_PATH)
    targets = articles_pending_abstract(conn)
    print(f"abstract再取得の対象: {len(targets)} 件 (猶予 {ABSTRACT_GIVEUP_DAYS} 日)")

    filled = 0
    gave_up = 0

    for doi, title, fetched_at in targets:
        try:
            abstract = get_abstract_by_doi(doi, OPENALEX_API_KEY)
        except Exception as e:
            print(f"  取得失敗 ({doi}): {e}")
            time.sleep(OPENALEX_REQUEST_INTERVAL)
            continue

        label = (title or doi)[:60]

        if abstract:
            mark_abstract_found(conn, doi, abstract)
            filled += 1
            print(f"  + 補完: {label}")
        elif _is_past_giveup(fetched_at, ABSTRACT_GIVEUP_DAYS):
            mark_abstract_unavailable(conn, doi)
            gave_up += 1
            print(f"  - 断念(タイトルのみ扱いへ): {label}")

        time.sleep(OPENALEX_REQUEST_INTERVAL)

    print(f"\n{filled}/{len(targets)} 件を補完、{gave_up} 件を断念(unavailable)にしました。")
    conn.close()


if __name__ == "__main__":
    run()

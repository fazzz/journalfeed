# -*- coding: utf-8 -*-
"""
Mendeleyへのドキュメント登録スクリプト。

デフォルトでは DB内の未登録記事(mendeley_added = 0)を全件登録するが、
--dois-file でDOI一覧ファイル(1行1DOI)を渡すと、その記事だけを登録する。
report.py が出力するHTMLレポート上でチェックを入れて書き出した
selected_dois.txt をそのまま渡す使い方を想定している。

事前に `python mendeley_auth.py` を一度実行しておくこと。

使い方:
    python mendeley_sync.py                          # 未登録の記事を全件登録
    python mendeley_sync.py --dois-file selected_dois.txt  # 指定したDOIだけ登録
"""

import argparse
import time
from pathlib import Path

from config import DB_PATH, MENDELEY_REQUEST_INTERVAL
from db import get_conn, unsynced_to_mendeley, get_articles_by_dois, mark_mendeley_synced
from mendeley_client import get_valid_access_token, add_document


def _extract_year(pub_date):
    if not pub_date:
        return None
    try:
        return int(pub_date.split("-")[0])
    except (ValueError, IndexError):
        return None


def _read_dois_file(path):
    text = Path(path).read_text(encoding="utf-8")
    dois = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            dois.append(line)
    return dois


def run(dois_file=None):
    conn = get_conn(DB_PATH)

    if dois_file:
        dois = _read_dois_file(dois_file)
        print(f"{dois_file} から {len(dois)} 件のDOIを読み込みました")
        targets = get_articles_by_dois(conn, dois)
    else:
        targets = unsynced_to_mendeley(conn)

    print(f"Mendeleyに登録する記事: {len(targets)} 件")

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
    parser = argparse.ArgumentParser(description="Mendeleyへのドキュメント登録")
    parser.add_argument(
        "--dois-file",
        type=str,
        default=None,
        help="登録したい記事のDOI一覧ファイル(1行1DOI)。省略時は未登録分を全件登録。",
    )
    args = parser.parse_args()
    run(dois_file=args.dois_file)

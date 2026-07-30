# -*- coding: utf-8 -*-
"""
config.py の JOURNALS に登録した各誌について、Crossref上の一般的な略称
(short-container-title)を取得し、journal_abbreviations.json にキャッシュする。

report.py はこのキャッシュがあれば、レポート上でジャーナル名の代わりに
略称を表示する(見つからなかった誌は正式名称のまま表示される)。

新しいジャーナルをJOURNALSに追加したときや、まだ略称が見つかっていない誌を
再確認したいときに実行してください(既に略称が分かっている誌はスキップされる
ので、何度実行しても安全)。

使い方:
    python fetch_journal_abbreviations.py
"""

import time

from config import JOURNALS, FILTERED_JOURNALS, CROSSREF_REQUEST_INTERVAL
from crossref_client import fetch_short_title
from journal_abbrev import load_abbreviations, save_abbreviations


def run():
    mapping = load_abbreviations()
    updated = 0
    not_found = []

    for j in JOURNALS + FILTERED_JOURNALS:
        name = j["journal"]
        issn = j["issn"]

        if mapping.get(name):
            continue  # 既に略称が分かっているのでスキップ

        try:
            abbrev = fetch_short_title(issn)
        except Exception as e:
            print(f"  取得失敗 ({name}): {e}")
            time.sleep(CROSSREF_REQUEST_INTERVAL)
            continue

        if abbrev:
            mapping[name] = abbrev
            updated += 1
            print(f"  + {name} -> {abbrev}")
        else:
            not_found.append(name)
            print(f"  - 略称が見つかりませんでした: {name}")

        time.sleep(CROSSREF_REQUEST_INTERVAL)

    save_abbreviations(mapping)
    print(f"\n{updated} 誌の略称を新たに取得しました。")

    if not_found:
        print(f"見つからなかった誌 ({len(not_found)}件、正式名称のまま表示されます):")
        for n in not_found:
            print(f"  - {n}")


if __name__ == "__main__":
    run()

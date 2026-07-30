# -*- coding: utf-8 -*-
"""著者ウォッチリストの一致判定ロジック(keyword_utils.pyと対になるモジュール)。"""


def matched_authors(authors_str, watchlist):
    """著者欄(カンマ区切り文字列)にウォッチリストの名前が含まれるかを判定する
    (大小文字を区別しない部分一致)。一致したウォッチリスト側の名前のリストを返す。
    """
    if not authors_str or not watchlist:
        return []
    haystack = authors_str.lower()
    return [name for name in watchlist if name.lower() in haystack]

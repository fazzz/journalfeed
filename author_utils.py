# -*- coding: utf-8 -*-
"""著者ウォッチリストの一致判定ロジック(keyword_utils.pyと対になるモジュール)。"""


def _split_name(full_name):
    """"Michael R. Shirts" -> ("michael", "shirts") のように、名(最初のトークン)と
    姓(最後のトークン)を取り出す(ミドルネームは無視)。"""
    parts = full_name.strip().split()
    if not parts:
        return None, None
    return parts[0].lower().rstrip("."), parts[-1].lower()


def _first_name_compatible(a, b):
    """2つの名(first name)が同一人物の表記ゆれとして妥当かを判定する。

    完全一致、または片方が1文字(イニシャル)でもう片方の先頭文字と一致する
    場合のみ真とする。単に頭文字が同じというだけでは真としない
    (例: "Michael" と "Mark" はどちらも "M" だが別人として扱う)。
    """
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) == 1:
        return a == b[0]
    if len(b) == 1:
        return b == a[0]
    return False


def matched_authors(authors_str, watchlist):
    """著者欄(カンマ区切り文字列)にウォッチリストの著者が含まれるかを判定する。

    姓が完全一致し、かつ名が「完全一致」または「どちらかがイニシャル表記で
    先頭文字が一致」する場合にのみマッチとする(ミドルネームは無視)。
    一致したウォッチリスト側の名前(元の表記)のリストを返す。
    """
    if not authors_str or not watchlist:
        return []

    author_tokens = [a.strip() for a in authors_str.split(",") if a.strip()]
    parsed_tokens = [_split_name(t) for t in author_tokens]
    parsed_tokens = [(f, l) for f, l in parsed_tokens if f and l]

    matched = []
    for name in watchlist:
        wl_first, wl_family = _split_name(name)
        if not wl_family:
            continue
        for token_first, token_family in parsed_tokens:
            if token_family == wl_family and _first_name_compatible(wl_first, token_first):
                matched.append(name)
                break

    return matched

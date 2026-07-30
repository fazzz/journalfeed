# -*- coding: utf-8 -*-
"""キーワード一致判定ロジック(report.pyの表示強調とmain.pyの取得フィルタで共用)。"""


def matched_keywords(title, abstract, keywords):
    """タイトル・アブストラクトに含まれるキーワードのリストを返す(大小文字を区別しない)。"""
    haystack = f"{title or ''} {abstract or ''}".lower()
    return [kw for kw in keywords if kw.lower() in haystack]

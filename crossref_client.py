# -*- coding: utf-8 -*-
"""Crossref API クライアント。RSSを介さず、ISSN指定で新着論文を直接取得する。"""

import re
from datetime import date, timedelta

import requests

from config import CROSSREF_MAILTO

BASE_URL = "https://api.crossref.org/works"


def _strip_jats_tags(text):
    """Crossrefのabstractは JATS XML タグ付きで返ることが多いので簡易除去する。"""
    if not text:
        return text
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_work(msg):
    """Crossrefの1レコード(message.items[i])を扱いやすい辞書に変換する。"""
    authors = []
    for a in msg.get("author", []):
        given = a.get("given", "")
        family = a.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)

    title_list = msg.get("title", [])
    title = title_list[0] if title_list else None

    abstract = _strip_jats_tags(msg.get("abstract"))

    date_parts = (
        msg.get("published-print", {}).get("date-parts")
        or msg.get("published-online", {}).get("date-parts")
        or msg.get("created", {}).get("date-parts")
    )
    pub_date = None
    if date_parts and date_parts[0]:
        pub_date = "-".join(f"{p:02d}" if i > 0 else str(p) for i, p in enumerate(date_parts[0]))

    doi = msg.get("DOI")
    link = msg.get("URL") or (f"https://doi.org/{doi}" if doi else None)

    return {
        "doi": doi,
        "title": title,
        "authors": ", ".join(authors) if authors else None,
        "abstract": abstract,
        "pub_date": pub_date,
        "link": link,
    }


def fetch_new_works(issn, from_date, rows=100):
    """指定ISSNの雑誌について、from_date以降にCrossrefへ初めて登録(deposit)された
    論文一覧を、新しい順に取得する。

    from-index-date ではなく from-created-date を使っている点に注意。
    from-index-date は「被引用数の更新など、他者による変更で触られただけの
    古い記録」まで拾ってしまい、結果的に1990年代・2000年代の論文が大量に
    混ざる不具合の原因になった。from-created-date は「Crossrefに初めて
    登録された日」を指すため、これで本来の目的である「新着論文」に絞られる。

    from_date: "YYYY-MM-DD" 形式の文字列
    戻り値: _parse_work() の辞書のリスト(created日時が新しい順)
    """
    params = {
        "filter": f"issn:{issn},from-created-date:{from_date}",
        "sort": "created",
        "order": "desc",
        "rows": rows,
        "mailto": CROSSREF_MAILTO,
    }
    headers = {"User-Agent": f"journalfeed/0.1 (mailto:{CROSSREF_MAILTO})"}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])
    return [_parse_work(item) for item in items]


def default_from_date(lookback_days):
    """本日から lookback_days 日前の日付を YYYY-MM-DD で返す。"""
    d = date.today() - timedelta(days=lookback_days)
    return d.isoformat()

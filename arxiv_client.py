# -*- coding: utf-8 -*-
"""arXiv API(Atom形式)クライアント。Crossrefには登録されていないarXivを
別ルートで扱うためのモジュール。カテゴリと日付範囲を指定して新着論文を取得する。
"""

from datetime import date, timedelta

import feedparser
import requests

BASE_URL = "http://export.arxiv.org/api/query"


def arxiv_date_range(lookback_days):
    """本日を基準に、arXivのsubmittedDateクエリに使う YYYYMMDD の (from, to) を返す。"""
    today = date.today()
    start = today - timedelta(days=lookback_days)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _extract_arxiv_id(entry_id):
    """entry.id (例: "http://arxiv.org/abs/2507.12345v2") からバージョン無しのIDを取り出す。"""
    tail = (entry_id or "").rsplit("/", 1)[-1]
    if "v" in tail:
        base, _, ver = tail.rpartition("v")
        if ver.isdigit():
            tail = base
    return tail


def fetch_new_arxiv(category, from_date, to_date, max_results=100):
    """指定カテゴリについて、from_date〜to_date(YYYYMMDD形式)に投稿された
    論文一覧を新しい順に取得する。

    戻り値: doi(実際は "arxiv:<id>" という擬似DOI) / title / authors / abstract /
             pub_date / link を持つ辞書のリスト。
    """
    query = f"cat:{category}+AND+submittedDate:[{from_date}0000+TO+{to_date}2359]"
    url = (
        f"{BASE_URL}?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    headers = {"User-Agent": "journalfeed/0.1 (mailto:your_email@example.com)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    parsed = feedparser.parse(resp.text)
    works = []
    for e in parsed.entries:
        arxiv_id = _extract_arxiv_id(e.get("id", ""))
        authors = ", ".join(
            a.get("name", "") for a in e.get("authors", []) if a.get("name")
        )
        published = (e.get("published") or "")[:10]  # YYYY-MM-DD
        title = (e.get("title") or "").replace("\n", " ").strip()
        abstract = (e.get("summary") or "").replace("\n", " ").strip()

        works.append(
            {
                "doi": f"arxiv:{arxiv_id}",
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "pub_date": published,
                "link": f"https://arxiv.org/abs/{arxiv_id}",
            }
        )
    return works

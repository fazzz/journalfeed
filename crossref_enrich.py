# -*- coding: utf-8 -*-
"""Crossref API (無料・登録不要) でDOIから書誌情報を補完する。"""

import re
import time

import requests

from config import CROSSREF_MAILTO

CROSSREF_URL = "https://api.crossref.org/works/{doi}"


def _strip_jats_tags(text):
    """Crossrefのabstractは JATS XML タグ付きで返ることが多いので簡易除去する。"""
    if not text:
        return text
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_metadata(doi):
    """DOIからCrossrefのメタデータを取得する。取得失敗時は None を返す。"""
    url = CROSSREF_URL.format(doi=doi)
    headers = {"User-Agent": f"journal-crawler/0.1 (mailto:{CROSSREF_MAILTO})"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    msg = resp.json().get("message", {})

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
        pub_date = "-".join(str(p) for p in date_parts[0])

    return {
        "title": title,
        "authors": ", ".join(authors) if authors else None,
        "abstract": abstract,
        "pub_date": pub_date,
    }


def fetch_metadata_polite(doi, interval_sec):
    """先方への連続アクセスを避けるため、呼び出し後に一定時間スリープする版。"""
    result = fetch_metadata(doi)
    time.sleep(interval_sec)
    return result

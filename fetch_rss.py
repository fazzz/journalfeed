# -*- coding: utf-8 -*-
"""RSSフィードの取得とパース。"""

import re
import feedparser

# DOI の一般的な正規表現 (10.xxxx/... 形式)
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def extract_doi(entry):
    """entryのlink, id, summaryなどからDOIを推測する。"""
    candidates = []
    for key in ("id", "link", "guid"):
        val = entry.get(key)
        if val:
            candidates.append(val)
    for link in entry.get("links", []):
        href = link.get("href")
        if href:
            candidates.append(href)
    summary = entry.get("summary")
    if summary:
        candidates.append(summary)

    for text in candidates:
        m = DOI_RE.search(text)
        if m:
            # 末尾に余計な文字(引用符やタグの断片)が付くことがあるので簡易クリーニング
            doi = m.group(0).rstrip(').,"\'<>')
            return doi
    return None


def fetch_feed_entries(feed_url):
    """1つのRSSフィードから記事エントリのリストを取得する。

    戻り値は dict のリスト: title, link, published, summary, doi
    """
    parsed = feedparser.parse(feed_url)
    entries = []
    for e in parsed.entries:
        entries.append(
            {
                "title": e.get("title", "").strip(),
                "link": e.get("link", ""),
                "published": e.get("published", e.get("updated", "")),
                "summary": e.get("summary", ""),
                "doi": extract_doi(e),
            }
        )
    return entries

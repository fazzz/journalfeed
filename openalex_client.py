# -*- coding: utf-8 -*-
"""OpenAlex API クライアント。DOI単体でのlookupでabstractを補完する。

DOI単体のlookup(singleton)は無料枠の対象外で、実質無制限に使える
(2026年2月のAPIキー必須化以降もこの点は変わらない)。
"""

import requests

BASE_URL = "https://api.openalex.org/works"


def reconstruct_abstract(inverted_index):
    """OpenAlexのabstract_inverted_index(単語→出現位置のリスト)を
    プレーンテキストに復元する。

    OpenAlexは著作権上の理由でプレーンテキストのabstractを直接返さず、
    単語の位置情報(inverted index)として返すため、この変換が必要。
    """
    if not inverted_index:
        return None

    positions = {}
    for word, idxs in inverted_index.items():
        for idx in idxs:
            positions[idx] = word

    if not positions:
        return None

    max_idx = max(positions.keys())
    words = [positions.get(i, "") for i in range(max_idx + 1)]
    text = " ".join(w for w in words if w)
    return text or None


def get_abstract_by_doi(doi, api_key):
    """DOIからOpenAlexのWorkを取得し、abstractのプレーンテキストを返す。

    見つからない場合やabstractが無い場合は None を返す。
    """
    url = f"{BASE_URL}/doi:{doi}"
    params = {"api_key": api_key}
    resp = requests.get(url, params=params, timeout=20)

    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    work = resp.json()
    return reconstruct_abstract(work.get("abstract_inverted_index"))

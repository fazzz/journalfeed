# -*- coding: utf-8 -*-
"""ジャーナル名の略称(abbreviation)キャッシュの読み書き。

正式名称 -> 略称 のマッピングをJSONファイルに保持する。
report.py はこれを読み込み、あれば略称を、無ければ正式名称のまま表示する。
"""

import json
from pathlib import Path

from config import JOURNAL_ABBREV_FILE

BASE_DIR = Path(__file__).resolve().parent


def _path():
    return BASE_DIR / JOURNAL_ABBREV_FILE


def load_abbreviations():
    path = _path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_abbreviations(mapping):
    _path().write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

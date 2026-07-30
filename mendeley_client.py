# -*- coding: utf-8 -*-
"""Mendeley API クライアント。OAuth2トークンの管理とドキュメント登録を担う。"""

import base64
import json
import time
from pathlib import Path

import requests

from config import (
    MENDELEY_CLIENT_ID,
    MENDELEY_CLIENT_SECRET,
    MENDELEY_REDIRECT_URI,
    MENDELEY_TOKEN_FILE,
)

TOKEN_URL = "https://api.mendeley.com/oauth/token"
DOCUMENTS_URL = "https://api.mendeley.com/documents"
DOC_MEDIA_TYPE = "application/vnd.mendeley-document.1+json"


def _basic_auth_header():
    raw = f"{MENDELEY_CLIENT_ID}:{MENDELEY_CLIENT_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _token_path():
    return Path(__file__).resolve().parent / MENDELEY_TOKEN_FILE


def save_token(token_data):
    """トークン情報をファイルに保存する。取得時刻も併せて記録し、期限切れ判定に使う。"""
    token_data = dict(token_data)
    token_data["obtained_at"] = time.time()
    _token_path().write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def load_token():
    path = _token_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def exchange_code_for_token(code):
    """初回の認可コードを access_token / refresh_token に交換する(mendeley_auth.pyから使用)。"""
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": MENDELEY_REDIRECT_URI,
        },
        timeout=20,
    )
    resp.raise_for_status()
    token_data = resp.json()
    save_token(token_data)
    return token_data


def _refresh(refresh_token):
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=20,
    )
    resp.raise_for_status()
    token_data = resp.json()
    if "refresh_token" not in token_data:
        # レスポンスにrefresh_tokenが含まれない場合は既存のものを引き継ぐ
        token_data["refresh_token"] = refresh_token
    save_token(token_data)
    return token_data


def get_valid_access_token():
    """有効なaccess_tokenを返す。期限切れ(または期限間近)ならrefresh_tokenで自動更新する。"""
    token_data = load_token()
    if not token_data:
        raise RuntimeError(
            "Mendeleyの認証情報がありません。先に `python mendeley_auth.py` を実行してください。"
        )

    obtained_at = token_data.get("obtained_at", 0)
    expires_in = token_data.get("expires_in", 3600)
    if time.time() < obtained_at + expires_in - 60:
        return token_data["access_token"]

    token_data = _refresh(token_data["refresh_token"])
    return token_data["access_token"]


def _split_name(full_name):
    parts = full_name.strip().split()
    if not parts:
        return None
    if len(parts) == 1:
        return {"first_name": "", "last_name": parts[0]}
    return {"first_name": " ".join(parts[:-1]), "last_name": parts[-1]}


def parse_authors(authors_str):
    """"Taro Yamada, Hanako Suzuki" 形式の文字列をMendeley用のauthorsリストに変換する。
    (氏名の分割は最後の単語をlast_name、残りをfirst_nameとする簡易ルール)
    """
    if not authors_str:
        return []
    names = [_split_name(n) for n in authors_str.split(",") if n.strip()]
    return [n for n in names if n]


def add_document(access_token, title, journal=None, authors_str=None, year=None, doi=None, abstract=None):
    """Mendeleyライブラリに1件のドキュメントを追加する。"""
    body = {"title": title, "type": "journal"}

    authors = parse_authors(authors_str)
    if authors:
        body["authors"] = authors
    if journal:
        body["source"] = journal
    if year:
        body["year"] = year
    if abstract:
        body["abstract"] = abstract
    if doi:
        if doi.startswith("arxiv:"):
            body["identifiers"] = {"arxiv": doi.split(":", 1)[1]}
        else:
            body["identifiers"] = {"doi": doi}

    resp = requests.post(
        DOCUMENTS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": DOC_MEDIA_TYPE,
            "Accept": DOC_MEDIA_TYPE,
        },
        data=json.dumps(body),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()

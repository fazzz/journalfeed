# -*- coding: utf-8 -*-
"""
Mendeleyの初回ユーザー認可(OAuth2 authorization_code flow)を行うスクリプト。
最初に1回だけ実行すればよい(refresh_tokenが失効しない限り再実行は不要)。

流れ:
  1. ブラウザでMendeleyの認可ページを開く
  2. ログイン・許可すると、ローカルに一時起動したサーバーへリダイレクトされる
  3. リダイレクトURLに含まれる認可コードを受け取り、access_token / refresh_token に交換
  4. 結果を config.py の MENDELEY_TOKEN_FILE に保存

使い方:
    python mendeley_auth.py
"""

import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import MENDELEY_CLIENT_ID, MENDELEY_REDIRECT_URI
from mendeley_client import exchange_code_for_token

AUTH_URL = "https://api.mendeley.com/oauth/authorize"

_received = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if code:
            _received["code"] = code
            self.wfile.write("<h2>認証が完了しました。このタブは閉じて構いません。</h2>".encode("utf-8"))
        else:
            _received["error"] = error or "unknown_error"
            self.wfile.write(f"<h2>認証に失敗しました: {error}</h2>".encode("utf-8"))

    def log_message(self, format, *args):
        pass  # コンソール出力を抑制


def run():
    parsed_redirect = urllib.parse.urlparse(MENDELEY_REDIRECT_URI)
    port = parsed_redirect.port or 8765

    params = {
        "client_id": MENDELEY_CLIENT_ID,
        "redirect_uri": MENDELEY_REDIRECT_URI,
        "response_type": "code",
        "scope": "all",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("以下のURLをブラウザで開き、Mendeleyにログインして許可してください:")
    print(auth_url)
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", port), _CallbackHandler)
    print(f"認可コードの受信を待っています (http://localhost:{port})...")
    while "code" not in _received and "error" not in _received:
        server.handle_request()

    if "error" in _received:
        print(f"認証に失敗しました: {_received['error']}")
        return

    token_data = exchange_code_for_token(_received["code"])
    print("認証に成功し、トークンを保存しました。")
    print(f"  有効期限: {token_data.get('expires_in')} 秒(以降はrefresh_tokenで自動更新されます)")


if __name__ == "__main__":
    run()

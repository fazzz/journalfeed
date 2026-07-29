# -*- coding: utf-8 -*-
"""
設定ファイル。

FEEDS の url は、各ジャーナルのページにある「RSS」または「Follow」ボタンから
直接コピーしたリンクを貼ってください。ACS Publications は最近プラットフォームを
移行しており、以前ネット上で紹介されていた showFeed?... 形式の推測URLは
古い可能性があるため、必ず実際のページで確認したものを使うのが安全です。

ACS: 各journalのトップページ (例: https://pubs.acs.org/journal/jacsat) を開き、
     ページ内の Follow / RSS アイコンからリンクを取得。
Elsevier(ScienceDirect): 各journalのトップページを開き、
     "RSS" リンク (rss.sciencedirect.com/publication/science/xxxxxxxx 形式が多い)
     を取得。
"""

FEEDS = [
    # 例: 実際のURLに置き換えてください
    {"journal": "Journal of the American Chemical Society", "url": "https://example.com/replace-with-real-jacs-rss"},
    {"journal": "Journal of Chemical Theory and Computation", "url": "https://example.com/replace-with-real-jctc-rss"},
    {"journal": "Computer Physics Communications", "url": "https://example.com/replace-with-real-cpc-rss"},
]

DB_PATH = "articles.db"

# Crossref API の "polite pool"(応答が安定しやすい)を使うため、
# 自分のメールアドレスを入れておくことを推奨
CROSSREF_MAILTO = "your_email@example.com"

# Crossref への問い合わせ間隔(秒)。連続アクセスで先方に負荷をかけないための最低限のマナー
CROSSREF_REQUEST_INTERVAL = 1.0

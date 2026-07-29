# -*- coding: utf-8 -*-
"""
設定ファイル。

RSSではなく、Crossref API を直接叩いて「指定ジャーナル(ISSN)の新着論文」を
取得する方式にしている(publisherごとのRSS仕様やbot対策の違いを気にしなくてよいため)。

ISSNは各ジャーナルの About ページや、Google で「<journal name> ISSN」と
検索すればすぐ見つかります。print ISSN / online ISSN のどちらでもCrossref上は
同じ雑誌に紐づいていることが多いですが、念のため journal のトップページに
書かれている ISSN を使ってください。
"""

JOURNALS = [
    # 例: 実際のISSNに置き換えてください
    {"journal": "Journal of the American Chemical Society", "issn": "0002-7863"},
    {"journal": "Journal of Chemical Theory and Computation", "issn": "1549-9618"},
    {"journal": "Computer Physics Communications", "issn": "0010-4655"},
]

DB_PATH = "articles.db"

# Crossref API の「polite pool」(応答が安定しやすい)を使うため、
# 自分のメールアドレスに変更してください
CROSSREF_MAILTO = "your_email@example.com"

# Crossref への問い合わせ間隔(秒)。連続アクセスで先方に負荷をかけないためのマナー
CROSSREF_REQUEST_INTERVAL = 1.0

# 何日前までを「新着」として問い合わせるか。
# Crossrefへの登録(indexing)は出版から数日遅れることがあるため、
# 1(=今日だけ)ではなく数日分のバッファを持たせて取りこぼしを防ぐ。
# 実際の重複はDOIで排除されるので、日数を大きくしても二重登録にはならない。
LOOKBACK_DAYS = 3

# 1回のクエリで取得する最大件数(雑誌1誌・1回の実行あたり)
ROWS_PER_QUERY = 100

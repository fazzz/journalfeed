# journalfeed (Step 1: Crossref APIでの新着論文取得 → SQLite保存)

RSSは使わず、Crossref API を直接叩いて「指定ジャーナル(ISSN)の新着論文」を
取得する方式にしています。ACSのRSSが最近Cloudflareのbot対策の対象になり、
自動化ツールから安定して取得できなくなっているため、この方式の方が確実です。

## セットアップ

```bash
pip install -r requirements.txt
```

## 使う前にやること

1. `config.py` の `JOURNALS` に、追跡したいジャーナルの名前とISSNを書く。
   ISSNはジャーナルのAboutページや「<journal name> ISSN」で検索すればすぐ見つかります。
2. `config.py` の `CROSSREF_MAILTO` を自分のメールアドレスに変更する
   (Crossref APIの「polite pool」を使うためのマナー的な設定)。

## 実行

```bash
python main.py
```

- 各ジャーナルについて、Crossref APIに `issn` + `from-index-date` でフィルタをかけ、
  直近 `LOOKBACK_DAYS`(デフォルト3日)分の新着論文を取得します。
- タイトル・著者・出版日・アブスト(登録されていれば)・DOIを取得します。
- `articles.db` (SQLite) に、DOIをキーとして重複を排除しながら保存します。
- 2回目以降の実行でも同じ期間を問い合わせますが、既存DOIは自動的にスキップされるので
  何度実行しても安全です(冪等)。

## ファイル構成

- `config.py`         : 追跡するジャーナル(ISSN)や各種設定
- `db.py`              : SQLiteの初期化・保存・重複判定
- `crossref_client.py` : Crossref APIへの問い合わせとレスポンスのパース
- `main.py`            : 上記を組み合わせて実行するエントリポイント

## 既知の制約・注意点

- Crossrefのabstractフィールドは、出版社が実際にCrossrefへアブストを登録している
  場合のみ取得できます。ACSは登録していないことが多く、その場合はabstractが空に
  なります(Step2の要約フェーズでは、タイトルのみから要約するか、abstractが空の
  記事はスキップするかを検討してください)。
- `from-index-date` はCrossrefへの「登録日」であり、実際の出版日(pub_date)とは
  ずれることがあります。LOOKBACK_DAYSのバッファはこのズレを吸収するためのものです。
- 次のステップ(LLM要約、レポート生成、Mendeley連携、日次自動化)は別途追加していく想定です。

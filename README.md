# journal_crawler (Step 1: RSS取得 → Crossref補完 → SQLite保存)

## セットアップ

```bash
pip install -r requirements.txt
```

## 使う前にやること

1. `config.py` の `FEEDS` を編集する。
   各ジャーナルのページ(例: https://pubs.acs.org/journal/jacsat や
   ScienceDirectの該当ジャーナルページ)を開き、"RSS" または "Follow" の
   アイコンから**実際のフィードURL**をコピーして貼り付けてください。
   (ACSはプラットフォーム移行済みのため、ネット上の古い記事にある
   URLパターンをそのまま推測で使うのは避けてください。)

2. `config.py` の `CROSSREF_MAILTO` を自分のメールアドレスに変更する。
   (Crossref APIの「polite pool」を使うためのマナー的な設定です)

## 実行

```bash
python main.py
```

- 各フィードを取得し、記事ごとにDOIを抽出します。
- DOIが取れた記事はCrossref API (https://api.crossref.org) で
  タイトル・著者・出版日・アブスト(取得できる場合)を補完します。
- `articles.db` (SQLite) に、DOIをキーとして重複を排除しながら保存します。
- 2回目以降の実行では、既にDBにある記事は再取得・再挿入されません
  (差分だけが `+ 新規:` として表示されます)。

## ファイル構成

- `config.py`      : フィードURLなどの設定
- `db.py`           : SQLiteの初期化・保存・重複判定
- `fetch_rss.py`    : RSSパースとDOI抽出
- `crossref_enrich.py` : Crossref APIでの書誌情報補完
- `main.py`         : 上記を組み合わせて実行するエントリポイント

## 既知の制約・注意点

- Crossrefのabstractフィールドは、出版社が実際にCrossrefへ
  アブストを登録している場合のみ取得できます。ACSは登録していない
  ことが多く、その場合はRSSのdescription(短い抜粋)がabstract欄に
  入ります。Elsevierは比較的アブストが取れることが多いです。
- DOIがRSS本文から見つからない記事は、リンクURLをキー代わりに
  使って保存します(重複判定の精度は少し落ちます)。
- 次のステップ(LLM要約、レポート生成、Mendeley連携、日次自動化)は
  別途追加していく想定です。

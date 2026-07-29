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

## Step 1.5: abstractの補完 (OpenAlex)

CrossrefはElsevier・ACSからabstractをほぼ受け取っていないため
(実測でも本プロジェクトのCPC/JACSは0%、JCTCも10%程度)、
abstractのカバー率が高いOpenAlex APIで別途補完します。

1. https://openalex.org で無料アカウント登録
2. https://openalex.org/settings/api でAPIキーを取得し、`config.py` の
   `OPENALEX_API_KEY` に設定
3. 実行:
   ```bash
   python enrich_abstracts.py
   ```
   DB内でabstractが空の記事だけを対象に、DOI単体lookup(無料・無制限)で
   OpenAlexに問い合わせてabstractを埋めます。何度実行しても、既に埋まって
   いる記事は対象外なので安全です。

## abstract取得ポリシー(C -> B)

1. `enrich_abstracts.py` は毎回、abstractがまだ無い記事のうち
   `abstract_status != 'unavailable'` のものだけを対象にOpenAlexへ再取得を試みる
   (= 数日おきに再実行することで自然に「しばらく待って再取得」が実現される)。
2. `fetched_at` から `ABSTRACT_GIVEUP_DAYS`(デフォルト7日)を過ぎても見つからない
   記事は `abstract_status = 'unavailable'` にし、以降は問い合わせ対象から外れる。
3. Step2のLLM要約では、`summarizable_articles()` で abstract のある記事だけを要約対象にし、
   `title_only_articles()` で unavailable な記事をタイトルのみの一覧として別扱いする想定。

## Step 2: LLM要約 (Claude API)

abstractのある記事について、Claude API (Anthropic) で日本語の要約(3行程度)を
生成し、`summary_ja` 列に保存します。

1. `config.py` の `ANTHROPIC_API_KEY` を設定する。
   環境変数 `ANTHROPIC_API_KEY` からも読めるようになっているので、
   GitHub Actions等で自動化する場合はSecretsに登録して環境変数経由で渡すのがおすすめ
   (config.pyに直書きしたキーをうっかりgitにコミットしないよう注意)。
2. 実行:
   ```bash
   python summarize.py
   ```
- 要約はデフォルトで `claude-haiku-4-5-20251001` を使用(定型的な要約タスクなので
  コスト効率重視)。質が物足りなければ `config.py` の `SUMMARY_MODEL` を
  `"claude-sonnet-5"` に変更してください。
- `abstract_status = 'unavailable'`(タイトルのみ扱い)の記事は要約対象から自動的に
  除外されます。
- 既に `summary_ja` が入っている記事は再要約されません(冪等)。

### 動作確認の手順(初回はここから)

1. APIキーを設定(環境変数推奨): `export ANTHROPIC_API_KEY="sk-ant-..."`
2. まず3件だけ試す:
   ```bash
   python summarize.py --limit 3
   ```
   生成された要約が表示されるので、内容・トーン・長さを確認してください。
3. 問題なければ残りを全件処理:
   ```bash
   python summarize.py
   ```
   (`--limit` を付けなければ全件。既に要約済みの記事はスキップされるので、
   3件だけ試した後にもう一度実行しても二重に課金・処理されません。)

## Step 3: レポート表示 (HTML生成)

DB内の直近の記事(既定: `fetched_at` から `REPORT_LOOKBACK_DAYS`=7日分)を
ジャーナルごとにまとめ、静的HTMLレポートを生成します。LLM要約(Step2)を
まだ実行していなくても動作し、その場合は「要約待ち」等の表示になります。

```bash
python report.py
```

- `reports/report_YYYY-MM-DD.html`(その日の日付付き)と `reports/latest.html`
  (常に最新版を指す)の2つが生成されます。
- `latest.html` をブラウザで開けば見た目を確認できます。
- 表示は記事ごとに3パターン:
  - 要約あり(緑背景)
  - abstractはあるが未要約(グレー斜体、「要約はまだ生成されていません」)
  - abstractが無い(赤系斜体、「要約はありません(タイトルのみ)」)
- `config.py` の `REPORT_LOOKBACK_DAYS` で対象期間、`REPORT_OUTPUT_DIR` で
  出力先フォルダ名を変更できます。

## 既知の不具合と修正 (from-index-date -> from-created-date)

当初 `from-index-date` フィルタを使っていましたが、これは「被引用数の更新など
第三者による変更で触られただけの古い記録」まで拾ってしまう仕様のため、
1990年代・2000年代の論文が大量に混ざる不具合が発生しました。

`from-created-date`(Crossrefへの初回登録日)+ `sort=created&order=desc` に
変更し、本来の目的である「新着論文」に絞り込むよう修正済みです。

もし再びこの現象(古い論文が大量に混ざる)が起きたら、DBを一度作り直して
(`articles.db` を削除して `main.py` から再実行)から様子を見てください。

## Mendeley連携

Mendeleyへの「自分のライブラリに文献を追加する」操作は、読み取り専用の
Catalog検索とは異なり、**ユーザー本人によるログイン許可(OAuth2 authorization_code
フロー)が必要**です。そのため最初に1回だけブラウザでの認証手順が入ります。

### 1. アプリ登録

1. https://dev.mendeley.com で(既存のMendeleyアカウントで)サインインし、
   「My Apps」からアプリを新規登録する。
2. Redirect URL には `http://localhost:8765/oauth/callback` を設定する
   (`config.py` の `MENDELEY_REDIRECT_URI` と完全に一致させること)。
3. 発行された `client_id` / `client_secret` を `config.py` の
   `MENDELEY_CLIENT_ID` / `MENDELEY_CLIENT_SECRET` に設定する。

### 2. 初回認証(1回だけ)

```bash
python mendeley_auth.py
```

ブラウザが開くのでMendeleyにログインして許可すると、ローカルの一時サーバーが
認可コードを受け取り、`mendeley_token.json` に access_token / refresh_token を
保存する。以降はこのファイルを使って自動的にトークンが更新されるので、
基本的にこのスクリプトの再実行は不要(refresh_tokenが失効した場合を除く)。

`mendeley_token.json` には認証情報が入るため、gitには絶対にコミットしない
こと(`.gitignore` に追加済み)。

### 3. 登録の実行

```bash
python mendeley_sync.py
```

DB内で `mendeley_added = 0` の記事(まだMendeleyに登録していない記事)を
1件ずつMendeleyライブラリに登録し、成功したものから `mendeley_added = 1` に
更新する。何度実行しても、既に登録済みの記事は対象から外れるので安全(冪等)。

### 補足

- Mendeleyに登録するドキュメントのtypeは "journal" 固定にしている。
- 著者名は "Taro Yamada, Hanako Suzuki" のようなカンマ区切り文字列を、
  最後の単語をlast_name・残りをfirst_nameとする簡易ルールで分割している。
  複合姓や特殊な表記では正しく分割できない場合があるので、その場合は
  Mendeley側で手動修正してください。

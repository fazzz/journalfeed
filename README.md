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

## レポートからの選択登録(推奨フロー)

全件を自動でMendeleyに放り込むのではなく、レポートを見ながら気になる論文だけ
チェックして取り込む運用にできます。

1. `python report.py` で `reports/latest.html` を生成し、ブラウザで開く
2. 気になる論文のチェックボックスにチェックを入れる
3. 右下の「選択した論文を書き出す」ボタンを押すと `selected_dois.txt` が
   ダウンロードされる
4. ダウンロードしたファイルを使って登録:
   ```bash
   python mendeley_sync.py --dois-file ~/Downloads/selected_dois.txt
   ```
   (パスはダウンロード先に合わせて読み替えてください)

`--dois-file` を付けずに `python mendeley_sync.py` を実行すると、従来通り
未登録分を全件登録します(自動化したくなった場合用に残しています)。

## キーワード強調表示

`config.py` の `KEYWORDS` に興味のあるキーワードを書いておくと、レポート上で
自動的に目立つように表示されます。

- **記事単位**: タイトル・アブストラクトにキーワードが1件でも一致すると、
  記事カードの左に色付きの縦線と「🔑 一致キーワード: ...」のバッジが付く。
  一致数が多いほど濃い色(1件=黄、2件=オレンジ、3件以上=赤)になる。
- **ジャーナル単位**: そのジャーナル内でヒットした記事の割合が
  `JOURNAL_HOT_MIN_HIT_RATIO`(既定0.3)以上、またはヒット数の合計が
  `JOURNAL_HOT_MIN_HITS`(既定3)以上のとき、そのジャーナルを
  「🔥 ヒット多数」として目次・見出しの両方で強調表示する。
- 目次(TOC)と本文中のジャーナルの並び順も、ヒット数が多いジャーナルが
  上に来るように自動的に並べ替えられる(従来のジャーナル名順ではなくなった点に注意)。

キーワードは大文字小文字を区別せず、単純な部分一致で判定しています。

## GitHub Actionsでの日次自動化

`main.py`(取得)→ `enrich_abstracts.py`(abstract補完)→ `report.py`(レポート生成)
を毎日自動実行し、結果(`articles.db` と `reports/`)をリポジトリにコミットします。
Step2(LLM要約)は課金が発生するため、あえて自動化から外しています
(要約したい場合は手元で `python summarize.py` を実行してください)。

### セットアップ手順

1. **秘密情報をconfig.pyから環境変数ベースに変更済み**
   `CROSSREF_MAILTO` と `OPENALEX_API_KEY` は、もう `config.py` に直書きされて
   いません(`os.environ.get(...)` 経由で読む形に変更済み)。そのため
   `config.py` はそのままgitにコミットして問題ありません
   (`.gitignore` からも外しました)。

   ローカルで実行する際は、これまで通り環境変数を設定してください:
   ```bash
   export CROSSREF_MAILTO="あなたのメールアドレス"
   export OPENALEX_API_KEY="あなたのOpenAlex APIキー"
   export ANTHROPIC_API_KEY="あなたのAnthropic APIキー"
   ```

2. **GitHubリポジトリを作成し、このフォルダの中身をpushする**
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-account>/journalfeed.git
   git push -u origin main
   ```
   (`articles.db` が既にある場合はそれも一緒にコミットされます。無ければ空の
   状態からスタートし、初回のActions実行で作られます。)

3. **リポジトリにSecretsを登録する**
   GitHubリポジトリの Settings → Secrets and variables → Actions →
   New repository secret から、以下を登録:
   - `CROSSREF_MAILTO`
   - `OPENALEX_API_KEY`

4. **Actionsの書き込み権限を確認する**
   Settings → Actions → General → Workflow permissions で
   「Read and write permissions」になっていることを確認してください
   (デフォルトのままだとpushに失敗することがあります)。

5. **動作確認**
   Actionsタブ → "journalfeed daily crawl" → "Run workflow" で手動実行できます。
   スケジュール実行は毎日 UTC 21:00(日本時間 朝6:00)です
   (`.github/workflows/daily.yml` の `cron` で変更可能)。

### 運用イメージ

- 毎朝、自動でDBとレポートが更新され、リポジトリにコミットされる
- あなたは `git pull` して `reports/latest.html` を見るか、GitHubの
  Web UI上でファイルを直接開いて確認する
- 気になる論文があれば、そのままレポート上でチェック→書き出し→
  手元で `python mendeley_sync.py --dois-file ...` を実行してMendeleyに登録
- 要約が欲しくなったら、任意のタイミングで手元 or 別のActionsワークフローで
  `python summarize.py` を実行(このワークフローには含まれていません)

## GitHub Pagesでの公開

`python report.py` を実行すると、これまでの `reports/` に加えて
`docs/index.html` にも同じ内容を書き出すようにしています。GitHub Pagesの
公開元をこの `docs/` フォルダに設定すれば、毎日Actionsが自動更新した
最新レポートを固定URLで見られるようになります。

### 設定手順(初回のみ)

1. 一度 `python main.py && python enrich_abstracts.py && python report.py` を
   実行するか、Actionsを1回手動実行(workflow_dispatch)して `docs/index.html`
   をリポジトリに作っておく(空のリポジトリだと選択肢に出てこないため)。
2. GitHubリポジトリの **Settings → Pages** を開く
3. "Build and deployment" の Source を **Deploy from a branch** にし、
   Branch を **main** / **/docs** に設定して Save
4. 数分待つと、`https://<あなたのアカウント>.github.io/<リポジトリ名>/` で
   レポートが見られるようになる(以降は毎日のActions実行のたびに自動更新)

## articles.dbの肥大化対策(アーカイブ)

articles.dbは毎日新着記事が増え続けるため、放置すると将来的に肥大化します
(GitHubは単体ファイル100MBで強制ブロック、リポジトリ全体でも1GB程度が推奨上限)。

そこで `ARCHIVE_KEEP_DAYS`(既定180日)より古い記事は、`archives/` フォルダの
中に「その時点までの記事」としてアーカイブファイル(`archive_until_YYYY-MM-DD.db`)
を作って移し、articles.db本体からは削除・VACUUMして実サイズも縮めます。
アーカイブファイルは一度作ったら二度と書き換えないので、gitの差分もそこで
止まり、リポジトリが際限なく肥大化するのを防げます。

```bash
python archive_old_articles.py
```

`.github/workflows/archive.yml` として、毎月1日に自動実行するワークフローも
用意しました(手動実行 workflow_dispatch にも対応)。日次クロールとは別の
ワークフローなので、頻繁に走って小さなアーカイブファイルが乱立することは
ありません。

過去の記事を調べたくなったら、該当する `archives/archive_until_*.db` を
`sqlite3` などで直接開けば、当時のタイトル・abstract・要約がすべて残っています。

## プリプリントサーバー対応 (bioRxiv / ChemRxiv / arXiv)

ジャーナルに加えて、プリプリントサーバーの新着もチェックできます。

- **bioRxiv・ChemRxiv**: Crossrefに登録されているため、`config.py` の
  `PREPRINT_SOURCES` にDOIプレフィックス(bioRxiv=`10.1101`,
  ChemRxiv=`10.26434`)を指定するだけで、ジャーナルと同じCrossref経由の
  仕組みで取得できる。bioRxivはmedRxivとプレフィックスを共用しているため、
  `institution_filter` で「bioRxivだけ」に絞り込んでいる。
- **arXiv**: Crossrefに登録されていないため、arXiv専用API
  (`arxiv_client.py`)で別途取得する。`config.py` の `ARXIV_CATEGORIES` で
  カテゴリ(例: `physics.chem-ph`, `cond-mat.soft`, `q-bio.BM`)を指定する。

### ジャーナルとプリプリントで扱いを変えている点

ジャーナル(`JOURNALS`)は誌名自体である程度絞り込まれているため、これまで
通り全件保存する。一方、プリプリント(`PREPRINT_SOURCES` と
`ARXIV_CATEGORIES`)は誌名による絞り込みが効かず、特にarXivは分野が広く
投稿数も多いため、`config.py` の `KEYWORDS` に
`MIN_KEYWORD_HITS_FOR_PREPRINTS`(既定2件)以上ヒットしたものだけを
DBに保存するようにしている。これによりノイズと肥大化の両方を抑えている。

しきい値は用途に応じて調整してください(緩くしたいなら1に、厳しくしたいなら
3以上に)。

### Mendeley登録時の識別子

arXivの論文はDOIを持たないことが多いため、`arxiv:<ID>` という擬似DOIを
内部的なキーとして使っている。Mendeleyへの登録時には、これを自動判定して
`identifiers.arxiv` として送るようにしている(通常のDOIを持つ記事は
従来通り `identifiers.doi`)。

## enrich_abstracts.pyについて(処理時間と安全な中断)

対象記事が多いと、1件ずつ順番にOpenAlexへ問い合わせる都合上、それなりに
時間がかかることがあります。進捗は `[現在の件数/全体件数]` の形で表示される
ので、進んでいるかどうかは確認できます。

- **途中でCtrl+Cで止めても安全です**。1件処理するごとにDBへ保存(commit)
  しているので、途中で止めても壊れたり重複したりしません。次に実行すれば
  続きから処理されます。
- 動作確認だけしたい場合は `python enrich_abstracts.py --limit 50` のように
  件数を絞れます。

## ジャーナル名の略称表示

レポート上のジャーナル名を、正式名称ではなく一般的な略称(例:
"Journal of the American Chemical Society" → "J. Am. Chem. Soc.")で
表示できます。Crossref上の論文データに含まれる `short-container-title`
(出版社が登録している場合)を利用して自動取得します。

```bash
python fetch_journal_abbreviations.py
```

- `JOURNALS` に登録した各誌について、Crossrefから略称を取得し
  `journal_abbreviations.json` に保存します。
- 既に分かっている誌はスキップされるので、新しいジャーナルを追加したときや
  未取得の誌を再確認したいときに、何度実行しても安全です。
- 出版社がshort-container-titleを登録していない誌は略称が見つからず、
  その場合はレポート上も正式名称のまま表示されます(マウスホバーすると
  正式名称がツールチップで見られるので、略称が付いた誌でも元の誌名を
  確認できます)。

このスクリプトは頻繁に実行する必要はないので、GitHub Actionsには組み込んで
いません。手元で1回実行し、`journal_abbreviations.json` をコミットしておく
運用を想定しています。

## FILTERED_JOURNALS(キーワードフィルタ付きの通常ジャーナル)

Frontiers in Molecular Biosciencesのように、ISSNを持つ通常のジャーナルだが
掲載点数が多く分野も広いため、プリプリントと同様にキーワードフィルタを
掛けたい場合は `config.py` の `FILTERED_JOURNALS` に追加してください。
取得方法自体は `JOURNALS` と同じ(Crossref / ISSN指定)ですが、
`MIN_KEYWORD_HITS_FOR_PREPRINTS` 件以上ヒットしたものだけが保存されます。

```python
FILTERED_JOURNALS = [
    {"journal": "Frontiers in Molecular Biosciences", "issn": "2296-889X"},
]
```

## Mendeleyのclient_idについて

`MENDELEY_CLIENT_ID` はOAuthのclient_id(公開アプリにも埋め込まれる類のもので、
一般的に秘密情報としては扱われない)なので、`config.py` に直書きしています。
秘密にすべき `MENDELEY_CLIENT_SECRET` だけ環境変数から読む構成にしています。

## 著者ウォッチリスト

`config.py` の `AUTHOR_WATCHLIST` にフルネームを追加すると、その著者の記事は
自動的に目立つように表示されます。

```python
AUTHOR_WATCHLIST = ["Michael Shirts", "David Mobley"]
```

- **レポート表示**: 著者ウォッチにヒットした記事は、キーワードのヒット数に
  関わらず(0件でも)最低限のハイライト(枠線・通常サイズの文字)が付き、
  タイトル横に ⭐ バッジで一致した著者名が表示される。
- **プリプリントのフィルタ**: `FILTERED_JOURNALS` や `PREPRINT_SOURCES`、
  `ARXIV_CATEGORIES` では通常キーワードのヒット数でフィルタしているが、
  著者ウォッチにヒットした記事はキーワードのヒットが無くても保存される
  (見逃し防止)。
- 判定は大小文字を区別しない部分一致。著者欄の表記ゆれ(ミドルネームの
  有無など)で一致しないことがあるので、うまく拾えない場合はウォッチ
  リストの書き方を調整してください。

## 著者ウォッチのジャンプリンク

`AUTHOR_WATCHLIST` に登録した著者のうち、その回のレポートで実際にヒットが
あった著者だけが、ページ上部にチップ形式(⭐著者名(件数))で表示されます。
クリックするとその著者の(複数ある場合は最初の)該当記事にジャンプします。
ヒットが無い著者はそもそも表示されないので、スペースを圧迫しません。

## 著者ウォッチの表記ゆれ対応

初期実装では「ウォッチリストの名前が著者欄に一字一句含まれるか」という
厳密な部分一致だったため、ミドルネームの有無(例: "Michael R. Shirts" vs
"Michael Shirts")で一致しないことがありました。現在は「姓が一致し、かつ
名の頭文字が一致する」という緩い基準に変更済みです。

## 著者ウォッチの判定精度をさらに向上

「姓が一致し名の頭文字が一致すればOK」という基準は、"Michael R. Shirts"に
対して"Mark Shirts"のような別人まで拾ってしまう問題がありました。現在は
「名が完全一致、またはどちらかがイニシャル表記でその頭文字が一致する」
という、より厳密な基準に変更済みです(ミドルネームの有無は引き続き無視)。

## 著者チップもページ上部に固定表示

著者ウォッチのチップ列を、ジャーナルの目次(TOC)と同じ固定表示エリア
(`sticky-nav`)にまとめました。スクロールしても両方とも常に見える位置に
表示され続けます。

## キーワードタグでの絞り込み

著者チップ・ジャーナル目次と同じ固定表示エリアに、キーワードタグの行も
追加しました(ヒットが1件もないキーワードは表示されません)。

- タグをクリックすると、そのキーワードにヒットした記事だけが表示される
  (該当記事が無いジャーナルのセクションごと非表示になる)
- 同じタグをもう一度クリックすると解除
- 「すべて表示」をクリックするといつでも全解除
- ページ内蔵のJavaScriptだけで動作するので、サーバー等は不要

jsdomを使った自動テストで、絞り込み・解除・セクションの表示非表示が
正しく動作することを確認済みです。

## キーワードの週次トレンド表示

ヘッダー直下に「📈 キーワードの週次トレンド」という折りたたみセクションを
追加しました(初期状態は閉じていて、クリックで開きます)。

- 直近 `TREND_WEEKS`(既定8週)分について、週ごとに各キーワードが何件の
  記事にヒットしたかをシンプルな棒グラフ(バーの高さ)で表示
- 集計は`REPORT_LOOKBACK_DAYS`(通常のレポート表示範囲)に関係なく、
  articles.db全体が対象(ただしアーカイブ済みの古いデータは含まない)
- ヒットが1件も無いキーワードは表示されない
- 各キーワードの中での相対的な推移が見えるよう、バーの高さはキーワードごとに
  正規化している(キーワード間の絶対件数比較には向かない)

## researchmap連携用スナップショット画像

`generate_snapshot.py` を実行すると、直近(既定24時間、
`SNAPSHOT_LOOKBACK_HOURS`で調整可能)の新着論文をまとめた、SNS共有カード風の
画像 `docs/snapshot.png` と、それを表示するだけの単独ページ
`docs/snapshot.html` が生成されます。

```bash
python generate_snapshot.py
```

- 見出しはハイライトの強さ(キーワード・著者ウォッチのヒット数)が高い順に
  最大`SNAPSHOT_MAX_HEADLINES`件(既定5件)表示され、それぞれ色付きの
  ドット(黄→オレンジ→赤の順で強調度が高い)が付く
- 新着が無い日は「本日の新着はありません」という状態を表示
- 日次のGitHub Actionsに組み込み済みで、`report.py`の後に自動実行される

GitHub Pagesを設定済みなら、以下のURLが安定して使えます(pushのたびに
自動更新):

- 画像そのもの: `https://<アカウント>.github.io/<リポジトリ名>/snapshot.png`
- 画像を表示するだけのページ: `https://<アカウント>.github.io/<リポジトリ名>/snapshot.html`

researchmapのプロフィールに直接画像を埋め込める欄があれば前者を、外部
リンクとして貼るだけなら後者を使ってください(researchmap側の仕様は
変わりやすいので、実際にどちらが使えるかはご自身のプロフィール編集画面で
確認してみてください)。

日本語を描画するため、GitHub Actions上では `fonts-noto-cjk` を
apt installするステップを追加しています。ローカルで実行する場合、
macOSやWindowsでは別のフォントパスにフォールバックが必要になることが
あります(見つからない場合は日本語が文字化けしたフォントになります)。

# -*- coding: utf-8 -*-
import os
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
    {"journal": "Journal of the American Chemical Society", "issn": "1520-5126"},
    {"journal": "The Journal of Chemical Physics", "issn": "1089-7690"},
    {"journal": "Chemical Physics Letters", "issn": "1873-4448"},
    {"journal": "Journal of Computational Chemistry", "issn": "1096-987X"},
    {"journal": "Journal of Chemical Theory and Computation", "issn": "1549-9626"},
    {"journal": "Journal of Chemical Information and Modeling", "issn": "1549-960X"},
    {"journal": "The Journal of Physical Chemistry A", "issn": "1520-5215"},
    {"journal": "The Journal of Physical Chemistry B", "issn": "1520-5207"},
    {"journal": "The Journal of Physical Chemistry C", "issn": "1932-7455"},
    {"journal": "The Journal of Physical Chemistry Letters", "issn": "1948-7185"},
    {"journal": "Chemical Physics", "issn": "1873-4421"},
    {"journal": "Computational and Theoretical Chemistry", "issn": "1872-7999"},
    {"journal": "Computer Physics Communications", "issn": "0010-4655"},
    {"journal": "Molecular Simulation", "issn": "1029-0435"},
    {"journal": "Molecular Physics", "issn": "1362-3028"},
    {"journal": "Physical Chemistry Chemical Physics", "issn": "1463-9084"},
    {"journal": "Chemical Communications", "issn": "1364-548X"},
    {"journal": "Faraday Discussions", "issn": "1364-5498"},
    {"journal": "ChemistryOpen", "issn": "2191-1363"},
    {"journal": "FEBS Letters", "issn": "1873-3468"},
    {"journal": "Biochemistry", "issn": "1520-4995"},
    {"journal": "Biopolymers", "issn": "1097-0282"},
    {"journal": "Nature", "issn": "1476-4687"},
    {"journal": "Nature Communications", "issn": "2041-1723"},
    {"journal": "Nature Chemistry", "issn": "1755-4349"},
    {"journal": "Nature Chemical Biology", "issn": "1552-4469"},
    {"journal": "Nature Physics", "issn": "1745-2481"},
    {"journal": "Cell", "issn": "1097-4172"},
    {"journal": "Structure", "issn": "1878-4186"},
    {"journal": "Journal of Molecular Biology", "issn": "1089-8638"},
    {"journal": "Journal of Molecular Recognition", "issn": "1099-1352"},
    {"journal": "Journal of Molecular Graphics and Modelling", "issn": "1873-4243"},
    {"journal": "Journal of Structural Biology", "issn": "1095-8657"},
    {"journal": "Current Opinion in Structural Biology", "issn": "1879-033X"},
    {"journal": "Nucleic Acids Research", "issn": "1362-4962"},
    {"journal": "Bioinformatics", "issn": "1460-2059"},
    {"journal": "Journal of Computational Biology", "issn": "1557-8666"},
    {"journal": "Proteins: Structure, Function, and Bioinformatics", "issn": "1097-0134"},
    {"journal": "Protein Engineering, Design and Selection", "issn": "1741-0134"},
    {"journal": "Journal of Biological Chemistry", "issn": "1083-351X"},
    {"journal": "PLOS ONE", "issn": "1932-6203"},
    {"journal": "PLOS Biology", "issn": "1545-7885"},
    {"journal": "PLOS Computational Biology", "issn": "1553-7358"},
    {"journal": "PeerJ", "issn": "2167-8359"},
    {"journal": "Science", "issn": "1095-9203"},
    {"journal": "Proceedings of the National Academy of Sciences", "issn": "1091-6490"},
    {"journal": "Proceedings of the Royal Society B: Biological Sciences", "issn": "1471-2954"},
    {"journal": "Physical Review Letters", "issn": "1079-7114"},
    {"journal": "Physical Review E", "issn": "2470-0053"},
    {"journal": "Journal of Physics: Condensed Matter", "issn": "1361-648X"},
    {"journal": "New Journal of Physics", "issn": "1367-2630"},
    {"journal": "Journal of the Physical Society of Japan", "issn": "1347-4073"},
    {"journal": "Progress of Theoretical Physics", "issn": "1347-4081"},
    {"journal": "The British Journal for the Philosophy of Science", "issn": "1464-3537"},
    {"journal": "Systematic Biology", "issn": "1076-836X"},
    {"journal": "Journal of the ACM", "issn": "1557-735X"},
    {"journal": "Macromolecules", "issn": "1520-5835"},
    {"journal": "ACS Omega", "issn": "2470-1343"},
    {"journal": "Scientific Reports", "issn": "2045-2322"},
    {"journal": "Biophysical Journal", "issn": "0006-3495"},
    {"journal": "Protein Science", "issn": "0961-8368"},
    {"journal": "Journal of Biomolecular Structure and Dynamics", "issn": "0739-1102"},
    {"journal": "Living Journal of Computational Molecular Science", "issn": "2575-6524"},
]

DB_PATH = "articles.db"

# Crossref API の「polite pool」(応答が安定しやすい)を使うため、
# 自分のメールアドレスに変更してください
CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "your_email@example.com")

# Crossref への問い合わせ間隔(秒)。連続アクセスで先方に負荷をかけないためのマナー
CROSSREF_REQUEST_INTERVAL = 1.0

# 何日前までを「新着」として問い合わせるか。
# Crossrefへの初回登録(created)は出版から数日遅れることがあるため、
# 1(=今日だけ)ではなく数日分のバッファを持たせて取りこぼしを防ぐ。
# 実際の重複はDOIで排除されるので、日数を大きくしても二重登録にはならない。
LOOKBACK_DAYS = 3

# 1回のクエリで取得する最大件数(雑誌1誌・1回の実行あたり)
ROWS_PER_QUERY = 100

# --- プリプリントサーバー (Crossref / DOIプレフィックス指定) ---
# bioRxiv・ChemRxivはCrossrefに登録されているため、ISSNの代わりに
# DOIプレフィックスで同じ仕組みが使える。
# bioRxivはmedRxivとプレフィックス(10.1101)を共用しているため、
# institution_filter で絞り込む。
PREPRINT_SOURCES = [
    {"journal": "bioRxiv", "prefix": "10.1101", "institution_filter": "bioRxiv"},
    {"journal": "ChemRxiv", "prefix": "10.26434", "institution_filter": None},
]

# --- arXiv (専用API) ---
# 自分の研究テーマに合わせてカテゴリを編集してください。
# 参考: physics.chem-ph(化学物理)、cond-mat.soft(ソフトマター)、
#      cond-mat.stat-mech(統計力学)、q-bio.BM(生体高分子)
ARXIV_CATEGORIES = [
    "physics.chem-ph",
    "cond-mat.soft",
    "q-bio.BM",
]
ARXIV_MAX_RESULTS = 100

# プリプリント(PREPRINT_SOURCES・ARXIV_CATEGORIES)は、ジャーナルと違って
# 誌名自体による絞り込みが効かず、そのまま全件保存すると量が多くなりすぎる。
# そのため、KEYWORDS(下で定義)に何件以上ヒットしたものだけをDBに保存するかを
# ここで指定する。ジャーナル(JOURNALS)側には適用されない。
MIN_KEYWORD_HITS_FOR_PREPRINTS = 2

# ISSNを持つ通常のジャーナルだが、掲載点数が多い・分野が広いなどの理由で
# プリプリントと同様にキーワードフィルタ(MIN_KEYWORD_HITS_FOR_PREPRINTS)を
# 適用したいジャーナル。取得方法自体はJOURNALSと同じくISSN指定のCrossref。
FILTERED_JOURNALS = [
    {"journal": "Frontiers in Molecular Biosciences", "issn": "2296-889X"},
]

# --- abstract補完用 (OpenAlex) ---
# 2026年2月よりAPIキーが必須。openalex.org で無料アカウント登録し、
# https://openalex.org/settings/api でキーを取得して設定してください。
# (DOI単体でのlookupは無料枠の対象外で、実質無制限に使えます)
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "your_openalex_api_key")
OPENALEX_REQUEST_INTERVAL = 0.2

# 補完を諦めるまでの猶予日数。
# fetched_at からこの日数を過ぎてもabstractが見つからない記事は
# abstract_status を 'unavailable' にし、以降は問い合わせをスキップする
# (LLM要約フェーズではタイトルのみ扱いか、要約対象から除外する)。
ABSTRACT_GIVEUP_DAYS = 7

# --- LLM要約用 (Anthropic API) ---
# GitHub Actions等で自動化する際にconfig.pyへキーを直書きしなくて済むよう、
# 環境変数 ANTHROPIC_API_KEY からも読めるようにしている。
# (config.py に直接書いてもよいが、gitにコミットしないよう .gitignore を忘れずに)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your_anthropic_api_key")

# 定型的な要約タスクなのでコスト効率のよいHaikuを既定にしている。
# 要約の質が物足りない場合は "claude-sonnet-5" に変更する。
SUMMARY_MODEL = "claude-haiku-4-5-20251001"
SUMMARY_MAX_TOKENS = 300
SUMMARY_REQUEST_INTERVAL = 0.5

# --- レポート表示用 ---
REPORT_OUTPUT_DIR = "reports"
REPORT_LOOKBACK_DAYS = 7  # 直近何日分(fetched_at基準)をレポートに含めるか

# GitHub Pagesで公開する場合の出力先(Pagesの公開元を "main" / "docs" に設定する想定)。
# report.py実行のたびに、最新のレポートをこのパスにも書き出す。
DOCS_OUTPUT_PATH = "docs/index.html"

# ジャーナル略称(abbreviation)のキャッシュファイル。
# fetch_journal_abbreviations.py が書き込み、report.py が読み込んで表示に使う。
JOURNAL_ABBREV_FILE = "journal_abbreviations.json"

# --- 古いデータのアーカイブ用 ---
# articles.db に残す期間(日)。これより古い fetched_at の記事はアーカイブに移す。
ARCHIVE_KEEP_DAYS = 180
ARCHIVE_DIR = "archives"

# --- Mendeley連携用 ---
# https://dev.mendeley.com で無料でアプリ登録し、CLIENT_ID/CLIENT_SECRETを取得。
# アプリ登録時の「Redirect URL」は、下の MENDELEY_REDIRECT_URI と
# 完全に一致させること(末尾のスラッシュの有無なども)。
MENDELEY_CLIENT_ID = "24369"
MENDELEY_CLIENT_SECRET = os.environ.get("MENDELEY_CLIENT_SECRET")
MENDELEY_REDIRECT_URI = "http://localhost:8765/oauth/callback"

# 認証後のaccess_token/refresh_tokenを保存するファイル。
# 秘密情報が入るので、gitを使うなら必ず.gitignoreに入れること。
MENDELEY_TOKEN_FILE = "mendeley_token.json"

MENDELEY_REQUEST_INTERVAL = 0.5

# --- キーワード強調表示用 (Step3レポート) ---
# タイトル・アブストラクトに含まれるかを大文字小文字を区別せず判定する。
# 自分の研究テーマに合わせて自由に編集してください。
KEYWORDS = [
    # MD手法・強化サンプリング
    "molecular dynamics",
    "enhanced sampling",
    "free energy",
    "free energy perturbation",
    "alchemical free energy",
    "replica exchange",
    "metadynamics",
    "umbrella sampling",
    "collective variable",
    "coarse-grained",
    "machine learning potential",

    # 解析・理論
    "Markov state model",
    "transition path sampling",
    "protein folding",

    # 手法・ツール(積分法・自由エネルギー推定・解析ライブラリ)
    "BAOAB integrator",
    "Multistate Bennett acceptance ratio",
    "MBAR",
    "WHAM",
    "MDTraj",
    "MDAnalysis",
    "OpenMM",
    "GROMACS",

    # 構造予測・タンパク質デザイン
    "alphafold",
    "protein design",
    "de novo protein design",
    "protein language model",
    "diffusion model",
    "RFdiffusion",
    "ProteinMPNN",
    "cryo-EM",
]

# ジャーナルの見出しを「ヒットが多い」として目立たせる閾値。
# ヒットした記事の割合、またはヒット数の合計のどちらかを満たせば目立たせる。
JOURNAL_HOT_MIN_HIT_RATIO = 0.3
JOURNAL_HOT_MIN_HITS = 3

# --- 著者ウォッチリスト ---
# ここに載せた名前が著者欄に含まれる記事は、キーワードのヒット数に関わらず
# 目立つように表示される(大小文字を区別しない部分一致)。
# フルネームで書いてください(例: "Michael Shirts")。
AUTHOR_WATCHLIST = []

# --- キーワードの週次トレンド表示 ---
# レポート上に、直近何週分のキーワード出現数の推移を表示するか。
TREND_WEEKS = 8

# --- SNSカード風スナップショット画像(researchmap等への埋め込み用) ---
SNAPSHOT_LOOKBACK_HOURS = 24  # 何時間以内に取得した記事を「本日分」として扱うか
SNAPSHOT_OUTPUT_PATH = "docs/snapshot.png"
SNAPSHOT_PAGE_PATH = "docs/snapshot.html"
SNAPSHOT_MAX_HEADLINES = 5

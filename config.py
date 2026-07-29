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
]

DB_PATH = "articles.db"

# Crossref API の「polite pool」(応答が安定しやすい)を使うため、
# 自分のメールアドレスに変更してください
CROSSREF_MAILTO = "yu.yamamori@alumni.tus.ac.jp"

# Crossref への問い合わせ間隔(秒)。連続アクセスで先方に負荷をかけないためのマナー
CROSSREF_REQUEST_INTERVAL = 1.0

# 何日前までを「新着」として問い合わせるか。
# Crossrefへの初回登録(created)は出版から数日遅れることがあるため、
# 1(=今日だけ)ではなく数日分のバッファを持たせて取りこぼしを防ぐ。
# 実際の重複はDOIで排除されるので、日数を大きくしても二重登録にはならない。
LOOKBACK_DAYS = 3

# 1回のクエリで取得する最大件数(雑誌1誌・1回の実行あたり)
ROWS_PER_QUERY = 100

# --- abstract補完用 (OpenAlex) ---
# 2026年2月よりAPIキーが必須。openalex.org で無料アカウント登録し、
# https://openalex.org/settings/api でキーを取得して設定してください。
# (DOI単体でのlookupは無料枠の対象外で、実質無制限に使えます)
OPENALEX_API_KEY = "aw92bKl5NYN9jqcA6x3tg8"
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
import os
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your_anthropic_api_key")

# 定型的な要約タスクなのでコスト効率のよいHaikuを既定にしている。
# 要約の質が物足りない場合は "claude-sonnet-5" に変更する。
SUMMARY_MODEL = "claude-haiku-4-5-20251001"
SUMMARY_MAX_TOKENS = 300
SUMMARY_REQUEST_INTERVAL = 0.5

# --- レポート表示用 ---
REPORT_OUTPUT_DIR = "reports"
REPORT_LOOKBACK_DAYS = 7  # 直近何日分(fetched_at基準)をレポートに含めるか

# --- Mendeley連携用 ---
# https://dev.mendeley.com で無料でアプリ登録し、CLIENT_ID/CLIENT_SECRETを取得。
# アプリ登録時の「Redirect URL」は、下の MENDELEY_REDIRECT_URI と
# 完全に一致させること(末尾のスラッシュの有無なども)。
MENDELEY_CLIENT_ID = "your_mendeley_client_id"
MENDELEY_CLIENT_SECRET = "your_mendeley_client_secret"
MENDELEY_REDIRECT_URI = "http://localhost:8765/oauth/callback"

# 認証後のaccess_token/refresh_tokenを保存するファイル。
# 秘密情報が入るので、gitを使うなら必ず.gitignoreに入れること。
MENDELEY_TOKEN_FILE = "mendeley_token.json"

MENDELEY_REQUEST_INTERVAL = 0.5

# --- キーワード強調表示用 (Step3レポート) ---
# タイトル・アブストラクトに含まれるかを大文字小文字を区別せず判定する。
# 自分の研究テーマに合わせて自由に編集してください。
KEYWORDS = [
    "enhanced sampling",
    "free energy",
    "coarse-grained",
    "replica exchange",
    "metadynamics",
    "molecular dynamics",
    "folding",
    "alphafold",
    "alchemical free energy",
    "free energy puterbation", 
]

# ジャーナルの見出しを「ヒットが多い」として目立たせる閾値。
# ヒットした記事の割合、またはヒット数の合計のどちらかを満たせば目立たせる。
JOURNAL_HOT_MIN_HIT_RATIO = 0.3
JOURNAL_HOT_MIN_HITS = 3

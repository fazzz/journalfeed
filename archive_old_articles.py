# -*- coding: utf-8 -*-
"""
articles.db 内の古い記事(fetched_at が ARCHIVE_KEEP_DAYS 日より前のもの)を
別のアーカイブファイル(archives/archive_until_YYYY-MM-DD.db)に移し、
articles.db 本体からは削除してVACUUMで実ファイルサイズも縮める。

アーカイブファイルは作成後に書き換えない想定なので、gitにコミットしても
差分が増え続けず、リポジトリの肥大化を抑えられる。

数ヶ月に1回程度、手動またはスケジュールされたGitHub Actionsで実行することを
想定している(毎日実行するようなものではない)。

使い方:
    python archive_old_articles.py
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import DB_PATH, ARCHIVE_KEEP_DAYS, ARCHIVE_DIR
from db import get_conn

BASE_DIR = Path(__file__).resolve().parent


def run():
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=ARCHIVE_KEEP_DAYS)
    ).strftime("%Y-%m-%d %H:%M:%S")

    src_conn = get_conn(DB_PATH)
    cursor = src_conn.execute(
        "SELECT * FROM articles WHERE fetched_at < ? ORDER BY fetched_at", (cutoff,)
    )
    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    print(f"アーカイブ対象 (fetched_at < {cutoff}): {len(rows)} 件")

    if not rows:
        src_conn.close()
        print("対象がないため、何もせず終了します。")
        return

    archive_dir = BASE_DIR / ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = archive_dir / f"archive_until_{today_str}.db"

    archive_conn = get_conn(archive_path)
    col_list = ",".join(columns)
    placeholders = ",".join("?" for _ in columns)
    archive_conn.executemany(
        f"INSERT OR IGNORE INTO articles ({col_list}) VALUES ({placeholders})",
        rows,
    )
    archive_conn.commit()
    archive_conn.close()

    src_conn.execute("DELETE FROM articles WHERE fetched_at < ?", (cutoff,))
    src_conn.commit()
    src_conn.execute("VACUUM")
    src_conn.close()

    print(f"{len(rows)} 件を {archive_path} に移動し、articles.db から削除しました。")


if __name__ == "__main__":
    run()

# -*- coding: utf-8 -*-
"""SQLite への保存まわり。DOIをキーに重複を排除する。"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    doi TEXT PRIMARY KEY,
    journal TEXT,
    title TEXT,
    authors TEXT,
    pub_date TEXT,
    link TEXT,
    abstract TEXT,
    abstract_status TEXT DEFAULT 'pending',
    summary_ja TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    mendeley_added INTEGER DEFAULT 0
);
"""


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    # 既存DB(abstract_status列がまだ無いもの)への後方互換マイグレーション
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN abstract_status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass  # 既に列がある場合はここに来る
    conn.commit()
    return conn


def article_exists(conn, doi):
    row = conn.execute("SELECT 1 FROM articles WHERE doi = ?", (doi,)).fetchone()
    return row is not None


def insert_article(conn, journal, doi, title, authors, pub_date, link, abstract):
    """新規記事のみ挿入する。既存なら False を返す(要約フェーズはStep2で行う)。"""
    if article_exists(conn, doi):
        return False
    status = "found" if abstract else "pending"
    conn.execute(
        """
        INSERT INTO articles (doi, journal, title, authors, pub_date, link, abstract, abstract_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (doi, journal, title, authors, pub_date, link, abstract, status),
    )
    conn.commit()
    return True


def articles_pending_abstract(conn):
    """abstractが空で、まだ'unavailable'判定になっていない記事一覧を返す
    (doi, title, fetched_at)。enrich_abstracts.py がこれを対象に再取得を試みる。
    """
    return conn.execute(
        """
        SELECT doi, title, fetched_at FROM articles
        WHERE (abstract IS NULL OR abstract = '')
          AND abstract_status != 'unavailable'
        """
    ).fetchall()


def mark_abstract_found(conn, doi, abstract):
    """abstractが見つかった記事を更新する。"""
    conn.execute(
        "UPDATE articles SET abstract = ?, abstract_status = 'found' WHERE doi = ?",
        (abstract, doi),
    )
    conn.commit()


def mark_abstract_unavailable(conn, doi):
    """猶予期間を過ぎてもabstractが見つからなかった記事に印を付け、
    以降の再取得対象から除外する。"""
    conn.execute(
        "UPDATE articles SET abstract_status = 'unavailable' WHERE doi = ?",
        (doi,),
    )
    conn.commit()


def summarizable_articles(conn):
    """要約対象(abstractがある、またはfound/pending中でabstractが付いた)記事のうち、
    まだsummary_jaが無いもの(Step2で使用)。abstract_status='unavailable'は除外。
    """
    return conn.execute(
        """
        SELECT doi, title, abstract FROM articles
        WHERE summary_ja IS NULL
          AND abstract IS NOT NULL AND abstract != ''
        """
    ).fetchall()


def title_only_articles(conn):
    """abstractが最終的に手に入らなかった(unavailable)記事一覧。
    要約対象からは除外するが、一覧表示にはタイトルのみで含める想定(Step2以降で使用)。
    """
    return conn.execute(
        "SELECT doi, journal, title, link FROM articles WHERE abstract_status = 'unavailable'"
    ).fetchall()


def update_summary(conn, doi, summary_ja):
    """LLMが生成した日本語要約を保存する。"""
    conn.execute(
        "UPDATE articles SET summary_ja = ? WHERE doi = ?",
        (summary_ja, doi),
    )
    conn.commit()


def recent_articles_for_report(conn, since_fetched_at):
    """fetched_at が since_fetched_at 以降の記事を新しい順に返す(Step3のレポート生成用)。"""
    return conn.execute(
        """
        SELECT doi, journal, title, authors, pub_date, link,
               abstract, abstract_status, summary_ja, fetched_at
        FROM articles
        WHERE fetched_at >= ?
        ORDER BY fetched_at DESC
        """,
        (since_fetched_at,),
    ).fetchall()


def unsynced_to_mendeley(conn):
    """まだMendeleyに登録していない記事一覧を返す
    (doi, journal, title, authors, pub_date, abstract)。"""
    return conn.execute(
        """
        SELECT doi, journal, title, authors, pub_date, abstract
        FROM articles
        WHERE mendeley_added = 0
        """
    ).fetchall()


def mark_mendeley_synced(conn, doi):
    """Mendeleyへの登録が完了した記事に印を付ける。"""
    conn.execute("UPDATE articles SET mendeley_added = 1 WHERE doi = ?", (doi,))
    conn.commit()

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
    summary_ja TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    mendeley_added INTEGER DEFAULT 0
);
"""


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def article_exists(conn, doi):
    row = conn.execute("SELECT 1 FROM articles WHERE doi = ?", (doi,)).fetchone()
    return row is not None


def insert_article(conn, journal, doi, title, authors, pub_date, link, abstract):
    """新規記事のみ挿入する。既存なら False を返す(要約フェーズはStep2で行う)。"""
    if article_exists(conn, doi):
        return False
    conn.execute(
        """
        INSERT INTO articles (doi, journal, title, authors, pub_date, link, abstract)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (doi, journal, title, authors, pub_date, link, abstract),
    )
    conn.commit()
    return True


def unsummarized_articles(conn):
    """summary_ja がまだ入っていない記事一覧(Step2で使用)。"""
    return conn.execute(
        "SELECT doi, title, abstract FROM articles WHERE summary_ja IS NULL"
    ).fetchall()

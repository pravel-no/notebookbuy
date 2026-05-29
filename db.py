"""
Unified SQLite schema for ads, price history, and analysis cache.
All entry points should call init_database() before using the DB.
"""
import datetime
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


# Python 3.12 deprecated the implicit datetime->str adapter. Register an
# explicit one that reproduces the previous output ("YYYY-MM-DD HH:MM:SS.ffffff")
# so stored timestamps — and price-history ordering — stay byte-for-byte stable.
sqlite3.register_adapter(
    datetime.datetime, lambda dt: dt.isoformat(sep=" ", timespec="microseconds")
)


DEFAULT_DB_NAME = "laptops_database.db"


_initialized_dbs = set()


def init_database(db_name: str = DEFAULT_DB_NAME) -> None:
    """Create all tables and indexes if they do not exist."""
    if db_name in _initialized_dbs:
        return
    with sqlite3.connect(db_name) as conn:
        _create_ads_tables(conn)
        _create_analysis_cache(conn)
        conn.commit()
    _initialized_dbs.add(db_name)


def _create_ads_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ads (
            id          INTEGER PRIMARY KEY,
            title       TEXT,
            price       REAL,
            currency    TEXT,
            url         TEXT,
            description TEXT,
            image_url   TEXT,
            parsed_at   TIMESTAMP
        )
        """
    )
    # Migration: Add image_url to existing databases
    cursor = conn.execute("PRAGMA table_info(ads)")
    cols = [col[1] for col in cursor.fetchall()]
    if "image_url" not in cols:
        conn.execute("ALTER TABLE ads ADD COLUMN image_url TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id       INTEGER NOT NULL,
            price       REAL    NOT NULL,
            recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ad_id) REFERENCES ads(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ph_ad_id ON price_history(ad_id)"
    )


def _create_analysis_cache(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_cache (
            id               TEXT PRIMARY KEY,
            cpu              TEXT,
            gpu              TEXT,
            ram              INTEGER,
            ssd              INTEGER,
            is_broken        INTEGER,
            year_est         INTEGER,
            cpu_score        INTEGER,
            gpu_score        INTEGER,
            content_hash     TEXT,
            analysis_version TEXT,
            analyzed_at      TIMESTAMP
        )
        """
    )
    existing_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(analysis_cache)").fetchall()
    }
    migrations = {
        "content_hash": "ALTER TABLE analysis_cache ADD COLUMN content_hash TEXT",
        "analysis_version": "ALTER TABLE analysis_cache ADD COLUMN analysis_version TEXT",
        "analyzed_at": "ALTER TABLE analysis_cache ADD COLUMN analyzed_at TIMESTAMP",
    }
    for col, sql in migrations.items():
        if col not in existing_cols:
            conn.execute(sql)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cache_id ON analysis_cache(id)"
    )


@contextmanager
def connect(db_name: str = DEFAULT_DB_NAME) -> Iterator[sqlite3.Connection]:
    init_database(db_name)
    conn = sqlite3.connect(db_name)
    try:
        yield conn
    finally:
        conn.close()

"""Tests for database schema creation and migrations."""
import sqlite3

import pytest

from db import _initialized_dbs, init_database


@pytest.fixture()
def tmp_db(tmp_path):
    """Yield a path to a fresh temporary database and clean up the init cache."""
    db_path = str(tmp_path / "test.db")
    _initialized_dbs.discard(db_path)
    yield db_path
    _initialized_dbs.discard(db_path)


def test_creates_all_tables(tmp_db):
    """init_database should create ads, price_history, and analysis_cache."""
    init_database(tmp_db)

    with sqlite3.connect(tmp_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert "ads" in tables
    assert "price_history" in tables
    assert "analysis_cache" in tables


def test_ads_has_image_url_column(tmp_db):
    """ads table should include the image_url column."""
    init_database(tmp_db)

    with sqlite3.connect(tmp_db) as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(ads)").fetchall()]

    assert "image_url" in cols


def test_idempotent_init(tmp_db):
    """Calling init_database twice should not raise."""
    init_database(tmp_db)
    _initialized_dbs.discard(tmp_db)  # force re-entry
    init_database(tmp_db)  # should not raise


def test_analysis_cache_has_migration_columns(tmp_db):
    """analysis_cache should have content_hash, analysis_version, analyzed_at."""
    init_database(tmp_db)

    with sqlite3.connect(tmp_db) as conn:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(analysis_cache)").fetchall()
        }

    for col in ("content_hash", "analysis_version", "analyzed_at"):
        assert col in cols, f"Missing migration column: {col}"


def test_price_history_index(tmp_db):
    """An index on price_history(ad_id) should exist."""
    init_database(tmp_db)

    with sqlite3.connect(tmp_db) as conn:
        indexes = {
            row[1]
            for row in conn.execute(
                "SELECT * FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }

    assert "idx_ph_ad_id" in indexes

"""Tests for price-tracking upsert logic and price-drop detection."""
import sqlite3

import pytest

import lappars
from db import _initialized_dbs, init_database


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "ads.db")
    _initialized_dbs.discard(path)
    init_database(path)
    yield path
    _initialized_dbs.discard(path)


def _ad(ad_id: int, price: float, title: str = "Laptop") -> dict:
    return {
        "ID": ad_id,
        "Заголовок": title,
        "Цена": price,
        "Валюта": "MDL",
        "Ссылка": f"https://999.md/ru/{ad_id}",
        "HTML_страницы": "description text",
        "Изображение": "",
    }


def test_new_then_unchanged(db):
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        assert lappars.save_or_update_ad(cur, _ad(1, 10000)) == "new"
        assert lappars.save_or_update_ad(cur, _ad(1, 10000)) == "unchanged"
        conn.commit()


def test_price_drop_then_rise(db):
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        lappars.save_or_update_ad(cur, _ad(1, 10000))
        assert lappars.save_or_update_ad(cur, _ad(1, 8000)) == "price_drop"
        assert lappars.save_or_update_ad(cur, _ad(1, 9000)) == "price_rise"
        conn.commit()


def test_sub_one_percent_change_is_unchanged(db):
    """Changes under 1% are treated as FX noise, not a real price move."""
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        lappars.save_or_update_ad(cur, _ad(1, 10000))
        assert lappars.save_or_update_ad(cur, _ad(1, 10050)) == "unchanged"
        conn.commit()


def test_get_price_drops_reports_drop(db):
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        lappars.save_or_update_ad(cur, _ad(1, 10000, "Dropper"))
        lappars.save_or_update_ad(cur, _ad(1, 8000, "Dropper"))  # -20%
        lappars.save_or_update_ad(cur, _ad(2, 5000, "Stable"))   # single record
        conn.commit()

    drops = lappars.get_price_drops(min_drop_pct=5.0, db=db)
    by_id = {d["ad_id"]: d for d in drops}
    assert 1 in by_id
    assert by_id[1]["first_price"] == 10000
    assert by_id[1]["last_price"] == 8000
    assert by_id[1]["drop_pct"] == 20.0
    # Single-record ad must not appear (needs > 1 history row).
    assert 2 not in by_id

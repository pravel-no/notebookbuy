"""Tests for the Telegram digest deal filtering."""
import send_telegram


def _row(**over) -> dict:
    base = {
        "id": 1,
        "title": "Dell Latitude i5",
        "price": 9000,
        "url": "https://999.md/ru/1",
        "description": "[Region: Chișinău]",
        "cpu": "i5-1135g7",
        "gpu": "integrated",
        "ram": 8,
        "ssd": 256,
        "is_broken": 0,
        "year_est": 2020,
        "cpu_score": 8000,
        "gpu_score": 1000,
    }
    base.update(over)
    return base


def test_low_value_deal_kept_with_default_floor(monkeypatch):
    """With the default floor (0) a modest laptop is still ranked, not dropped."""
    monkeypatch.setattr(send_telegram, "TELEGRAM_MIN_VALUE_SCORE", 0.0)
    deals = send_telegram.process_deals([_row()], {}, {}, {})
    assert len(deals) == 1
    assert deals[0]["value_score"] < 100  # would have been excluded by the old gate


def test_quality_floor_excludes_weak_deal(monkeypatch):
    monkeypatch.setattr(send_telegram, "TELEGRAM_MIN_VALUE_SCORE", 100.0)
    deals = send_telegram.process_deals([_row()], {}, {}, {})
    assert deals == []


def test_unwanted_ad_skipped(monkeypatch):
    monkeypatch.setattr(send_telegram, "TELEGRAM_MIN_VALUE_SCORE", 0.0)
    rows = [_row(title="Куплю ноутбук дорого")]
    assert send_telegram.process_deals(rows, {}, {}, {}) == []

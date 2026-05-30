"""Tests for Passmark fuzzy-match lookup (no network: items are injected)."""
from benchmarks import HardwareBenchmarker


def _bench(items: list[dict]) -> HardwareBenchmarker:
    """Build a benchmarker without triggering cache/network loading."""
    b = HardwareBenchmarker.__new__(HardwareBenchmarker)
    b.hw_type = "cpu"
    b.score_key = "cpumark"
    b.items = items
    b.names = [i["name"] for i in items]
    return b


ITEMS = [
    {"name": "Intel Core i7-12700H", "cpumark": 26000},
    {"name": "Intel Core i5-1235U", "cpumark": 13000},
    {"name": "AMD Ryzen 7 5800H", "cpumark": 21000},
]


def test_subset_match_returns_score():
    b = _bench(ITEMS)
    # Hyphenated model as produced by the regex parser.
    assert b.search("i7-12700h") == 26000
    # Multi-word query whose tokens are a subset of the DB name.
    assert b.search("ryzen 7 5800h") == 21000


def test_unknown_query_returns_zero():
    b = _bench(ITEMS)
    assert b.search("totally unknown chip xyz") == 0


def test_empty_query_returns_zero():
    b = _bench(ITEMS)
    assert b.search("") == 0


def test_no_items_returns_zero():
    b = _bench([])
    assert b.search("i7 12700h") == 0

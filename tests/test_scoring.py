"""Unit tests for shared scoring and classification logic."""
import pytest

from scoring import (
    ANALYSIS_VERSION,
    classify_laptop,
    estimate_year_from_cpu,
    normalize_cpu_name,
    score_laptop,
)


@pytest.mark.parametrize(
    "cpu,expected_year",
    [
        ("Intel Core i7-12700H", 2022),
        ("i5-1135g7", 2021),
        ("Core Ultra 7 155H", 2024),
        ("AMD Ryzen 7 5800H", 2021),
        ("Apple M2 Pro", 2022),
        ("", None),
    ],
)
def test_estimate_year_from_cpu(cpu: str, expected_year: int | None) -> None:
    assert estimate_year_from_cpu(cpu) == expected_year


@pytest.mark.parametrize(
    "cpu,gpu_score,price,expected",
    [
        ("Apple M1", 0, 8000, "MacBook"),
        ("Intel Core i7-12700H", 8000, 12000, "Gaming"),
        ("i5-1235u", 0, 5000, "Office"),
        ("Intel Core i7-1165G7", 3000, 9000, "Ultrabook"),
    ],
)
def test_classify_laptop(cpu: str, gpu_score: int, price: int, expected: str) -> None:
    assert classify_laptop(cpu, gpu_score, price) == expected


def test_normalize_cpu_name() -> None:
    assert normalize_cpu_name("i7-12700h").startswith("Core ")
    assert len(normalize_cpu_name("Intel Core i7-12700H")) <= 25


def test_score_laptop_broken_penalty() -> None:
    ok = score_laptop(
        cpu_score=5000,
        gpu_score=2000,
        ram=16,
        ssd=512,
        year_est=2022,
        price=8000,
        is_broken=False,
    )
    broken = score_laptop(
        cpu_score=5000,
        gpu_score=2000,
        ram=16,
        ssd=512,
        year_est=2022,
        price=8000,
        is_broken=True,
    )
    assert broken["tech_pts"] < ok["tech_pts"]
    assert broken["value_score"] < ok["value_score"]


def test_score_laptop_higher_price_lowers_value() -> None:
    cheap = score_laptop(5000, 2000, 16, 512, 2022, 6000, False)
    pricey = score_laptop(5000, 2000, 16, 512, 2022, 12000, False)
    assert cheap["value_score"] > pricey["value_score"]
    assert cheap["tech_pts"] == pytest.approx(pricey["tech_pts"])


def test_analysis_version_is_set() -> None:
    assert ANALYSIS_VERSION

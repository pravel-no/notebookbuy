"""Tests for exchange rate loading and fallback behavior."""


def test_fallback_values_are_reasonable():
    """Default fallback rates should be plausible for MDL."""
    from currency import DEFAULT_EUR_TO_MDL, DEFAULT_USD_TO_MDL

    assert 10 < DEFAULT_USD_TO_MDL < 30, "USD/MDL fallback is out of range"
    assert 10 < DEFAULT_EUR_TO_MDL < 35, "EUR/MDL fallback is out of range"


def test_loaded_rates_are_positive():
    """Module-level USD_TO_MDL and EUR_TO_MDL must be positive floats."""
    from currency import EUR_TO_MDL, USD_TO_MDL

    assert isinstance(USD_TO_MDL, (int, float))
    assert isinstance(EUR_TO_MDL, (int, float))
    assert USD_TO_MDL > 0
    assert EUR_TO_MDL > 0


def test_eur_greater_than_usd():
    """1 EUR should buy more MDL than 1 USD (historically true)."""
    from currency import EUR_TO_MDL, USD_TO_MDL

    assert EUR_TO_MDL > USD_TO_MDL

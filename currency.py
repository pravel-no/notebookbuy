"""
Dynamic currency rate fetching and caching.
Provides USD_TO_MDL and EUR_TO_MDL exchange rates.
"""
import json
import logging
import os
import time

import requests


log = logging.getLogger(__name__)

CACHE_FILE = "currency_cache.json"
CACHE_TTL_SEC = 86400  # 24 hours

# Fallback values
DEFAULT_USD_TO_MDL = 17.8
DEFAULT_EUR_TO_MDL = 19.3


def _fetch_rates_from_api() -> dict:
    """Fetch USD-based rates from a free API."""
    url = "https://open.er-api.com/v6/latest/USD"
    log.info("Fetching exchange rates from open.er-api.com...")
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        raise RuntimeError("API returned failure status")
    return data["rates"]


def load_rates() -> tuple[float, float]:
    """
    Load exchange rates from cache or API.
    Returns (USD_TO_MDL, EUR_TO_MDL).
    """
    # Try to load from cache
    cache_fresh = False
    rates = {}

    if os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if time.time() - mtime < CACHE_TTL_SEC:
                with open(CACHE_FILE, encoding="utf-8") as f:
                    rates = json.load(f)
                if "MDL" in rates and "EUR" in rates:
                    cache_fresh = True
        except Exception as e:
            log.warning("Failed to read currency cache: %s", e)

    if not cache_fresh:
        try:
            api_rates = _fetch_rates_from_api()
            # Cache the standard rates
            rates = {
                "MDL": api_rates["MDL"],
                "EUR": api_rates["EUR"]
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(rates, f, indent=2)
        except Exception as e:
            log.warning("Failed to fetch fresh rates, using fallback: %s", e)
            if not rates:
                # If cache is old but exists, we can still use it as secondary fallback
                if os.path.exists(CACHE_FILE):
                    try:
                        with open(CACHE_FILE, encoding="utf-8") as f:
                            rates = json.load(f)
                    except Exception:
                        pass

            if not rates or "MDL" not in rates or "EUR" not in rates:
                rates = {"MDL": DEFAULT_USD_TO_MDL, "EUR": DEFAULT_USD_TO_MDL / DEFAULT_EUR_TO_MDL}

    usd_to_mdl = rates["MDL"]
    # open.er-api.com returns rates relative to USD.
    # 1 EUR = rates["EUR"] USD
    # 1 USD = rates["MDL"] MDL
    # 1 EUR = rates["MDL"] / rates["EUR"] MDL
    eur_to_mdl = rates["MDL"] / rates["EUR"] if rates.get("EUR") else DEFAULT_EUR_TO_MDL

    return usd_to_mdl, eur_to_mdl


# Expose loaded values
USD_TO_MDL, EUR_TO_MDL = load_rates()
log.info("Loaded exchange rates: USD/MDL = %.2f, EUR/MDL = %.2f", USD_TO_MDL, EUR_TO_MDL)

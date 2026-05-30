"""
Runtime configuration from environment (.env).
Keeps scoring.py free of I/O and side effects.
"""
import os

from dotenv import load_dotenv

from scoring import MIN_CPU_SCORE as DEFAULT_MIN_CPU_SCORE


load_dotenv()


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

GEMINI_MAX_WORKERS = max(1, _env_int("GEMINI_MAX_WORKERS", 3))
GEMINI_REQUEST_DELAY_SEC = max(0.0, _env_float("GEMINI_REQUEST_DELAY_SEC", 0.5))
GEMINI_SEARCH_DELAY_SEC = max(0.0, _env_float("GEMINI_SEARCH_DELAY_SEC", 1.5))
GEMINI_MAX_RETRIES = max(1, _env_int("GEMINI_MAX_RETRIES", 3))

ENABLE_EXTERNAL_LOOKUPS = _env_bool("ENABLE_EXTERNAL_LOOKUPS", True)

MIN_CPU_SCORE = _env_int("MIN_CPU_SCORE", DEFAULT_MIN_CPU_SCORE)
ADS_ANALYZE_LIMIT = max(1, _env_int("ADS_ANALYZE_LIMIT", 500))

PASSMARK_CACHE_DAYS = max(1, _env_int("PASSMARK_CACHE_DAYS", 7))
WORLD_PRICE_TOP_N = max(0, _env_int("WORLD_PRICE_TOP_N", 10))

# Telegram digest: how many deals per section, and an optional quality floor.
# The floor defaults to 0 so the digest always shows the top-N best deals;
# raise it to hide low value_score listings.
TELEGRAM_TOP_N = max(1, _env_int("TELEGRAM_TOP_N", 5))
TELEGRAM_MIN_VALUE_SCORE = max(0.0, _env_float("TELEGRAM_MIN_VALUE_SCORE", 0.0))

DB_NAME = os.getenv("DB_NAME", "laptops_database.db")

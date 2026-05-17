"""Small retry helper for network / API calls."""
import logging
import time
from collections.abc import Callable
from typing import TypeVar


log = logging.getLogger(__name__)

T = TypeVar("T")

_RATE_LIMIT_HINTS = ("429", "resource exhausted", "quota", "rate limit", "too many requests")


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay_sec: float = 1.0,
    label: str = "request",
) -> T:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                break
            msg = str(exc).lower()
            delay = base_delay_sec * (2**attempt)
            if any(hint in msg for hint in _RATE_LIMIT_HINTS):
                delay *= 2
            log.warning("%s failed (attempt %s/%s): %s; retry in %.1fs", label, attempt + 1, max_retries, exc, delay)
            time.sleep(delay)
    assert last_error is not None
    raise last_error

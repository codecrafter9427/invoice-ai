"""Simple in-memory rate limiter for auth and AI endpoints (portfolio-safe)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from app.core.errors import ApiError

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(
    key: str,
    *,
    limit: int,
    window_seconds: int,
    code: str = "rate_limited",
    message: str = "Too many requests — try again shortly",
) -> None:
    """Raise ApiError 429 when `key` exceeds `limit` hits in `window_seconds`."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _hits[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise ApiError(
                status_code=429,
                code=code,
                message=message,
                details={"limit": limit, "window_seconds": window_seconds},
            )
        bucket.append(now)


def reset_rate_limits() -> None:
    """Test helper — clear all buckets."""
    with _lock:
        _hits.clear()

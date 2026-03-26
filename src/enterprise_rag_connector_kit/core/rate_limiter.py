from __future__ import annotations

import logging
import time

LOGGER = logging.getLogger(__name__)


class RateLimiter:
    """
    Very small pacing helper for outbound calls.

    This is intentionally lightweight. For this exercise, we do not need a
    distributed or token-bucket implementation; we simply ensure a minimum
    spacing between requests when configured.
    """

    def __init__(self, min_interval_seconds: float = 0.0) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be >= 0.")
        self._min_interval_seconds = min_interval_seconds
        self._last_run_at: float | None = None

    def wait(self) -> None:
        if self._min_interval_seconds <= 0:
            return

        now = time.perf_counter()

        if self._last_run_at is None:
            self._last_run_at = now
            return

        elapsed = now - self._last_run_at
        remaining = self._min_interval_seconds - elapsed

        if remaining > 0:
            LOGGER.debug("Rate limiter sleeping %.3fs", remaining)
            time.sleep(remaining)

        self._last_run_at = time.perf_counter()

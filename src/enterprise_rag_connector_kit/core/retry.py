from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExecutor:
    """
    Generic retry helper for transient operations.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        backoff_jitter_seconds: float = 0.25,
        retry_on: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero.")
        if backoff_base_seconds < 0:
            raise ValueError("backoff_base_seconds must be >= 0.")
        if backoff_jitter_seconds < 0:
            raise ValueError("backoff_jitter_seconds must be >= 0.")

        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_jitter_seconds = backoff_jitter_seconds
        self._retry_on = retry_on

    def run(
        self,
        func: Callable[[], T],
        *,
        operation_name: str = "operation",
    ) -> T:
        last_error: BaseException | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                return func()
            except self._retry_on as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    LOGGER.error(
                        "Retry exhausted for %s after %s attempts: %s",
                        operation_name,
                        attempt,
                        exc,
                    )
                    raise

                sleep_seconds = self._compute_sleep_seconds(attempt)
                LOGGER.warning(
                    "Retryable failure during %s attempt %s/%s: %s. "
                    "Sleeping %.3fs before retry.",
                    operation_name,
                    attempt,
                    self._max_attempts,
                    exc,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)

        if last_error is not None:
            raise last_error

        raise RuntimeError("RetryExecutor reached an unexpected state.")

    def _compute_sleep_seconds(self, attempt: int) -> float:
        exponential_delay = self._backoff_base_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, self._backoff_jitter_seconds)
        return exponential_delay + jitter
from __future__ import annotations

import logging
import sys


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    Keeps logging simple, readable, and suitable for local execution or
    interview screen sharing. This can later be replaced with JSON logging
    if needed.
    """
    normalized_level = (log_level or "INFO").strip().upper()
    level = getattr(logging, normalized_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)


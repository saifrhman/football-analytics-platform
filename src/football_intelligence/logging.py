"""Logging configuration for platform services."""

import logging

from football_intelligence.config.settings import get_settings


def configure_logging() -> None:
    """Configure process-wide structured-enough console logging."""

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

"""Configuration du logging structure avec Rich."""

from __future__ import annotations

import logging
from typing import Any

from rich.logging import RichHandler


_LOGGING_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure le logger global une seule fois."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_level=True, show_time=True)],
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str, extra: dict[str, Any] | None = None) -> logging.LoggerAdapter:
    """Retourne un logger adapte avec contexte optionnel."""
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, extra or {})

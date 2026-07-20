"""Logging configuration using structlog with an stdlib fallback formatter."""

from __future__ import annotations

import contextlib
import logging
import sys

import structlog


def _force_utf8_streams() -> None:
    """Ensure stdout/stderr use UTF-8.

    On Windows the default console codepage (e.g. cp1251) cannot encode Cyrillic
    or box-drawing characters, which would crash any log/print containing them.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            # Platform-dependent; ignore if the stream can't be reconfigured.
            with contextlib.suppress(ValueError, OSError):  # pragma: no cover
                reconfigure(encoding="utf-8", errors="replace")


def setup_logging(level: str = "INFO", json: bool = False) -> None:
    """Configure structlog + stdlib logging for the whole application.

    Args:
        level: Root log level name (e.g. ``"INFO"``, ``"DEBUG"``).
        json: When True, emit machine-readable JSON logs (useful in production).
    """
    _force_utf8_streams()
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if json
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (used by aiogram / SQLAlchemy) through the same level.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )
    # aiohttp access logs are noisy; keep them at WARNING.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)

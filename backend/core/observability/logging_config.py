"""
Structured logging configuration for AFianco backend.

Two output formats supported, opt-in via LOG_FORMAT env var:

    LOG_FORMAT=text  (default in development)
        Plain text with [cid=...] tag.  Backward compatible with the
        existing format produced by services/correlation_context.py
        install_correlation_id_logging().

    LOG_FORMAT=json  (recommended in production)
        Each log record is a single JSON line containing:
            ts, level, logger, msg, request_id, user_id, org_id,
            and any extra fields passed via logger.X(..., extra={...}).
        Parsable by Loki / Datadog / ELK without regex.

Design notes:
    - We must NOT clobber the existing CorrelationIdFilter installed by
      install_correlation_id_logging() — extending its formatter, not
      replacing the filter, keeps Stripe webhook correlation working.
    - python-json-logger is a small, stable dependency; we feature-detect
      it so the app boots even if the package is missing (LOG_FORMAT=json
      falls back to text with a warning).
    - init_logging is idempotent: repeated calls are safe.
"""
import logging
import os
import sys
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def _build_text_formatter() -> logging.Formatter:
    """
    Backward-compat text formatter mirroring the format produced by
    install_correlation_id_logging() in services/correlation_context.py.
    """
    fmt = (
        "%(asctime)s - %(name)s - %(levelname)s "
        "[cid=%(correlation_id)s] - %(message)s"
    )
    return logging.Formatter(fmt)


def _build_json_formatter() -> logging.Formatter:
    """
    JSON formatter using python-json-logger if available, else falls back
    to text with a warning logged once.
    """
    try:
        from pythonjsonlogger import jsonlogger
    except ImportError:
        logger.warning(
            "LOG_FORMAT=json requested but python-json-logger is not installed; "
            "falling back to text formatter. Add to requirements: python-json-logger>=2.0.7"
        )
        return _build_text_formatter()

    class AfiancoJsonFormatter(jsonlogger.JsonFormatter):
        """Add per-request context fields and standardize field names."""

        def add_fields(
            self,
            log_record: dict,
            record: logging.LogRecord,
            message_dict: Mapping[str, Any],
        ) -> None:
            super().add_fields(log_record, record, message_dict)
            # Standardize timestamp to ISO 8601 UTC (replaces non-portable
            # "asctime" key from default formatter).
            log_record["ts"] = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
            log_record["level"] = record.levelname
            log_record["logger"] = record.name

            # request_id from CorrelationIdFilter (already attached as attr).
            # Falls back to "-" sentinel when no request context is active.
            log_record["request_id"] = getattr(record, "correlation_id", "-")

            # user_id / org_id are populated lazily on demand from ContextVars
            # so this works whether or not the request_context middleware
            # has run (e.g. background tasks / lifespan hooks).
            from core.observability.request_context import (
                get_user_id,
                get_org_id,
            )
            uid = get_user_id()
            oid = get_org_id()
            if uid is not None:
                log_record["user_id"] = uid
            if oid is not None:
                log_record["org_id"] = oid

            # Drop noisy/duplicate keys from the default JSON output.
            for legacy_key in ("asctime", "message"):
                log_record.pop(legacy_key, None)
            log_record["msg"] = record.getMessage()

    # Format string here selects which RECORD fields are emitted by the base
    # formatter; add_fields above adds custom ones on top.
    return AfiancoJsonFormatter("%(message)s")


def init_logging() -> str:
    """
    Initialize logging based on LOG_FORMAT env var.

    Returns the active format ("text" or "json") for diagnostic logging.
    Idempotent: re-running replaces the existing handler formatters.
    """
    raw = os.getenv("LOG_FORMAT", "text").strip().lower()
    fmt = "json" if raw == "json" else "text"

    if fmt == "json":
        formatter = _build_json_formatter()
    else:
        formatter = _build_text_formatter()

    root = logging.getLogger()

    # AGGRESSIVE STRATEGY (Phase 1 Step A3 — production hardening):
    # gunicorn worker boot installs its own root handler with a plain
    # `%(message)s` Formatter, AFTER server.py finishes importing. Naively
    # calling setFormatter on existing handlers therefore loses the race in
    # production. Instead we wipe root.handlers and install a single fresh
    # StreamHandler with our formatter + CorrelationIdFilter. This is the
    # ONLY pattern that survives both:
    #   1. import-time invocation (no handlers yet)
    #   2. lifespan re-invocation (gunicorn handlers already installed)
    #
    # Side effects:
    #   - gunicorn's "access logfile" goes through `gunicorn.access` logger
    #     (separate from root), so removing root handlers does NOT affect
    #     access logging.
    #   - uvicorn / FastAPI emit via `uvicorn.error` and `uvicorn.access`
    #     loggers which have their own handlers — same story, untouched.
    for h in list(root.handlers):
        root.removeHandler(h)

    new_handler = logging.StreamHandler(sys.stdout)
    new_handler.setFormatter(formatter)

    # Install CorrelationIdFilter so format strings referencing
    # `%(correlation_id)s` (text formatter) never KeyError. Also feeds the
    # JSON formatter via getattr.
    from services.correlation_context import CorrelationIdFilter
    new_handler.addFilter(CorrelationIdFilter())

    root.addHandler(new_handler)

    # Default log level: INFO. Honor LOG_LEVEL env var if set (DEBUG/WARNING/ERROR).
    level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    if level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        root.setLevel(getattr(logging, level))

    logger.info("Logging initialized: format=%s, level=%s", fmt, level)
    return fmt

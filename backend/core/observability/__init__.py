"""
Observability module for AFianco backend.

Public API:
    init_sentry()  — initialize Sentry SDK (Step A1)
    init_logging() — configure structured/text logging (Step A3)
    Request context helpers:
        get_request_id, get_user_id, get_org_id
        set_user_id, set_org_id (called by auth dependencies)

Components (each opt-in via dedicated env var):
    - Sentry SDK         (SENTRY_DSN)        — Step A1
    - Structured logging (LOG_FORMAT)        — Step A3
    - Prometheus metrics (always-on)         — Phase 0 Step 10

Each component is fail-safe: missing env var / dependency → component
disabled, app continues.
"""
from .sentry import init_sentry
from .logging_config import init_logging
from .request_context import (
    new_correlation_id,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    set_user_id,
    get_user_id,
    clear_user_id,
    set_org_id,
    get_org_id,
    clear_org_id,
    get_request_id,
)
from . import metrics

__all__ = [
    "init_sentry",
    "init_logging",
    "new_correlation_id",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "set_user_id",
    "get_user_id",
    "clear_user_id",
    "set_org_id",
    "get_org_id",
    "clear_org_id",
    "get_request_id",
    "metrics",
]

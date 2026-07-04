"""
ai_service.py — Backward-compatible facade.

Phase 2: internals split into:
  - ai_analytics_service.py  (data aggregation / metrics)
  - ai_insight_service.py    (LLM calls / insight construction)

All symbols that were previously imported from this module are
re-exported here unchanged, so no existing caller needs to be updated.
"""
from typing import Optional

# Re-export public API — zero breaking change for any existing import
from services.ai_analytics_service import get_analytics_summary, _get_date_range as get_date_range
from services.ai_insight_service import generate_cashflow_insight

__all__ = [
    "get_date_range",
    "get_analytics_summary",
    "generate_cashflow_insight",
]

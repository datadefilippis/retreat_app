"""Template loader — locale-aware, no I/O at request time.

Templates live in this directory as JSON files keyed by template name.
Each file holds the four locales (it/en/de/fr) so a missing translation
is impossible; we'd fail at load time, not at click time.

Layout::

    templates/library.json
        {
          "at_risk_followup": {
            "it": {"subject": "...", "body": "Ciao {customer_name}, ..."},
            "en": {...},
            "de": {...},
            "fr": {...}
          },
          "new_welcome": {...},
          "top_personal_note": {...},
          ...
        }

Variables available for ``{...}`` interpolation:
  • {customer_name}      — display name from the Customer record
  • {merchant_name}      — set by the caller (org.name)
  • {days_since_last}    — int, optional, only at-risk templates use it

The loader caches the parsed file at module level; live edits during
development require an explicit ``reload_templates()`` call.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


_TEMPLATES_PATH = Path(__file__).resolve().parent / "library.json"
_cache: Optional[dict] = None


def _load_from_disk() -> dict:
    if not _TEMPLATES_PATH.exists():
        logger.error("customer_outreach.templates: library.json missing at %s", _TEMPLATES_PATH)
        return {}
    try:
        return json.loads(_TEMPLATES_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(
            "customer_outreach.templates: parse error on library.json: %s", exc,
        )
        return {}


def _ensure_loaded() -> dict:
    global _cache
    if _cache is None:
        _cache = _load_from_disk()
    return _cache


def reload_templates() -> int:
    """Force reload of the templates library. Returns # of templates."""
    global _cache
    _cache = _load_from_disk()
    return len(_cache)


def list_templates(locale: str = "it") -> list[dict]:
    """Return ``[{key, subject_preview, body_preview}, ...]`` for the
    locale picker UI. Falls back to ``it`` for keys missing the
    requested locale."""
    lib = _ensure_loaded()
    out: list[dict] = []
    for key in sorted(lib.keys()):
        entry = lib[key]
        loc = entry.get(locale) or entry.get("it") or {}
        out.append({
            "key": key,
            "subject_preview": (loc.get("subject") or "")[:80],
            "body_preview": (loc.get("body") or "")[:120],
        })
    return out


def render(
    template_key: str,
    locale: str,
    *,
    customer_name: str,
    merchant_name: str = "",
    days_since_last: Optional[int] = None,
) -> Optional[dict]:
    """Render a template into ``{"subject": str, "body": str}``.

    Falls back to ``it`` when the key exists but the requested locale
    is missing. Returns None if the template_key is unknown — caller
    is expected to surface a useful error to the merchant.

    All ``{...}`` placeholders that aren't supplied here render as the
    empty string. We use ``str.format_map`` with a default-empty dict
    rather than ``str.format`` so a future placeholder addition doesn't
    crash existing templates.
    """
    lib = _ensure_loaded()
    entry = lib.get(template_key)
    if not entry:
        logger.info("customer_outreach.templates: unknown template_key=%r", template_key)
        return None

    loc = entry.get(locale) or entry.get("it")
    if not loc:
        return None

    ctx = _DefaultDict({
        "customer_name": customer_name,
        "merchant_name": merchant_name,
        "days_since_last": str(days_since_last) if days_since_last is not None else "",
    })

    try:
        subject = (loc.get("subject") or "").format_map(ctx)
        body = (loc.get("body") or "").format_map(ctx)
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning(
            "customer_outreach.templates: render failed for %s/%s: %s",
            template_key, locale, exc,
        )
        return None

    return {"subject": subject, "body": body}


class _DefaultDict(dict):
    """``str.format_map`` helper: missing keys → empty string."""

    def __missing__(self, key):
        return ""

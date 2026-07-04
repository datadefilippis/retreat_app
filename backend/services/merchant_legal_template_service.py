"""Merchant legal template service — Wave GDPR-Commerce Phase CG-1.

Renders a generic Privacy Policy or Terms of Service draft pre-filled
with the merchant's own data, for the merchant to then EDIT and publish
on their storefront.

The templates live as Markdown files under::

    backend/legal/merchant_templates/<doc_type>_<locale>.template.md

with ``{{variable}}`` placeholders. Variable interpolation is
intentionally simple (string replace, no Jinja2 / no eval) so:

  · merchants who edit the rendered output don't accidentally
    re-trigger interpolation
  · we can't accidentally template-inject attacker-controlled fields
  · no new dependency

The template style is deliberately CAUTIOUS:
  · every section the average merchant might need is present
  · sections that depend on a vars flag (``uses_marketing``,
    ``collects_shipping_address`` …) are present unconditionally but
    contain a soft "Se applicabile: …" note the merchant can delete
  · NO legal-jurisdiction promises beyond what we can stand behind
    (the merchant is the Data Controller; we say so explicitly)

Public API
==========
``render_template(doc_type, locale, vars) -> str``

Where ``vars`` is a TemplateVars Pydantic model (validated upstream).
Missing string vars render as the literal placeholder so the merchant
can spot what was not filled.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


SUPPORTED_LOCALES = ("it", "en", "de", "fr")
SUPPORTED_DOC_TYPES = ("privacy", "terms")

_TEMPLATE_DIR = (
    Path(__file__).resolve().parent.parent / "legal" / "merchant_templates"
)


class TemplateVars(BaseModel):
    """Variables interpolated into the merchant template.

    All string fields are required-but-empty-ok: an empty string renders
    as the literal placeholder so the merchant can spot it in the
    editor. Boolean flags drive the soft "Se applicabile" annotations.
    """

    # Identity of the controller (the merchant)
    merchant_name: str = Field(default="", max_length=255)
    merchant_email: str = Field(default="", max_length=255)
    merchant_country: str = Field(default="", max_length=100)
    store_name: str = Field(default="", max_length=255)
    store_country: str = Field(default="", max_length=100)

    # Data-collection flags — drive conditional notes in the template
    collects_phone: bool = False
    collects_shipping_address: bool = False
    uses_marketing: bool = False
    ships_to_eu: bool = False

    # The platform processor identifier — kept as a var so the same
    # template stays usable if afianco ever rebrands.
    platform_name: str = Field(default="afianco", max_length=64)
    platform_controller_name: str = Field(
        default="Davide De Filippis", max_length=255
    )
    platform_controller_email: str = Field(
        default="davide@afianco.ch", max_length=255
    )
    platform_controller_country: str = Field(
        default="Switzerland", max_length=100
    )


# ─── Internal helpers ────────────────────────────────────────────────────


_PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


def _read_template(doc_type: str, locale: str) -> str:
    """Load the raw template markdown for (doc_type, locale).

    Raises FileNotFoundError if the file is missing; the caller treats
    that as a 500 (template missing is a deployment bug, not a user
    error).
    """
    path = _TEMPLATE_DIR / f"{doc_type}_{locale}.template.md"
    return path.read_text(encoding="utf-8")


def _interpolate(template: str, vars_obj: TemplateVars) -> str:
    """Replace ``{{var}}`` occurrences with the corresponding value.

    Unknown placeholders are left as-is (the merchant will see the
    placeholder text and can fill or delete it manually). Boolean values
    render as the language-neutral string "True"/"False" — they are
    intended for use in the soft-conditional notes, not for raw display.
    """
    data = vars_obj.model_dump()

    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key in data:
            v = data[key]
            if v is None:
                return m.group(0)
            if isinstance(v, bool):
                return "True" if v else "False"
            return str(v)
        return m.group(0)

    return _PLACEHOLDER_RE.sub(repl, template)


# ─── Public API ──────────────────────────────────────────────────────────


def render_template(
    doc_type: Literal["privacy", "terms"],
    locale: Literal["it", "en", "de", "fr"],
    vars: TemplateVars,
) -> str:
    """Render a merchant legal draft for the given doc + locale.

    Raises:
        ValueError on invalid doc_type or locale
        FileNotFoundError if the template file is missing on disk
            (deployment bug — caller should bubble to 500)
    """
    if doc_type not in SUPPORTED_DOC_TYPES:
        raise ValueError(
            f"Invalid doc_type {doc_type!r}; allowed: {SUPPORTED_DOC_TYPES}"
        )
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(
            f"Invalid locale {locale!r}; allowed: {SUPPORTED_LOCALES}"
        )

    raw = _read_template(doc_type, locale)
    return _interpolate(raw, vars)


def list_template_files() -> list[Path]:
    """Return the absolute paths of all template files present on disk.

    Used by the sentinel test to assert the full 4×2 matrix is shipped.
    """
    if not _TEMPLATE_DIR.is_dir():
        return []
    return sorted(_TEMPLATE_DIR.glob("*.template.md"))

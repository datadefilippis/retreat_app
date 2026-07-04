"""
Shared locale utilities for AI-generated content.

Maps supported locale codes to language-specific instructions for AI prompts:
  - language name (for "respond in …" directives)
  - number formatting guidance (decimal / thousands separators)
  - currency placement convention

Used by chat_service, and eventually by commerce_signals, health
explanations, alert analysis, and digest builders.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class LocaleProfile:
    """AI-facing locale metadata (not for UI — see i18n frontend)."""

    code: str
    language_name: str          # e.g. "italiano", "English"
    respond_instruction: str    # e.g. "Rispondi SOLO in italiano"
    number_format_hint: str     # e.g. "1.500,00 EUR"
    date_format_hint: str       # e.g. "gg/mm/aaaa"


_PROFILES: Dict[str, LocaleProfile] = {
    "it": LocaleProfile(
        code="it",
        language_name="italiano",
        respond_instruction="Rispondi SOLO in italiano",
        number_format_hint="formato europeo (es. 1.500,00 EUR)",
        date_format_hint="gg/mm/aaaa",
    ),
    "en": LocaleProfile(
        code="en",
        language_name="English",
        respond_instruction="Respond ONLY in English",
        number_format_hint="standard format (e.g. 1,500.00 EUR)",
        date_format_hint="YYYY-MM-DD",
    ),
    "de": LocaleProfile(
        code="de",
        language_name="Deutsch",
        respond_instruction="Antworte NUR auf Deutsch",
        number_format_hint="europaeisches Format (z.B. 1.500,00 EUR)",
        date_format_hint="TT.MM.JJJJ",
    ),
    "fr": LocaleProfile(
        code="fr",
        language_name="francais",
        respond_instruction="Reponds UNIQUEMENT en francais",
        number_format_hint="format europeen (ex. 1 500,00 EUR)",
        date_format_hint="JJ/MM/AAAA",
    ),
}

DEFAULT_LOCALE = "it"


def get_locale_profile(locale: str) -> LocaleProfile:
    """Return the LocaleProfile for *locale*, falling back to Italian."""
    return _PROFILES.get(locale, _PROFILES[DEFAULT_LOCALE])


def get_supported_locale_codes() -> list[str]:
    """Return the list of locale codes that have AI profiles."""
    return list(_PROFILES.keys())

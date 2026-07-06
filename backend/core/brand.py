"""Brand della piattaforma — AURYA (deciso 11/7/2026, dominio aurya.life).

FONTE UNICA lato backend (gemello di frontend/src/config/brand.js).
Email, export, OpenAPI, copy: tutto legge da qui — il rebrand futuro
(se mai) è una modifica a UN file. I default sono overridabili via env
per staging/dev.
"""

import os

BRAND_NAME = os.environ.get("BRAND_NAME", "Aurya")
BRAND_DOMAIN = os.environ.get("BRAND_DOMAIN", "aurya.life")

# Mittenti email transazionali (autenticati via SPF/DKIM su Brevo)
BRAND_FROM_EMAIL = os.environ.get("BRAND_FROM_EMAIL", f"noreply@{BRAND_DOMAIN}")
BRAND_FROM_NAME = os.environ.get("BRAND_FROM_NAME", BRAND_NAME)
BRAND_SUPPORT_EMAIL = os.environ.get("BRAND_SUPPORT_EMAIL", f"info@{BRAND_DOMAIN}")

# Tagline nelle 4 lingue (footer email + copy istituzionale)
BRAND_TAGLINE = {
    "it": "Ritiri ed esperienze olistiche, in un posto solo.",
    "en": "Holistic retreats and experiences, all in one place.",
    "de": "Holistische Retreats und Erlebnisse, an einem Ort.",
    "fr": "Retraites et expériences holistiques, au même endroit.",
}

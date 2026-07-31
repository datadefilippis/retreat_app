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

# HP1 (31/7/2026) — il PAYOFF sostituisce il vecchio motto in tre
# parole su ogni superficie (email, meta, social). E' una legge del mondo, non
# una descrizione di Aurya: dice che l'oggetto della fiducia e' la
# persona, non la piattaforma (docs/BRAND_HOME_AURYA_2026-07.md §2).
# A differenza del vecchio motto SI TRADUCE.
BRAND_PAYOFF = {
    "it": "Ci si fida di qualcuno, non di qualcosa.",
    "en": "Trust is placed in someone, not something.",
    "de": "Man vertraut jemandem, nicht etwas.",
    "fr": "On fait confiance à quelqu'un, pas à quelque chose.",
}

# Tagline nelle 4 lingue (footer email + copy istituzionale).
# AN1 — allineate a docs/BRAND_AURYA.md: oneste ("in Italia") e con la
# promessa (caparra protetta), non generiche.
# RB4 — nessuna geografia imposta (si parte da Italia e Svizzera, ma
# le esperienze che trasformano non hanno confini) e zero trattini.
BRAND_TAGLINE = {
    "it": "Trova e prenota ritiri olistici ed esperienze per evolvere. Con caparra protetta, senza pensieri.",
    "en": "Find and book holistic retreats and experiences that help you grow. With a protected deposit, worry free.",
    "de": "Finde und buche holistische Retreats und Erlebnisse, die dich wachsen lassen. Mit geschützter Anzahlung, sorgenfrei.",
    "fr": "Trouvez et réservez des retraites holistiques et des expériences qui vous font grandir. Avec un acompte protégé, l'esprit tranquille.",
}

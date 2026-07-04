"""Tassonomia categorie ritiri (Fase 5) — fonte unica backend.

Le chiavi sono slug stabili (URL /ritiri/{categoria}); le label le
risolve il frontend (i18n). Mappabile sulle 9 categorie SIAF.
"""

RETREAT_CATEGORIES = {
    "yoga": "Yoga",
    "meditazione": "Meditazione & Mindfulness",
    "detox": "Detox & Digiuno",
    "suono": "Suono & Sound Healing",
    "massaggio": "Massaggio & Bodywork",
    "breathwork": "Breathwork",
    "cammini": "Cammini & Natura",
    "femminile": "Cerchi & Femminile",
    "aziendale": "Benessere aziendale",
}

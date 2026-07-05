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


# V4 (5/7/2026) — tassonomie per gli ALTRI tipi prodotto (decise dal
# founder): dropdown nei wizard, MAI testo libero. Le chiavi sono slug
# stabili; le label le risolve il frontend (i18n) con questi default.
PRODUCT_TAXONOMIES = {
    "service": {
        "trattamenti": "Trattamenti & Massaggi",
        "consulenze": "Consulenze",
        "lezioni": "Lezioni private",
        "cerimonie": "Cerimonie",
    },
    "physical": {
        "cura_di_se": "Cura di sé",
        "casa_benessere": "Casa & Benessere",
        "cibo_tisane": "Cibo & Tisane",
        "abbigliamento": "Abbigliamento",
        "artigianato": "Artigianato",
    },
    "digital": {
        "guide_ebook": "Guide & E-book",
        "audio_meditazioni": "Audio & Meditazioni",
        "video": "Video",
    },
}

"""Frequenze by Aurya — basi sonore curate (FQ2, 18/8/2026).

La libreria e' DELLA PIATTAFORMA: carica solo il system admin, con
licenza annotata (CC0 o licenziata — mai materiale di terzi senza
diritti). L'operatore le sceglie, non ne carica di sue (decisione
founder 18/8). I byte vivono su disco in uploads/audio/, mai in Mongo.
"""

SOUND_CATEGORIES = {
    "ambient": "Ambient",
    "droni": "Droni",
    "campane": "Campane",
    "natura": "Natura",
    "ritmi": "Ritmi",
    "voce": "Voce",
}

ALLOWED_EXTENSIONS = {"mp3", "m4a", "ogg", "wav"}
ALLOWED_MIME_PREFIXES = ("audio/",)
MAX_FILE_BYTES = 60 * 1024 * 1024   # 60MB: una base da ~30 min in mp3
TITLE_MAX = 80
LICENSE_MAX = 300


def clean_category(raw):
    return raw if raw in SOUND_CATEGORIES else None


def safe_extension(filename: str):
    """Estensione consentita del file, o None."""
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return ext if ext in ALLOWED_EXTENSIONS else None

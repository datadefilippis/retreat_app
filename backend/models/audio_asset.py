"""Frequenze by Aurya — basi sonore curate (FQ2, 18/8/2026).

La libreria e' DELLA PIATTAFORMA: carica solo il system admin, con
licenza annotata (CC0 o licenziata — mai materiale di terzi senza
diritti). L'operatore le sceglie, non ne carica di sue (decisione
founder 18/8). I byte vivono su disco in uploads/audio/, mai in Mongo.
"""

# SL (20/8): l'ordine e' quello dei tab in Esplora → Suoni, dal letto
# piu' comune al dettaglio piu' raro. `corpo` e' la serie dalla radice
# alla testa; `transizioni` sono i passaggi brevi tra due momenti.
# Il frontend tiene la stessa lista (guardia di parita' nei test).
SOUND_CATEGORIES = {
    "ambient": "Ambient",
    "natura": "Natura",
    "droni": "Droni",
    "corpo": "Corpo",
    "campane": "Campane",
    "ritmi": "Ritmi",
    "voce": "Voce",
    "transizioni": "Transizioni",
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

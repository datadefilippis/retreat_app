"""Lo specchio server del Catalogo Aurya Core (S2, 26/8/2026).

Il catalogo VERO e' frontend/src/features/frequenze/pro/catalogo.js:
contenuto editoriale in git, con le schede oneste. Il server pero'
deve poter APRIRE UNA SESSIONE su un protocollo core — e per farlo
gli bastano i METADATI: quali id esistono, che titolo hanno, quale
versione, quanto durano. Le ricette NON si specchiano: qui non c'e'
un solo layer, e non deve mai essercene uno.

Perche' per i protocolli core la sessione NON porta lo snapshot dello
score (a differenza di quelli dell'operatore): il catalogo e'
versionato in git — «calm, versione 1» e' un riferimento COMPLETO e
immutabile, riproducibile per sempre dal repository. Lo snapshot
serve dove il documento puo' cambiare sotto i piedi (sound_protocols,
in Mongo), non dove la storia e' il version control.

La parita' con catalogo.js e' sotto guardia nei test S2: id, titolo,
versione e durata devono coincidere — se una scheda cambia la' e
questo specchio resta indietro, la suite rompe prima che una sessione
registri un riferimento sbagliato.
"""

# id → (titolo, versione, durata_sec)
CATALOGO_CORE = {
    "calm":        ("CALM",        1, 360),
    "respiro":     ("RESPIRO",     1, 600),
    "ground":      ("GROUND",      1, 480),
    "rilassare":   ("Rilassare",   1, 1200),
    "dormire":     ("Dormire",     1, 1200),
    "meditare":    ("Meditare",    1, 1200),
    "elaborare":   ("Elaborare",   1, 1200),
    "concentrare": ("Concentrare", 1, 1200),
    "energizzare": ("Energizzare", 1, 1200),
}


def protocollo_core(protocollo_id):
    """(titolo, versione, durata_sec) oppure None se non esiste."""
    return CATALOGO_CORE.get(protocollo_id)


# ── M2 (26/8) — lo specchio dei PERCORSI ────────────────────────────
# Il percorso vero e' frontend/.../pro/percorsi.js (contenuto
# editoriale in git). Al server servono solo i metadati per validare
# una sessione che dichiara «tappa N del percorso X»: quali percorsi
# esistono, quante tappe hanno, quale protocollo suona ogni tappa.
# Le note editoriali NON si specchiano. Parita' sotto guardia (test
# M2, eseguendo percorsi.js in Node).
#
# id → (titolo, [protocollo_id di ogni tappa, in ordine])
PERCORSI_CORE = {
    "radicamento": ("Radicamento",
                    ["ground", "rilassare", "ground", "ground",
                     "rilassare", "ground", "ground", "ground"]),
    "verso-il-sonno": ("Verso il sonno",
                       ["rilassare", "rilassare", "dormire", "dormire",
                        "rilassare", "dormire"]),
    "spazio-di-calma": ("Spazio di calma",
                        ["calm", "calm", "rilassare", "calm",
                         "rilassare", "calm"]),
}


def percorso_core(percorso_id):
    """(titolo, tappe) oppure None se non esiste."""
    return PERCORSI_CORE.get(percorso_id)

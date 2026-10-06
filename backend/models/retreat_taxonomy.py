"""Tassonomia categorie ritiri (Fase 5) — fonte unica backend.

Le chiavi sono slug stabili (URL /ritiri/{categoria}); le label le
risolve il frontend (i18n). Mappabile sulle 9 categorie SIAF.
"""

# TX (10/9/2026 sera, founder: «le categorie dei ritiri sono complete
# come quelle del profilo? serve integrazione per essere consistenti»).
# Prima erano nove, e chi cercava un ritiro sceglieva fra QUATTORDICI vie
# (routers/subscribers.EXPERIENCE_INTERESTS, la landing /cerca-ritiro):
# sei vie (reiki, costellazioni, astrologia, ayurveda, tantra, crescita)
# non esistevano come categoria, quindi «ti scriviamo quando c'e' un
# ritiro sulle tue vie» non poteva funzionare per quelle. Ora la
# tassonomia dei ritiri E' l'elenco delle vie (meno «misto», che e' una
# preferenza, non una categoria) piu' massaggio e aziendale (esistono
# come ritiri, nessuno li «cerca» come via). Le discipline del profilo
# (models/disciplines, 40 voci) si mappano qui sotto: il wizard
# suggerisce la categoria coerente con quello che l'operatore pratica.
RETREAT_CATEGORIES = {
    "yoga": "Yoga",
    "meditazione": "Meditazione & Mindfulness",
    "breathwork": "Breathwork",
    "suono": "Suono & Sound Healing",
    "reiki": "Reiki & Pratiche energetiche",
    "costellazioni": "Costellazioni familiari",
    "astrologia": "Astrologia & Tarocchi",
    "ayurveda": "Ayurveda & Discipline orientali",
    "tantra": "Tantra & Relazioni",
    "detox": "Detox & Digiuno",
    "cammini": "Cammini & Natura",
    "femminile": "Cerchi & Femminile",
    "crescita": "Crescita personale",
    "massaggio": "Massaggio & Bodywork",
    "aziendale": "Benessere aziendale",
}

# disciplina del profilo (models/disciplines) → categoria di ritiro.
# Ogni disciplina ha una casa; la prima disciplina dichiarata decide il
# suggerimento nel wizard (categoria_suggerita).
DISCIPLINA_TO_CATEGORIA = {
    # corpo & movimento
    "yoga": "yoga", "pilates": "yoga", "tai-chi": "yoga", "qi-gong": "yoga",
    "danzaterapia": "crescita", "bioenergetica": "crescita", "feldenkrais": "yoga",
    "biodanza": "crescita", "danze-sacre": "femminile", "allineamento": "yoga",
    # meditazione & mente
    "meditazione": "meditazione", "mindfulness": "meditazione", "breathwork": "breathwork",
    "training-autogeno": "meditazione", "ipnosi": "meditazione", "mind-movie": "meditazione", "regressione-vite-passate": "meditazione",
    # massaggio & bodywork
    "massaggio": "massaggio",
    "massaggio-olistico": "massaggio", "shiatsu": "massaggio", "massaggio-ayurvedico": "ayurveda",
    "massaggio-thai": "massaggio", "riflessologia": "massaggio", "craniosacrale": "massaggio",
    "linfodrenaggio": "massaggio", "hot-stone": "massaggio",
    # energia & vibrazione
    "reiki": "reiki", "pranoterapia": "reiki", "cristalloterapia": "reiki", "pulizia-energetica": "reiki",
    "allineamento-chakra": "reiki", "lavoro-energetico-chakra": "reiki",
    "sound-healing": "suono", "theta-healing": "reiki", "access-bars": "reiki", "kinesiologia": "reiki",
    # natura & rimedi
    "naturopatia": "detox", "aromaterapia": "detox", "floriterapia": "detox", "erboristeria": "detox",
    "alimentazione-olistica": "detox", "bagni-di-bosco": "cammini", "consulenza-ayurvedica": "ayurveda",
    # psicologia & psicoterapia (24/9)
    "psicologia": "crescita", "psicoterapia": "crescita",
    "sostegno-psicologico": "crescita", "psicologia-perinatale": "femminile",
    # anima & percorsi interiori
    "costellazioni-familiari": "costellazioni", "counseling-olistico": "crescita",
    "counseling-gestalt": "crescita",
    "percorsi-spirituali": "crescita", "crescita-personale": "crescita", "crescita-spirituale": "crescita",
    "coaching-olistico": "crescita", "cerchi-di-donne": "femminile", "sacro-femminile": "femminile",
    "sciamanesimo": "crescita", "astrologia": "astrologia", "numerologia": "astrologia",
    "tarocchi-evolutivi": "astrologia",
}


def categoria_suggerita(discipline) -> str | None:
    """La categoria di ritiro coerente con le discipline del profilo
    (la prima dichiarata che ha una casa), o None."""
    for d in discipline or []:
        c = DISCIPLINA_TO_CATEGORIA.get(d)
        if c:
            return c
    return None


# V4 (5/7/2026) — tassonomie per gli ALTRI tipi prodotto (decise dal
# founder): dropdown nei wizard, MAI testo libero. Le chiavi sono slug
# stabili; le label le risolve il frontend (i18n) con questi default.
PRODUCT_TAXONOMIES = {
    # Formati di EROGAZIONE, non discipline (quelle vivono in
    # models/disciplines.py): due assi complementari — la disciplina dice
    # cosa pratichi, il formato come lo si compra. Volutamente minimale.
    # Slug storici invariati (righe già create), label riallineate 16/8.
    "service": {
        "trattamenti": "Trattamenti individuali",
        "consulenze": "Consulenze & Colloqui",
        "lezioni": "Lezioni private",
        "corsi-gruppo": "Classi & Corsi di gruppo",
        "cerimonie": "Cerimonie & Cerchi",
        "percorsi": "Percorsi & Pacchetti",
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


# P4 «formato» (6/10/2026, founder: «formazione non sostituisce la
# disciplina yoga, meditazione… ci dovrebbe essere un campo nuovo che
# indica una seconda categoria: evento, ritiro, formazione»). Fino a oggi
# l'unico asse di un'esperienza con una data era la disciplina (sopra) e
# la pagina chiamava tutto «ritiro» per convenzione. Il formato e' il
# secondo asse, ORTOGONALE alla disciplina: dice che cosa e' (un ritiro
# di piu' giorni, un evento di un giorno, una formazione), non di che
# cosa parla. Vive in product.metadata.formato degli event_ticket,
# facoltativo: le righe nate prima restano senza e si mostrano come
# prima (nessun backfill automatico; la mappatura delle esperienze gia'
# in produzione la fa la regia con scripts/formato_esperienze.py).
FORMATI_ESPERIENZA = {
    "ritiro": "Ritiro",
    "evento": "Evento",
    "formazione": "Formazione",
}

# Etichette al plurale per il filtro «Tipo» di /esperienze.
FORMATI_ESPERIENZA_PLURALE = {
    "ritiro": "Ritiri",
    "evento": "Eventi",
    "formazione": "Formazione",
}


def errore_formato(metadata) -> "str | None":
    """Il messaggio d'errore se metadata.formato c'e' ed e' fuori lista,
    altrimenti None. Assente o None = valido (riga senza formato). Usata
    dal wizard eventi e dal PATCH prodotto: validate_metadata_for_type
    non alza mai e conserva i valori grezzi, quindi senza questo controllo
    un formato inventato finirebbe in archivio."""
    if not isinstance(metadata, dict) or metadata.get("formato") is None:
        return None
    if metadata["formato"] not in FORMATI_ESPERIENZA:
        return ("Formato non valido. Scegli fra: "
                + ", ".join(FORMATI_ESPERIENZA.values()).lower() + ".")
    return None


def formato_suggerito(start_at: "str | None", end_at: "str | None") -> str:
    """Il suggerimento del wizard (anche lato server, per lo script di
    mappatura): piu' giorni → ritiro, un giorno → evento. La formazione
    non si indovina dalle date: la dichiara chi la tiene."""
    s = (start_at or "")[:10]
    e = (end_at or "")[:10]
    return "ritiro" if (s and e and e > s) else "evento"

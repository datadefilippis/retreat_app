"""SEO shell — HTML pubblico con meta server-side (S0.2, SEO_MASTER_PLAN).

PROBLEMA: la SPA (CRA) inietta title/meta/OG/JSON-LD via JavaScript.
Google renderizza, ma Bing e gli scraper social (WhatsApp, Instagram,
LinkedIn, iMessage) leggono SOLO l'HTML iniziale: ogni condivisione di
un ritiro usciva senza titolo né anteprima.

SOLUZIONE: il reverse proxy instrada le route PUBBLICHE qui; questo
router serve l'index.html della build con title/meta/OG/canonical/
JSON-LD già iniettati per QUELLA route, calcolati dagli stessi dati
delle API pubbliche. Il JS poi idrata come sempre (useSeoMeta resta il
driver della navigazione SPA). Stesso HTML per bot e umani: nessun
cloaking.

Config:
  SEO_SHELL_INDEX_PATH  sorgente dell'index.html della build:
                        - path su disco (default dev: ../frontend/build/
                          index.html) → riletto quando cambia (mtime);
                        - URL http(s):// (deploy Docker split-container:
                          il backend legge l'index dal container frontend,
                          es. http://frontend/index.html) → cache TTL.
  PUBLIC_APP_URL        base URL assoluta per canonical/OG

Proxy (Caddy) — vedi docs/DEPLOY_CHECKLIST.md:
  route pubbliche (/, /ritiri*, /e/*, /p/*, /ph/*, /dg/*, /co/*, /r/*,
  /o/*, /s/*) → backend /__seo/<path>; il resto degli asset → build.

Cache: per-URL, TTL 10 minuti (i contenuti cambiano al ritmo dei
publish, non dei click).
"""

import html as _html
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Response

from core.prelaunch import prelaunch_mode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/__seo", tags=["SEO shell"])

_CACHE: dict = {}          # path → (html, monotonic_ts)
_CACHE_TTL = 600
_INDEX_CACHE: dict = {"html": None, "mtime": None}
# Deploy Docker: l'index vive nel container frontend, letto via HTTP e
# ricontrollato ogni _INDEX_HTTP_TTL secondi (un redeploy riavvia il
# backend e svuota comunque la cache).
_INDEX_HTTP_TTL = 300

# Template minimo per dev/test quando la build non esiste: la shell è
# testabile senza `pnpm build`.
_DEV_TEMPLATE = (
    "<!DOCTYPE html><html lang=\"it\"><head><meta charset=\"utf-8\">"
    "<title>Aurya</title>"
    "<meta name=\"description\" content=\"Aurya\">"
    "</head><body><div id=\"root\"></div></body></html>"
)


def _base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def _index_html() -> str:
    src = os.environ.get(
        "SEO_SHELL_INDEX_PATH",
        str(Path(__file__).resolve().parent.parent.parent
            / "frontend" / "build" / "index.html"),
    )
    if src.startswith("http://") or src.startswith("https://"):
        return _index_html_http(src)
    path = Path(src)
    try:
        mtime = path.stat().st_mtime
        if _INDEX_CACHE["html"] is None or _INDEX_CACHE["mtime"] != mtime:
            _INDEX_CACHE["html"] = path.read_text(encoding="utf-8")
            _INDEX_CACHE["mtime"] = mtime
        return _INDEX_CACHE["html"]
    except OSError:
        return _DEV_TEMPLATE


def _index_html_http(url: str) -> str:
    """Deploy Docker: legge l'index dal container frontend via HTTP con
    cache TTL. Best-effort assoluto: se il frontend non risponde si serve
    la shell neutra (la SPA idrata comunque quando l'asset torna su)."""
    import urllib.request
    now = time.monotonic()
    cached_at = _INDEX_CACHE["mtime"]
    if (_INDEX_CACHE["html"] is not None and cached_at is not None
            and (now - cached_at) < _INDEX_HTTP_TTL):
        return _INDEX_CACHE["html"]
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            _INDEX_CACHE["html"] = resp.read().decode("utf-8")
            _INDEX_CACHE["mtime"] = now
        return _INDEX_CACHE["html"]
    except Exception as exc:                # noqa: BLE001 — mai 500 sulla shell
        logger.warning("seo_shell: index fetch da %s fallito: %s", url, exc)
        return _INDEX_CACHE["html"] or _DEV_TEMPLATE


def _inject(template: str, meta: dict) -> str:
    """Sostituisce title/description e appende OG/canonical/JSON-LD."""
    title = _html.escape(meta.get("title") or "Aurya")
    desc = _html.escape(meta.get("description") or "")

    out = re.sub(r"<title>.*?</title>", f"<title>{title}</title>",
                 template, count=1, flags=re.S)
    # PL21b — via i meta og:/twitter: STATICI di index.html prima di
    # iniettare i nostri: due og:image = i crawler prendono il primo
    # (quello generico) e l'immagine per-pagina non appare mai.
    out = re.sub(r'<meta\s+(?:property="og:[^"]*"|name="twitter:[^"]*")[^>]*/?>\s*', "", out)
    out = re.sub(r'<meta name="description"[^>]*/?>',
                 f'<meta name="description" content="{desc}"/>',
                 out, count=1)

    # SE1 — og:type "article" sugli articoli (con i tempi), "website"
    # su tutto il resto: prima ogni pagina si dichiarava sito.
    og_type = meta.get("og_type") or "website"
    extra = [
        f'<meta property="og:title" content="{title}"/>',
        f'<meta property="og:description" content="{desc}"/>',
        f'<meta property="og:type" content="{og_type}"/>',
        '<meta property="og:site_name" content="Aurya"/>',
        '<meta name="twitter:card" content="summary_large_image"/>',
    ]
    if og_type == "article" and meta.get("article_times"):
        pub, upd = meta["article_times"]
        if pub:
            extra.append(f'<meta property="article:published_time" content="{_html.escape(str(pub))}"/>')
        if upd:
            extra.append(f'<meta property="article:modified_time" content="{_html.escape(str(upd))}"/>')
    if meta.get("image"):
        extra.append(f'<meta property="og:image" content="{_html.escape(meta["image"])}"/>')
        extra.append(f'<meta name="twitter:image" content="{_html.escape(meta["image"])}"/>')
    if meta.get("canonical"):
        canonical = _html.escape(meta["canonical"])
        extra.append(f'<link rel="canonical" href="{canonical}"/>')
        extra.append(f'<meta property="og:url" content="{canonical}"/>')
    for lang, href in (meta.get("hreflang") or {}).items():
        extra.append(f'<link rel="alternate" hreflang="{lang}" href="{_html.escape(href)}"/>')
    if meta.get("noindex"):
        extra.append('<meta name="robots" content="noindex"/>')
    # jsonld può essere un dict singolo o una LISTA di blocchi (es. entità
    # principale + BreadcrumbList + ItemList): uno <script> per blocco,
    # come raccomanda Google.
    blocks = meta.get("jsonld")
    if blocks:
        if not isinstance(blocks, list):
            blocks = [blocks]
        for block in blocks:
            if block:
                extra.append('<script type="application/ld+json">'
                             + json.dumps(block, ensure_ascii=False)
                             + "</script>")

    out = out.replace("</head>", "".join(extra) + "</head>", 1)

    # SE1 — il CONTENUTO nell'HTML iniziale: dentro #root, dove React
    # monta e sostituisce. Prima il body era vuoto (108 byte) e per i
    # crawler senza JS — Bing, GPTBot, ClaudeBot, PerplexityBot — le
    # pagine non avevano testo. Google stesso indicizza il primo HTML
    # senza aspettare la coda di rendering.
    if meta.get("content_html"):
        out = out.replace('<div id="root"></div>',
                          f'<div id="root">{meta["content_html"]}</div>', 1)
    return out


def _abs_image(url: Optional[str]) -> str:
    """Cover assoluta con fallback SEMPRE presente (og-cover 1200x630:
    il logo quadrato rende male nelle card social large)."""
    base = _base_url()
    if not url:
        return f"{base}/og-cover.jpg"
    if url.startswith("http"):
        return url
    return f"{base}{url}"


# ── Resolver per tipo di route ───────────────────────────────────────────────

def _hub_hreflang(canonical: str) -> dict:
    """Hub UI-translated in tutte e 4 le lingue (i18n files completi):
    alternates piene, x-default italiano.

    GS4 (25/8, sblocco indicizzazione) — in fase RETE gli alternates
    mentono: la UI e' tradotta ma i CONTENUTI (articoli, profili) sono
    solo italiani (decisione solo-italiano del 2/8). Dichiarare a
    Google una ?lang=en che serve contenuto italiano e' rumore che
    confonde la classificazione di lingua — ed e' ESATTAMENTE la
    classificazione di lingua a tradirci (pagine col body vuoto gia'
    indicizzate come inglesi: «Traduci questa pagina» in SERP). In
    marketplace gli alternates tornano da soli."""
    out = {"it": canonical, "x-default": canonical}
    from core.prelaunch import site_phase
    if site_phase() == "network":
        return out
    for lang in ("en", "de", "fr"):
        out[lang] = f"{canonical}?lang={lang}"
    return out


# ── GS1 (25/8) — la home PARLA ai crawler ────────────────────────────────────
# Misurato in Search Console: la home era indicizzata col copy
# marketplace di LUGLIO, e le pagine d'ingresso col body vuoto venivano
# classificate INGLESI («Traduci questa pagina») perche' l'unico testo
# nel body era "You need to enable JavaScript to run this app". La
# pagina piu' forte del sito non diceva niente a Google — e quel niente
# era pure in un'altra lingua.
#
# Il copy e' quello del founder (HP5, 2/8): la FONTE e' il locale
# frontend/src/locales/it/landings.json (chiavi nwHome.*) — in Docker
# il backend non vede i sorgenti frontend, quindi le stringhe vivono
# qui COPIATE e una guardia di parita' le confronta col locale, come
# per la biblioteca Sound e le tabelle del visual. React monta sopra
# e sostituisce: l'utente vede la home viva, il crawler legge questa.
_HOME_COPY = {
    "heroTitle": "Il benessere inizia dalle persone.",
    "heroP1": ("Trovare il professionista giusto, comprendere una pratica "
               "o scegliere un’esperienza non dovrebbe essere una "
               "questione di fortuna."),
    "heroP2": ("Aurya è uno spazio dedicato a chi vuole orientarsi nel "
               "mondo del benessere con maggiore consapevolezza."),
    "heroP3": ("Attraverso contenuti, professionisti raccontati con cura "
               "ed esperienze selezionate, aiutiamo le persone a trovare "
               "ciò che fa davvero per loro."),
    "findTitle": ("Un luogo dove conoscere, confrontare e scegliere "
                  "con consapevolezza"),
    "findP1": "Il benessere non è fatto solo di discipline.",
    "findP2": "È fatto di persone, approcci, esperienze e percorsi diversi.",
    "findP3": "Per questo Aurya non nasce come una semplice directory.",
    "findP4": ("Nasce per aiutarti a orientarti, conoscere chi hai davanti "
               "e scegliere con maggiore consapevolezza."),
    "pillarMagTitle": "Magazine",
    "pillarMagText": ("Guide, approfondimenti e storie per capire il mondo "
                      "del benessere senza semplificazioni e senza "
                      "promesse facili."),
    "pillarProTitle": "Professionisti",
    "pillarProText": ("Stiamo costruendo una rete di professionisti "
                      "raccontati attraverso le loro storie, il loro "
                      "metodo e la loro esperienza."),
    "pillarExpTitle": "Esperienze",
    "pillarExpText": ("Workshop, ritiri ed eventi per trasformare ciò che "
                      "hai scoperto in qualcosa da vivere."),
    "whyTitle": "Perché esiste Aurya?",
    "whyP2": "Trovare un professionista è semplice.",
    "whyP3": "Scegliere quello giusto è ciò che conta.",
    "whyP4": ("Noi crediamo che ogni percorso inizi dalla fiducia, e che "
              "la fiducia abbia bisogno di tempo, conoscenza e trasparenza."),
    "magTitle": "Dal Magazine",
    "magBody": ("Il Magazine è il cuore di Aurya. Qui raccontiamo pratiche, "
                "persone e idee che aiutano a comprendere il benessere con "
                "uno sguardo aperto, concreto e curioso."),
    "prosTitle": "Per chi dedica la propria vita al benessere degli altri.",
    "prosP4": ("Aurya nasce anche per questo: raccontare il tuo lavoro con "
               "cura, aiutarti a costruire una presenza digitale autorevole "
               "e, nel tempo, offrirti gli strumenti per far crescere la "
               "tua attività."),
    "letterTitle": "Ricevi la Lettera di Aurya.",
    "letterP6": ("Solo contenuti scelti con cura, da ricevere con calma e "
                 "leggere con attenzione."),
}


async def _home_content_html() -> str:
    """Il corpo della home in HTML semantico: il racconto del founder
    piu' i LINK — dalla pagina col piu' alto PageRank del sito verso
    gli articoli (che aspettano in coda di indicizzazione) e le porte
    della rete. E' anche cio' che ripara la classificazione di lingua:
    finalmente c'e' dell'ITALIANO nel body."""
    from database import db
    c = {k: _html.escape(v) for k, v in _HOME_COPY.items()}
    parti = [
        "<div>",
        f"<h1>{c['heroTitle']}</h1>",
        f"<p>{c['heroP1']}</p><p>{c['heroP2']}</p><p>{c['heroP3']}</p>",
        f"<h2>{c['findTitle']}</h2>",
        f"<p>{c['findP1']} {c['findP2']}</p>",
        f"<p>{c['findP3']} {c['findP4']}</p>",
        "<ul>",
        (f"<li><a href=\"/blog\">{c['pillarMagTitle']}</a> — "
         f"{c['pillarMagText']}</li>"),
        # T7 (25/8) — DUE porte, non una: il racconto della rete e
        # l'elenco di chi c'e'. Prima la home linkava solo il primo, e
        # /esplora-operatori — la pagina con i professionisti veri —
        # restava ORFANA: indicizzabile ma senza un solo voto interno,
        # che in SEO vale quanto non esistere.
        (f"<li><a href=\"/operatori\">{c['pillarProTitle']}</a> — "
         f"{c['pillarProText']} "
         f"<a href=\"/esplora-operatori\">Vedi i professionisti</a></li>"),
        f"<li>{c['pillarExpTitle']} — {c['pillarExpText']}</li>",
        "</ul>",
        f"<h2>{c['whyTitle']}</h2>",
        f"<p>{c['whyP2']} {c['whyP3']} {c['whyP4']}</p>",
        f"<p><a href=\"/manifesto\">Leggi il Manifesto</a> · "
        f"<a href=\"/chi-siamo\">Chi siamo</a></p>",
        f"<h2>{c['magTitle']}</h2>",
        f"<p>{c['magBody']}</p>",
    ]
    # gli articoli piu' recenti, con link VERI: e' la corsia dalla home
    # al Magazine che i crawler non avevano mai visto
    try:
        docs = await (db.articles
                      .find({"published": True},
                            {"_id": 0, "slug": 1, "title": 1,
                             "description": 1})
                      .sort("published_at", -1).to_list(8))
    except Exception:   # noqa: BLE001 — senza DB la home resta il racconto
        docs = []
    if docs:
        parti.append("<ul>")
        for d in docs:
            parti.append(
                f"<li><a href=\"/blog/{_html.escape(d['slug'])}\">"
                f"{_html.escape(d['title'])}</a> — "
                f"{_html.escape((d.get('description') or '')[:160])}</li>")
        parti.append("</ul>")
    parti += [
        "<p><a href=\"/blog\">Tutti gli articoli del Magazine</a></p>",
        f"<h2>{c['prosTitle']}</h2>",
        f"<p>{c['prosP4']}</p>",
        "<p><a href=\"/entra-nella-rete\">Entra nella rete</a></p>",
        f"<h2>{c['letterTitle']}</h2>",
        f"<p>{c['letterP6']}</p>",
        "<p><a href=\"/newsletter\">Scopri la Lettera</a> · "
        "<a href=\"/sound\">Aurya Sound</a></p>",
        "</div>",
    ]
    return "".join(parti)


async def _meta_home() -> dict:
    base = _base_url()
    # OF3 — il meta della home dipende dalla FASE, come gia' fa
    # _meta_operators_index. Fino a ieri il server serviva a Google e
    # alle anteprime dei link "Trova e prenota... con caparra protetta
    # e recensioni verificate" mentre la home di rete non vende niente,
    # non ha caparre e non ha recensioni: era la prima cosa che il
    # mondo leggeva di noi ed era di un altro sito. In piu' il client
    # sovrascriveva con un titolo diverso, quindi la stessa rotta
    # dichiarava due titoli. Il ramo marketplace resta intatto: al
    # lancio quelle parole tornano vere da sole.
    from core.prelaunch import site_phase
    content_html = None
    if site_phase() == "network":
        title = "Aurya | Il benessere inizia dalle persone"
        description = ("Guide oneste sul benessere e i professionisti "
                       "che lo praticano, raccontati uno a uno. "
                       "Per orientarsi prima di scegliere.")
        # GS1 — solo in fase rete: la home marketplace e' la directory,
        # un'altra pagina, e questo racconto non le appartiene
        content_html = await _home_content_html()
    else:
        # AN1 — il title porta la promessa, non solo la categoria
        # (docs/BRAND_AURYA.md): caparra protetta + recensioni verificate.
        title = "Aurya | Ritiri olistici ed esperienze per evolvere"
        description = ("Trova e prenota ritiri di yoga, meditazione, detox "
                       "ed esperienze olistiche: prenoti online con caparra "
                       "protetta e recensioni solo verificate.")
    return {
        "title": title,
        "description": description,
        "canonical": f"{base}/",
        "hreflang": _hub_hreflang(f"{base}/"),
        **({"content_html": content_html} if content_html else {}),
        "image": f"{base}/media/aurya-hero-poster.jpg",
        # SEO6 — WebSite + Organization: l'entita' Aurya nel Knowledge
        # Graph (logo, fondatori, contatto). sameAs si aggiunge quando
        # nascono i profili social del brand (playbook P1).
        "jsonld": [
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Aurya",
                "url": f"{base}/",
                "publisher": {"@id": f"{base}/#organization"},
            },
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "@id": f"{base}/#organization",
                "name": "Aurya",
                "url": f"{base}/",
                "logo": {"@type": "ImageObject",
                         "url": f"{base}/logo-aurya-512.png"},
                "description": ("La casa dei ritiri olistici italiani: "
                                "trova e prenota ritiri ed esperienze di "
                                "benessere con professionisti verificati."),
                "email": "info@aurya.life",
                "founder": [
                    {"@type": "Person", "name": "Davide De Filippis"},
                    {"@type": "Person", "name": "Valentina"},
                ],
            },
        ],
    }


# AN1 — pagine istituzionali del brand: meta statiche, hreflang hub
_BRAND_PAGES = {
    # PL21 — le landing lead del pre-lancio: sono I link condivisi ora,
    # devono avere titolo/descrizione/immagine social impeccabili.
    "cerca-ritiro": {
        "title": "Trova il tuo ritiro olistico | Aurya",
        "description": ("C'è un ritiro che ti sta aspettando. Raccontaci "
                        "cosa cerchi e al lancio ricevi una selezione di "
                        "ritiri olistici scelti per te, con caparra e "
                        "pagamento diretto online."),
        "image": "/media/hero-destination.webp",
    },
    "per-operatori": {
        "title": "Porta i tuoi ritiri su Aurya | Per operatori olistici",
        "description": ("Tu crei l'esperienza, noi la facciamo trovare. "
                        "Visibilità vera, prenotazioni con caparra e "
                        "pagamento diretto. I primi operatori partono "
                        "da fondatori."),
        "image": "/media/hero-organizer.webp",
    },
    # RT5 (piano sito-rete) — le pagine della fase rete.
    "manifesto": {
        "title": "Il manifesto di Aurya | La rete del benessere olistico in Italia",
        "description": ("Da dove nasce Aurya, cosa vogliamo costruire e chi "
                        "siamo. La rete degli operatori olistici in Italia, "
                        "raccontata con onestà."),
    },
    # OF3 — la cadenza dichiarata era in tre versioni diverse (qui
    # "ogni due settimane", sulla landing "ogni tanto", nel modulo del
    # blog di nuovo quindicinale). Vale quella del founder, che e'
    # anche l'unica che non diventa un debito il giorno in cui saltiamo
    # un'uscita: si scrive quando c'e' qualcosa da dire.
    "newsletter": {
        "title": "La Lettera di Aurya | Una lettera, ogni tanto",
        "description": ("Pratiche, persone e idee del benessere, una "
                        "lettera alla volta. La scriviamo solo quando "
                        "abbiamo qualcosa che vale il tuo tempo."),
    },
    # OF3 — tre bugie in due righe: la pagina non si chiama piu' cosi'
    # ("Per i professionisti del benessere"), non usa mai la parola
    # intervista (il profilo lo scrive la redazione), e chiudeva con
    # "Gratuitamente", che come promessa e' vietata fuori dalla FAQ.
    "entra-nella-rete": {
        "title": "Per i professionisti del benessere | Aurya",
        # RD — con la registrazione diretta la promessa cambia: si
        # entra subito, la conversazione arriva dopo (ed e' il racconto)
        "description": ("Crei il tuo account in un minuto e inizi a "
                        "costruire il tuo profilo. Poi ci conosciamo: "
                        "il racconto del tuo lavoro lo scriviamo insieme."),
    },
    # SW3 — /chi-siamo e' di nuovo una pagina propria (le persone dietro
    # Aurya), quindi torna canonica di se stessa: il canonical_slug che
    # la mandava su /manifesto e' caduto insieme al redirect.
    "chi-siamo": {
        "title": "Chi siamo | Aurya",
        # OF3 — la pagina non racconta piu' l'attivita' di terreno:
        # risponde a "perche' fidarsi di chi sta costruendo Aurya".
        "description": ("Siamo Valentina e Davide. Perché abbiamo "
                        "costruito Aurya, come lavoriamo e cosa vogliamo "
                        "che diventi nei prossimi dieci anni."),
    },
    # ES2 (25/8) — DUE PAGINE PUBBLICHE CHE ERANO MUTE. Trovate
    # censendo gli URL che rispondono 200: /meditazioni e' linkata dal
    # menu e dalla landing Sound, /costi e' la pagina dei prezzi — e
    # tutte e due servivano ai crawler 46 caratteri e il TITOLO
    # MARKETPLACE di luglio, perche' non erano nell'elenco delle rotte
    # che passano di qui. Il difetto della home, in piccolo, su due
    # pagine che nessuno aveva pensato di controllare.
    "meditazioni": {
        "title": "Le meditazioni di Aurya | Sessioni vibrazionali",
        "description": ("Sessioni sonore composte dai professionisti della "
                        "rete Aurya, per dormire, meditare, rilassarsi. "
                        "L'ascolto è riservato a chi fa parte del cerchio."),
    },
    "costi": {
        "title": "Quanto costa Aurya | Piani e commissioni, per intero",
        "description": ("La piattaforma è gratuita: profilo, listino, "
                        "ritiri e clienti non si pagano. Fino al 31 "
                        "dicembre 2026 nessun costo, nemmeno sulle "
                        "prenotazioni. Poi scegli tu."),
    },
    "come-funziona": {
        "title": "Come funziona Aurya: prenota ritiri olistici con caparra e pagamento diretto",
        "description": ("Scegli il ritiro, blocca il posto con una piccola "
                        "caparra e il pagamento diretto online, vivi "
                        "l'esperienza e recensisci: su Aurya solo recensioni "
                        "verificate."),
    },
}


# GS2 (25/8) — un corpo MINIMO per le pagine di brand: h1 + il
# riassunto + i link di navigazione. Non e' il copy completo (quello
# vive nella SPA e duplicarlo qui sarebbe una seconda verita' che
# deriva): e' abbastanza ITALIANO da riparare la classificazione di
# lingua (body vuoto → unico testo inglese → «Traduci questa pagina»)
# e abbastanza link da tenere il crawler in cammino.
_BRAND_BODY_LINKS = (
    '<p><a href="/">Aurya</a> · <a href="/blog">Il Magazine</a> · '
    '<a href="/operatori">La rete dei professionisti</a> · '
    '<a href="/newsletter">La Lettera</a></p>')


async def _meta_brand_page(slug: str) -> Optional[dict]:
    from core.prelaunch import site_phase
    page = _BRAND_PAGES.get(slug)
    if not page:
        return None
    # LC2 — /come-funziona racconta il percorso d'acquisto (caparra,
    # prenotazione, recensione): in fase rete quel percorso non esiste
    # e la pagina prometteva ai crawler un marketplace spento. None →
    # 404 vero; la SPA intanto redirige le persone sul Manifesto.
    # Al flip in marketplace torna indicizzabile da sola.
    if slug == "come-funziona" and site_phase() == "network":
        return None
    base = _base_url()
    canonical = f"{base}/{page.get('canonical_slug', slug)}"
    # GS2 — il titolo senza il suffisso brand fa da h1
    h1 = _html.escape(page["title"].split("|")[0].strip())
    body = (f"<div><h1>{h1}</h1>"
            f"<p>{_html.escape(page['description'])}</p>"
            f"{_BRAND_BODY_LINKS}</div>")
    return {
        **page,
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "content_html": body,
        # immagine per-pagina se dichiarata (landing lead), altrimenti og-cover
        "image": (f"{base}{page['image']}" if page.get("image")
                  else f"{base}/og-cover.jpg"),
    }


# ── SP5 — Aurya Sound pubblico: la biblioteca educativa sul suono ────────────
# I titoli delle schede sono COPIATI da frontend/src/features/frequenze/
# content/biblioteca.js: in produzione (Docker) il backend non vede i
# sorgenti frontend, quindi niente lettura a runtime — la guardia di
# parita' nella suite (che gira dove il repo e' completo) impedisce a
# questo elenco di divergere dalla biblioteca vera.
_SOUND_CARDS = {
    "Bande cerebrali": ["Delta", "Theta", "Alpha", "SMR", "Beta", "Gamma"],
    "Altre frequenze": ["40 Hz", "7,83 Hz — Schumann", "Armoniche di Schumann",
                        "111 Hz", "136,1 Hz — Om", "432 Hz",
                        "440 Hz — lo standard", "174 Hz", "285 Hz", "396 Hz",
                        "417 Hz", "528 Hz", "639 Hz", "741 Hz", "852 Hz",
                        "963 Hz"],
    # ONDA 3 (21/8) — i ritmi del corpo: respiro, cuore, passo
    "Ritmi del corpo": ["Ritmo del respiro", "Passo del cuore a riposo",
                        "Cadenza del cammino"],
    "Metodi": ["Battito binaurale", "Tono isocronico", "Battito monaurale",
               "Stimolazione bilaterale", "Soffio modulato",
               # ONDA 4 (21/8)
               "Bordone armonico", "Il colore del soffio", "Battimento lento",
               # ONDA 5 (21/8)
               "Discesa infinita", "Scegliere la portante",
               "Tono puro"],
}

_SOUND_PAGES = {
    None: {
        "title": "Aurya Sound: onde cerebrali, frequenze e metodi | Aurya",
        "description": ("Una biblioteca educativa sul suono: cosa sono le "
                        "bande cerebrali, le frequenze e i metodi di "
                        "stimolazione sonora — con il livello di evidenza "
                        "dichiarato per ogni scheda."),
    },
    "esplora": {
        "title": "Esplora le frequenze: bande, frequenze e metodi | Aurya Sound",
        "description": ("Bande cerebrali, 40 Hz, risonanza di Schumann, 432 Hz, "
                        "solfeggio, battiti binaurali e isocronici: ogni scheda "
                        "spiega cosa sappiamo davvero e cosa resta tradizione."),
    },
    "impara": {
        "title": "Le fondamenta: capire il suono prima di usarlo | Aurya Sound",
        "description": ("Onde cerebrali, entrainment, la differenza tra "
                        "binaurale, monoaurale e isocronico, cuffie o "
                        "altoparlanti: la guida essenziale in sei tappe."),
    },
    "glossario": {
        "title": "Glossario del suono: Hz, EEG, battiti e metodi | Aurya Sound",
        "description": ("Le parole del suono spiegate in una riga: Hertz, "
                        "banda cerebrale, entrainment, battito binaurale, "
                        "frequenza portante e le altre."),
    },
}


def _sound_index_html() -> str:
    """Corpo minimo per i crawler: l'indice testuale della biblioteca
    (stesso spirito di _articles_index_html per il Magazine)."""
    parts = ["<h1>Aurya Sound — la biblioteca educativa sul suono</h1>"]
    for cat, titles in _SOUND_CARDS.items():
        parts.append(f"<h2>{cat}</h2><ul>")
        parts.extend(f"<li>{t}</li>" for t in titles)
        parts.append("</ul>")
    return "".join(parts)


async def _meta_sound(parts: list) -> Optional[dict]:
    """/sound[...]. Esplora e Impara sono editoriali e indicizzabili;
    crea e tracce sono il workspace operatore: vivi ma noindex (la SPA
    redirige al login)."""
    base = _base_url()
    sub = parts[0] if parts else None
    # `visual` (Aurya Visuals, AV2) e' della stessa natura di crea e
    # tracce: uno STRUMENTO, non una pagina editoriale. Senza questa
    # riga nginx lo manda al prerender, il prerender non lo conosce e
    # l'utente prende un 404 (successo davvero, deploy del 22/8).
    if sub in ("crea", "tracce", "visual"):
        meta = {**_SOUND_PAGES[None], "noindex": True}
        return {**meta, "canonical": None, "hreflang": None}
    if sub == "impara":
        key = "glossario" if len(parts) > 1 and parts[1] == "glossario" else "impara"
        slug = "/sound/impara/glossario" if key == "glossario" else "/sound/impara"
        canonical = f"{base}{slug}"
        return {**_SOUND_PAGES[key], "canonical": canonical,
                "hreflang": _hub_hreflang(canonical),
                "image": f"{base}/og-cover.jpg"}
    if sub == "esplora" or sub is None:
        key = "esplora" if sub == "esplora" else None
        canonical = f"{base}/sound/esplora" if sub else f"{base}/sound"
        meta = {**_SOUND_PAGES[key], "canonical": canonical,
                "hreflang": _hub_hreflang(canonical),
                "image": f"{base}/og-cover.jpg"}
        if sub == "esplora":
            meta["content_html"] = _sound_index_html()
        return meta
    return None


async def _meta_category(cat: str, region: Optional[str] = None) -> dict:
    from services import seo_schema as sx, seo_listing as sl
    from core.prelaunch import site_phase
    base = _base_url()
    label = cat.replace("-", " ").title()
    where = f" in {region.title()}" if region else ""
    path = f"/ritiri/{cat}" + (f"/{region}" if region else "")
    canonical = f"{base}{path}"
    try:
        retreats = await sl.listable_retreats(category=cat, place=region, limit=20)
        empty = not retreats
    except Exception:            # noqa: BLE001 — fail open: un errore DB NON
        retreats, empty = [], False   # deve deindicizzare una pagina buona
    crumbs = sx.breadcrumb([
        ("Aurya", f"{base}/"),
        (f"Ritiri di {label}", f"{base}/ritiri/{cat}"),
        *([(region.title(), canonical)] if region else []),
    ])
    blocks = [b for b in (crumbs, sx.item_list(retreats, base)) if b]
    # PP2 — in fase rete la pagina è noindex ma og:title/description
    # viaggiano comunque nelle anteprime social: niente promesse di
    # prenotazione finché il marketplace è spento.
    if site_phase() == "network":
        descr = (f"Ritiri di {label.lower()}{where}: cosa sono e come "
                 "sceglierli. Su Aurya trovi guide oneste e i "
                 "professionisti della rete, raccontati uno a uno.")
    else:
        descr = (f"I migliori ritiri di {label.lower()}{where}: "
                 "date, prezzi e posti disponibili. Prenota online "
                 "con la caparra su Aurya.")
    return {
        "title": f"Ritiri di {label}{where} | Aurya",
        "description": descr,
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": blocks or None,
        # anti thin-content: categoria senza ritiri prenotabili → noindex
        "noindex": empty,
    }


async def _meta_event(org_slug: str, occ_slug: str) -> Optional[dict]:
    from database import (event_occurrences_collection, products_collection,
                          organizations_collection)
    from services import seo_schema as sx
    base = _base_url()
    occ = await event_occurrences_collection.find_one(
        {"slug": occ_slug, "status": "published"},
        {"_id": 0, "product_id": 1, "start_at": 1, "end_at": 1, "city": 1,
         "region": 1, "country": 1, "postal_code": 1, "venue_name": 1,
         "address": 1, "latitude": 1, "longitude": 1, "capacity": 1,
         "cover_image_url": 1, "price_override": 1},
    )
    if not occ:
        return None
    prod = await products_collection.find_one(
        {"id": occ["product_id"], "is_published": True},
        {"_id": 0, "name": 1, "description": 1, "images": 1, "category": 1,
         "organization_id": 1, "price": 1, "unit_price": 1, "currency": 1,
         "translations": 1},
    )
    if not prod:
        return None
    org = await organizations_collection.find_one(
        {"id": prod["organization_id"]}, {"_id": 0, "name": 1,
                                          "store_settings": 1})
    org_name = ((org or {}).get("store_settings") or {}).get("display_name") \
        or (org or {}).get("name") or ""

    when = sx.human_date(occ.get("start_at"))         # data leggibile, no ISO
    where = occ.get("city") or occ.get("region") or "Italia"
    desc = (prod.get("description") or "")[:300]
    image = _abs_image(occ.get("cover_image_url")
                       or (prod.get("images") or [None])[0])
    canonical = f"{base}/e/{org_slug}/{occ_slug}"

    # SEO1 — location strutturata (PostalAddress + GeoCoordinates) e Offer:
    # è ciò che sblocca il rich result evento con luogo, data e prezzo per
    # le query "ritiro yoga [città]". Niente aggregateRating sull'Event:
    # Google non usa le stelle sugli eventi (finirebbe 'invalid').
    address = sx.postal_address(
        street=occ.get("venue_name") or occ.get("address"),
        city=occ.get("city"), region=occ.get("region"),
        postal_code=occ.get("postal_code"), country=occ.get("country"))
    location = sx.place(
        name=occ.get("venue_name") or where, address=address,
        geo=sx.geo_coordinates(occ.get("latitude"), occ.get("longitude")),
        fallback_name=where)
    price = occ.get("price_override")
    if price is None:
        price = prod.get("unit_price") if prod.get("unit_price") is not None \
            else prod.get("price")
    offer = sx.offer(price=price, currency=prod.get("currency"), url=canonical)

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": prod["name"],
        "startDate": occ.get("start_at"),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": location,
        "image": [image],
        "description": desc,
        "organizer": {"@type": "Organization", "name": org_name},
        "url": canonical,
    }
    if occ.get("end_at"):
        jsonld["endDate"] = occ["end_at"]
    if offer:
        jsonld["offers"] = offer
    if occ.get("capacity"):
        jsonld["maximumAttendeeCapacity"] = occ["capacity"]

    title = f"{prod['name']} · {where} · {when} | Aurya" if when \
        else f"{prod['name']} · {where} | Aurya"
    cat = prod.get("category")
    crumbs = sx.breadcrumb([
        ("Aurya", f"{base}/"),
        *([(cat.replace("-", " ").title(), f"{base}/ritiri/{cat}")] if cat else []),
        (prod["name"], canonical),
    ])
    return {
        "title": title,
        "description": desc or f"Ritiro a {where} il {when}. Prenota su Aurya.",
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        # hreflang: solo lingue con description tradotta (multilingua manuale)
        "hreflang": _hreflang_for(prod.get("translations"), canonical),
    }


def _articles_index_html(titolo: str, docs: list, base: str) -> str:
    """SE1 — l'indice come HTML vero: ogni articolo un link con la sua
    description. E' la pagina di scoperta per i crawler senza JS."""
    items = "".join(
        '<li><a href="{href}">{t}</a><p>{d}</p></li>'.format(
            href=f"{base}/blog/{_html.escape(d['slug'])}",
            t=_html.escape(d.get("title") or d["slug"]),
            d=_html.escape(d.get("description") or ""))
        for d in docs)
    return (f'<section><h1>{_html.escape(titolo)}</h1>'
            f'<ul>{items}</ul></section>')


async def _meta_blog_list() -> dict:
    """AN6 — hub del blog: hreflang pieno come gli altri hub."""
    from database import db
    from services import seo_schema as sx
    base = _base_url()
    canonical = f"{base}/blog"
    docs = await (db.articles
                  .find({"published": True},
                        {"_id": 0, "slug": 1, "title": 1, "description": 1})
                  .sort("published_at", -1).limit(100).to_list(100))
    return {
        # SEO1 — il title dell'hub porta le keyword di categoria, non
        # solo la parola "Blog" (che non cerca nessuno).
        "title": "Ritiri, discipline olistiche e benessere | Il Magazine di Aurya",
        "description": ("Guide oneste su ritiri olistici, discipline e "
                        "benessere, scritte da chi le pratica e da chi "
                        "le organizza. Il Magazine di Aurya."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": sx.breadcrumb([("Aurya", f"{base}/"), ("Blog", canonical)]),
        "content_html": _articles_index_html(
            "Il Magazine di Aurya", docs, base),
    }


async def _meta_blog_category(cat: str) -> Optional[dict]:
    """BN5 — hub categoria del Magazine (/blog/categoria/{cat}): rotta
    vera indicizzabile con ItemList degli articoli. Categoria vuota →
    noindex (thin content, stessa regola delle destinazioni)."""
    from database import db
    from models.article import ARTICLE_CATEGORIES
    from services import seo_schema as sx
    if cat not in ARTICLE_CATEGORIES:
        return None
    base = _base_url()
    canonical = f"{base}/blog/categoria/{cat}"
    label = ARTICLE_CATEGORIES[cat]
    docs = await (db.articles
                  .find({"published": True, "category": cat},
                        {"_id": 0, "slug": 1, "title": 1, "description": 1})
                  .sort("published_at", -1).to_list(50))
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), ("Blog", f"{base}/blog"),
                            (label, canonical)])
    blocks = [crumbs] if crumbs else []
    if docs:
        blocks.append({
            "@context": "https://schema.org", "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": d["title"], "url": f"{base}/blog/{d['slug']}"}
                for i, d in enumerate(docs)],
        })
    return {
        "title": f"{label}: articoli e guide | Il Magazine di Aurya",
        "description": (f"Articoli e guide su {label.lower()}: pratiche "
                        "raccontate con onesta', costi reali e consigli "
                        "di chi le vive. Dal Magazine di Aurya."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": blocks,
        "noindex": not docs,
        "content_html": _articles_index_html(
            f"{label}: articoli e guide", docs, base) if docs else None,
    }


def _md_to_text(md: str) -> str:
    """Markdown → testo piano per articleBody: i crawler senza JS (la
    maggior parte dei crawler LLM) leggono SOLO l'HTML iniziale, e il
    corpo della SPA è vuoto. Il testo completo nel JSON-LD è il modo
    più pulito per dare l'articolo a Google E ai motori generativi."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)   # [testo](url) → testo
    t = re.sub(r"^#{1,3}\s+", "", t, flags=re.M)       # heading markers
    t = t.replace("**", "").replace("*", "")
    t = re.sub(r"^[-]\s+", "", t, flags=re.M)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _extract_faq(md: str) -> list:
    """FAQPage dal blocco '## Domande frequenti': domanda in grassetto
    su riga propria, risposta nei paragrafi successivi. Best-effort:
    se la struttura non c'è, niente FAQ (mai rompere il publish)."""
    m = re.search(r"##\s+Domande frequenti\s*\n(.+)$", md, re.S)
    if not m:
        return []
    faqs = []
    for qm in re.finditer(
            r"\*\*([^*]+?)\*\*\s*\n(.+?)(?=\n\*\*|\Z)", m.group(1), re.S):
        q = qm.group(1).strip()
        a = _md_to_text(qm.group(2)).strip()
        if q.endswith("?") and a:
            faqs.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            })
    return faqs


async def _meta_blog_article(slug: str) -> Optional[dict]:
    """AN6 — articolo: BlogPosting JSON-LD, hreflang solo sulle lingue
    davvero tradotte (title+content, la regola della lista pubblica)."""
    from database import db
    base = _base_url()
    doc = await db.articles.find_one(
        {"slug": slug, "published": True},
        {"_id": 0, "title": 1, "description": 1, "featured_image_url": 1,
         "published_at": 1, "updated_at": 1, "translations": 1,
         "author_name": 1, "content": 1, "category": 1, "access": 1,
         "in_breve": 1},
    )
    if not doc:
        return None
    canonical = f"{base}/blog/{slug}"
    image = _abs_image(doc.get("featured_image_url"))
    desc = (doc.get("description") or "")[:300]

    hreflang = {"it": canonical, "x-default": canonical}
    for lang, tr in (doc.get("translations") or {}).items():
        if lang in ("en", "de", "fr") and (tr or {}).get("title")                 and (tr or {}).get("content"):
            hreflang[lang] = f"{canonical}?lang={lang}"

    def _iso_utc(dt):
        """SE1 — datePublished senza timezone non valida: i nostri
        timestamp sono UTC naive, si dichiara."""
        if hasattr(dt, "isoformat"):
            s = dt.isoformat()
            return s if ("+" in s[10:] or s.endswith("Z")) else s + "+00:00"
        return dt

    pub = _iso_utc(doc.get("published_at"))
    upd = _iso_utc(doc.get("updated_at"))
    # SEO4 — firma vera = Person (E-E-A-T): "Valentina · Aurya" è una
    # persona che scrive per l'organizzazione, non l'organizzazione.
    raw_author = doc.get("author_name") or "Aurya"
    if raw_author == "Aurya":
        author = {"@type": "Organization", "name": "Aurya"}
    else:
        author = {"@type": "Person",
                  "name": raw_author.split("·")[0].strip(),
                  "affiliation": {"@type": "Organization", "name": "Aurya"}}
    content_md = doc.get("content") or ""
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": doc["title"],
        "description": desc,
        "author": author,
        "publisher": {"@type": "Organization", "name": "Aurya",
                      "url": f"{base}/"},
        "datePublished": pub,
        "dateModified": upd,
        "url": canonical,
        "inLanguage": "it",
    }
    # SEO4 — l'articolo INTERO nell'HTML iniziale: i crawler senza JS
    # (GPTBot, ClaudeBot, PerplexityBot...) non vedono il body della SPA.
    # BN3 — guida riservata: il crawler vede la STESSA anteprima
    # dell'utente non iscritto (niente cloaking) + il markup standard
    # dei contenuti gated (isAccessibleForFree, Google paywalled docs).
    gated = doc.get("access") == "subscriber"
    if gated and content_md:
        from routers.articles import gated_preview
        preview = gated_preview(content_md)
        jsonld["articleBody"] = _md_to_text(preview["content"])
        jsonld["isAccessibleForFree"] = False
        jsonld["hasPart"] = {"@type": "WebPageElement",
                             "isAccessibleForFree": False,
                             "cssSelector": ".gated-content"}
    elif content_md:
        jsonld["articleBody"] = _md_to_text(content_md)
        jsonld["wordCount"] = len(jsonld["articleBody"].split())
    # `abstract` e' il campo schema.org per il sommario di un'opera:
    # dichiararlo aiuta chi legge i dati strutturati invece del testo
    if (doc.get("in_breve") or "").strip():
        jsonld["abstract"] = " ".join(
            r.strip().lstrip("-• ") for r in doc["in_breve"].split("\n")
            if r.strip())[:1200]
    from models.article import ARTICLE_CATEGORIES
    if doc.get("category") in ARTICLE_CATEGORIES:
        jsonld["articleSection"] = ARTICLE_CATEGORIES[doc["category"]]
    if image:
        jsonld["image"] = [image]
    from services import seo_schema as sx
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), ("Blog", f"{base}/blog"),
                            (doc["title"], canonical)])
    blocks = [jsonld]
    if crumbs:
        blocks.append(crumbs)
    # SEO4 — FAQPage dalle Domande frequenti (rich snippet + fonte
    # diretta per i motori generativi)
    faqs = [] if gated else _extract_faq(content_md)
    if faqs:
        blocks.append({"@context": "https://schema.org",
                       "@type": "FAQPage", "mainEntity": faqs})
    # SE1 — l'articolo VISIBILE nell'HTML iniziale, non solo nel
    # JSON-LD: e' il contenuto che Bing e i crawler AI leggono e che
    # Google indicizza senza aspettare il rendering. Per i riservati
    # si rende la STESSA anteprima dell'utente non iscritto (niente
    # cloaking, come per l'articleBody qui sopra). React monta sopra
    # e sostituisce.
    from services.markdown_html import render_markdown
    visible_md = content_md
    if gated and content_md:
        from routers.articles import gated_preview as _gp
        visible_md = _gp(content_md)["content"]
    body_html = render_markdown(visible_md)
    # T5 (25/8) — LA RETE DEI LINK INTERNI. Misurato: l'articolo sul
    # Reiki linkava DUE pezzi su 47. Un Magazine senza rete interna e'
    # 47 pagine sole: l'autorita' che arriva sulla home non si
    # distribuisce, e il lettore non ha una seconda porta.
    # Si costruisce QUI, server-side, invece di chiedere alla redazione
    # di infilare link a mano in 47 testi: i link nascono dai DATI
    # (stesso argomento, i piu' recenti) e restano giusti da soli
    # quando il Magazine cresce. I link che l'autrice scrive dentro il
    # testo restano quelli che contano: questi sono la rete di fondo.
    correlati = await (db.articles
                       .find({"published": True,
                              "slug": {"$ne": slug},
                              "category": doc.get("category")},
                             {"_id": 0, "slug": 1, "title": 1})
                       .sort("published_at", -1).limit(4).to_list(4))
    if len(correlati) < 4:
        visti = {c["slug"] for c in correlati} | {slug}
        altri = await (db.articles
                       .find({"published": True,
                              "slug": {"$nin": list(visti)}},
                            {"_id": 0, "slug": 1, "title": 1})
                       .sort("published_at", -1).limit(4 - len(correlati))
                       .to_list(4))
        correlati += altri
    rete = ""
    if correlati:
        voci = "".join(
            f'<li><a href="/blog/{_html.escape(c["slug"])}">'
            f'{_html.escape(c["title"])}</a></li>' for c in correlati)
        rete = ("<nav><h2>Continua a leggere</h2>"
                f"<ul>{voci}</ul>"
                '<p><a href="/blog">Tutti gli articoli del Magazine</a> · '
                '<a href="/operatori">I professionisti della rete</a></p>'
                "</nav>")

    # M1 (25/8) — «In breve» PRIMA del racconto. Gli articoli aprono
    # con una scena (la voce del brand, che non si tocca): bella da
    # leggere, impossibile da citare. Questo blocco da' la risposta
    # fattuale in testa, dove un motore generativo la trova. Sta nel
    # markup come <aside> perche' e' cio' che e': un a-parte che
    # riassume, non l'inizio dell'articolo.
    breve = (doc.get("in_breve") or "").strip()
    breve_html = ""
    if breve and not gated:
        righe = "".join(f"<li>{_html.escape(r.strip().lstrip('-• '))}</li>"
                        for r in breve.split("\n") if r.strip())
        breve_html = (f'<aside><h2>In breve</h2><ul>{righe}</ul></aside>'
                      if righe else "")

    content_html = (
        '<article>'
        f'<h1>{_html.escape(doc["title"])}</h1>'
        + (f'<img src="{_html.escape(image)}" alt=""/>' if image else '')
        + breve_html
        + body_html
        + '</article>'
        + rete
    )
    return {
        "title": f"{doc['title']} | Aurya",
        "description": desc or "Un articolo dal Magazine di Aurya.",
        "canonical": canonical,
        "image": image,
        "jsonld": blocks,
        "hreflang": hreflang,
        "og_type": "article",
        "article_times": (pub, upd),
        "content_html": content_html,
    }


def _hreflang_for(translations: Optional[dict], canonical: str) -> dict:
    out = {"it": canonical, "x-default": canonical}
    for lang, tr in (translations or {}).items():
        if lang in ("en", "de", "fr") and (tr or {}).get("description"):
            out[lang] = f"{canonical}?lang={lang}"
    return out


async def _meta_product(kind: str, org_slug: str, product_slug: str) -> Optional[dict]:
    """Landing prodotto generica: /p /ph /dg /co /r — S1 completerà i
    JSON-LD per tipo; la shell intanto dà title/desc/OG/canonical veri."""
    from database import products_collection
    from services import seo_schema as sx
    base = _base_url()
    prod = await products_collection.find_one(
        {"slug": product_slug, "is_published": True, "is_active": True},
        {"_id": 0, "name": 1, "description": 1, "images": 1, "price": 1,
         "item_type": 1, "translations": 1},
    )
    if not prod:
        return None
    canonical = f"{base}/{kind}/{org_slug}/{product_slug}"
    image = _abs_image((prod.get("images") or [None])[0])
    desc = (prod.get("description") or "")[:300]
    types = {"p": "Service", "co": "Course", "ph": "Product",
             "dg": "Product", "r": "Product"}
    jsonld = {
        "@context": "https://schema.org",
        "@type": types.get(kind, "Product"),
        "name": prod["name"],
        "description": desc,
        "image": [image],
        "url": canonical,
    }
    if prod.get("price") is not None:
        jsonld["offers"] = {"@type": "Offer", "price": prod["price"],
                            "priceCurrency": "EUR",
                            "availability": "https://schema.org/InStock"}
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), (prod["name"], canonical)])
    return {
        "title": f"{prod['name']} | Aurya",
        "description": desc or prod["name"],
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        "hreflang": _hreflang_for(prod.get("translations"), canonical),
    }


async def _meta_destination(place_slug: Optional[str] = None) -> dict:
    from services import seo_schema as sx, seo_listing as sl
    base = _base_url()
    label = place_slug.replace("-", " ").title() if place_slug else None
    path = "/destinazioni" + (f"/{place_slug}" if place_slug else "")
    canonical = f"{base}{path}"

    if not label:
        # hub destinazioni: solo breadcrumb (l'indice dei luoghi lo rende
        # il client; niente noindex, è una pagina hub legittima)
        return {
            "title": "Destinazioni · dove vuoi ritrovarti? | Aurya",
            "description": ("Scegli la destinazione del tuo prossimo ritiro: "
                            "i luoghi con ritiri ed esperienze in programma "
                            "su Aurya."),
            "canonical": canonical,
            "hreflang": _hub_hreflang(canonical),
            "image": f"{base}/og-cover.jpg",
            "jsonld": sx.breadcrumb([("Aurya", f"{base}/"),
                                     ("Destinazioni", canonical)]),
        }

    try:
        retreats = await sl.listable_retreats(place=place_slug, limit=20)
        empty = not retreats
    except Exception:            # noqa: BLE001 — fail open, mai deindicizzare
        retreats, empty = [], False
    # il nome vero del luogo dal primo ritiro (Ostuni, non "Ostuni" slugato)
    real = next((r.get("city") or r.get("region") for r in retreats), label)
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"),
                            ("Destinazioni", f"{base}/destinazioni"),
                            (real, canonical)])
    blocks = [b for b in (crumbs, sx.item_list(retreats, base)) if b]
    return {
        "title": f"Ritiri ed esperienze a {real} | Aurya",
        "description": (f"Ritiri di yoga, meditazione ed esperienze olistiche "
                        f"a {real}: date, prezzi e disponibilità reali. "
                        "Prenota online con la caparra."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": blocks or None,
        # destinazione senza ritiri prenotabili → noindex (thin content)
        "noindex": empty,
    }


async def _meta_experiences(category: Optional[str] = None) -> dict:
    base = _base_url()
    label = category.replace("-", " ").title() if category else None
    path = "/esperienze" + (f"/{category}" if category else "")
    return {
        "title": (f"Esperienze di {label} | Aurya" if label
                  else "Esperienze olistiche: massaggi, corsi e soggiorni | Aurya"),
        "description": ("Massaggi, trattamenti, corsi e soggiorni olistici "
                        "dai professionisti di Aurya. Prenoti online, paghi "
                        "in sicurezza."),
        "canonical": f"{base}{path}",
        "hreflang": _hub_hreflang(f"{base}{path}"),
        "image": f"{base}/og-cover.jpg",
    }


async def _meta_operators_index(category: Optional[str] = None) -> dict:
    from core.prelaunch import site_phase
    base = _base_url()
    label = category.replace("-", " ").title() if category else None
    path = "/operatori" + (f"/{category}" if category else "")
    # RT5 — fase rete: /operatori e' la landing della rete, il title
    # coincide con quello della pagina (NetworkOperatorsPage). Anche le
    # varianti /operatori/{cat} rendono la stessa landing: canonical
    # sulla radice.
    if site_phase() == "network":
        # GS3 (25/8) — anche questa landing era un body vuoto (46
        # caratteri inglesi). Il corpo: il racconto + i LINK ai profili
        # dei membri (/o/{slug}) — la corsia dei crawler verso le
        # pagine che nessun elenco puo' replicare. Stesso perimetro di
        # /public/network/members.
        descr = ("Costruiamo una rete di professionisti del "
                 "benessere, una persona alla volta. Ogni "
                 "profilo nasce da una conversazione vera.")
        membri_html = ""
        try:
            from database import organizations_collection
            orgs = await organizations_collection.find(
                {"network_member": True, "is_active": {"$ne": False},
                 "is_sample": {"$ne": True},
                 "exclude_from_listings": {"$ne": True},
                 "public_slug": {"$nin": [None, ""]}},
                {"_id": 0, "name": 1, "public_slug": 1},
            ).sort("name", 1).to_list(100)
            if orgs:
                voci = "".join(
                    f'<li><a href="/o/{_html.escape(o["public_slug"])}">'
                    f'{_html.escape(o.get("name") or o["public_slug"])}'
                    f"</a></li>" for o in orgs)
                membri_html = f"<ul>{voci}</ul>"
        except Exception:   # noqa: BLE001 — senza DB resta il racconto
            pass
        body = ("<div><h1>La rete Aurya</h1>"
                f"<p>{_html.escape(descr)}</p>"
                f"{membri_html}"
                '<p><a href="/esplora-operatori">Vedi i professionisti '
                "della rete</a> · "
                '<a href="/entra-nella-rete">Sei un professionista '
                "del benessere? Entra nella rete</a></p>"
                f"{_BRAND_BODY_LINKS}</div>")
        return {
            # OF3 — "operatori" e' il nome interno, "professionisti"
            # quello che il sito usa da agosto. E la vecchia descrizione
            # prometteva interviste e racconti al plurale su una rete
            # che oggi ha una persona sola: promettere a Google piu' di
            # quello che si trova arrivando e' il modo piu' rapido di
            # far rimbalzare chi arriva.
            "title": "La rete Aurya | I professionisti che stiamo conoscendo",
            "description": descr,
            "canonical": f"{base}/operatori",
            "hreflang": _hub_hreflang(f"{base}/operatori"),
            "content_html": body,
            "image": f"{base}/og-cover.jpg",
        }
    return {
        "title": (f"Professionisti di {label} | Aurya" if label
                  else "Tutti i professionisti del benessere | Aurya"),
        "description": ("Scopri i professionisti del benessere su Aurya: "
                        "pratiche, esperienze e percorsi, con profili, "
                        "prossime date e prenotazione online."),
        "canonical": f"{base}{path}",
        "hreflang": _hub_hreflang(f"{base}{path}"),
        "image": f"{base}/og-cover.jpg",
    }


async def _meta_esplora_operatori(categoria: Optional[str] = None) -> dict:
    """ES1 (25/8) — la DIRECTORY dei professionisti registrati.

    Attenzione a non confonderla con `/operatori`: quella e' la pagina
    che RACCONTA la rete (perche' esiste, come si entra), questa e'
    l'elenco di chi c'e'. Due intenti diversi, due pagine diverse:
    nessun contenuto doppio.

    La pagina viva chiama l'API con `preview=1`, che salta lo specchio
    di fase del pre-lancio e serve gli operatori VERI: qui si fa lo
    stesso perimetro, o il crawler vedrebbe una lista diversa da quella
    che vede la persona (che e' la definizione di cloaking).
    """
    from database import organizations_collection
    base = _base_url()
    canonical = f"{base}/esplora-operatori"
    titolo = "Professionisti del benessere in Italia | Aurya"
    descr = ("Scopri i professionisti del benessere su Aurya: pratiche, "
             "discipline e percorsi, raccontati uno a uno.")

    voci, quanti = "", 0
    try:
        orgs = await organizations_collection.find(
            {"is_sample": {"$ne": True}, "is_active": {"$ne": False},
             "exclude_from_listings": {"$ne": True},
             "public_slug": {"$nin": [None, ""]}},
            {"_id": 0, "name": 1, "public_slug": 1, "public_profile": 1},
        ).sort("name", 1).to_list(200)
        quanti = len(orgs)
        from models.disciplines import DISCIPLINES
        righe = []
        for o in orgs:
            pp = o.get("public_profile") or {}
            dove = ", ".join(x for x in (pp.get("city"), pp.get("region")) if x)
            disc = ", ".join(DISCIPLINES[d] for d in (pp.get("disciplines") or [])
                             if d in DISCIPLINES)
            coda = " — ".join(x for x in (dove, disc) if x)
            righe.append(
                f'<li><a href="/o/{_html.escape(o["public_slug"])}">'
                f'{_html.escape(o.get("name") or o["public_slug"])}</a>'
                + (f" — {_html.escape(coda)}" if coda else "") + "</li>")
        voci = "".join(righe)
    except Exception:   # noqa: BLE001 — la shell non muore mai per il DB
        pass

    corpo = (f"<div><h1>Professionisti del benessere</h1>"
             f"<p>{_html.escape(descr)}</p>"
             + (f"<ul>{voci}</ul>" if voci else "")
             + '<p><a href="/operatori">Come funziona la rete Aurya</a> · '
               '<a href="/blog">Il Magazine</a></p></div>')
    return {
        "title": titolo,
        "description": descr,
        # le varianti per categoria mostrano un sottoinsieme della
        # stessa lista: una sola pagina negli indici
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "content_html": corpo,
        # anti thin-content: un elenco vuoto non si indicizza. Quando
        # entra il primo professionista si accende da solo.
        "noindex": quanti == 0,
    }


async def _meta_esplora_ritiri(categoria: Optional[str] = None,
                               regione: Optional[str] = None) -> dict:
    """ES2 (25/8) — il calendario dei ritiri.

    Oggi e' VUOTO, e va bene cosi': i campioni del pre-lancio sono
    stati rimossi e i professionisti veri non hanno ancora pubblicato.
    Resta `noindex` finche' e' vuoto (promettere ritiri che non ci sono
    e' il rimbalzo garantito) e **si accende da solo** al primo evento
    pubblicato: e' esattamente cio' che il founder ha chiesto — non
    dover fare niente quel giorno.
    """
    base = _base_url()
    canonical = f"{base}/esplora-ritiri"
    quanti = 0
    try:
        from services.seo_listing import listable_retreats
        quanti = len(await listable_retreats())
    except Exception:   # noqa: BLE001
        quanti = 0
    corpo = ("<div><h1>Ritiri ed esperienze di benessere</h1>"
             "<p>Il calendario dei ritiri dei professionisti della rete "
             "Aurya: date, luoghi e chi li conduce.</p>"
             + ("" if quanti else
                "<p>Non ci sono ancora ritiri in calendario. "
                "Intanto puoi conoscere i professionisti della rete.</p>")
             + '<p><a href="/esplora-operatori">I professionisti</a> · '
               '<a href="/blog">Il Magazine</a></p></div>')
    return {
        "title": "Ritiri ed esperienze di benessere in Italia | Aurya",
        "description": ("Il calendario dei ritiri dei professionisti della "
                        "rete Aurya: date, luoghi e chi li conduce."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "content_html": corpo,
        "noindex": quanti == 0,
    }


async def _meta_operator(org_slug: str) -> Optional[dict]:
    from database import stores_collection, organizations_collection
    from services import seo_schema as sx
    base = _base_url()
    _proj = {"_id": 0, "id": 1, "name": 1, "public_profile": 1,
             "store_settings": 1, "reviews_stats": 1}
    store = await stores_collection.find_one(
        {"slug": org_slug, "is_published": True},
        {"_id": 0, "organization_id": 1, "name": 1, "description": 1},
    )
    if store:
        org = await organizations_collection.find_one(
            {"id": store["organization_id"]}, _proj)
    else:
        org = await organizations_collection.find_one(
            {"public_slug": org_slug}, _proj)
    if not org:
        return None
    profile = org.get("public_profile") or {}
    # OP4 — stessa risoluzione del pubblico: nome org (settings) prima
    name = (org.get("name")
            or (org.get("store_settings") or {}).get("display_name")
            or org_slug)
    bio = (profile.get("tagline") or profile.get("bio") or "")[:300]
    image = _abs_image(profile.get("logo_url") or profile.get("cover_url")
                       or profile.get("portrait_url"))
    canonical = f"{base}/o/{org_slug}"

    # SEO1 — l'operatore è un LocalBusiness geo-taggato: è ciò che lo fa
    # comparire su Google nella sua zona (la promessa commerciale). Address
    # + geo dal profilo, stelle dalle recensioni verificate, social in
    # sameAs. Solo LocalBusiness/Organization possono portare aggregateRating.
    city, region = profile.get("city"), profile.get("region")
    jsonld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "url": canonical,
        "description": bio,
    }
    if image:
        jsonld["image"] = image
    address = sx.postal_address(city=city, region=region)
    if address:
        jsonld["address"] = address
    geo = sx.geo_coordinates(profile.get("latitude"), profile.get("longitude"))
    if geo:
        jsonld["geo"] = geo
    rating = sx.aggregate_rating(org.get("reviews_stats"))
    if rating:
        jsonld["aggregateRating"] = rating
    sa = sx.same_as(profile.get("instagram"), profile.get("facebook"),
                    profile.get("website"))
    if sa:
        jsonld["sameAs"] = sa
    if profile.get("show_contacts"):
        if profile.get("public_phone"):
            jsonld["telephone"] = profile["public_phone"]
        if profile.get("public_email"):
            jsonld["email"] = profile["public_email"]

    # TW2 (piano Listino) — il profilo E' il negozio: i servizi
    # pubblicati come OfferCatalog del LocalBusiness (schema.org).
    from routers.public import _operator_listino
    _org_id_for_listino = org.get("id") if isinstance(org, dict) else None
    if _org_id_for_listino:
        try:
            _rows = await _operator_listino(_org_id_for_listino)
        except Exception:               # noqa: BLE001 — mai 500 sulla shell
            _rows = []
        if _rows:
            jsonld["hasOfferCatalog"] = {
                "@type": "OfferCatalog",
                "name": f"Listino di {name}",
                "itemListElement": [
                    {"@type": "Offer",
                     "itemOffered": {"@type": "Service",
                                     "name": r["name"],
                                     "provider": {"@type": "LocalBusiness",
                                                  "name": name}},
                     **({"price": r["price"], "priceCurrency": "EUR"}
                        if (r.get("price") and not r.get("on_request"))
                        else {})}
                    for r in _rows[:20]
                ],
            }

    # Title local-oriented: "{nome} · ritiri a {città} | Aurya" cattura la
    # query di brand+luogo dell'operatore.
    title = f"{name} · ritiri a {city} | Aurya" if city \
        else f"{name} · professionista su Aurya"
    desc = bio or (f"Ritiri ed esperienze di {name}"
                   + (f" a {city}" if city else "") + " su Aurya.")
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"),
                            ("Professionisti", f"{base}/operatori"),
                            (name, canonical)])
    hreflang = {"it": canonical, "x-default": canonical}
    for _lang, _f in (profile.get("translations") or {}).items():
        if _lang in ("en", "de", "fr") and (_f or {}).get("bio"):
            hreflang[_lang] = f"{canonical}?lang={_lang}"

    # GS7 (25/8) — IL PROFILO PARLA. Misurato in produzione: i profili
    # dei professionisti veri rispondevano 200 con meta e JSON-LD
    # perfetti e un BODY DI 46 CARATTERI. Sono le pagine che nessun
    # elenco puo' replicare (bio scritta, discipline, il racconto) e
    # sono anche il bersaglio del volano-backlink del piano: ogni
    # professionista che linka il suo profilo mandava i crawler su una
    # pagina muta. Qui va il testo VERO del profilo — bio e tagline le
    # ha scritte la redazione con la persona, non sono riempitivo.
    from models.disciplines import DISCIPLINES
    pezzi = [f"<div><h1>{_html.escape(name)}</h1>"]
    if profile.get("tagline"):
        pezzi.append(f"<p>{_html.escape(profile['tagline'][:300])}</p>")
    bio_piena = (profile.get("bio") or "").strip()
    if bio_piena:
        for capo in bio_piena.split("\n"):
            if capo.strip():
                pezzi.append(f"<p>{_html.escape(capo.strip()[:1200])}</p>")
    # DISCIPLINES e' gia' slug → etichetta leggibile (models/disciplines)
    disc = [DISCIPLINES[d] for d in (profile.get("disciplines") or [])
            if d in DISCIPLINES]
    if disc:
        pezzi.append("<p>Pratiche: " + ", ".join(
            _html.escape(d) for d in disc) + "</p>")
    dove = ", ".join(x for x in (city, region) if x)
    if dove:
        pezzi.append(f"<p>Dove: {_html.escape(dove)}</p>")
    pezzi.append('<p><a href="/esplora-operatori">Tutti i professionisti '
                 'della rete Aurya</a> · <a href="/blog">Il Magazine</a>'
                 '</p></div>')

    return {
        "title": title,
        "description": desc,
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        "hreflang": hreflang,
        "content_html": "".join(pezzi),
    }


async def _meta_link_page(org_slug: str) -> Optional[dict]:
    """LK2 — pagina link (/@slug, /l/slug): la bio di Instagram.

    MAI indicizzata (l'asset SEO resta /o/, niente contenuti doppi),
    ma con title/description/OG image pieni: questa pagina vive nelle
    chat, e l'anteprima su WhatsApp/IG deve mostrare foto e nome.
    Il ritratto vince sul logo: e' una pagina-persona, non una vetrina."""
    meta = await _meta_operator(org_slug)
    if not meta:
        return None
    from database import organizations_collection, stores_collection
    portrait = None
    store = await stores_collection.find_one(
        {"slug": org_slug, "is_published": True},
        {"_id": 0, "organization_id": 1})
    org = await organizations_collection.find_one(
        {"id": store["organization_id"]} if store
        else {"public_slug": org_slug},
        {"_id": 0, "public_profile.portrait_url": 1})
    if org:
        portrait = _abs_image(
            (org.get("public_profile") or {}).get("portrait_url"))
    return {**meta,
            "image": portrait or meta.get("image"),
            "noindex": True, "canonical": None,
            "hreflang": None, "jsonld": None}


async def _meta_store(slug: str) -> Optional[dict]:
    from database import stores_collection, organizations_collection
    from services import seo_schema as sx
    base = _base_url()
    store = await stores_collection.find_one(
        {"slug": slug, "is_published": True, "visibility": "public"},
        {"_id": 0, "name": 1, "description": 1, "organization_id": 1},
    )
    if not store:
        return None
    canonical = f"{base}/s/{slug}"
    name = store.get("name") or slug
    jsonld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "url": canonical,
    }
    # SEO1 — lo store è la stessa entità dell'operatore: eredita geo,
    # address, rating e social dal profilo pubblico dell'org collegata.
    org = await organizations_collection.find_one(
        {"id": store.get("organization_id")},
        {"_id": 0, "public_profile": 1, "reviews_stats": 1})
    profile = (org or {}).get("public_profile") or {}
    address = sx.postal_address(city=profile.get("city"),
                                region=profile.get("region"))
    if address:
        jsonld["address"] = address
    geo = sx.geo_coordinates(profile.get("latitude"), profile.get("longitude"))
    if geo:
        jsonld["geo"] = geo
    rating = sx.aggregate_rating((org or {}).get("reviews_stats"))
    if rating:
        jsonld["aggregateRating"] = rating
    sa = sx.same_as(profile.get("instagram"), profile.get("facebook"),
                    profile.get("website"))
    if sa:
        jsonld["sameAs"] = sa
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), (name, canonical)])
    return {
        "title": f"{name} · negozio su Aurya",
        "description": (store.get("description") or "")[:300]
                       or f"Il negozio di {name} su Aurya.",
        "canonical": canonical,
        "image": f"{base}/og-cover.jpg",
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
    }


# ── Routing ──────────────────────────────────────────────────────────────────

_PRODUCT_KINDS = ("p", "ph", "dg", "co", "r")

# RT5 — path noindex quando il marketplace e' spento (prelaunch_mode):
# solo il transazionale. /operatori NON c'e': in fase rete e' la landing
# dei membri, con contenuto vero, e si indicizza.
_PHASE_NOINDEX_HEADS = ("ritiri", "destinazioni", "esperienze")


# GS5 (25/8) — le rotte APP: pagine vive per le persone, mai per gli
# indici. Misurato in Search Console: /inizia, /login, /termini erano
# INDICIZZATE (una pure classificata inglese, per il body vuoto) mentre
# 46 articoli su 47 aspettavano in coda — il crawl budget di un dominio
# nuovo sprecato sulla porta di servizio. Queste rotte prima non
# passavano dalla shell (andavano al frontend statico, nessun modo di
# dire noindex): ora nginx le instrada qui e la shell risponde 200 +
# noindex. NB: NON vanno messe in Disallow nel robots — un crawler che
# non puo' leggere la pagina non ne vede nemmeno il noindex.
_APP_NOINDEX_ROUTES = ("login", "accedi", "inizia", "benvenuto",
                       "account", "termini", "privacy")


async def resolve_meta(path: str) -> Optional[dict]:
    """path SENZA query, es. '/e/borgo-sereno/ritiro-x'. None = 404 →
    si serve comunque la shell neutra (la SPA mostrerà il suo 404)."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return await _meta_home()
    head = parts[0]
    if head in _APP_NOINDEX_ROUTES:
        return {"title": "Aurya", "description": "",
                "noindex": True, "canonical": None, "hreflang": None}
    if head == "ritiri":
        if len(parts) == 1:
            return await _meta_home()          # /ritiri redirige alla home
        return await _meta_category(parts[1], parts[2] if len(parts) > 2 else None)
    if head == "e" and len(parts) >= 3:
        return await _meta_event(parts[1], parts[2])
    if head in _PRODUCT_KINDS and len(parts) >= 3:
        return await _meta_product(head, parts[1], parts[2])
    if head == "operatori":
        return await _meta_operators_index(parts[1] if len(parts) > 1 else None)
    # ES (25/8) — le due directory vere della fase rete. Nate come
    # anteprime non linkate (29/7) e tenute fuori dagli indici finche'
    # la vetrina conteneva i CAMPIONI del pre-lancio. Rimossi quelli
    # (scripts/pulisci_campioni_prelancio.py), qui dentro c'e' solo
    # roba vera: /esplora-operatori elenca i professionisti registrati,
    # /esplora-ritiri i loro eventi — oggi zero, e si riempira' da
    # solo. Decisione founder: indicizzarle ORA, cosi' quando
    # pubblicheranno i primi ritiri non ci sara' niente da fare.
    if head == "esplora-operatori":
        return await _meta_esplora_operatori(
            parts[1] if len(parts) > 1 else None)
    if head == "esplora-ritiri":
        return await _meta_esplora_ritiri(
            parts[1] if len(parts) > 1 else None,
            parts[2] if len(parts) > 2 else None)
    if head == "destinazioni":
        return await _meta_destination(parts[1] if len(parts) > 1 else None)
    # DS3: /esperienze fuori per ora (redirect alla home lato SPA)
    if head == "o" and len(parts) >= 2:
        return await _meta_operator(parts[1])
    # LK2 — pagina link: /@slug (l'URL da bio Instagram) e /l/slug
    if head.startswith("@") and len(parts) == 1 and len(head) > 1:
        return await _meta_link_page(head[1:])
    if head == "l" and len(parts) == 2:
        return await _meta_link_page(parts[1])
    if head == "s" and len(parts) == 2:
        # TW3 — la vetrina /s/{slug} e' migrata sul profilo: i crawler
        # ricevono le meta del profilo con canonical /o/{slug} (la SPA
        # redirige). Le sottopagine legal (/s/x/privacy, /terms)
        # restano store (servono al checkout).
        return await _meta_operator(parts[1])
    if head == "s" and len(parts) > 2:
        return await _meta_store(parts[1])
    if head in _BRAND_PAGES and len(parts) == 1:
        return await _meta_brand_page(head)   # AN1 — /chi-siamo, /come-funziona
    if head == "newsletter" and len(parts) > 1:
        # BN2 — pagine token (conferma/preferenze): vive, mai indicizzate.
        # 200 con noindex: il link nell'email deve aprirsi pulito, non 404.
        meta = await _meta_brand_page("newsletter")
        return {**meta, "noindex": True, "canonical": None, "hreflang": None}
    if head == "blog":                        # AN6 — il blog sulle stesse rotaie
        if len(parts) == 1:
            return await _meta_blog_list()
        if parts[1] == "categoria" and len(parts) >= 3:
            return await _meta_blog_category(parts[2])   # BN5 — hub categoria
        return await _meta_blog_article(parts[1])
    if head == "sound":                       # SP5 — biblioteca educativa
        return await _meta_sound(parts[1:])
    return None


@router.get("/{full_path:path}")
async def seo_shell(full_path: str):
    path = "/" + full_path.strip("/")
    now = time.monotonic()
    hit = _CACHE.get(path)
    if hit and now - hit[1] < _CACHE_TTL:
        cached_status = hit[2] if len(hit) > 2 else 200
        return Response(hit[0], media_type="text/html",
                        status_code=cached_status,
                        headers={"Cache-Control": "no-cache"})

    meta = None
    try:
        meta = await resolve_meta(path)
    except Exception as exc:  # noqa: BLE001 — la shell non deve MAI 500
        logger.warning("seo_shell: resolve failed for %s: %s", path, exc)

    # PL22→RT5 — fase network: il transazionale resta fuori dagli indici
    # (ritiri/destinazioni/esperienze), ma /operatori ORA e' la landing
    # della rete con contenuto vero e si indicizza. In marketplace tutto
    # torna indicizzabile.
    if meta and prelaunch_mode():
        head = path.strip("/").split("/")[0]
        if head in _PHASE_NOINDEX_HEADS:
            meta = {**meta, "noindex": True}

    template = _index_html()
    if meta:
        page = _inject(template, meta)
        status = 200
    else:
        # SEO6 — 404 VERO, non soft-404: il path ha la forma di un
        # contenuto pubblico (nginx instrada qui solo quei pattern) ma
        # il contenuto non esiste (articolo/evento/profilo mancante).
        # Si serve comunque la shell cosi' la SPA mostra il suo 404,
        # ma lo status dice ai crawler la verita'.
        page = template
        status = 404
    _CACHE[path] = (page, now, status)
    # L'HTML D'INGRESSO NON SI CACHA MAI (22/8: il founder ha testato
    # per TRE round build vecchie — «nulla sta cambiando» — perche'
    # questa risposta usciva senza header sul ramo caldo e con 300s
    # sul freddo, e il telefono decideva da solo). no-cache = il
    # browser RIVALIDA a ogni apertura: 3KB, costo zero, build sempre
    # fresca. I chunk hanno l'hash nel nome e restano cacheabili.
    return Response(page, media_type="text/html", status_code=status,
                    headers={"Cache-Control": "no-cache"})

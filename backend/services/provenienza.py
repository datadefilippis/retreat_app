"""Lotto B1 (24/9/2026) — da dove arriva un iscritto del Cerchio.

`source` e' una stringa libera con almeno 13 forme (cerca-ritiro,
newsletter, home_letter, blog_<cat>, gate_<slug>, meditazioni,
cancello:<slug>, sound:esplora:<slug>, sound:lab:<slug>, signup_pro,
account_signup, gestionale, frequenze:<slug>, piu' il suffisso
«:<porta>» dei form della landing). Qui c'e' la SOLA tabella che la
traduce in tre livelli leggibili (canale › superficie › dettaglio), con
le etichette per l'admin. `source` resta com'e' nel documento: le
sequenze e i test la leggono ancora.

La `porta` e' un asse separato: da dove e' arrivato il traffico
(`?porta=home|magazine|esperienze|pagina-link`, o l'UTM), non dove si
e' iscritto. Qui la si legge dal suffisso della fonte o dall'URL; il
«meditazioni|altro» delle sequenze resta in `sequenze.porta_cerchio`.

docs/ANALISI_SYSTEM_ADMIN_2026-09-24.md §3.2, PIANO_ESECUZIONE B1.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, urlsplit

# canale → superfici ammesse (l'ordine e' quello delle tendine in admin)
TASSONOMIA = {
    "sito": ("cerca-ritiro", "home", "landing-cerchio", "esperienze"),
    "magazine": ("articolo", "guida", "cta-categoria"),
    "sound": ("meditazioni", "cancello", "esplora", "lab", "frequenza"),
    "account": ("signup", "signup-pro", "reinvio"),
    "gestionale": ("lettera-operatore",),
    "prelancio": ("lead-viaggiatore", "lead-professionista"),
    "manuale": ("admin", "import"),
    # Lotto E (24/9) — le porte nuove del commercio: casella al checkout,
    # bottone nella pagina grazie, riga nell'email d'ordine e in quella
    # del codice recensione (clic firmato = consenso + verifica)
    "commercio": ("checkout", "pagina-grazie", "email-ordine", "email-recensione"),
    "altro": ("sconosciuta",),
}

# etichette umane, un dizionario piatto (canali e superfici insieme)
ETICHETTE = {
    "sito": "Sito", "magazine": "Magazine", "sound": "Aurya Sound",
    "account": "Account", "gestionale": "Gestionale", "prelancio": "Prelancio",
    "manuale": "A mano", "commercio": "Acquisti", "altro": "Altro",
    "checkout": "Casella al checkout", "pagina-grazie": "Pagina grazie",
    "email-ordine": "Email dell'ordine", "email-recensione": "Email della recensione",
    "cerca-ritiro": "Cerca un ritiro", "home": "Home", "landing-cerchio": "Landing del Cerchio",
    "esperienze": "Esperienze",
    "articolo": "Articolo", "guida": "Guida (cancello)", "cta-categoria": "Invito di categoria",
    "meditazioni": "Meditazioni", "cancello": "Cancello di una traccia", "esplora": "Esplora",
    "lab": "Lab", "frequenza": "Frequenza",
    "signup": "Registrazione", "signup-pro": "Registrazione professionista", "reinvio": "Reinvio dall'account",
    "lettera-operatore": "Lettera dal gestionale",
    "lead-viaggiatore": "Lead viaggiatore", "lead-professionista": "Lead professionista",
    "admin": "Inserito dall'admin", "import": "Importato",
    "sconosciuta": "Sconosciuta",
}

# le porte che il sito mette nell'URL (?porta=...): il suffisso della
# fonte dei form della landing e' una di queste (RB13)
_PORTA_RX = re.compile(r"^[a-z0-9_-]{1,20}$")

# fonti «esatte» → (canale, superficie). Chi ha un suffisso :<porta> ci
# passa lo stesso: si guarda la parte prima dei due punti.
_ESATTE = {
    "cerca-ritiro": ("sito", "cerca-ritiro"),
    "hero": ("sito", "cerca-ritiro"),          # SchedaForm «racconta» della landing
    "home_letter": ("sito", "home"),
    "home": ("sito", "home"),
    "newsletter": ("sito", "landing-cerchio"),
    "landing": ("sito", "landing-cerchio"),    # LeadForm senza context
    "esperienze": ("sito", "esperienze"),
    "blog": ("magazine", "articolo"),
    "meditazioni": ("sound", "meditazioni"),
    "gate_meditazione": ("sound", "meditazioni"),
    "sound": ("sound", "esplora"),
    "invito": ("sound", "esplora"),
    "frequenze": ("sound", "frequenza"),
    "account_signup": ("account", "signup"),
    "signup_passwordless": ("account", "signup"),
    "signup_pro": ("account", "signup-pro"),
    "account_resend": ("account", "reinvio"),
    "gestionale": ("gestionale", "lettera-operatore"),
    "prelaunch_lead": ("prelancio", "lead-viaggiatore"),
    "prelaunch_lead_operator": ("prelancio", "lead-professionista"),
    "lead_operator": ("prelancio", "lead-professionista"),
    "admin": ("manuale", "admin"),
    "manuale": ("manuale", "admin"),
    "import": ("manuale", "import"),
    "checkout": ("commercio", "checkout"),
    "pagina-grazie": ("commercio", "pagina-grazie"),
    "email-ordine": ("commercio", "email-ordine"),
    "email-recensione": ("commercio", "email-recensione"),
    "recensione": ("sito", "recensione"),       # RC1 (2/10): la casella nel modal della recensione
}


def _porta_da_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        qs = parse_qs(urlsplit(url).query)
    except ValueError:
        return None
    for chiave in ("porta", "utm_source"):
        val = (qs.get(chiave) or [""])[0].strip().lower()
        if val and _PORTA_RX.match(val):
            return val
    return None


def classifica(source: Optional[str], porta: Optional[str] = None,
               url: Optional[str] = None) -> dict:
    """Da una fonte grezza a {canale, superficie, dettaglio, porta}.
    Mai un'eccezione: l'ignoto finisce in altro › sconosciuta col
    valore grezzo come dettaglio, cosi' non si perde niente."""
    s = (source or "").strip().lower()
    canale, superficie, dettaglio = "altro", "sconosciuta", (s or None)
    porta_fonte: Optional[str] = None

    testa, _, coda = s.partition(":")

    if testa in _ESATTE and testa not in ("sound", "frequenze"):
        canale, superficie = _ESATTE[testa]
        dettaglio = None
        # il suffisso e' la porta (RB13: «cerca-ritiro:magazine»)
        if coda and _PORTA_RX.match(coda):
            porta_fonte = coda
    elif testa == "sound":
        # sound:esplora:<slug>, sound:lab:<stanza>, sound (nudo)
        canale = "sound"
        sup, _, slug = coda.partition(":")
        if sup in ("esplora", "lab", "meditazioni", "cancello", "frequenza"):
            superficie, dettaglio = sup, (slug or None)
        else:
            superficie, dettaglio = "esplora", (coda or None)
    elif testa == "frequenze":
        canale, superficie, dettaglio = "sound", "frequenza", (coda or None)
    elif testa == "cancello":
        canale, superficie, dettaglio = "sound", "cancello", (coda or None)
    elif testa.startswith("guardia-fq"):
        canale, superficie, dettaglio = "sound", "frequenza", None
    elif testa.startswith("blog_"):
        canale, superficie, dettaglio = "magazine", "cta-categoria", testa[len("blog_"):] or None
        if coda and _PORTA_RX.match(coda):
            porta_fonte = coda
    elif testa.startswith("gate_"):
        canale, superficie, dettaglio = "magazine", "guida", testa[len("gate_"):] or None
        if coda and _PORTA_RX.match(coda):
            porta_fonte = coda
    elif testa.startswith("prelaunch") or testa.startswith("lead"):
        canale = "prelancio"
        superficie = "lead-professionista" if "operator" in s or "professionista" in s else "lead-viaggiatore"
        dettaglio = None

    p = (porta or "").strip().lower()
    porta_finale = p if (p and _PORTA_RX.match(p)) else (porta_fonte or _porta_da_url(url))
    return {"canale": canale, "superficie": superficie,
            "dettaglio": dettaglio, "porta": porta_finale}


_MOBILE_RX = re.compile(r"mobi|android|iphone|ipad|ipod|windows phone", re.I)


def dispositivo(user_agent: Optional[str]) -> Optional[str]:
    """mobile | desktop dallo user-agent; None se non lo sappiamo."""
    ua = (user_agent or "").strip()
    if not ua:
        return None
    return "mobile" if _MOBILE_RX.search(ua) else "desktop"


def pulisci_utm(raw) -> Optional[dict]:
    """Tiene solo source/medium/campaign (+ content/term dal 5/10, MP0:
    l'inserzione e la parola chiave), corte."""
    if not isinstance(raw, dict):
        return None
    out = {}
    for k in ("source", "medium", "campaign", "content", "term"):
        v = raw.get(k) or raw.get(f"utm_{k}")
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()[:80]
    return out or None


# MP0 (5/10/2026) — gli identificativi di clic delle piattaforme pubblicitarie:
# servono alla Conversions API (fbc) e alla regia («questo iscritto viene
# da un clic su un'inserzione»). Solo questi due, corti, mai altro.
_CLICK_RX = re.compile(r"^[A-Za-z0-9_\-.]{4,256}$")


def pulisci_click_ids(raw) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    out = {}
    for k in ("fbclid", "gclid"):
        v = raw.get(k)
        if isinstance(v, str) and _CLICK_RX.match(v.strip()):
            out[k] = v.strip()
    return out or None


# MP0/MP3 — il blocco di tracciamento che il browser manda con un gesto
# (iscrizione, registrazione, contatti): l'event_id condiviso con il pixel
# (dedup lato Meta), i cookie _fbp/_fbc e il consenso marketing letto dal
# banner. Senza consenso marketing si tiene SOLO il flag (false) e nessun
# identificativo: il server non manda niente a Meta per quella persona.
_EVENT_ID_RX = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")
_FB_COOKIE_RX = re.compile(r"^fb\.[0-9]\.[0-9]{6,16}\.[A-Za-z0-9_\-]{1,128}$")


def pulisci_tracciamento(raw) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    marketing = raw.get("marketing") is True
    out = {"marketing": marketing}
    if not marketing:
        return out
    eid = raw.get("event_id")
    if isinstance(eid, str) and _EVENT_ID_RX.match(eid.strip()):
        out["event_id"] = eid.strip()
    for k in ("fbp", "fbc"):
        v = raw.get(k)
        if isinstance(v, str) and _FB_COOKIE_RX.match(v.strip()):
            out[k] = v.strip()
    return out


def provenienza_registrazione(source: str, raw, user_agent: Optional[str]) -> dict:
    """MP0 — il blocco `provenienza` per una REGISTRAZIONE (professionista o
    account cliente), dallo stesso oggetto che il browser costruisce per il
    Cerchio (url, referrer, utm, click_ids, tracciamento). `raw` puo'
    mancare (client vecchio): resta la classificazione dalla fonte."""
    raw = raw if isinstance(raw, dict) else {}
    url = (str(raw.get("url") or "").strip()[:500]) or None
    referrer = (str(raw.get("referrer") or "").strip()[:500]) or None
    utm = pulisci_utm(raw.get("utm"))
    base = classifica(source, None, url)
    if not base.get("porta") and utm and utm.get("source"):
        base["porta"] = utm["source"][:20].lower()
    out = {**base, "url": url, "referrer": referrer, "utm": utm,
           "dispositivo": dispositivo(user_agent)}
    click = pulisci_click_ids(raw.get("click_ids"))
    if click:
        out["click_ids"] = click
    tracc = pulisci_tracciamento(raw.get("tracciamento"))
    if tracc:
        out["tracciamento"] = tracc
    return out


def canali_per_admin() -> list:
    """La tassonomia con le etichette, per le due tendine collegate."""
    return [{"canale": c, "label": ETICHETTE[c],
             "superfici": [{"superficie": s, "label": ETICHETTE[s]} for s in sups]}
            for c, sups in TASSONOMIA.items()]
